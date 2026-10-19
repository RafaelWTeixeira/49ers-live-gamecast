import asyncio
import gzip
import json
from pathlib import Path

import httpx2
import pytest

from app.models.event import GameEvent, GameEventKind
from app.models.game import GamePhase
from app.providers.espn_provider import (
    EspnProvider,
    EventTracker,
    Freshest,
    Recorder,
    competition_progress,
    find_matchup,
    to_game_state,
)

FIXTURES = Path(__file__).parent / "fixtures" / "espn"
SF_ID, DEN_ID = "25", "7"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def competitor(team_id, abbr, name, color, alternate, home_away, score):
    team = {"id": team_id, "abbreviation": abbr, "name": name}
    team |= {"color": color, "alternateColor": alternate}
    return {"id": team_id, "homeAway": home_away, "score": score, "team": team}


def competition(
    state="in",
    name="STATUS_IN_PROGRESS",
    period=2,
    clock=522.0,
    situation=None,
    sf_home=True,
    sf_score="7",
    den_score="3",
):
    return {
        "id": "1",
        "status": {"clock": clock, "period": period, "type": {"state": state, "name": name}},
        "competitors": [
            competitor(
                SF_ID, "SF", "49ers", "aa0000", "b3995d", "home" if sf_home else "away", sf_score
            ),
            competitor(
                DEN_ID,
                "DEN",
                "Broncos",
                "0a2343",
                "fc4c02",
                "away" if sf_home else "home",
                den_score,
            ),
        ],
        "situation": situation or {},
    }


def play(play_id, kind, team_id, text="", **extra):
    return {
        "id": str(play_id),
        "type": {"text": kind},
        "text": text,
        "start": {"team": {"id": team_id}},
    } | extra


def summary(plays=(), scoring=(), passing=()):
    return {
        "drives": {"previous": [{"plays": list(plays)}]},
        "scoringPlays": list(scoring),
        "boxscore": {"players": list(passing)},
    }


def passing(team_id, *athletes):
    labels = ["C/ATT", "YDS", "AVG", "TD", "INT", "SACKS", "QBR", "RTG"]
    lines = [{"athlete": {"displayName": name}, "stats": stats} for name, stats in athletes]
    return {
        "team": {"id": team_id},
        "statistics": [{"name": "passing", "labels": labels, "athletes": lines}],
    }


def drive_situation(possession=SF_ID, down=2, distance=6, yard_line=66, **extra):
    return {
        "possession": possession,
        "down": down,
        "distance": distance,
        "yardLine": yard_line,
    } | extra


class TestGameStateFromARealGame:
    def setup_method(self):
        scoreboard = load("scoreboard_ari_at_sf_final.json")
        self.state = to_game_state(
            scoreboard["events"][0]["competitions"][0], load("summary_ari_at_sf_final.json"), "SF"
        )

    def test_final_score_and_teams(self):
        assert self.state.phase == GamePhase.FINAL
        assert (self.state.featured.abbr, self.state.featured.score) == ("SF", 36)
        assert (self.state.opponent.abbr, self.state.opponent.score) == ("ARI", 30)
        assert self.state.featured.primary_color == "#AA0000"

    def test_quarterbacks_match_the_espn_rating(self):
        assert self.state.featured.quarterback.name == "Brock Purdy"
        assert self.state.featured.quarterback.passer_rating == 133.8
        assert self.state.opponent.quarterback.passer_rating == 98.2

    def test_last_play_skips_the_end_of_game_marker(self):
        assert self.state.last_play.description == "B.Purdy kneels to ARZ 46 for -1 yards."
        assert self.state.last_play.yards == -1

    def test_no_drive_after_the_game(self):
        assert self.state.possession is None


class TestSituation:
    def test_featured_team_at_home_keeps_the_espn_yard_line(self):
        state = to_game_state(competition(situation=drive_situation()), summary(), "SF")

        assert (state.possession, state.yardline, state.down, state.distance) == (
            "featured",
            66,
            2,
            6,
        )
        assert state.field_position_label == "DEN 34"

    def test_featured_team_away_mirrors_the_yard_line(self):
        state = to_game_state(
            competition(situation=drive_situation(), sf_home=False), summary(), "SF"
        )

        assert state.yardline == 34
        assert state.field_position_label == "SF 34"

    def test_opponent_possession(self):
        situation = drive_situation(possession=DEN_ID, down=1, distance=10, yard_line=75)

        state = to_game_state(competition(situation=situation), summary(), "SF")

        assert (state.possession, state.line_to_gain) == ("opponent", 65)

    @pytest.mark.parametrize(
        "situation",
        [
            {},
            drive_situation(possession=None),
            drive_situation(down=0),
            drive_situation(distance=0),
            drive_situation(yard_line=None),
            drive_situation(yard_line=0),
            drive_situation(yard_line=100),
        ],
    )
    def test_incomplete_situation_hides_the_drive(self, situation):
        state = to_game_state(competition(situation=situation), summary(), "SF")

        assert state.possession is None

    def test_clock_and_quarter(self):
        state = to_game_state(competition(period=3, clock=522.0), summary(), "SF")

        assert (state.phase, state.quarter, state.clock) == (GamePhase.LIVE, 3, "08:42")

    def test_overtime_beyond_the_first_is_still_overtime(self):
        assert to_game_state(competition(period=6), summary(), "SF").quarter == 5

    def test_pre_game(self):
        state = to_game_state(
            competition(state="pre", name="STATUS_SCHEDULED", period=0, clock=0), summary(), "SF"
        )

        assert (state.phase, state.quarter, state.clock, state.last_play) == (
            GamePhase.PRE_GAME,
            1,
            "15:00",
            None,
        )

    def test_halftime_has_no_drive(self):
        halftime = competition(name="STATUS_HALFTIME", clock=0, situation=drive_situation())

        state = to_game_state(halftime, summary(), "SF")

        assert state.phase == GamePhase.HALFTIME
        assert state.possession is None

    def test_invalid_colors_fall_back(self):
        game = competition()
        game["competitors"][1]["team"]["color"] = None

        assert to_game_state(game, summary(), "SF").opponent.primary_color == "#333333"

    def test_featured_team_must_play_the_game(self):
        with pytest.raises(ValueError):
            to_game_state(competition(), summary(), "KC")


class TestLastPlay:
    def test_scrimmage_plays_carry_yards(self):
        last = play(10, "Rush", SF_ID, "C.McCaffrey up the middle for 6 yards", statYardage=6)

        state = to_game_state(competition(situation={"lastPlay": last}), summary(), "SF")

        assert (state.last_play.description, state.last_play.yards) == (last["text"], 6)

    def test_other_plays_have_no_yards(self):
        last = play(10, "Kickoff", DEN_ID, "W.Lutz kicks 65 yards", statYardage=65)

        assert (
            to_game_state(
                competition(situation={"lastPlay": last}), summary(), "SF"
            ).last_play.yards
            is None
        )

    def test_null_fields_from_espn_do_not_break_the_update(self):
        broken = {"id": "10", "type": None, "text": None, "start": None}
        game = live(broken)

        state = to_game_state(game, summary([broken]), "SF")
        events = EventTracker().new_events(game, summary([broken]), find_matchup(game, "SF"), "SF")

        assert (state.last_play, events) == (None, [])

    def test_markers_fall_back_to_the_last_real_play(self):
        marker = play(11, "End Period", SF_ID, "END QUARTER 1")
        real = play(
            10, "Pass Reception", SF_ID, "B.Purdy pass to G.Kittle for 8 yards", statYardage=8
        )

        state = to_game_state(
            competition(situation={"lastPlay": marker}), summary([real, marker]), "SF"
        )

        assert state.last_play.description == real["text"]


class TestQuarterbacks:
    def test_the_passer_with_most_attempts_is_the_qb(self):
        box = passing(
            SF_ID,
            ("Brock Purdy", ["17/24", "237", "9.9", "2", "0", "1-6", "80.0", "130.0"]),
            ("Christian McCaffrey", ["1/1", "12", "12.0", "0", "0", "0-0", "0", "118.8"]),
        )

        state = to_game_state(competition(), summary(passing=[box]), "SF")

        assert state.featured.quarterback.name == "Brock Purdy"
        assert state.opponent.quarterback is None

    def test_unreadable_lines_are_ignored(self):
        box = passing(
            SF_ID, ("Brock Purdy", ["--", "237", "9.9", "2", "0", "1-6", "80.0", "130.0"])
        )

        assert (
            to_game_state(competition(), summary(passing=[box]), "SF").featured.quarterback is None
        )


def live(last_play=None):
    return competition(situation={"lastPlay": last_play} if last_play else None)


def events_after(last_play=None, scoring=()):
    """Primeira leitura vazia (só memoriza) e depois a leitura com as novidades."""
    tracker = EventTracker()
    matchup = find_matchup(competition(), "SF")
    tracker.new_events(live(), summary(), matchup, "SF")
    return tracker.new_events(live(last_play), summary(scoring=scoring), matchup, "SF")


class TestEvents:
    def test_history_on_the_first_read_is_not_announced(self):
        intercepted = play(1, "Pass Interception Return", DEN_ID, isTurnover=True)
        scoring = {"id": "9", "type": {"text": "Passing Touchdown"}, "team": {"id": SF_ID}}
        game = live(intercepted)

        events = EventTracker().new_events(
            game, summary(scoring=[scoring]), find_matchup(game, "SF"), "SF"
        )

        assert events == []

    def test_interception_goes_to_the_defense(self):
        events = events_after(play(1, "Pass Interception Return", DEN_ID, isTurnover=True))

        assert events == [GameEvent(kind=GameEventKind.TURNOVER, side="featured")]

    def test_muffed_punt_goes_to_the_kicking_team_even_without_the_flag(self):
        events = events_after(play(1, "Muffed Punt Recovery (Opponent)", DEN_ID, isTurnover=False))

        assert events == [GameEvent(kind=GameEventKind.TURNOVER, side="opponent")]

    def test_timeout_belongs_to_the_team_that_called_it(self):
        events = events_after(play(1, "Timeout", DEN_ID, "Timeout #1 by DEN at 02:56."))

        assert events == [GameEvent(kind=GameEventKind.TIMEOUT, side="opponent")]

    @pytest.mark.parametrize(
        ("text", "side"),
        [
            ("PENALTY on SF-C.McKivitz, False Start, 5 yards", "featured"),
            ("PENALTY on ARZ-I.Adams, False Start, 5 yards", "opponent"),
            ("Penalty declined", None),
        ],
    )
    def test_flag_names_the_penalized_team_when_it_can(self, text, side):
        events = events_after(play(1, "Penalty", SF_ID, text, isPenalty=True))

        assert events == [GameEvent(kind=GameEventKind.FLAG, side=side)]

    @pytest.mark.parametrize(
        ("kind", "event"),
        [
            ("Passing Touchdown", GameEventKind.TOUCHDOWN),
            ("Interception Return Touchdown", GameEventKind.TOUCHDOWN),
            ("Field Goal Good", GameEventKind.FIELD_GOAL),
            ("Safety", GameEventKind.SAFETY),
        ],
    )
    def test_scoring_plays_from_the_summary(self, kind, event):
        scoring = {"id": "9", "type": {"text": kind}, "team": {"id": DEN_ID}}

        assert events_after(scoring=[scoring]) == [GameEvent(kind=event, side="opponent")]

    def test_offensive_score_is_announced_early_and_only_once(self):
        touchdown = play(9, "Passing Touchdown", SF_ID, "B.Purdy pass to G.Kittle, TOUCHDOWN")
        tracker = EventTracker()
        matchup = find_matchup(competition(), "SF")
        tracker.new_events(live(), summary(), matchup, "SF")

        early = tracker.new_events(live(touchdown), summary(), matchup, "SF")
        scoring = {"id": "9", "type": {"text": "Passing Touchdown"}, "team": {"id": SF_ID}}
        later = tracker.new_events(live(touchdown), summary(scoring=[scoring]), matchup, "SF")

        assert early == [GameEvent(kind=GameEventKind.TOUCHDOWN, side="featured")]
        assert later == []

    def test_plays_already_seen_are_not_repeated(self):
        tracker = EventTracker()
        matchup = find_matchup(competition(), "SF")
        timeout = play(1, "Timeout", SF_ID)
        tracker.new_events(live(), summary(), matchup, "SF")
        tracker.new_events(live(timeout), summary(), matchup, "SF")

        assert tracker.new_events(live(timeout), summary(), matchup, "SF") == []

    def test_late_plays_from_the_summary_are_not_announced(self):
        late_flag = play(1, "Penalty", SF_ID, "PENALTY on SF-C.McKivitz", isPenalty=True)
        tracker = EventTracker()
        matchup = find_matchup(competition(), "SF")
        tracker.new_events(live(), summary(), matchup, "SF")

        assert tracker.new_events(live(), summary([late_flag]), matchup, "SF") == []

    def test_penalty_inside_a_scrimmage_play(self):
        run = play(1, "Rush", DEN_ID, "J.Williams for 4 yards. PENALTY on DEN-G.Bolles, Holding")

        assert events_after(run) == [GameEvent(kind=GameEventKind.FLAG, side="opponent")]

    def test_score_not_announced_by_the_scoreboard_comes_from_the_summary(self):
        safety = play(9, "Safety", DEN_ID, "B.Nix sacked in the end zone, SAFETY")
        scoring = {"id": "9", "type": {"text": "Safety"}, "team": {"id": SF_ID}}
        tracker = EventTracker()
        matchup = find_matchup(competition(), "SF")
        tracker.new_events(live(), summary(), matchup, "SF")

        first = tracker.new_events(live(safety), summary(), matchup, "SF")
        later = tracker.new_events(live(safety), summary(scoring=[scoring]), matchup, "SF")

        assert first == []
        assert later == [GameEvent(kind=GameEventKind.SAFETY, side="featured")]


class TestFreshest:
    def test_ignores_a_response_older_than_the_one_already_seen(self):
        freshest = Freshest(competition_progress)
        newer = competition(
            sf_score="14", situation={"lastPlay": play(401872992321, "Rush", SF_ID)}
        )
        older = competition(sf_score="7", situation={"lastPlay": play(401872992315, "Rush", SF_ID)})

        freshest.offer(newer)

        assert freshest.offer(older) is newer

    def test_accepts_newer_and_unmarked_responses(self):
        freshest = Freshest(competition_progress)
        freshest.offer(competition(situation={"lastPlay": play(401872992315, "Rush", SF_ID)}))
        newer = competition(situation={"lastPlay": play(401872992321, "Rush", SF_ID)})
        halftime = competition(name="STATUS_HALFTIME")

        assert freshest.offer(newer) is newer
        assert freshest.offer(halftime) is halftime


class TestRecorder:
    def test_writes_only_responses_that_changed(self, tmp_path):
        recorder = Recorder(tmp_path)

        recorder.save(competition(), summary())
        recorder.save(competition(), summary())
        recorder.save(competition(sf_score="14"), summary())

        files = sorted(tmp_path.glob("*.json.gz"))
        assert len(files) == 2
        record = json.loads(gzip.decompress(files[-1].read_bytes()))
        assert record["competition"]["competitors"][0]["score"] == "14"


def espn_api(*, scoreboards, summary_body=None, schedule=None):
    """Transporte falso da ESPN; cada chamada ao scoreboard devolve o próximo da lista."""
    remaining = list(scoreboards)

    def handle(request: httpx2.Request) -> httpx2.Response:
        path = request.url.path
        if path.endswith("/scoreboard"):
            body = remaining.pop(0) if len(remaining) > 1 else remaining[0]
            return httpx2.Response(200, json=body)
        if path.endswith("/summary"):
            return httpx2.Response(200, json=summary_body or summary())
        if path.endswith("/teams/sf/schedule"):
            return httpx2.Response(200, json=schedule)
        return httpx2.Response(404)

    return httpx2.MockTransport(handle)


def scoreboard_with(game, event_id="401872975", short_name="DEN @ SF"):
    return {"events": [{"id": event_id, "shortName": short_name, "competitions": [game]}]}


def schedule_event(event_id, state):
    return {
        "id": event_id,
        "shortName": "X",
        "competitions": [{"status": {"type": {"state": state}}}],
    }


class TestEspnProvider:
    def test_discovers_the_game_of_the_featured_team(self):
        schedule = {
            "events": [
                schedule_event("401872958", "post"),
                schedule_event("401872975", "pre"),
                schedule_event("401872992", "pre"),
            ]
        }
        transport = espn_api(scoreboards=[scoreboard_with(competition())], schedule=schedule)
        provider = EspnProvider(transport=transport)

        update = asyncio.run(provider.fetch())

        assert provider.name == "ESPN DEN @ SF"
        assert update.state.featured.score == 7

    def test_a_stale_scoreboard_does_not_take_points_back(self):
        newer = competition(
            sf_score="14", situation={"lastPlay": play(401872992321, "Rush", SF_ID)}
        )
        older = competition(sf_score="7", situation={"lastPlay": play(401872992315, "Rush", SF_ID)})
        transport = espn_api(scoreboards=[scoreboard_with(newer), scoreboard_with(older)])
        provider = EspnProvider(event_id="401872975", transport=transport)

        async def two_fetches():
            await provider.fetch()
            return await provider.fetch()

        assert asyncio.run(two_fetches()).state.featured.score == 14

    def test_records_responses(self, tmp_path):
        transport = espn_api(scoreboards=[scoreboard_with(competition())])
        provider = EspnProvider(event_id="401872975", record_root=tmp_path, transport=transport)

        asyncio.run(provider.fetch())

        assert len(list((tmp_path / "401872975").glob("*.json.gz"))) == 1

    def test_http_errors_reach_the_sync_loop(self):
        transport = httpx2.MockTransport(lambda request: httpx2.Response(503))
        provider = EspnProvider(event_id="401872975", transport=transport)

        with pytest.raises(httpx2.HTTPStatusError):
            asyncio.run(provider.fetch())


class TestEventsFromTheDenAtSfGame:
    """Jogadas reais do DEN @ SF (04/10/2026) que saíram erradas na primeira live."""

    PLAYS = load("last_plays_den_at_sf.json")

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            # No scoreboard ao vivo, start.team do timeout é quem está com a bola.
            ("timeout_sf_with_den_ball", GameEvent(kind=GameEventKind.TIMEOUT, side="featured")),
            ("timeout_den", GameEvent(kind=GameEventKind.TIMEOUT, side="opponent")),
            # FG bloqueado é turnover, mas sem "(Opponent)" no tipo nem a marca no scoreboard.
            ("blocked_field_goal", GameEvent(kind=GameEventKind.TURNOVER, side="opponent")),
            # Fumble no retorno do punt recuperado por quem chutou: fica com o SF.
            (
                "punt_fumble_recovered_by_kicking_team",
                GameEvent(kind=GameEventKind.TURNOVER, side="featured"),
            ),
            # "Penalty on" em minúsculas.
            ("declined_penalty_lowercase", GameEvent(kind=GameEventKind.FLAG, side="featured")),
            ("defensive_penalty_sf", GameEvent(kind=GameEventKind.FLAG, side="featured")),
        ],
    )
    def test_announces_the_right_event_and_team(self, name, expected):
        assert events_after(self.PLAYS[name]) == [expected]


class TestFreshestWithTheSeaGame:
    """SF @ SEA (11/10/2026): o extra point veio com id negativo e travava o jogo."""

    def test_extra_point_with_a_negative_id_is_not_stale(self):
        freshest = Freshest(competition_progress)
        touchdown = competition(
            sf_score="6", situation={"lastPlay": play(401872992318, "Passing Touchdown", SF_ID)}
        )
        extra_point = competition(
            sf_score="7", situation={"lastPlay": play(-446877, "Extra Point Good", SF_ID)}
        )
        kickoff = competition(
            sf_score="7", situation={"lastPlay": play(401872992359, "Kickoff", SF_ID)}
        )

        freshest.offer(touchdown)

        assert freshest.offer(extra_point) is extra_point
        assert freshest.offer(kickoff) is kickoff

    def test_older_real_play_is_still_stale_after_the_extra_point(self):
        freshest = Freshest(competition_progress)
        newer = competition(situation={"lastPlay": play(401872992318, "Passing Touchdown", SF_ID)})
        freshest.offer(newer)
        freshest.offer(
            competition(situation={"lastPlay": play(-446877, "Extra Point Good", SF_ID)})
        )
        older = competition(situation={"lastPlay": play(401872992283, "Pass Reception", SF_ID)})

        assert freshest.offer(older) is not older


class TestEventsWhenTheSummaryArrivesFirst:
    """SF @ SEA (11/10/2026): o summary trouxe o FG antes do scoreboard e ele saiu duas vezes."""

    def test_score_announced_by_the_summary_is_not_repeated_by_the_scoreboard(self):
        field_goal = play(
            4018729923081, "Field Goal Good", DEN_ID, "J.Myers 48 yard field goal is GOOD"
        )
        scoring = {
            "id": "4018729923081",
            "type": {"text": "Field Goal Good"},
            "team": {"id": DEN_ID},
        }
        tracker = EventTracker()
        matchup = find_matchup(competition(), "SF")
        tracker.new_events(live(), summary(), matchup, "SF")

        from_summary = tracker.new_events(live(), summary(scoring=[scoring]), matchup, "SF")
        from_scoreboard = tracker.new_events(
            live(field_goal), summary(scoring=[scoring]), matchup, "SF"
        )

        assert from_summary == [GameEvent(kind=GameEventKind.FIELD_GOAL, side="opponent")]
        assert from_scoreboard == []
