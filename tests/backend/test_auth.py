"""
Unit Tests for EduMatch Authentication and Health Routes
"""

import pytest
from backend.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.get_json()["success"] is True


def test_invalid_login(client):
    res = client.post("/api/auth/login", json={
        "email": "nonexistent@user.com",
        "password": "WrongPassword123"
    })
    assert res.status_code == 401
    assert res.get_json()["success"] is False


def test_matching_endpoint(client):
    res = client.post("/api/matching/find-matches", json={
        "skills": ["Python", "Flask"],
        "budget": 3000
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert len(data["results"]) > 0
    assert "dsa_metadata" in data
