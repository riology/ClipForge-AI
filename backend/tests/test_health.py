"""Tests for the health check endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_200():
    """Health endpoint should return 200 OK."""
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_endpoint_returns_healthy_status():
    """Health endpoint should report healthy status."""
    response = client.get("/api/health")
    data = response.json()
    assert data["status"] == "healthy"


def test_health_endpoint_returns_app_info():
    """Health endpoint should include app name and version."""
    response = client.get("/api/health")
    data = response.json()
    assert data["app"] == "ClipForge AI"
    assert "version" in data
    assert data["version"] == "0.1.0"
