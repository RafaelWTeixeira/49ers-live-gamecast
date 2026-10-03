from abc import ABC, abstractmethod

from app.models.game import GameState


class Provider(ABC):
    """Fonte de dados de jogo. Cada implementação traduz a sua fonte para o Game State."""

    @abstractmethod
    async def fetch(self) -> GameState:
        """Devolve o Game State mais recente da fonte. Levanta exceção se a fonte falhar."""
