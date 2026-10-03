import pytest
from pydantic import ValidationError

from app.models.event import GameEvent, GameEventKind, apply_event
from app.models.game import GamePhase, GameState
from app.models.team import Team

SF = Team(abbr="SF", name="49ers", primary_color="#AA0000", secondary_color="#B3995D")
DEN = Team(abbr="DEN", name="Broncos", primary_color="#FB4F14", secondary_color="#0A2343")
DRIVE = GameState(
    featured=SF,
    opponent=DEN,
    phase=GamePhase.LIVE,
    possession="opponent",
    yardline=40,
    down=3,
    distance=4,
)


@pytest.mark.parametrize(
    ("kind", "points"),
    [
        (GameEventKind.TOUCHDOWN, 6),
        (GameEventKind.FIELD_GOAL, 3),
        (GameEventKind.SAFETY, 2),
        (GameEventKind.EXTRA_POINT, 1),
        (GameEventKind.TWO_POINT_CONVERSION, 2),
    ],
)
def test_scoring_events_add_points_to_their_side(kind, points):
    state = apply_event(DRIVE, GameEvent(kind=kind, side="featured"))

    assert state.featured.score == points
    assert state.opponent.score == 0


def test_turnover_gives_the_ball_to_the_side_with_first_and_ten():
    state = apply_event(DRIVE, GameEvent(kind=GameEventKind.TURNOVER, side="featured"))

    assert (state.possession, state.down, state.distance) == ("featured", 1, 10)
    assert state.yardline == 40


@pytest.mark.parametrize("kind", [GameEventKind.TIMEOUT, GameEventKind.FLAG])
def test_non_scoring_events_keep_the_state(kind):
    assert apply_event(DRIVE, GameEvent(kind=kind, side="featured")) == DRIVE


def test_flag_may_have_no_side():
    assert GameEvent(kind=GameEventKind.FLAG).side is None


def test_other_events_require_a_side():
    with pytest.raises(ValidationError):
        GameEvent(kind=GameEventKind.TOUCHDOWN)
