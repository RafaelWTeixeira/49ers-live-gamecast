import asyncio

import pytest

from app.models.control import ControlMode
from app.models.event import GameEvent, GameEventKind
from app.models.game import GameState
from app.models.quarterback import QuarterbackStats
from app.models.team import Team
from app.providers.base import Provider, ProviderUpdate
from app.services.game_service import ControlModeError, GameService, NothingToUndoError
from app.services.provider_sync import ProviderHealth, sync_once

SF = Team(abbr="SF", name="49ers", primary_color="#AA0000", secondary_color="#B3995D")
DEN = Team(abbr="DEN", name="Broncos", primary_color="#0A2343", secondary_color="#FC4C02")
PRE_GAME = GameState(featured=SF, opponent=DEN)
TOUCHDOWN = GameState(featured=SF.model_copy(update={"score": 7}), opponent=DEN)
TOUCHDOWN_EVENT = GameEvent(kind=GameEventKind.TOUCHDOWN, side="featured")
PURDY = QuarterbackStats(name="Brock Purdy", completions=16, attempts=23, yards=229, touchdowns=1)
WITH_QB = GameState(featured=SF.model_copy(update={"quarterback": PURDY}), opponent=DEN)


def write_state(path, state: GameState):
    path.write_text(state.model_dump_json(exclude=set(GameState.model_computed_fields)))


class TestListeners:
    def test_receive_the_new_state(self):
        service, received = GameService(PRE_GAME), []
        service.subscribe(received.append)

        service.update(TOUCHDOWN)

        assert received == [TOUCHDOWN]

    def test_are_not_bothered_when_nothing_changed(self):
        service, received = GameService(PRE_GAME), []
        service.subscribe(received.append)

        service.update(PRE_GAME)

        assert received == []

    def test_receive_events_after_the_state(self):
        service, received = GameService(PRE_GAME), []
        service.subscribe(received.append)

        service.update(TOUCHDOWN, [TOUCHDOWN_EVENT])

        assert received == [TOUCHDOWN, TOUCHDOWN_EVENT]

    def test_receive_events_even_without_a_state_change(self):
        service, received = GameService(TOUCHDOWN), []
        service.subscribe(received.append)

        service.update(TOUCHDOWN, [TOUCHDOWN_EVENT])

        assert received == [TOUCHDOWN_EVENT]

    def test_stop_receiving_after_unsubscribing(self):
        service, received = GameService(PRE_GAME), []
        unsubscribe = service.subscribe(received.append)

        unsubscribe()
        service.update(TOUCHDOWN)

        assert received == []


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

    async def fetch(self) -> ProviderUpdate:
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


def sync(result, service: GameService, health: ProviderHealth | None = None) -> bool:
    return asyncio.run(sync_once(StubProvider(result), service, health or ProviderHealth()))


class TestSyncOnce:
    def test_publishes_the_provider_state_in_auto(self):
        service = GameService(PRE_GAME)

        assert sync(ProviderUpdate(TOUCHDOWN, (TOUCHDOWN_EVENT,)), service) is True
        assert service.state == TOUCHDOWN

    def test_ignores_the_provider_in_manual(self):
        service = GameService(PRE_GAME, control_mode=ControlMode.MANUAL)

        assert sync(ProviderUpdate(TOUCHDOWN), service) is False
        assert service.state == PRE_GAME

    def test_keeps_last_state_when_provider_fails(self):
        service = GameService(TOUCHDOWN)

        assert sync(ConnectionError("API fora"), service) is False
        assert service.state == TOUCHDOWN

    def test_tracks_provider_health_even_in_manual(self):
        service = GameService(PRE_GAME, control_mode=ControlMode.MANUAL)
        health = ProviderHealth()

        sync(ConnectionError("API fora"), service, health)
        assert not health.healthy
        assert "API fora" in health.last_error

        sync(ProviderUpdate(TOUCHDOWN), service, health)
        assert health.healthy


def manual(state: GameState = PRE_GAME) -> GameService:
    return GameService(state, control_mode=ControlMode.MANUAL)


class TestControlMode:
    def test_manual_edits_are_refused_in_auto(self):
        with pytest.raises(ControlModeError):
            GameService(PRE_GAME).apply_manual(TOUCHDOWN)

    def test_manual_events_are_refused_in_auto(self):
        with pytest.raises(ControlModeError):
            GameService(PRE_GAME).announce_manual(TOUCHDOWN_EVENT)

    def test_manual_edit_publishes_the_state(self):
        service = manual()

        service.apply_manual(TOUCHDOWN)

        assert service.state == TOUCHDOWN

    def test_mode_survives_a_restart(self, tmp_path):
        snapshot, fallback = tmp_path / "game_state.json", tmp_path / "game.json"
        write_state(fallback, PRE_GAME)

        GameService.restore(snapshot, fallback).set_control_mode(ControlMode.MANUAL)

        assert GameService.restore(snapshot, fallback).control_mode == ControlMode.MANUAL


class TestFieldDirection:
    def test_provider_updates_keep_the_direction_chosen_by_the_operator(self):
        service = GameService(PRE_GAME)
        service.flip_field_direction()

        sync(ProviderUpdate(TOUCHDOWN), service)

        assert service.state.featured.score == 7
        assert service.state.opening_field_direction == "right"

    def test_a_new_game_starts_from_the_default_direction(self):
        last_game = PRE_GAME.with_changes(phase="FINAL", opening_field_direction="right")
        service = GameService(last_game)

        sync(ProviderUpdate(PRE_GAME), service)

        assert service.state.opening_field_direction == "left"

    def test_another_opponent_is_a_new_game(self):
        service = GameService(PRE_GAME.with_changes(opening_field_direction="right"))
        seattle = DEN.model_copy(update={"abbr": "SEA", "name": "Seahawks"})

        sync(ProviderUpdate(GameState(featured=SF, opponent=seattle)), service)

        assert service.state.opening_field_direction == "left"

    def test_provider_updates_keep_the_second_half_direction_too(self):
        service = GameService(PRE_GAME.with_changes(quarter=3))
        service.flip_field_direction()

        sync(ProviderUpdate(TOUCHDOWN.with_changes(quarter=3)), service)

        assert service.state.second_half_field_direction == "left"
        assert service.state.field_direction == "left"

    def test_flip_in_manual_can_be_undone(self):
        service = manual()
        service.flip_field_direction()

        service.undo()

        assert service.state.opening_field_direction == "left"


class TestQuarterbackStatsInManual:
    def test_are_removed_when_switching_to_manual(self):
        service, received = GameService(WITH_QB), []
        service.subscribe(received.append)

        service.set_control_mode(ControlMode.MANUAL)

        assert service.state.featured.quarterback is None
        assert received == [service.state]

    def test_manual_edits_cannot_bring_them_back(self):
        service = manual()

        service.apply_manual(WITH_QB)

        assert service.state.featured.quarterback is None

    def test_return_with_the_provider_in_auto(self):
        service = manual()
        service.set_control_mode(ControlMode.AUTO)

        sync(ProviderUpdate(WITH_QB), service)

        assert service.state.featured.quarterback == PURDY


class TestManualEvents:
    def test_touchdown_adds_six_points_and_is_announced(self):
        service, received = manual(), []
        service.subscribe(received.append)

        service.announce_manual(TOUCHDOWN_EVENT)

        assert service.state.featured.score == 6
        assert received[-1] == TOUCHDOWN_EVENT

    def test_safety_scores_for_the_side_that_made_it(self):
        service = manual()

        service.announce_manual(GameEvent(kind=GameEventKind.SAFETY, side="opponent"))

        assert service.state.opponent.score == 2

    def test_flag_changes_nothing_but_is_announced(self):
        service, received = manual(), []
        service.subscribe(received.append)

        service.announce_manual(GameEvent(kind=GameEventKind.FLAG))

        assert service.state == PRE_GAME
        assert received == [GameEvent(kind=GameEventKind.FLAG)]


class TestUndo:
    def test_returns_to_the_state_before_the_last_manual_change(self):
        service = manual()
        service.announce_manual(TOUCHDOWN_EVENT)
        service.announce_manual(GameEvent(kind=GameEventKind.EXTRA_POINT, side="featured"))

        service.undo()

        assert service.state.featured.score == 6

    def test_without_history_is_an_error(self):
        with pytest.raises(NothingToUndoError):
            manual().undo()

    def test_history_is_cleared_when_the_mode_changes(self):
        service = manual()
        service.announce_manual(TOUCHDOWN_EVENT)

        service.set_control_mode(ControlMode.AUTO)
        service.set_control_mode(ControlMode.MANUAL)

        assert not service.can_undo
