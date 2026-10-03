from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models.event import GameEvent
from app.models.game import GameState


@dataclass(frozen=True)
class ProviderUpdate:
    state: GameState
    events: tuple[GameEvent, ...] = ()


class Provider(ABC):
    """Fonte de dados de jogo. Cada implementação traduz a sua fonte para o Game State."""

    @abstractmethod
    async def fetch(self) -> ProviderUpdate:
        """Devolve o Game State mais recente e os eventos desde o último fetch.

        Levanta exceção se a fonte falhar.
        """
