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

def test_ai_category_tiered_ranking(client):
    res = client.post("/api/matching/find-matches", json={"category": "Artificial Intelligence"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    results = data["results"]
    assert len(results) > 0
    
    # 1. Top results should be primary specialists
    top_tier = results[0]["category_tier"]
    assert top_tier == "primary"
    assert results[0]["match_score"] > 90.0

    # 2. Mayank Rawat should be 'related' if present
    mayank = next((p for p in results if "mayank" in p["name"].lower()), None)
    if mayank:
        assert mayank["category_tier"] == "related"
        assert mayank["match_score"] < results[0]["match_score"]

    # 3. Pure unrelated providers must not appear
    unrelated = [p for p in results if p.get("category_tier") == "none"]
    assert len(unrelated) == 0

def test_provider_orders_endpoint(client):
    # Raman is provider user_id 2
    res = client.get("/api/provider/orders", headers={"X-User-Id": "2"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "orders" in data

