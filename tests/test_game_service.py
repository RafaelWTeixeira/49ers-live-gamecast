import asyncio

from app.models.game import GameState
from app.models.team import Team
from app.providers.base import Provider
from app.services.game_service import GameService
from app.services.provider_sync import sync_once

SF = Team(abbr="SF", name="49ers", primary_color="#AA0000", secondary_color="#B3995D")
DEN = Team(abbr="DEN", name="Broncos", primary_color="#FB4F14", secondary_color="#0A2343")
PRE_GAME = GameState(featured=SF, opponent=DEN)
TOUCHDOWN = GameState(featured=SF.model_copy(update={"score": 7}), opponent=DEN)


def write_state(path, state: GameState):
    path.write_text(state.model_dump_json(exclude=set(GameState.model_computed_fields)))


class TestSnapshot:
    def test_update_survives_a_restart(self, tmp_path):
        snapshot = tmp_path / "data" / "game_state.json"
        fallback = tmp_path / "game.json"
        write_state(fallback, PRE_GAME)

        GameService.restore(snapshot, fallback).update(TOUCHDOWN)
        restarted = GameService.restore(snapshot, fallback)

        assert restarted.state == TOUCHDOWN

    def test_uses_fallback_without_snapshot(self, tmp_path):
        fallback = tmp_path / "game.json"
        write_state(fallback, PRE_GAME)

        assert GameService.restore(tmp_path / "missing.json", fallback).state == PRE_GAME

    def test_uses_fallback_when_snapshot_is_corrupt(self, tmp_path):
        snapshot = tmp_path / "game_state.json"
        snapshot.write_text('{"phase": "LIV')
        fallback = tmp_path / "game.json"
        write_state(fallback, PRE_GAME)

        assert GameService.restore(snapshot, fallback).state == PRE_GAME


class StubProvider(Provider):
    def __init__(self, result):
        self._result = result

    async def fetch(self) -> GameState:
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


class TestSyncOnce:
    def test_publishes_the_provider_state(self):
        service = GameService(PRE_GAME)

        assert asyncio.run(sync_once(StubProvider(TOUCHDOWN), service)) is True
        assert service.state == TOUCHDOWN

    def test_keeps_last_state_when_provider_fails(self):
        service = GameService(TOUCHDOWN)

        assert asyncio.run(sync_once(StubProvider(ConnectionError("API fora")), service)) is False
        assert service.state == TOUCHDOWN
