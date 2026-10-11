"""
Hash Table Cache and Indexing for EduMatch
Module: dsa.hash_table
Author: Vishu & Team (BCA AI & Data Science)

Demonstrates custom Hash Table structure with separate chaining
for O(1) average-time provider profile caching and lookup.
"""

from typing import Any, List, Optional, Tuple


class HashTable:
    def __init__(self, capacity: int = 64):
        self.capacity = capacity
        self.size = 0
        self.buckets: List[List[Tuple[str, Any]]] = [[] for _ in range(self.capacity)]

    def _hash(self, key: str) -> int:
        hash_val = 0
        for char in str(key):
            hash_val = (hash_val * 31 + ord(char)) % self.capacity
        return hash_val

    def put(self, key: str, value: Any):
        index = self._hash(key)
        bucket = self.buckets[index]

        for i, (k, v) in enumerate(bucket):
            if k == key:
                bucket[i] = (key, value)
                return

        bucket.append((key, value))
        self.size += 1

        # Rehash if load factor exceeds 0.75
        if self.size / self.capacity > 0.75:
            self._resize(self.capacity * 2)

    def get(self, key: str) -> Optional[Any]:
        index = self._hash(key)
        for k, v in self.buckets[index]:
            if k == key:
                return v
        return None

    def contains(self, key: str) -> bool:
        return self.get(key) is not None

    def _resize(self, new_capacity: int):
        old_buckets = self.buckets
        self.capacity = new_capacity
        self.buckets = [[] for _ in range(new_capacity)]
        self.size = 0

        for bucket in old_buckets:
            for k, v in bucket:
                self.put(k, v)
