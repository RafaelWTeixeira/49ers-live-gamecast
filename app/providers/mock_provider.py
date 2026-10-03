import json
from pathlib import Path
from typing import Any

from app.models.game import GameState
from app.providers.base import Provider

TEAM_KEYS = ("featured", "opponent")


def apply_play(state: GameState, changes: dict[str, Any]) -> GameState:
    """Aplica as mudanças de uma jogada: times são mesclados campo a campo, o resto substituído."""
    data = state.stored_fields()
    for key, value in changes.items():
        data[key] = {**data[key], **value} if key in TEAM_KEYS else value
    return GameState.model_validate(data)


class MockProvider(Provider):
    """Simula um jogo: cada fetch avança uma jogada; ao fim da lista, o jogo recomeça."""

    def __init__(self, initial: GameState, plays: list[dict[str, Any]]) -> None:
        if not plays:
            raise ValueError("o MockProvider precisa de ao menos uma jogada")
        self._initial = initial
        self._plays = plays
        self._state = initial
        self._next_play = 0

    @classmethod
    def from_files(cls, game_path: Path, plays_path: Path) -> "MockProvider":
        initial = GameState.model_validate_json(game_path.read_text(encoding="utf-8"))
        plays = json.loads(plays_path.read_text(encoding="utf-8"))
        return cls(initial, plays)

    async def fetch(self) -> GameState:
        if self._next_play == len(self._plays):
            self._state, self._next_play = self._initial, 0
        self._state = apply_play(self._state, self._plays[self._next_play])
        self._next_play += 1
        return self._state
