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

# Campos com a Field Direction de cada período: são do operador (docs/adr/0006).
FIELD_DIRECTION_FIELDS = (
    "opening_field_direction",
    "second_half_field_direction",
    "overtime_field_direction",
)


def opposite(direction: FieldDirection) -> FieldDirection:
    return "right" if direction == "left" else "left"


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

    # Field Direction no início de cada período (docs/adr/0006). Os times trocam de lado do Q1
    # para o Q2 e do Q3 para o Q4; no intervalo e na prorrogação os lados são escolhidos de
    # novo. Sem escolha do operador, o Q3 mantém o lado do Q2 e a prorrogação, o do Q4.
    opening_field_direction: FieldDirection = "left"
    second_half_field_direction: FieldDirection | None = None
    overtime_field_direction: FieldDirection | None = None

    last_play: Play | None = None

    @model_validator(mode="after")
    def _possession_requires_a_complete_drive(self) -> Self:
        if self.possession is not None and None in (self.yardline, self.down, self.distance):
            raise ValueError("com posse de bola, yardline, down e distance são obrigatórios")
        return self

    def stored_fields(self) -> dict:
        """Os campos de entrada, sem os derivados: o que se grava e o que se valida de volta."""
        return self.model_dump(mode="json", exclude_computed_fields=True)

    def with_changes(self, **changes) -> "GameState":
        """Cópia com os campos alterados, validada de novo (model_copy não valida)."""
        stored = self.stored_fields()
        for key, value in changes.items():
            if isinstance(value, BaseModel):
                value = value.model_dump(mode="json", exclude_computed_fields=True)
            stored[key] = value
        return GameState.model_validate(stored)

    def without_quarterbacks(self) -> "GameState":
        """Cópia sem as estatísticas de QB, que só o Provider mantém (docs/adr/0004)."""
        return self.with_changes(
            featured=self.featured.model_copy(update={"quarterback": None}),
            opponent=self.opponent.model_copy(update={"quarterback": None}),
        )

    def _period_start_directions(self) -> dict[str, FieldDirection]:
        """Field Direction no início de cada período: Q1, Q3 e prorrogação."""
        first_half = self.opening_field_direction
        second_half = self.second_half_field_direction or opposite(first_half)
        overtime = self.overtime_field_direction or opposite(second_half)
        return {
            "opening_field_direction": first_half,
            "second_half_field_direction": second_half,
            "overtime_field_direction": overtime,
        }

    def _current_period_field(self) -> str:
        if self.quarter <= 2:
            return "opening_field_direction"
        if self.quarter <= 4:
            return "second_half_field_direction"
        return "overtime_field_direction"

    def field_directions(self) -> dict[str, FieldDirection | None]:
        """Os campos de Field Direction como estão, para copiar de um estado para outro."""
        return {name: getattr(self, name) for name in FIELD_DIRECTION_FIELDS}

    def with_flipped_field_direction(self) -> "GameState":
        """Inverte o lado do período atual (1º tempo, 2º tempo ou prorrogação), só dele."""
        field = self._current_period_field()
        return self.with_changes(**{field: opposite(self._period_start_directions()[field])})

    @computed_field
    @property
    def field_direction(self) -> FieldDirection:
        start = self._period_start_directions()[self._current_period_field()]
        return opposite(start) if self.quarter in (2, 4) else start

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
