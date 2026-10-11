"""
Unit Tests for DSA Matching Engine
"""

from dsa.matching import calculate_match_score, match_and_rank_providers
from dsa.sorting import merge_sort


def test_calculate_match_score_perfect():
    provider = {
        "id": 1,
        "name": "Aarav Sharma",
        "starting_price": 2500,
        "skills": ["Python", "Machine Learning", "Flask"],
        "rating": 5.0,
        "availability": "available"
    }
    required = ["Python", "Machine Learning", "Flask"]
    res = calculate_match_score(provider, required, student_budget=3000, strict_budget=True)

    assert res is not None
    assert res["skill_score"] == 100.0
    assert res["match_score"] > 85.0
    assert len(res["matching_skills"]) == 3


def test_calculate_match_score_strict_budget_filter():
    provider = {
        "id": 2,
        "name": "High Cost Provider",
        "starting_price": 6000,
        "skills": ["Python"],
        "rating": 5.0,
        "availability": "available"
    }
    # With strict budget of 4000, should be excluded
    res = calculate_match_score(provider, ["Python"], student_budget=4000, strict_budget=True)
    assert res is None


def test_merge_sort_descending():
    items = [{"score": 45}, {"score": 95}, {"score": 75}, {"score": 88}]
    sorted_items = merge_sort(items, key=lambda x: x["score"], reverse=True)
    scores = [x["score"] for x in sorted_items]
    assert scores == [95, 88, 75, 45]
