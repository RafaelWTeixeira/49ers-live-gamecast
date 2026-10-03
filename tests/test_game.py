import pytest
from pydantic import ValidationError

from app.models.game import GamePhase, GameState
from app.models.team import Team

SF = Team(abbr="SF", name="49ers", primary_color="#AA0000", secondary_color="#B3995D")
DEN = Team(abbr="DEN", name="Broncos", primary_color="#FB4F14", secondary_color="#0A2343")


def game(**overrides) -> GameState:
    return GameState(featured=SF, opponent=DEN, phase=GamePhase.LIVE, **overrides)


def drive(possession="featured", yardline=25, down=1, distance=10, **overrides) -> GameState:
    return game(possession=possession, yardline=yardline, down=down, distance=distance, **overrides)


class TestFieldPositionLabel:
    @pytest.mark.parametrize(
        ("yardline", "label"),
        [(25, "SF 25"), (1, "SF 1"), (50, "50"), (66, "DEN 34"), (99, "DEN 1")],
    )
    def test_names_the_half_of_the_field(self, yardline, label):
        assert drive(yardline=yardline).field_position_label == label

    def test_is_absent_without_a_ball_on_the_field(self):
        assert game().field_position_label is None


class TestLineToGain:
    def test_featured_team_advances_toward_100(self):
        assert drive("featured", yardline=66, distance=6).line_to_gain == 72

    def test_opponent_advances_toward_0(self):
        assert drive("opponent", yardline=72, distance=2).line_to_gain == 70

    def test_is_absent_without_possession(self):
        assert game().line_to_gain is None


class TestGoalToGo:
    def test_featured_team_inside_the_opponent_ten(self):
        assert drive("featured", yardline=92, distance=8).goal_to_go is True

    def test_opponent_inside_the_featured_team_ten(self):
        assert drive("opponent", yardline=5, distance=5).goal_to_go is True

    def test_regular_down(self):
        assert drive("featured", yardline=66, distance=6).goal_to_go is False

    def test_without_possession(self):
        assert game().goal_to_go is False


class TestFieldDirection:
    @pytest.mark.parametrize(
        ("quarter", "direction"),
        [(1, "left"), (2, "right"), (3, "left"), (4, "right"), (5, "left")],
    )
    def test_teams_switch_ends_on_second_and_fourth_quarters(self, quarter, direction):
        assert game(quarter=quarter).field_direction == direction

    def test_follows_the_opening_direction(self):
        assert game(quarter=1, opening_field_direction="right").field_direction == "right"
        assert game(quarter=2, opening_field_direction="right").field_direction == "left"


class TestValidation:
    def test_possession_requires_a_complete_drive(self):
        with pytest.raises(ValidationError):
            game(possession="featured", yardline=25)

    @pytest.mark.parametrize(
        "overrides",
        [{"quarter": 6}, {"quarter": 0}, {"clock": "8:42"}, {"down": 5}, {"yardline": 101}],
    )
    def test_rejects_impossible_values(self, overrides):
        with pytest.raises(ValidationError):
            game(**overrides)
