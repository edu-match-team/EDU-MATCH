"""
DSA LRU Cache (Doubly Linked List + Hash Map) for EduMatch
Module: dsa.lru_cache
Author: Vishu & Team (BCA AI & Data Science)

Implements an O(1) Least Recently Used Cache using:
1. Doubly Linked List for tracking usage order (recency).
2. Hash Map (Dictionary) for O(1) key-to-node pointer lookups.

Theoretical Complexity:
- get(key): O(1)
- put(key, value): O(1)
- Space: O(Capacity)
"""

from typing import Any, Dict, Optional


class DListNode:
    """Node in a Doubly Linked List."""
    def __init__(self, key: str = "", value: Any = None):
        self.key: str = key
        self.value: Any = value
        self.prev: Optional["DListNode"] = None
        self.next: Optional["DListNode"] = None


class LRUCache:
    """
    Least Recently Used Cache with capacity constraints.
    Evicts the least recently accessed item when full.
    """

    def __init__(self, capacity: int = 128):
        if capacity <= 0:
            raise ValueError("Capacity must be positive")
        self.capacity: int = capacity
        self.map: Dict[str, DListNode] = {}

        # Sentinel pseudo-head and pseudo-tail nodes
        self.head = DListNode("__HEAD__")
        self.tail = DListNode("__TAIL__")
        self.head.next = self.tail
        self.tail.prev = self.head

        self.hits: int = 0
        self.misses: int = 0

    def _remove(self, node: DListNode):
        """Unlinks a node from the doubly linked list."""
        prev_node = node.prev
        next_node = node.next
        if prev_node:
            prev_node.next = next_node
        if next_node:
            next_node.prev = prev_node

    def _add_to_front(self, node: DListNode):
        """Inserts a node right after head (most recently used position)."""
        node.next = self.head.next
        node.prev = self.head
        if self.head.next:
            self.head.next.prev = node
        self.head.next = node

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieves an item by key in O(1) time and marks it as recently used.
        """
        key_str = str(key)
        if key_str in self.map:
            node = self.map[key_str]
            self._remove(node)
            self._add_to_front(node)
            self.hits += 1
            return node.value

        self.misses += 1
        return None

    def put(self, key: str, value: Any):
        """
        Inserts or updates an item in O(1) time.
        Evicts the oldest node if capacity is reached.
        """
        key_str = str(key)
        if key_str in self.map:
            node = self.map[key_str]
            node.value = value
            self._remove(node)
            self._add_to_front(node)
            return

        if len(self.map) >= self.capacity:
            # Evict least recently used node (before tail)
            lru = self.tail.prev
            if lru and lru != self.head:
                self._remove(lru)
                if lru.key in self.map:
                    del self.map[lru.key]

        new_node = DListNode(key_str, value)
        self.map[key_str] = new_node
        self._add_to_front(new_node)

    def clear(self):
        self.map.clear()
        self.head.next = self.tail
        self.tail.prev = self.head
        self.hits = 0
        self.misses = 0

    def stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        hit_ratio = round((self.hits / total) * 100.0, 2) if total > 0 else 0.0
        return {
            "capacity": self.capacity,
            "size": len(self.map),
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio_percent": hit_ratio
        }
