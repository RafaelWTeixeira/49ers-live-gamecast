import pytest
from fastapi.testclient import TestClient

from app.dependencies import MOCK_GAME_PATH, get_game_service
from app.main import app
from app.models.game import GameState
from app.models.team import Team
from app.services.game_service import GameService

client = TestClient(app)


@pytest.fixture
def game_service():
    sf = Team(abbr="SF", name="49ers", score=3, primary_color="#AA0000", secondary_color="#B3995D")
    sea = Team(abbr="SEA", name="Seahawks", primary_color="#69BE28", secondary_color="#002244")
    service = GameService(
        GameState(featured=sf, opponent=sea, possession="opponent", yardline=8, down=1, distance=8)
    )
    app.dependency_overrides[get_game_service] = lambda: service
    yield service
    app.dependency_overrides.clear()


def test_health_returns_ok():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_game_returns_current_state_with_derived_fields(game_service):
    response = client.get("/api/game")

    assert response.status_code == 200
    body = response.json()
    assert body["featured"]["score"] == 3
    assert body["opponent"]["abbr"] == "SEA"
    assert body["field_position_label"] == "SF 8"
    assert body["line_to_gain"] == 0
    assert body["goal_to_go"] is True
    assert body["field_direction"] == "left"


def test_mock_initial_game_is_a_valid_game_state():
    service = GameService.from_file(MOCK_GAME_PATH)

    assert service.state.phase == "PRE_GAME"


def test_overlay_is_served_as_html():
    response = client.get("/overlay")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_overlay_stylesheets_are_served():
    for name in ("reset", "overlay", "scoreboard", "field"):
        assert client.get(f"/static/css/{name}.css").status_code == 200


def test_overlay_scripts_are_served():
    for name in ("overlay", "scoreboard", "field"):
        response = client.get(f"/static/js/{name}.js")
        assert response.status_code == 200
        assert "javascript" in response.headers["content-type"]
