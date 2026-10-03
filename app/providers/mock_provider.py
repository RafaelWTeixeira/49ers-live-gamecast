import json
from pathlib import Path
from typing import Any

from app.models.event import GameEvent
from app.models.game import GameState
from app.providers.base import Provider, ProviderUpdate

EVENTS_KEY = "events"


def merge(base: dict[str, Any], changes: dict[str, Any]) -> dict[str, Any]:
    """Mescla objetos campo a campo (ex.: só o placar de um time, só as jardas do QB)."""
    merged = dict(base)
    for key, value in changes.items():
        current = merged.get(key)
        both_objects = isinstance(current, dict) and isinstance(value, dict)
        merged[key] = merge(current, value) if both_objects else value
    return merged


def apply_play(state: GameState, changes: dict[str, Any]) -> GameState:
    """Aplica as mudanças de uma jogada: objetos são mesclados, valores simples substituídos."""
    play = {key: value for key, value in changes.items() if key != EVENTS_KEY}
    return GameState.model_validate(merge(state.stored_fields(), play))


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

    async def fetch(self) -> ProviderUpdate:
        if self._next_play == len(self._plays):
            self._state, self._next_play = self._initial, 0
        play = self._plays[self._next_play]
        self._state = apply_play(self._state, play)
        self._next_play += 1
        events = tuple(GameEvent.model_validate(e) for e in play.get(EVENTS_KEY, []))
        return ProviderUpdate(self._state, events)
