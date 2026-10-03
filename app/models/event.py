from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.game import GameState, Side


class GameEventKind(StrEnum):
    TOUCHDOWN = "TOUCHDOWN"
    FIELD_GOAL = "FIELD_GOAL"
    SAFETY = "SAFETY"
    EXTRA_POINT = "EXTRA_POINT"
    TWO_POINT_CONVERSION = "TWO_POINT_CONVERSION"
    TURNOVER = "TURNOVER"
    FLAG = "FLAG"
    TIMEOUT = "TIMEOUT"


POINTS = {
    GameEventKind.TOUCHDOWN: 6,
    GameEventKind.FIELD_GOAL: 3,
    GameEventKind.SAFETY: 2,
    GameEventKind.EXTRA_POINT: 1,
    GameEventKind.TWO_POINT_CONVERSION: 2,
}

# Só a Flag pode não ter dono (ex.: penalidades que se anulam).
OPTIONAL_SIDE = {GameEventKind.FLAG}

FIRST_DOWN_DISTANCE = 10


class GameEvent(BaseModel):
    """Acontecimento pontual: é anunciado ao overlay e não faz parte do Game State."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: GameEventKind
    # Protagonista: quem pontuou (no Safety, a defesa), quem ficou com a bola, quem pediu tempo.
    side: Side | None = None

    @model_validator(mode="after")
    def _side_is_required(self) -> Self:
        if self.side is None and self.kind not in OPTIONAL_SIDE:
            raise ValueError(f"{self.kind} precisa indicar o time (side)")
        return self

    @property
    def points(self) -> int:
        return POINTS.get(self.kind, 0)


def apply_event(state: GameState, event: GameEvent) -> GameState:
    """Efeito de um evento registrado manualmente: soma pontos ou troca a posse."""
    if event.points:
        team = getattr(state, event.side)
        return state.with_changes(
            **{event.side: team.model_copy(update={"score": team.score + event.points})}
        )
    if event.kind == GameEventKind.TURNOVER:
        return state.with_changes(possession=event.side, down=1, distance=FIRST_DOWN_DISTANCE)
    return state
