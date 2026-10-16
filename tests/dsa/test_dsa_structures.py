"""
Unit Tests for new DSA modules: PriorityQueue, LRUCache, GraphMatching
"""

import pytest
from dsa.priority_queue import PriorityQueue, top_k_elements
from dsa.lru_cache import LRUCache
from dsa.graph_matching import CollaborationGraph
from dsa.hash_table import HashTable


def test_priority_queue_ordering():
    pq = PriorityQueue()
    pq.push("Project Low", priority=10.0)
    pq.push("Project High", priority=95.0)
    pq.push("Project Med", priority=50.0)

    assert pq.size() == 3
    assert pq.pop() == "Project High"
    assert pq.pop() == "Project Med"
    assert pq.pop() == "Project Low"
    assert pq.is_empty()


def test_top_k_elements():
    items = [
        {"title": "P1", "budget": 1000},
        {"title": "P2", "budget": 5000},
        {"title": "P3", "budget": 3000},
        {"title": "P4", "budget": 8000},
    ]
    top_2 = top_k_elements(items, k=2, key=lambda x: x["budget"])
    assert len(top_2) == 2
    assert top_2[0]["title"] == "P4"
    assert top_2[1]["title"] == "P2"


def test_lru_cache_operations():
    cache = LRUCache(capacity=2)
    cache.put("k1", "val1")
    cache.put("k2", "val2")

    assert cache.get("k1") == "val1"

    # Adding third item should evict k2 because k1 was recently accessed
    cache.put("k3", "val3")
    assert cache.get("k2") is None
    assert cache.get("k3") == "val3"
    assert cache.get("k1") == "val1"


def test_graph_bfs_and_dijkstra():
    g = CollaborationGraph()
    g.add_edge("Student_1", "Category_Web", weight=1.0)
    g.add_edge("Category_Web", "Provider_Priya", weight=2.0)
    g.add_edge("Category_Web", "Provider_Vishu", weight=1.5)

    recs = g.bfs_recommendations("Student_1", max_depth=2)
    rec_nodes = [r["node_id"] for r in recs]
    assert "Category_Web" in rec_nodes
    assert "Provider_Priya" in rec_nodes or "Provider_Vishu" in rec_nodes

    cost, path = g.dijkstra_best_path("Student_1", "Provider_Vishu")
    assert path == ["Student_1", "Category_Web", "Provider_Vishu"]
    assert cost == pytest.approx(2.5)


def test_hash_table():
    ht = HashTable(capacity=8)
    ht.put("student_1", {"name": "OM"})
    ht.put("student_2", {"name": "Vishwajeet"})
    assert ht.contains("student_1")
    assert ht.get("student_1")["name"] == "OM"
    assert ht.get("student_3") is None
