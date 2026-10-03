import os
from functools import lru_cache
from pathlib import Path

from app.models.control import ControlMode
from app.providers.base import Provider
from app.providers.espn_provider import EspnProvider
from app.providers.mock_provider import MockProvider
from app.services.game_service import GameService
from app.services.provider_sync import ProviderHealth

ROOT_DIR = Path(__file__).parent.parent
MOCK_GAME_PATH = ROOT_DIR / "mock" / "game.json"
MOCK_PLAYS_PATH = ROOT_DIR / "mock" / "plays.json"
SNAPSHOT_PATH = ROOT_DIR / "data" / "game_state.json"
RECORDINGS_DIR = ROOT_DIR / "data" / "recordings"

SYNC_INTERVAL_SECONDS = float(os.getenv("GAMECAST_SYNC_INTERVAL", "3"))
# Modo inicial quando não há snapshot; com snapshot, vale o modo gravado.
DEFAULT_CONTROL_MODE = ControlMode(os.getenv("GAMECAST_CONTROL_MODE", "AUTO").upper())

# "mock" (padrão, desenvolvimento) ou "espn" (jogo real). Ver README.
PROVIDER = os.getenv("GAMECAST_PROVIDER", "mock").lower()
FEATURED_TEAM = os.getenv("GAMECAST_FEATURED_TEAM", "SF").upper()
# Sem evento, a ESPN usa o jogo do Featured Team em andamento ou o próximo.
ESPN_EVENT = os.getenv("GAMECAST_ESPN_EVENT") or None
ESPN_LEAGUE = os.getenv("GAMECAST_ESPN_LEAGUE", "nfl")


@lru_cache
def get_game_service() -> GameService:
    return GameService.restore(SNAPSHOT_PATH, MOCK_GAME_PATH, DEFAULT_CONTROL_MODE)


@lru_cache
def get_provider() -> Provider:
    if PROVIDER == "espn":
        return EspnProvider(FEATURED_TEAM, ESPN_EVENT, ESPN_LEAGUE, record_root=RECORDINGS_DIR)
    if PROVIDER == "mock":
        return MockProvider.from_files(MOCK_GAME_PATH, MOCK_PLAYS_PATH)
    raise ValueError(f"GAMECAST_PROVIDER inválido: {PROVIDER!r} (use 'mock' ou 'espn')")


@lru_cache
def get_provider_health() -> ProviderHealth:
    return ProviderHealth()
