import pytest
from pydantic import ValidationError

from app.models.game import GameState
from app.models.quarterback import QuarterbackStats
from app.models.team import Team


def qb(**stats) -> QuarterbackStats:
    return QuarterbackStats(name="Brock Purdy", **stats)


class TestPasserRating:
    def test_typical_game(self):
        stats = qb(completions=17, attempts=24, yards=237, touchdowns=2, interceptions=0)

        assert stats.passer_rating == 130.0

    def test_perfect_game_is_158_3(self):
        stats = qb(completions=20, attempts=20, yards=400, touchdowns=4)

        assert stats.passer_rating == 158.3

    def test_each_component_bottoms_out_at_zero(self):
        stats = qb(completions=0, attempts=10, yards=0, interceptions=3)

        assert stats.passer_rating == 0.0

    def test_is_absent_without_attempts(self):
        assert qb().passer_rating is None


class TestValidation:
    @pytest.mark.parametrize(
        "stats",
        [
            {"completions": 5, "attempts": 4},
            {"completions": 3, "attempts": 4, "interceptions": 2},
            {"completions": 1, "attempts": 4, "touchdowns": 2},
            {"attempts": -1},
            {"name": ""},
        ],
    )
    def test_rejects_impossible_lines(self, stats):
        with pytest.raises(ValidationError):
            QuarterbackStats(**{"name": "Brock Purdy", **stats})

    def test_passing_yards_can_be_negative(self):
        assert qb(completions=1, attempts=1, yards=-3).yards == -3


class TestStoredFields:
    def test_leaves_out_the_derived_rating(self):
        sf = Team(
            abbr="SF",
            name="49ers",
            primary_color="#AA0000",
            secondary_color="#B3995D",
            quarterback=qb(completions=1, attempts=1, yards=10),
        )
        den = Team(abbr="DEN", name="Broncos", primary_color="#FB4F14", secondary_color="#0A2343")
        state = GameState(featured=sf, opponent=den)

        stored = state.stored_fields()

        assert "passer_rating" not in stored["featured"]["quarterback"]
        assert GameState.model_validate(stored) == state
