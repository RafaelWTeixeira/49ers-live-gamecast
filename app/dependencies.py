from functools import lru_cache
from pathlib import Path

from app.services.game_service import GameService

MOCK_GAME_PATH = Path(__file__).parent.parent / "mock" / "game.json"


@lru_cache
def get_game_service() -> GameService:
    return GameService.from_file(MOCK_GAME_PATH)
