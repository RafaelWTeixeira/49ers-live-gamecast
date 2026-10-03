import asyncio
import logging

from app.providers.base import Provider
from app.services.game_service import GameService

logger = logging.getLogger(__name__)


async def sync_once(provider: Provider, service: GameService) -> bool:
    """Busca o estado no Provider. Se ele falhar, o último Game State continua no ar."""
    try:
        state = await provider.fetch()
    except Exception:
        logger.exception("Provider falhou; mantendo o último Game State")
        return False
    service.update(state)
    return True


async def sync_forever(provider: Provider, service: GameService, interval_seconds: float) -> None:
    while True:
        await sync_once(provider, service)
        await asyncio.sleep(interval_seconds)
