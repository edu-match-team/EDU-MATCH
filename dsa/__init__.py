# dsa/__init__.py
# EduMatch DSA Package — exposes all modules for easy importing
# Usage from backend:  from dsa import MatchingEngine, Trie

from dsa.trie import Trie, build_skill_trie
from dsa.hash_table import HashTable
from dsa.graph import Graph
from dsa.bfs import BFS
from dsa.dfs import DFS
from dsa.heap import MaxHeap
from dsa.priority_queue import PriorityQueue
from dsa.queue import Queue
from dsa.searching import LinearSearch, BinarySearch
from dsa.sorting import bubble_sort, selection_sort, insertion_sort, merge_sort
from dsa.matching import MatchingEngine

__all__ = [
    'Trie', 'build_skill_trie',
    'HashTable',
    'Graph',
    'BFS',
    'DFS',
    'MaxHeap',
    'PriorityQueue',
    'Queue',
    'LinearSearch', 'BinarySearch',
    'bubble_sort', 'selection_sort', 'insertion_sort', 'merge_sort',
    'MatchingEngine',
]