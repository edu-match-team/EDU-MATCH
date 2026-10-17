import pytest
from backend.app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

def test_senior_ai_ranking(client):
    res = client.post("/api/matching/find-matches", json={"query": "senior ai"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    results = data["results"]
    assert len(results) > 0
    top = results[0]
    assert "sarah" in top["name"].lower() or "senior ai" in top["title"].lower()
    assert top["match_score"] >= 90.0

def test_web_developer_ranking(client):
    res = client.post("/api/matching/find-matches", json={"query": "web developer"})
    assert res.status_code == 200
    data = res.get_json()
    results = data["results"]
    assert len(results) > 0
    top = results[0]
    assert "web" in top["title"].lower() or "developer" in top["title"].lower()
    assert top["match_score"] >= 90.0

def test_app_developer_ranking(client):
    res = client.post("/api/matching/find-matches", json={"query": "app developer"})
    assert res.status_code == 200
    data = res.get_json()
    results = data["results"]
    assert len(results) > 0
    top = results[0]
    assert "app" in top["title"].lower()
    assert top["match_score"] >= 90.0
