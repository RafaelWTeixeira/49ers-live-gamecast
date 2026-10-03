import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_game_service, get_provider_health
from app.main import app
from app.models.control import ControlMode
from app.models.game import GamePhase, GameState
from app.models.team import Team
from app.services.game_service import GameService
from app.services.provider_sync import ProviderHealth

client = TestClient(app)

SF = Team(abbr="SF", name="49ers", primary_color="#AA0000", secondary_color="#B3995D")
DEN = Team(abbr="DEN", name="Broncos", primary_color="#FB4F14", secondary_color="#0A2343")
DRIVE = GameState(
    featured=SF,
    opponent=DEN,
    phase=GamePhase.LIVE,
    possession="featured",
    yardline=66,
    down=2,
    distance=6,
)


def install(service: GameService) -> GameService:
    app.dependency_overrides[get_game_service] = lambda: service
    app.dependency_overrides[get_provider_health] = ProviderHealth
    return service


@pytest.fixture
def auto_service():
    yield install(GameService(DRIVE))
    app.dependency_overrides.clear()


@pytest.fixture
def manual_service():
    yield install(GameService(DRIVE, control_mode=ControlMode.MANUAL))
    app.dependency_overrides.clear()


def test_control_page_is_served():
    response = client.get("/control")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_status_reports_mode_and_provider(auto_service):
    body = client.get("/api/control").json()

    assert body["mode"] == "AUTO"
    assert body["can_undo"] is False
    assert body["provider"]["healthy"] is False


def test_switching_to_manual(auto_service):
    response = client.put("/api/control/mode", json={"mode": "MANUAL"})

    assert response.json()["mode"] == "MANUAL"
    assert auto_service.control_mode == ControlMode.MANUAL


def test_manual_actions_are_refused_in_auto(auto_service):
    touchdown = {"kind": "TOUCHDOWN", "side": "featured"}

    assert client.post("/api/control/events", json=touchdown).status_code == 409
    assert client.put("/api/control/game", json=DRIVE.stored_fields()).status_code == 409
    assert client.post("/api/control/flip-field").status_code == 409
    assert auto_service.state == DRIVE


def test_editing_the_game(manual_service):
    edited = {**DRIVE.stored_fields(), "quarter": 4, "clock": "01:59"}

    response = client.put("/api/control/game", json=edited)

    assert response.status_code == 200
    assert response.json()["quarter"] == 4
    assert manual_service.state.clock == "01:59"


def test_invalid_edit_is_rejected(manual_service):
    response = client.put("/api/control/game", json={**DRIVE.stored_fields(), "down": None})

    assert response.status_code == 422
    assert manual_service.state == DRIVE


def test_event_button_scores_and_undo_reverts(manual_service):
    client.post("/api/control/events", json={"kind": "FIELD_GOAL", "side": "featured"})
    assert manual_service.state.featured.score == 3

    response = client.post("/api/control/undo")

    assert response.status_code == 200
    assert manual_service.state.featured.score == 0


def test_undo_without_history_is_a_conflict(manual_service):
    assert client.post("/api/control/undo").status_code == 409


def test_flip_field_inverts_direction(manual_service):
    response = client.post("/api/control/flip-field")

    assert response.json()["field_direction"] == "right"
