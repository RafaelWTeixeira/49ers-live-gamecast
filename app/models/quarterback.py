from typing import Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

# Cada componente do Passer Rating da NFL fica entre 0 e 2.375.
RATING_COMPONENT_MAX = 2.375


def _clamp(value: float) -> float:
    return max(0.0, min(value, RATING_COMPONENT_MAX))


class QuarterbackStats(BaseModel):
    """Linha de passe do QB no jogo exibido. O Passer Rating é derivado, nunca informado."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    completions: int = Field(default=0, ge=0)
    attempts: int = Field(default=0, ge=0)
    # Jardas de passe podem ser negativas (ex.: passe completo atrás da linha).
    yards: int = 0
    touchdowns: int = Field(default=0, ge=0)
    interceptions: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _counts_fit_the_attempts(self) -> Self:
        # Interceptação é um passe não completado, então os dois juntos não passam das tentativas.
        if self.completions + self.interceptions > self.attempts:
            raise ValueError("completions + interceptions não podem passar de attempts")
        if self.touchdowns > self.completions:
            raise ValueError("touchdowns não podem passar de completions")
        return self

    @computed_field
    @property
    def passer_rating(self) -> float | None:
        """Fórmula oficial da NFL (0 a 158.3); sem tentativas, não há rating."""
        if self.attempts == 0:
            return None
        completion = _clamp((self.completions / self.attempts - 0.3) * 5)
        yards = _clamp((self.yards / self.attempts - 3) * 0.25)
        touchdowns = _clamp(self.touchdowns / self.attempts * 20)
        interceptions = _clamp(RATING_COMPONENT_MAX - self.interceptions / self.attempts * 25)
        return round((completion + yards + touchdowns + interceptions) / 6 * 100, 1)
