import json
import logging
from collections.abc import Callable, Iterable
from pathlib import Path

from pydantic import ValidationError

from app.models.event import GameEvent
from app.models.game import GameState

logger = logging.getLogger(__name__)

Listener = Callable[[GameState | GameEvent], None]


class GameService:
    """Guarda o Game State atual, grava um snapshot a cada mudança e avisa quem está ouvindo."""

    def __init__(self, state: GameState, snapshot_path: Path | None = None) -> None:
        self._state = state
        self._snapshot_path = snapshot_path
        self._listeners: list[Listener] = []

    @classmethod
    def from_file(cls, path: Path) -> "GameService":
        return cls(GameState.model_validate_json(path.read_text(encoding="utf-8")))

    @classmethod
    def restore(cls, snapshot_path: Path, fallback_path: Path) -> "GameService":
        """Retoma do snapshot (ex.: reinício no meio da live); sem ele, parte do fallback."""
        state = None
        if snapshot_path.exists():
            try:
                state = GameState.model_validate_json(snapshot_path.read_text(encoding="utf-8"))
            except ValidationError:
                logger.warning("Snapshot inválido em %s; usando %s", snapshot_path, fallback_path)
        if state is None:
            state = GameState.model_validate_json(fallback_path.read_text(encoding="utf-8"))
        return cls(state, snapshot_path)

    @property
    def state(self) -> GameState:
        return self._state

    def subscribe(self, listener: Listener) -> Callable[[], None]:
        """Registra quem recebe cada novo Game State e cada Game Event. Devolve o cancelamento."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def update(self, state: GameState, events: Iterable[GameEvent] = ()) -> None:
        """Publica o novo estado (só se mudou) e, depois dele, os eventos."""
        if state != self._state:
            self._state = state
            if self._snapshot_path is not None:
                self._save_snapshot(self._snapshot_path)
            self._notify(state)
        for event in events:
            self._notify(event)

    def _notify(self, item: GameState | GameEvent) -> None:
        for listener in list(self._listeners):
            listener(item)

    def _save_snapshot(self, path: Path) -> None:
        # Grava num temporário e troca, para nunca deixar um snapshot pela metade.
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        content = json.dumps(self._state.stored_fields(), indent=2, ensure_ascii=False)
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
