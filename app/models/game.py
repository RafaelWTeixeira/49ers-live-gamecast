from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.models.play import Play
from app.models.team import Team

OVERTIME = 5
MIDFIELD = 50
FEATURED_GOAL_LINE = 0
OPPONENT_GOAL_LINE = 100

Side = Literal["featured", "opponent"]
FieldDirection = Literal["left", "right"]


class GamePhase(StrEnum):
    PRE_GAME = "PRE_GAME"
    LIVE = "LIVE"
    HALFTIME = "HALFTIME"
    FINAL = "FINAL"


class GameState(BaseModel):
    """Fotografia do jogo exibido. Ver GLOSSARY.md e docs/adr/0001."""

    model_config = ConfigDict(extra="forbid")

    phase: GamePhase = GamePhase.PRE_GAME
    quarter: int = Field(default=1, ge=1, le=OVERTIME)
    clock: str = Field(default="15:00", pattern=r"^\d{2}:\d{2}$")

    featured: Team
    opponent: Team

    possession: Side | None = None
    yardline: int | None = Field(default=None, ge=FEATURED_GOAL_LINE, le=OPPONENT_GOAL_LINE)
    down: int | None = Field(default=None, ge=1, le=4)
    distance: int | None = Field(default=None, ge=1, le=99)

    # Field Direction nos quartos ímpares e na prorrogação; Q2 e Q4 são invertidos.
    opening_field_direction: FieldDirection = "left"

    last_play: Play | None = None

    @model_validator(mode="after")
    def _possession_requires_a_complete_drive(self) -> Self:
        if self.possession is not None and None in (self.yardline, self.down, self.distance):
            raise ValueError("com posse de bola, yardline, down e distance são obrigatórios")
        return self

    def stored_fields(self) -> dict:
        """Os campos de entrada, sem os derivados: o que se grava e o que se valida de volta."""
        return self.model_dump(mode="json", exclude=set(type(self).model_computed_fields))

    @computed_field
    @property
    def field_direction(self) -> FieldDirection:
        if self.quarter in (2, 4):
            return "right" if self.opening_field_direction == "left" else "left"
        return self.opening_field_direction

    @computed_field
    @property
    def line_to_gain(self) -> int | None:
        if self.possession is None:
            return None
        if self.possession == "featured":
            return min(self.yardline + self.distance, OPPONENT_GOAL_LINE)
        return max(self.yardline - self.distance, FEATURED_GOAL_LINE)

    @computed_field
    @property
    def goal_to_go(self) -> bool:
        if self.possession is None:
            return False
        target = OPPONENT_GOAL_LINE if self.possession == "featured" else FEATURED_GOAL_LINE
        return self.line_to_gain == target

    @computed_field
    @property
    def field_position_label(self) -> str | None:
        if self.yardline is None:
            return None
        if self.yardline < MIDFIELD:
            return f"{self.featured.abbr} {self.yardline}"
        if self.yardline > MIDFIELD:
            return f"{self.opponent.abbr} {OPPONENT_GOAL_LINE - self.yardline}"
        return str(MIDFIELD)
