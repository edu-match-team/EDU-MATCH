"""
DSA Sorting Algorithms for EduMatch
Module: dsa.sorting
Author: Vishu & Team (BCA AI & Data Science)

Implements Merge Sort and Quick Sort for ranking providers by match score.

Theoretical Complexity Analysis:
  - Merge Sort:
      Best Case:    O(N log N)
      Average Case: O(N log N)
      Worst Case:   O(N log N)
      Space:        O(N) auxiliary space
      Stability:    Stable (preserves original order for equal scores)

  - Quick Sort:
      Best Case:    O(N log N)
      Average Case: O(N log N)
      Worst Case:   O(N^2)
      Space:        O(log N) recursion stack
"""

from typing import List, Any, Callable


def merge_sort(items: List[Any], key: Callable[[Any], Any] = lambda x: x, reverse: bool = False) -> List[Any]:
    """
    Standard Divide-and-Conquer Merge Sort implementation.
    Guarantees stable O(N log N) time complexity.
    """
    if len(items) <= 1:
        return list(items)

    mid = len(items) // 2
    left = merge_sort(items[:mid], key=key, reverse=reverse)
    right = merge_sort(items[mid:], key=key, reverse=reverse)

    return _merge(left, right, key, reverse)


def _merge(left: List[Any], right: List[Any], key: Callable[[Any], Any], reverse: bool) -> List[Any]:
    merged = []
    i = 0
    j = 0

    while i < len(left) and j < len(right):
        left_val = key(left[i])
        right_val = key(right[j])

        if reverse:
            # For descending order (highest score first)
            if left_val >= right_val:
                merged.append(left[i])
                i += 1
            else:
                merged.append(right[j])
                j += 1
        else:
            # Ascending order
            if left_val <= right_val:
                merged.append(left[i])
                i += 1
            else:
                merged.append(right[j])
                j += 1

    merged.extend(left[i:])
    merged.extend(right[j:])
    return merged


def quick_sort(items: List[Any], key: Callable[[Any], Any] = lambda x: x, reverse: bool = False) -> List[Any]:
    """
    In-place Partition Quick Sort implementation.
    Average Time: O(N log N)
    """
    arr = list(items)
    _quicksort_helper(arr, 0, len(arr) - 1, key, reverse)
    return arr


def _quicksort_helper(arr: List[Any], low: int, high: int, key: Callable[[Any], Any], reverse: bool):
    if low < high:
        p_idx = _partition(arr, low, high, key, reverse)
        _quicksort_helper(arr, low, p_idx - 1, key, reverse)
        _quicksort_helper(arr, p_idx + 1, high, key, reverse)


def _partition(arr: List[Any], low: int, high: int, key: Callable[[Any], Any], reverse: bool) -> int:
    pivot = key(arr[high])
    i = low - 1

    for j in range(low, high):
        curr = key(arr[j])
        condition = (curr >= pivot) if reverse else (curr <= pivot)
        if condition:
            i += 1
            arr[i], arr[j] = arr[j], arr[i]

    arr[i + 1], arr[high] = arr[high], arr[i + 1]
    return i + 1
