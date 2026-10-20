import asyncio
import logging
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from app.providers.base import Provider, ProviderUpdate
from app.services.game_service import GameService

logger = logging.getLogger(__name__)


@dataclass
class ProviderHealth:
    """Como o Provider respondeu por último; aparece no painel de controle."""

    last_success_at: datetime | None = None
    last_error: str | None = None
    last_error_at: datetime | None = None

    @property
    def healthy(self) -> bool:
        return self.last_success_at is not None and self.last_error is None

    def record_success(self) -> None:
        self.last_success_at = datetime.now(UTC)
        self.last_error = None

    def record_failure(self, error: Exception) -> None:
        self.last_error = f"{type(error).__name__}: {error}"
        self.last_error_at = datetime.now(UTC)


MAX_DELAY_SECONDS = 120
RELEASE_TICK_SECONDS = 0.25


class ProviderDelay:
    """Segura cada atualização do Provider por alguns segundos antes de publicá-la, para o
    Gamecast não adiantar o que a transmissão ainda vai mostrar. A ordem é mantida.

    O operador muda o atraso no painel, e mudar não descarta nada: com menos atraso, o que já
    venceu sai na hora.
    """

    def __init__(self, seconds: float = 0, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._held: deque[tuple[float, ProviderUpdate]] = deque()
        self.seconds = seconds

    @property
    def seconds(self) -> float:
        return self._seconds

    @seconds.setter
    def seconds(self, value: float) -> None:
        if not 0 <= value <= MAX_DELAY_SECONDS:
            raise ValueError(f"o atraso vai de 0 a {MAX_DELAY_SECONDS} segundos")
        self._seconds = value

    @property
    def pending(self) -> int:
        return len(self._held)

    def hold(self, update: ProviderUpdate) -> None:
        self._held.append((self._clock(), update))

    def due(self) -> list[ProviderUpdate]:
        """Tira da fila, em ordem, as atualizações que já esperaram o atraso."""
        deadline = self._clock() - self._seconds
        released = []
        while self._held and self._held[0][0] <= deadline:
            released.append(self._held.popleft()[1])
        return released


def publish_due(delay: ProviderDelay, service: GameService) -> bool:
    """Publica o que venceu o atraso. Devolve se alguma atualização foi aplicada."""
    applied = False
    for update in delay.due():
        applied = service.apply_provider_update(update) or applied
    return applied


async def sync_once(
    provider: Provider,
    service: GameService,
    health: ProviderHealth,
    delay: ProviderDelay | None = None,
) -> bool:
    """Busca o Provider e publica (depois do atraso, se houver), se ele estiver no comando. Se
    falhar, o último estado fica.

    Em MANUAL o Provider continua sendo consultado só para o painel saber se ele está de pé.
    """
    try:
        update = await provider.fetch()
    except Exception as error:
        logger.exception("Provider falhou; mantendo o último Game State")
        health.record_failure(error)
        return False
    health.record_success()
    if delay is None:
        return service.apply_provider_update(update)
    delay.hold(update)
    return publish_due(delay, service)


async def sync_forever(
    provider: Provider,
    service: GameService,
    health: ProviderHealth,
    interval_seconds: float,
    delay: ProviderDelay,
) -> None:
    while True:
        await sync_once(provider, service, health, delay)
        await asyncio.sleep(interval_seconds)


async def release_forever(delay: ProviderDelay, service: GameService) -> None:
    """Publica o que vence o atraso entre uma consulta e outra, sem esperar a próxima."""
    while True:
        await asyncio.sleep(RELEASE_TICK_SECONDS)
        publish_due(delay, service)
