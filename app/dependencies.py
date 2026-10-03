import os
from functools import lru_cache
from pathlib import Path

from app.models.control import ControlMode
from app.providers.base import Provider
from app.providers.mock_provider import MockProvider
from app.services.game_service import GameService
from app.services.provider_sync import ProviderHealth

ROOT_DIR = Path(__file__).parent.parent
MOCK_GAME_PATH = ROOT_DIR / "mock" / "game.json"
MOCK_PLAYS_PATH = ROOT_DIR / "mock" / "plays.json"
SNAPSHOT_PATH = ROOT_DIR / "data" / "game_state.json"

SYNC_INTERVAL_SECONDS = float(os.getenv("GAMECAST_SYNC_INTERVAL", "3"))
# Modo inicial quando não há snapshot; com snapshot, vale o modo gravado.
DEFAULT_CONTROL_MODE = ControlMode(os.getenv("GAMECAST_CONTROL_MODE", "AUTO").upper())


@lru_cache
def get_game_service() -> GameService:
    return GameService.restore(SNAPSHOT_PATH, MOCK_GAME_PATH, DEFAULT_CONTROL_MODE)


@lru_cache
def get_provider() -> Provider:
    return MockProvider.from_files(MOCK_GAME_PATH, MOCK_PLAYS_PATH)


@lru_cache
def get_provider_health() -> ProviderHealth:
    return ProviderHealth()
