# EduMatch - Data Structures & Algorithms (DSA) Technical Architecture Guide

This comprehensive reference manual documents how **Data Structures and Algorithms (DSA)** power the EduMatch platform.

---

## 1. Executive Summary & Architecture Philosophy

EduMatch is built with an **algorithmic-first design**. Rather than delegating sorting, ranking, searching, and recommendations solely to SQL database queries, EduMatch implements standard and advanced data structures directly in Python.

```
                      +---------------------------------------+
                      |       EduMatch Frontend (UI)          |
                      |  (orders.html, dashboard.html, etc.)  |
                      +-------------------+-------------------+
                                          |
                         REST API Requests (JSON / HTTP)
                                          |
                                          v
                      +---------------------------------------+
                      |         Flask API Controllers         |
                      |   (requests.py, matching.py, etc.)    |
                      +-------------------+-------------------+
                                          |
                      +-------------------+-------------------+
                      |          Core DSA Engine              |
                      +---------------------------------------+
                      | [1] MergeSort (dsa/sorting.py)        |
                      | [2] Priority Queue (dsa/pq.py)        |
                      | [3] LRU Cache (dsa/lru_cache.py)      |
                      | [4] Trie & Binary Search (searching)  |
                      | [5] Separate Chaining Hash Table      |
                      | [6] Bipartite Graph BFS & Dijkstra    |
                      | [7] Set Intersection Matching         |
                      +-------------------+-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |           SQLite Database             |
                      |           (Raw Data Store)            |
                      +---------------------------------------+
```

---

## 2. Comprehensive Catalog of Data Structures & Algorithms

| # | Data Structure / Algorithm | Source File | Where Used in EduMatch | Time Complexity | Space Complexity |
|---|---|---|---|---|---|
| **1** | **MergeSort** (Divide & Conquer) | `dsa/sorting.py` | `backend/routes/requests.py` (`get_my_projects`) & `frontend/student/orders.html` | **$O(N \log N)$** (Best, Avg, Worst) | **$O(N)$** auxiliary space |
| **2** | **Priority Queue (Max-Heap)** | `dsa/priority_queue.py` | `backend/routes/matching.py` (Top-$K$ ranked matches) & `backend/routes/requests.py` | **$O(N \log K)$** for Top-$K$, **$O(\log N)$** push/pop | **$O(K)$** or **$O(N)$** |
| **3** | **LRU Cache** (Doubly-Linked List + Hash Map) | `dsa/lru_cache.py` | `backend/routes/matching.py` (`match_lru_cache`) | **$O(1)$** Get, **$O(1)$** Put, **$O(1)$** Eviction | **$O(C)$** where $C$ is capacity |
| **4** | **Trie (Prefix Tree)** | `dsa/searching.py` | `backend/routes/search.py` & `frontend/student/search.html` | **$O(L)$** Insert/Search ($L$ = string length) | **$O(\Sigma \cdot L \cdot N)$** |
| **5** | **Binary Search** | `dsa/searching.py` | Provider filtering, budget range lookups, rating cuts | **$O(\log N)$** search | **$O(1)$** auxiliary space |
| **6** | **Hash Table** (Separate Chaining) | `dsa/hash_table.py` | Fast provider profile retrieval, in-memory lookups | **$O(1)$** average lookup/insert, **$O(N)$** worst | **$O(N + B)$** ($B$ = bucket count) |
| **7** | **Bipartite Graph (BFS & Dijkstra)** | `dsa/graph_matching.py` | `GET /api/matching/graph-recommendations/<student_id>` | BFS: **$O(V + E)$**, Dijkstra: **$O((V + E) \log V)$** | **$O(V + E)$** |
| **8** | **Set Theory Matching (Jaccard)** | `dsa/matching.py` | `POST /api/matching/find-matches` | **$O(M \cdot S)$** ($M$ = providers, $S$ = avg skills) | **$O(S)$** |

---

## 3. Deep Dive into Each Algorithm

### 1. MergeSort (`dsa/sorting.py`)
- **How it works**: Uses the **Divide and Conquer** paradigm. Recursively splits the array into two halves until single-element subproblems remain, then merges them in sorted order using key functions (`created_at`, `budget`, or `match_score`).
- **Why MergeSort over QuickSort?**: MergeSort is **guaranteed $O(N \log N)$** in all cases (never degrades to $O(N^2)$ like unbalanced QuickSort) and is **stable**, preserving the relative order of items with identical dates or scores.
- **Project Integration**:
  - `backend/routes/requests.py`: Combines direct service requests and student-posted requirements, then sorts them chronologically using `merge_sort(all_items, key="created_at", reverse=True)`.
  - `frontend/student/orders.html`: Renders the sorted list with matching status cards.

### 2. Priority Queue & Top-$K$ Max-Heap (`dsa/priority_queue.py`)
- **How it works**: Implemented using an array-backed **Complete Binary Tree** satisfying the heap invariant ($Parent \ge Child$ for Max-Heap).
- **Mathematical Top-$K$ Optimization**: Rather than sorting $N$ total providers in $O(N \log N)$, `top_k_elements` maintains a Min-Heap of size $K$. Each element is compared in $O(\log K)$, achieving **$O(N \log K)$** time. When $N = 10,000$ and $K = 5$, this reduces comparisons by over 90%.
- **Project Integration**:
  - In `backend/routes/matching.py`, after computing compatibility scores across all available providers, the Top-$K$ most compatible providers are extracted using `top_k_elements(all_scored_providers, k=limit)`.

### 3. LRU Cache (`dsa/lru_cache.py`)
- **How it works**: Combines two classic data structures:
  1. **Doubly-Linked List**: Contains nodes with `prev` and `next` pointers. The most recently used node is moved to the `head`, and the oldest is at `tail`. Moving or deleting a node takes $O(1)$.
  2. **Hash Map (`dict`)**: Maps search keys (e.g., student skill set hash) to node references for $O(1)$ pointer access.
- **Project Integration**:
  - In `backend/routes/matching.py`, identical search queries reuse cached results instantly without recalculating scores or hitting the database.

### 4. Trie / Prefix Tree (`dsa/searching.py`)
- **How it works**: A tree where each node represents a character. Shared prefixes share branches.
- **Why it matters**: Autocompleting "py" -> "python", "pytorch" executes in $O(L)$ where $L$ is query length, regardless of whether there are 100 or 1,000,000 items in the database.
- **Project Integration**:
  - Powers provider search suggestions and skill filters in `search.html`.

### 5. Custom Hash Table with Separate Chaining (`dsa/hash_table.py`)
- **How it works**: Implements a custom hash function using polynomial rolling hash with a prime multiplier ($31$), dynamic bucket array, and singly linked lists for resolving collisions via separate chaining.
- **Project Integration**:
  - Used for fast in-memory indexing of user profiles by ID.

### 6. Bipartite Collaboration Graph (`dsa/graph_matching.py`)
- **How it works**: Models the EduMatch ecosystem as a graph $G = (V, E)$ where vertices $V = \{Students\} \cup \{Skills\} \cup \{Providers\}$.
  - **BFS (Breadth-First Search)**: Explores 2-hop paths ($Student \to Skill \to Provider$) to recommend providers with shared skill overlaps.
  - **Dijkstra's Shortest Path**: Uses edge weights representing inverse ratings/costs to find the most cost-effective path to project completion.
- **Project Integration**:
  - Exposed via `GET /api/matching/graph-recommendations/<student_id>`.

---

## 4. Live Verification Endpoint

EduMatch includes a live diagnostic endpoint exposing internal DSA state:
```http
GET /api/matching/dsa-overview
```
Sample response:
```json
{
  "status": "success",
  "dsa_features_active": [
    "MergeSort (dsa/sorting.py)",
    "PriorityQueue / Max-Heap (dsa/priority_queue.py)",
    "LRU Cache (dsa/lru_cache.py)",
    "Trie & Binary Search (dsa/searching.py)",
    "Separate Chaining Hash Table (dsa/hash_table.py)",
    "Bipartite Graph BFS & Dijkstra (dsa/graph_matching.py)",
    "Set Theory Compatibility (dsa/matching.py)"
  ],
  "lru_cache_stats": {
    "size": 2,
    "capacity": 50,
    "hits": 14,
    "misses": 3
  },
  "graph_network_stats": {
    "total_nodes": 12,
    "students": 4,
    "providers": 5,
    "skills": 3
  }
}
```

---

## 5. Academic Viva / Exam Questions & Answers

### Q1: Why did you use MergeSort instead of Python's built-in `list.sort()`?
> **Answer**: `list.sort()` in Python uses Timsort (a hybrid of MergeSort and InsertionSort). To demonstrate foundational DSA principles for academic evaluation, we implemented an explicit, instrumented `merge_sort` function. This guarantees $O(N \log N)$ worst-case time complexity, stability, and allows custom tracking of comparisons and recursive stack depth.

### Q2: What is the benefit of using a Max-Heap for Top-$K$ recommendations?
> **Answer**: Sorting $N$ items requires $O(N \log N)$ time. By using a Min-Heap bounded to size $K$, each element is evaluated in $O(\log K)$, giving a total time complexity of $O(N \log K)$. When $K \ll N$ (e.g., top 5 out of thousands of providers), this saves substantial CPU cycles and memory.

### Q3: How does your LRU Cache achieve $O(1)$ time for both get and put?
> **Answer**: A Hash Map alone gives $O(1)$ lookup, but ordering requires scanning. An array maintains order, but insertion/deletion requires $O(N)$ shifts. By coupling a **Doubly-Linked List** (for $O(1)$ removal and addition at the head) with a **Hash Map** (for $O(1)$ node lookup), both `get` and `put` operations run in strictly $O(1)$ time.

### Q4: How is graph theory applied to provider matching?
> **Answer**: We construct a Bipartite Graph connecting Student vertices to Provider vertices through Skill edges. Running Breadth-First Search (BFS) allows us to discover collaborative 2-hop connections, while Dijkstra's algorithm finds the optimal path minimizing cost and maximizing provider rating.
