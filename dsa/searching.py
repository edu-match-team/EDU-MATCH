"""
DSA Searching Algorithms & Trie for EduMatch
Module: dsa.searching
Author: Vishu & Team (BCA AI & Data Science)

Contains:
1. Binary Search for threshold querying in sorted provider lists (O(log N)).
2. Trie (Prefix Tree) for auto-completing and fast searching skills and provider titles (O(L)).
"""

from typing import List, Dict, Any, Optional


def binary_search_score(sorted_providers: List[Dict[str, Any]], min_score: float) -> int:
    """
    Finds the first index of a provider with match_score < min_score
    in a descending-sorted list.
    Time Complexity: O(log N)
    """
    low = 0
    high = len(sorted_providers) - 1
    cutoff_index = len(sorted_providers)

    while low <= high:
        mid = (low + high) // 2
        mid_score = sorted_providers[mid].get("match_score", 0.0)

        if mid_score < min_score:
            cutoff_index = mid
            high = mid - 1
        else:
            low = mid + 1

    return cutoff_index


class TrieNode:
    def __init__(self):
        self.children: Dict[str, TrieNode] = {}
        self.is_end_of_word: bool = False
        self.payload: Any = None


class SkillTrie:
    """
    Prefix Tree (Trie) for fast O(L) keyword lookup and autocomplete.
    """
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word: str, payload: Any = None):
        node = self.root
        word_clean = word.strip().lower()
        for char in word_clean:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end_of_word = True
        node.payload = payload or word

    def search_prefix(self, prefix: str) -> List[Any]:
        node = self.root
        prefix_clean = prefix.strip().lower()
        for char in prefix_clean:
            if char not in node.children:
                return []
            node = node.children[char]

        results: List[Any] = []
        self._dfs_collect(node, results)
        return results

    def _dfs_collect(self, node: TrieNode, results: List[Any]):
        if node.is_end_of_word and node.payload is not None:
            results.append(node.payload)
        for child in node.children.values():
            self._dfs_collect(child, results)
