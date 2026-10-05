import json
import logging
from collections.abc import Callable, Iterable
from pathlib import Path

from pydantic import ValidationError

from app.models.control import ControlMode
from app.models.event import GameEvent, apply_event
from app.models.game import GamePhase, GameState
from app.providers.base import ProviderUpdate

logger = logging.getLogger(__name__)

Listener = Callable[[GameState | GameEvent], None]

UNDO_LIMIT = 50


class ControlModeError(Exception):
    """Alteração vinda de quem não tem autoridade no Control Mode atual."""


class NothingToUndoError(Exception):
    pass


class GameService:
    """Guarda o Game State e o Control Mode, grava snapshot a cada mudança e avisa os ouvintes.

    Em AUTO só o Provider altera o jogo; em MANUAL, só o operador (docs/adr/0002), e sem
    estatísticas de QB, que ninguém mantém à mão (docs/adr/0004). A Field Direction é do
    operador nos dois modos (docs/adr/0006).
    """

    def __init__(
        self,
        state: GameState,
        snapshot_path: Path | None = None,
        control_mode: ControlMode = ControlMode.AUTO,
    ) -> None:
        self._state = state
        self._snapshot_path = snapshot_path
        self._control_mode = control_mode
        self._listeners: list[Listener] = []
        self._history: list[GameState] = []

    @classmethod
    def from_file(cls, path: Path) -> "GameService":
        return cls(GameState.model_validate_json(path.read_text(encoding="utf-8")))

    @classmethod
    def restore(
        cls,
        snapshot_path: Path,
        fallback_path: Path,
        default_mode: ControlMode = ControlMode.AUTO,
    ) -> "GameService":
        """Retoma do snapshot (ex.: reinício no meio da live); sem ele, parte do fallback."""
        if snapshot_path.exists():
            try:
                snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
                state = GameState.model_validate(snapshot["game"])
                mode = ControlMode(snapshot["control_mode"])
                return cls(state, snapshot_path, mode)
            except (ValueError, KeyError, TypeError, ValidationError):
                logger.warning("Snapshot inválido em %s; usando %s", snapshot_path, fallback_path)
        state = GameState.model_validate_json(fallback_path.read_text(encoding="utf-8"))
        return cls(state, snapshot_path, default_mode)

    @property
    def state(self) -> GameState:
        return self._state

    @property
    def control_mode(self) -> ControlMode:
        return self._control_mode

    @property
    def can_undo(self) -> bool:
        return bool(self._history)

    def subscribe(self, listener: Listener) -> Callable[[], None]:
        """Registra quem recebe cada novo Game State e cada Game Event. Devolve o cancelamento."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def set_control_mode(self, mode: ControlMode) -> None:
        if mode == self._control_mode:
            return
        self._control_mode = mode
        self._history.clear()
        self._save_snapshot()
        if mode == ControlMode.MANUAL:
            # Estatísticas congeladas enganariam: saem até o Provider voltar ao comando.
            self.update(self._state.without_quarterbacks())

    def apply_provider_update(self, update: ProviderUpdate) -> bool:
        """Publica o que veio do Provider, se ele estiver no comando. Devolve se aplicou."""
        if self._control_mode != ControlMode.AUTO:
            return False
        state = update.state
        # O Provider não sabe como a TV mostra o campo: o lado fica o que o operador escolheu,
        # a não ser num jogo novo, que começa do lado padrão.
        if not self._is_new_game(state):
            state = state.with_changes(**self._state.field_directions())
        self.update(state, update.events)
        return True

    def _is_new_game(self, incoming: GameState) -> bool:
        current = self._state
        other_opponent = incoming.opponent.abbr != current.opponent.abbr
        restarted = current.phase == GamePhase.FINAL and incoming.phase != GamePhase.FINAL
        return other_opponent or restarted

    def apply_manual(self, state: GameState, events: Iterable[GameEvent] = ()) -> None:
        self._require_manual()
        state = state.without_quarterbacks()
        if state != self._state:
            self._history = [*self._history, self._state][-UNDO_LIMIT:]
        self.update(state, events)

    def announce_manual(self, event: GameEvent) -> None:
        """Registra um evento pelo painel: aplica o efeito no placar/posse e o anuncia."""
        self._require_manual()
        self.apply_manual(apply_event(self._state, event), [event])

    def flip_field_direction(self) -> None:
        """Inverte a Field Direction do período atual. Vale em qualquer modo; em MANUAL entra no
        desfazer."""
        state = self._state.with_flipped_field_direction()
        if self._control_mode == ControlMode.MANUAL:
            self.apply_manual(state)
        else:
            self.update(state)

    def undo(self) -> None:
        self._require_manual()
        if not self._history:
            raise NothingToUndoError("não há alteração manual para desfazer")
        self.update(self._history.pop())

    def update(self, state: GameState, events: Iterable[GameEvent] = ()) -> None:
        """Publica o novo estado (só se mudou) e, depois dele, os eventos. Não checa o modo."""
        if state != self._state:
            self._state = state
            self._save_snapshot()
            self._notify(state)
        for event in events:
            self._notify(event)

    def _require_manual(self) -> None:
        if self._control_mode != ControlMode.MANUAL:
            raise ControlModeError("o jogo está em modo AUTO; mude para MANUAL para editar")

    def _notify(self, item: GameState | GameEvent) -> None:
        for listener in list(self._listeners):
            listener(item)

    def _save_snapshot(self) -> None:
        if self._snapshot_path is None:
            return
        # Grava num temporário e troca, para nunca deixar um snapshot pela metade.
        self._snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._snapshot_path.with_suffix(".tmp")
        snapshot = {"control_mode": self._control_mode, "game": self._state.stored_fields()}
        temporary.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
        temporary.replace(self._snapshot_path)
