from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Verify that GET /health returns 200 and indicates healthy backend status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "healthy"
    assert "JanMitra Assist backend is running successfully" in data.get("message", "")


def test_root_endpoint():
    """Verify that GET / returns 200 and valid project metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "online"
    assert data.get("project") == "JanMitra Assist"
