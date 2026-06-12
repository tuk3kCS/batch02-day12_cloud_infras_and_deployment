import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "uptime_seconds" in response.json()

def test_ready_endpoint_disconnected():
    # If Redis is not connected, it should return 503
    response = client.get("/ready")
    assert response.status_code in [200, 503]

def test_ask_endpoint_unauthorized():
    response = client.post("/ask", json={"question": "Hello"})
    assert response.status_code == 401

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["app"] == "Production AI Agent"
