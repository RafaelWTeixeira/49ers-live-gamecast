"""Provider da API pública e não oficial da ESPN (site.api.espn.com). Ver docs/adr/0005.

Duas chamadas por fetch:
- scoreboard: placar, fase, relógio e a situação ao vivo (posse, down & distance, bola,
  última jogada);
- summary: estatísticas de passe (QBs), jogadas e pontuações, de onde saem os Game Events.

Na ESPN o `yardLine` é medido a partir da goal line do time da casa; a Yardline do Game State é
medida a partir do Featured Team (docs/adr/0001).
"""

import gzip
import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx2
from pydantic import ValidationError

from app.models.event import GameEvent, GameEventKind
from app.models.game import OPPONENT_GOAL_LINE, OVERTIME, GamePhase, GameState, Side
from app.models.play import Play
from app.models.quarterback import QuarterbackStats
from app.models.team import Team
from app.providers.base import Provider, ProviderUpdate

logger = logging.getLogger(__name__)

Json = dict[str, Any]

BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/football"
REQUEST_TIMEOUT_SECONDS = 5.0
QUARTER_SECONDS = 15 * 60
FALLBACK_COLORS = ("#333333", "#FFFFFF")

# Jogadas de scrimmage: só nelas as jardas da última jogada fazem sentido para o público.
SCRIMMAGE_PLAY_TYPES = {
    "Rush",
    "Pass Reception",
    "Pass Incompletion",
    "Sack",
    "Rushing Touchdown",
    "Passing Touchdown",
}
# Marcadores do jogo que a ESPN registra como jogada, mas que não são a "última jogada".
MARKER_PLAY_TYPES = {
    "End Period",
    "End of Half",
    "End of Game",
    "End of Regulation",
    "Two-minute warning",
    "Official Timeout",
    "Coin Toss",
}
# Seções do summary que valem gravar; o resto (notícias, odds, vídeos…) só ocupa espaço.
RECORDED_SUMMARY_KEYS = ("header", "boxscore", "drives", "scoringPlays")


# ---------- Tradução para o Game State ----------


@dataclass(frozen=True)
class Matchup:
    """Quem é quem no evento da ESPN, a partir do Featured Team."""

    featured_id: str
    featured_is_home: bool

    def side_of(self, team_id: Any) -> Side:
        return "featured" if str(team_id) == self.featured_id else "opponent"

    def to_yardline(self, espn_yard_line: int) -> int:
        return espn_yard_line if self.featured_is_home else OPPONENT_GOAL_LINE - espn_yard_line


def find_matchup(competition: Json, featured_abbr: str) -> Matchup:
    for competitor in competition["competitors"]:
        if competitor["team"]["abbreviation"].upper() == featured_abbr.upper():
            return Matchup(str(competitor["id"]), competitor["homeAway"] == "home")
    raise ValueError(f"{featured_abbr} não joga o evento {competition.get('id')}")


def _hex_color(value: Any, fallback: str) -> str:
    if isinstance(value, str) and re.fullmatch(r"[0-9A-Fa-f]{6}", value):
        return f"#{value.upper()}"
    return fallback


def _phase(status: Json) -> GamePhase:
    kind = status["type"]
    if kind["state"] == "pre":
        return GamePhase.PRE_GAME
    if kind["state"] == "post":
        return GamePhase.FINAL
    if kind["name"] == "STATUS_HALFTIME":
        return GamePhase.HALFTIME
    return GamePhase.LIVE


def _clock(status: Json, phase: GamePhase) -> str:
    if phase == GamePhase.PRE_GAME:
        return "15:00"
    seconds = int(min(max(float(status.get("clock") or 0), 0), QUARTER_SECONDS))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _drive(situation: Json, matchup: Matchup) -> Json:
    """Posse, bola e down & distance; sem dado completo e válido, o drive fica vazio."""
    team_id = situation.get("possession")
    down, distance, yard_line = (situation.get(k) for k in ("down", "distance", "yardLine"))
    valid = (
        team_id
        and isinstance(down, int)
        and 1 <= down <= 4
        and isinstance(distance, int)
        and 1 <= distance <= 99
        and isinstance(yard_line, int)
        # Bola em jogo nunca fica sobre a goal line; 0 ou 100 é dado provisório da ESPN.
        and 0 < yard_line < OPPONENT_GOAL_LINE
    )
    if not valid:
        return {"possession": None, "yardline": None, "down": None, "distance": None}
    return {
        "possession": matchup.side_of(team_id),
        "yardline": matchup.to_yardline(yard_line),
        "down": down,
        "distance": distance,
    }


def _kind(play: Json) -> str:
    """Tipo da jogada; a ESPN às vezes manda campos nulos."""
    return (play.get("type") or {}).get("text") or ""


def _text(play: Json) -> str:
    return (play.get("text") or "").strip()


def _start_team(play: Json) -> Any:
    return ((play.get("start") or {}).get("team") or {}).get("id")


def _is_marker(play: Json) -> bool:
    return _kind(play) in MARKER_PLAY_TYPES


def _to_play(play: Json | None) -> Play | None:
    if not play or not _text(play):
        return None
    yards = play.get("statYardage")
    meaningful = _kind(play) in SCRIMMAGE_PLAY_TYPES and isinstance(yards, int)
    return Play(description=_text(play), yards=yards if meaningful else None)


def all_plays(summary: Json) -> list[Json]:
    drives = summary.get("drives") or {}
    found = [*(drives.get("previous") or [])]
    if drives.get("current"):
        found.append(drives["current"])
    return [play for drive in found for play in drive.get("plays") or []]


def _passing_line(labels: list[str], athlete: Json) -> QuarterbackStats | None:
    stats = dict(zip(labels, athlete.get("stats") or [], strict=False))
    try:
        completions, attempts = (int(n) for n in stats["C/ATT"].split("/"))
        return QuarterbackStats(
            name=athlete["athlete"]["displayName"],
            completions=completions,
            attempts=attempts,
            yards=int(stats["YDS"]),
            touchdowns=int(stats["TD"]),
            interceptions=int(stats["INT"]),
        )
    except (KeyError, ValueError, ValidationError):
        return None


def quarterbacks(summary: Json) -> dict[str, QuarterbackStats]:
    """QB de cada time (id da ESPN): quem mais tentou passes no jogo."""
    found = {}
    for team in (summary.get("boxscore") or {}).get("players") or []:
        for category in team.get("statistics") or []:
            if category.get("name") != "passing":
                continue
            lines = [_passing_line(category["labels"], a) for a in category.get("athletes") or []]
            lines = [line for line in lines if line is not None]
            if lines:
                found[str(team["team"]["id"])] = max(lines, key=lambda line: line.attempts)
    return found


def _team(competitor: Json, quarterback: QuarterbackStats | None) -> Team:
    team = competitor["team"]
    return Team(
        abbr=team["abbreviation"],
        name=team["name"],
        score=int(competitor.get("score") or 0),
        primary_color=_hex_color(team.get("color"), FALLBACK_COLORS[0]),
        secondary_color=_hex_color(team.get("alternateColor"), FALLBACK_COLORS[1]),
        quarterback=quarterback,
    )


def to_game_state(competition: Json, summary: Json, featured_abbr: str) -> GameState:
    matchup = find_matchup(competition, featured_abbr)
    passers = quarterbacks(summary)
    teams = {
        matchup.side_of(c["id"]): _team(c, passers.get(str(c["id"])))
        for c in competition["competitors"]
    }
    status = competition["status"]
    phase = _phase(status)
    situation = competition.get("situation") or {}
    candidates = [situation.get("lastPlay"), *reversed(all_plays(summary))]
    last_play = next((p for p in candidates if p and not _is_marker(p)), None)
    return GameState(
        phase=phase,
        quarter=min(max(int(status.get("period") or 1), 1), OVERTIME),
        clock=_clock(status, phase),
        featured=teams["featured"],
        opponent=teams["opponent"],
        last_play=_to_play(last_play) if phase != GamePhase.PRE_GAME else None,
        **(_drive(situation, matchup) if phase == GamePhase.LIVE else _drive({}, matchup)),
    )


# ---------- Game Events ----------


def _end_team(play: Json) -> Any:
    return ((play.get("end") or {}).get("team") or {}).get("id")


def _is_turnover(play: Json) -> bool:
    # Nem sempre a ESPN marca isTurnover (ex.: fumble no retorno de punt veio sem a marca).
    kind = _kind(play)
    return bool(
        play.get("isTurnover")
        or "(Opponent)" in kind
        or "Interception" in kind
        or kind.startswith("Blocked")
    )


def _turnover_side(play: Json, matchup: Matchup) -> Side | None:
    """Quem ficou com a bola: end.team. Sem ele, deduz pelo tipo da jogada."""
    if not _is_turnover(play):
        return None
    if _end_team(play) is not None:
        return matchup.side_of(_end_team(play))
    if _start_team(play) is None:
        return None
    starting = matchup.side_of(_start_team(play))
    # Em punt/kickoff quem começa com a bola é quem chuta: recuperar é ficar com ela.
    if "Punt" in _kind(play) or "Kickoff" in _kind(play):
        return starting
    return "opponent" if starting == "featured" else "featured"


def _side_named_in_text(play: Json, pattern: str, featured_abbr: str) -> Side | None:
    """Time citado no texto. A ESPN usa abreviações próprias (ARZ, LA…) e só a do Featured
    Team é confiável, então qualquer outra sigla é o Opponent."""
    match = re.search(pattern, _text(play), re.IGNORECASE)
    if not match:
        return None
    return "featured" if match.group(1).upper() == featured_abbr.upper() else "opponent"


def play_events(play: Json, matchup: Matchup, featured_abbr: str) -> list[GameEvent]:
    events = []
    side = _turnover_side(play, matchup)
    if side:
        events.append(GameEvent(kind=GameEventKind.TURNOVER, side=side))
    if play.get("isPenalty") or "PENALTY" in _text(play).upper():
        penalized = _side_named_in_text(play, r"PENALTY on (\w+)", featured_abbr)
        events.append(GameEvent(kind=GameEventKind.FLAG, side=penalized))
    if _kind(play) == "Timeout":
        # No scoreboard ao vivo, start.team é quem está com a bola, não quem pediu o tempo.
        caller = _side_named_in_text(play, r"Timeout #\d+ by (\w+)", featured_abbr)
        if caller:
            events.append(GameEvent(kind=GameEventKind.TIMEOUT, side=caller))
    return events


def scoring_event(scoring_play: Json, matchup: Matchup) -> GameEvent | None:
    kind = _kind(scoring_play)
    team_id = (scoring_play.get("team") or {}).get("id")
    if team_id is None:
        return None
    side = matchup.side_of(team_id)
    if "Touchdown" in kind:
        return GameEvent(kind=GameEventKind.TOUCHDOWN, side=side)
    if "Field Goal" in kind and "Good" in kind:
        return GameEvent(kind=GameEventKind.FIELD_GOAL, side=side)
    if "Safety" in kind:
        return GameEvent(kind=GameEventKind.SAFETY, side=side)
    return None


# Pontuações do ataque que o scoreboard já mostra ~8s antes do summary: anunciadas por ele.
EARLY_SCORING_TYPES = {
    "Passing Touchdown": GameEventKind.TOUCHDOWN,
    "Rushing Touchdown": GameEventKind.TOUCHDOWN,
    "Field Goal Good": GameEventKind.FIELD_GOAL,
}


def early_scoring_event(last_play: Json, matchup: Matchup) -> GameEvent | None:
    kind = EARLY_SCORING_TYPES.get(_kind(last_play))
    offense = _start_team(last_play)
    if kind is None or offense is None:
        return None
    return GameEvent(kind=kind, side=matchup.side_of(offense))


class EventTracker:
    """Anuncia só o que é novo. A primeira leitura só memoriza: o histórico não vira evento.

    O anúncio sai da última jogada do scoreboard, que chega na hora. O summary pode atrasar
    até um minuto: dele só vêm as pontuações que o scoreboard não anunciou (TD de retorno,
    safety), porque o placar já mudou e o aviso ainda faz sentido. Flags e timeouts atrasados
    só confundiriam. O id de uma pontuação é o mesmo da jogada, então nada sai duas vezes.
    """

    def __init__(self) -> None:
        self._seen: set[str] | None = None

    def new_events(
        self, competition: Json, summary: Json, matchup: Matchup, featured_abbr: str
    ) -> list[GameEvent]:
        last_play = (competition.get("situation") or {}).get("lastPlay") or {}
        play_mark = f"play:{last_play['id']}" if last_play.get("id") is not None else None
        score_marks = {f"score:{s.get('id')}": s for s in summary.get("scoringPlays") or []}
        if self._seen is None:
            self._seen = set(score_marks) | {play_mark} - {None}
            if play_mark:
                self._seen.add(f"score:{last_play['id']}")
            return []

        events = []
        if play_mark and play_mark not in self._seen:
            self._seen.add(play_mark)
            events.extend(play_events(last_play, matchup, featured_abbr))
            early = early_scoring_event(last_play, matchup)
            if early:
                events.append(early)
                self._seen.add(f"score:{last_play['id']}")
        for mark, scoring_play in score_marks.items():
            if mark not in self._seen:
                self._seen.add(mark)
                event = scoring_event(scoring_play, matchup)
                if event:
                    events.append(event)
        return events


# ---------- Respostas atrasadas ----------


def _play_number(play_id: Any) -> int | None:
    # Ids de jogada são o id do evento seguido do número da jogada: crescem ao longo do jogo.
    try:
        return int(play_id)
    except (TypeError, ValueError):
        return None


def competition_progress(competition: Json) -> int | None:
    last_play = (competition.get("situation") or {}).get("lastPlay") or {}
    return _play_number(last_play.get("id"))


def summary_progress(summary: Json) -> int | None:
    numbers = [n for n in (_play_number(p.get("id")) for p in all_plays(summary)) if n is not None]
    return max(numbers, default=None)


class Freshest:
    """Fica com a resposta mais nova de um endpoint: a CDN da ESPN às vezes devolve uma antiga.

    Uma resposta é antiga quando a sua jogada mais recente é anterior à já vista. Correções
    reais (ex.: TD anulado na revisão) vêm junto de uma jogada nova e passam normalmente.
    """

    def __init__(self, progress) -> None:
        self._progress = progress
        self._payload: Json | None = None
        self._mark: int | None = None

    def offer(self, payload: Json) -> Json:
        mark = self._progress(payload)
        if self._payload is not None and None not in (mark, self._mark) and mark < self._mark:
            logger.info("ESPN devolveu uma resposta antiga; mantendo a mais nova")
            return self._payload
        self._payload = payload
        if mark is not None:
            self._mark = mark
        return payload


# ---------- Gravação ----------


class Recorder:
    """Grava cada resposta que mudou (gzip), para reproduzir e depurar o jogo depois."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory
        self._last_digest: str | None = None

    def save(self, competition: Json, summary: Json) -> None:
        content = {
            "competition": competition,
            "summary": {key: summary.get(key) for key in RECORDED_SUMMARY_KEYS},
        }
        digest = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
        if digest == self._last_digest:
            return
        record = {"fetched_at": datetime.now(UTC).isoformat(), **content}
        self._directory.mkdir(parents=True, exist_ok=True)
        path = self._directory / f"{datetime.now(UTC):%Y%m%dT%H%M%S%f}.json.gz"
        path.write_bytes(gzip.compress(json.dumps(record, ensure_ascii=False).encode()))
        self._last_digest = digest


# ---------- Provider ----------


class EspnProvider(Provider):
    def __init__(
        self,
        featured_abbr: str = "SF",
        event_id: str | None = None,
        league: str = "nfl",
        record_root: Path | None = None,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self._featured_abbr = featured_abbr
        self._event_id = event_id
        # Outra liga (ex.: college-football) só serve para testar com jogos ao vivo de outro dia.
        self._league = league
        self._record_root = record_root
        self._transport = transport
        self._client: httpx2.AsyncClient | None = None
        self._recorder: Recorder | None = None
        self._tracker = EventTracker()
        self._competitions = Freshest(competition_progress)
        self._summaries = Freshest(summary_progress)
        self._label: str | None = None

    @property
    def name(self) -> str:
        return f"ESPN {self._label}" if self._label else "ESPN"

    async def fetch(self) -> ProviderUpdate:
        if self._event_id is None:
            self._event_id = await self._discover_event()
        event_id = self._event_id
        raw_summary = await self._get_json("/summary", {"event": event_id})
        raw_competition = await self._find_competition(event_id, raw_summary)
        # Grava o que veio de fato, inclusive respostas antigas: é o retrato fiel da ESPN.
        self._record(event_id, raw_competition, raw_summary)

        summary = self._summaries.offer(raw_summary)
        competition = self._competitions.offer(raw_competition)
        self._label = competition.get("shortName") or self._label
        matchup = find_matchup(competition, self._featured_abbr)
        state = to_game_state(competition, summary, self._featured_abbr)
        events = self._tracker.new_events(competition, summary, matchup, self._featured_abbr)
        return ProviderUpdate(state, tuple(events))

    async def _discover_event(self) -> str:
        """Sem evento configurado: o jogo do Featured Team em andamento ou, senão, o próximo."""
        schedule = await self._get_json(f"/teams/{self._featured_abbr.lower()}/schedule")
        events = schedule.get("events") or []
        by_state: dict[str, list[Json]] = {}
        for event in events:
            state = event["competitions"][0]["status"]["type"]["state"]
            by_state.setdefault(state, []).append(event)
        chosen = (by_state.get("in") or by_state.get("pre") or events[-1:] or [None])[0]
        if chosen is None:
            raise LookupError(f"nenhum jogo de {self._featured_abbr} encontrado na ESPN")
        logger.info("ESPN: usando o evento %s (%s)", chosen["id"], chosen.get("shortName"))
        return str(chosen["id"])

    async def _find_competition(self, event_id: str, summary: Json) -> Json:
        """A situação ao vivo só vem no scoreboard: o da semana atual ou o do dia do jogo."""
        attempts: list[dict[str, str]] = [{}]
        header = (summary.get("header") or {}).get("competitions") or [{}]
        if header[0].get("date"):
            kickoff = datetime.fromisoformat(header[0]["date"].replace("Z", "+00:00"))
            # O scoreboard usa a data dos EUA: um jogo noturno já é "amanhã" em UTC.
            for day in (kickoff, kickoff - timedelta(days=1)):
                attempts.append({"dates": f"{day:%Y%m%d}"})
        for params in attempts:
            scoreboard = await self._get_json("/scoreboard", params)
            for event in scoreboard.get("events") or []:
                if str(event["id"]) == str(event_id):
                    return {**event["competitions"][0], "shortName": event.get("shortName")}
        raise LookupError(f"evento {event_id} não encontrado no scoreboard da ESPN")

    def _record(self, event_id: str, competition: Json, summary: Json) -> None:
        if self._record_root is None:
            return
        if self._recorder is None:
            self._recorder = Recorder(self._record_root / str(event_id))
        try:
            self._recorder.save(competition, summary)
        except OSError:
            # Gravar é bônus: nunca derruba a atualização do jogo.
            logger.exception("Falha ao gravar a resposta da ESPN")

    async def _get_json(self, path: str, params: dict[str, str] | None = None) -> Json:
        if self._client is None:
            self._client = httpx2.AsyncClient(
                base_url=f"{BASE_URL}/{self._league}",
                timeout=REQUEST_TIMEOUT_SECONDS,
                transport=self._transport,
            )
        response = await self._client.get(path, params=params)
        response.raise_for_status()
        return response.json()
