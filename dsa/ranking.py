"""
Ranking logic helper for EduMatch
Module: dsa.ranking
"""

from typing import List, Dict, Any
from dsa.sorting import merge_sort, quick_sort


def rank_by_field(items: List[Dict[str, Any]], field: str = "match_score", descending: bool = True) -> List[Dict[str, Any]]:
    """
    Ranks items using Merge Sort on specified field.
    """
    return merge_sort(items, key=lambda x: x.get(field, 0), reverse=descending)
