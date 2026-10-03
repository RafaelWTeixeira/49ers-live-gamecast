from pathlib import Path

from app.models.game import GameState


class GameService:
    """Guarda o Game State atual; único ponto de leitura e (futuramente) escrita."""

    def __init__(self, state: GameState) -> None:
        self._state = state

    @classmethod
    def from_file(cls, path: Path) -> "GameService":
        return cls(GameState.model_validate_json(path.read_text(encoding="utf-8")))

    @property
    def state(self) -> GameState:
        return self._state
