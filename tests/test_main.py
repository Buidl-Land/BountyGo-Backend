"""
Test main application functionality
"""
import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert data["service"] == "bountygo-backend"


def test_api_info(client: TestClient):
    """Test API info endpoint"""
    response = client.get("/api/v1/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "BountyGo API v1"
    assert data["version"] == "1.0.0"
    assert data["status"] == "active"