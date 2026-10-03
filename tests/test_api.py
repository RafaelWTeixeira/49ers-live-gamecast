from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_overlay_is_served_as_html():
    response = client.get("/overlay")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_overlay_stylesheets_are_served():
    for name in ("reset", "overlay", "scoreboard", "field"):
        assert client.get(f"/static/css/{name}.css").status_code == 200
