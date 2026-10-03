import asyncio

import pytest
from pydantic import ValidationError

from app.dependencies import MOCK_GAME_PATH, MOCK_PLAYS_PATH
from app.models.event import GameEvent, GameEventKind
from app.models.game import GamePhase, GameState
from app.models.team import Team
from app.providers.base import ProviderUpdate
from app.providers.mock_provider import MockProvider, apply_play

SF = Team(abbr="SF", name="49ers", primary_color="#AA0000", secondary_color="#B3995D")
DEN = Team(abbr="DEN", name="Broncos", primary_color="#0A2343", secondary_color="#FC4C02")
KICKOFF = GameState(featured=SF, opponent=DEN)


def fetch_update(provider: MockProvider) -> ProviderUpdate:
    return asyncio.run(provider.fetch())


def fetch(provider: MockProvider) -> GameState:
    return fetch_update(provider).state


class TestApplyPlay:
    def test_replaces_plain_fields(self):
        state = apply_play(KICKOFF, {"phase": "LIVE", "clock": "14:22"})

        assert state.phase == GamePhase.LIVE
        assert state.clock == "14:22"

    def test_merges_team_fields(self):
        state = apply_play(KICKOFF, {"featured": {"score": 7}})

        assert state.featured.score == 7
        assert state.featured.abbr == "SF"

    def test_merges_nested_objects_field_by_field(self):
        purdy = {"quarterback": {"name": "Brock Purdy", "completions": 1, "attempts": 1}}
        state = apply_play(KICKOFF, {"featured": purdy})

        state = apply_play(state, {"featured": {"quarterback": {"completions": 2, "attempts": 2}}})

        assert state.featured.quarterback.name == "Brock Purdy"
        assert state.featured.quarterback.completions == 2

    def test_rejects_unknown_fields(self):
        with pytest.raises(ValidationError):
            apply_play(KICKOFF, {"posession": "featured"})


class TestMockProvider:
    def test_advances_one_play_per_fetch(self):
        provider = MockProvider(KICKOFF, [{"clock": "14:00"}, {"clock": "13:00"}])

        assert fetch(provider).clock == "14:00"
        assert fetch(provider).clock == "13:00"

    def test_restarts_the_game_after_the_last_play(self):
        provider = MockProvider(KICKOFF, [{"featured": {"score": 3}}, {"featured": {"score": 6}}])
        fetch(provider)
        fetch(provider)

        assert fetch(provider).featured.score == 3

    def test_announces_the_events_declared_in_the_play(self):
        touchdown = {
            "featured": {"score": 6},
            "events": [{"kind": "TOUCHDOWN", "side": "featured"}],
        }
        provider = MockProvider(KICKOFF, [touchdown])

        update = fetch_update(provider)

        assert update.state.featured.score == 6
        assert update.events == (GameEvent(kind=GameEventKind.TOUCHDOWN, side="featured"),)

    def test_plays_without_events_announce_nothing(self):
        assert fetch_update(MockProvider(KICKOFF, [{"clock": "14:00"}])).events == ()

    def test_requires_at_least_one_play(self):
        with pytest.raises(ValueError):
            MockProvider(KICKOFF, [])


def test_every_play_in_the_mock_game_is_a_valid_game_state():
    provider = MockProvider.from_files(MOCK_GAME_PATH, MOCK_PLAYS_PATH)
    states = [fetch(provider) for _ in provider._plays]

    assert states[0].phase == GamePhase.LIVE
    assert states[-1].phase == GamePhase.FINAL
