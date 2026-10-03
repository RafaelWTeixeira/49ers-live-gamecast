import pytest
from fastapi.testclient import TestClient

from app.dependencies import MOCK_GAME_PATH, get_game_service
from app.main import app
from app.models.event import GameEvent, GameEventKind
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


def test_websocket_sends_current_state_then_changes_and_events(game_service):
    scored = game_service.state.model_copy(
        update={"featured": game_service.state.featured.model_copy(update={"score": 9})}
    )

    with client.websocket_connect("/ws/game") as ws:
        first = ws.receive_json()
        game_service.update(scored, [GameEvent(kind=GameEventKind.FIELD_GOAL, side="featured")])
        second = ws.receive_json()
        third = ws.receive_json()

    assert first["type"] == "GAME_STATE"
    assert first["game"]["featured"]["score"] == 3
    assert second["type"] == "GAME_STATE"
    assert second["game"]["featured"]["score"] == 9
    assert second["game"]["field_position_label"] == "SF 8"
    assert third == {"type": "GAME_EVENT", "event": {"kind": "FIELD_GOAL", "side": "featured"}}


def test_websocket_stops_listening_after_disconnect(game_service):
    with client.websocket_connect("/ws/game") as ws:
        ws.receive_json()

    assert game_service._listeners == []


def test_mock_initial_game_is_a_valid_game_state():
    service = GameService.from_file(MOCK_GAME_PATH)

    assert service.state.phase == "PRE_GAME"


def test_overlay_is_served_as_html():
    response = client.get("/overlay")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_overlay_stylesheets_are_served():
    for name in ("reset", "overlay", "scoreboard", "field", "events"):
        assert client.get(f"/static/css/{name}.css").status_code == 200


def test_overlay_scripts_are_served():
    for name in ("overlay", "scoreboard", "field", "events", "websocket"):
        response = client.get(f"/static/js/{name}.js")
        assert response.status_code == 200
        assert "javascript" in response.headers["content-type"]
