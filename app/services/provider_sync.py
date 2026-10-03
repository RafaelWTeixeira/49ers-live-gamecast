import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from app.providers.base import Provider
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


async def sync_once(provider: Provider, service: GameService, health: ProviderHealth) -> bool:
    """Busca o Provider e publica, se ele estiver no comando. Se falhar, o último estado fica.

    Em MANUAL o Provider continua sendo consultado só para o painel saber se ele está de pé.
    """
    try:
        update = await provider.fetch()
    except Exception as error:
        logger.exception("Provider falhou; mantendo o último Game State")
        health.record_failure(error)
        return False
    health.record_success()
    return service.apply_provider_update(update)


async def sync_forever(
    provider: Provider, service: GameService, health: ProviderHealth, interval_seconds: float
) -> None:
    while True:
        await sync_once(provider, service, health)
        await asyncio.sleep(interval_seconds)
