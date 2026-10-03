from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.models.game import Side


class GameEventKind(StrEnum):
    TOUCHDOWN = "TOUCHDOWN"
    FIELD_GOAL = "FIELD_GOAL"
    SAFETY = "SAFETY"
    EXTRA_POINT = "EXTRA_POINT"
    TWO_POINT_CONVERSION = "TWO_POINT_CONVERSION"
    TURNOVER = "TURNOVER"
    FLAG = "FLAG"
    TIMEOUT = "TIMEOUT"


class GameEvent(BaseModel):
    """Acontecimento pontual: é anunciado ao overlay e não faz parte do Game State."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: GameEventKind
    # Time que protagonizou o evento (quem pontuou, quem recuperou a bola, quem pediu tempo).
    side: Side | None = None
