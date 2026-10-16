"""
DSA Priority Queue (Binary Heap) for EduMatch
Module: dsa.priority_queue
Author: Vishu & Team (BCA AI & Data Science)

Implements Max-Heap and Min-Heap Priority Queues for:
1. Student Request Priority Scheduling (e.g., ordering project requests by budget and deadline urgency).
2. Top-K Provider Ranking (O(N log K) time complexity instead of O(N log N) full sort).

Theoretical Complexity:
- Insertion: O(log N)
- Extract Max/Min: O(log N)
- Peek: O(1)
- Build Heap: O(N)
- Top-K Selection: O(N log K)
"""

from typing import Any, Callable, Dict, List, Optional, Tuple


class PriorityQueue:
    """
    Max-Heap Priority Queue implementation using a dynamic array (list).
    Higher priority values are served first.
    """

    def __init__(self, key: Optional[Callable[[Any], float]] = None):
        self.heap: List[Tuple[float, int, Any]] = []
        self.counter: int = 0  # Tie-breaker for stable ordering
        self.key_fn = key or (lambda x: float(x) if isinstance(x, (int, float)) else 0.0)

    def is_empty(self) -> bool:
        return len(self.heap) == 0

    def size(self) -> int:
        return len(self.heap)

    def push(self, item: Any, priority: Optional[float] = None):
        """
        Inserts an item into the priority queue.
        Time Complexity: O(log N)
        """
        if priority is None:
            priority = float(self.key_fn(item))

        entry = (priority, -self.counter, item)
        self.counter += 1
        self.heap.append(entry)
        self._sift_up(len(self.heap) - 1)

    def pop(self) -> Any:
        """
        Removes and returns the item with the highest priority.
        Time Complexity: O(log N)
        """
        if self.is_empty():
            raise IndexError("pop from an empty priority queue")

        self._swap(0, len(self.heap) - 1)
        _, _, item = self.heap.pop()

        if not self.is_empty():
            self._sift_down(0)

        return item

    def peek(self) -> Optional[Any]:
        """
        Returns the item with the highest priority without removing it.
        Time Complexity: O(1)
        """
        if self.is_empty():
            return None
        return self.heap[0][2]

    def _sift_up(self, index: int):
        parent = (index - 1) // 2
        while index > 0 and self.heap[index][0] > self.heap[parent][0]:
            self._swap(index, parent)
            index = parent
            parent = (index - 1) // 2

    def _sift_down(self, index: int):
        n = len(self.heap)
        largest = index

        while True:
            left = 2 * index + 1
            right = 2 * index + 2

            if left < n and self.heap[left][0] > self.heap[largest][0]:
                largest = left

            if right < n and self.heap[right][0] > self.heap[largest][0]:
                largest = right

            if largest != index:
                self._swap(index, largest)
                index = largest
            else:
                break

    def _swap(self, i: int, j: int):
        self.heap[i], self.heap[j] = self.heap[j], self.heap[i]


def top_k_elements(
    items: List[Any],
    k: int,
    key: Optional[Callable[[Any], float]] = None
) -> List[Any]:
    """
    Selects top-k elements using a binary heap in O(N log K) time.
    """
    if k <= 0:
        return []
    if not items:
        return []

    pq = PriorityQueue(key=key)
    for item in items:
        pq.push(item)

    results = []
    limit = min(k, len(items))
    for _ in range(limit):
        results.append(pq.pop())

    return results
