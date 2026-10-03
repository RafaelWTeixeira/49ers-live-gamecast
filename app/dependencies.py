import os
from functools import lru_cache
from pathlib import Path

from app.providers.base import Provider
from app.providers.mock_provider import MockProvider
from app.services.game_service import GameService

ROOT_DIR = Path(__file__).parent.parent
MOCK_GAME_PATH = ROOT_DIR / "mock" / "game.json"
MOCK_PLAYS_PATH = ROOT_DIR / "mock" / "plays.json"
SNAPSHOT_PATH = ROOT_DIR / "data" / "game_state.json"

SYNC_INTERVAL_SECONDS = float(os.getenv("GAMECAST_SYNC_INTERVAL", "3"))


@lru_cache
def get_game_service() -> GameService:
    return GameService.restore(SNAPSHOT_PATH, fallback_path=MOCK_GAME_PATH)


@lru_cache
def get_provider() -> Provider:
    return MockProvider.from_files(MOCK_GAME_PATH, MOCK_PLAYS_PATH)
