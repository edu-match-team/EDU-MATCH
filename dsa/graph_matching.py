"""
DSA Graph Matching & Recommendation Network for EduMatch
Module: dsa.graph_matching
Author: Vishu & Team (BCA AI & Data Science)

Models the Student-Provider interaction network as an Adjacency-List Graph.
Implements:
1. Breadth-First Search (BFS): For discovering k-degree collaboration connections.
2. Dijkstra's Algorithm: For computing the highest affinity / shortest matching path.
3. Bipartite Interaction Graph: For modeling Student -> Provider relationship edges.

Theoretical Complexity:
- BFS Traversal: O(V + E)
- Dijkstra's Algorithm: O((V + E) log V) with min-priority queue
"""

from collections import deque
import heapq
from typing import Any, Dict, List, Optional, Set, Tuple


class CollaborationGraph:
    """
    Weighted Adjacency-List Graph representation.
    Nodes can be Students ('S_1'), Providers ('P_5'), or Project Categories.
    """

    def __init__(self):
        # node -> list of (neighbor, weight, metadata)
        self.adj: Dict[str, List[Tuple[str, float, Dict[str, Any]]]] = {}
        self.node_metadata: Dict[str, Dict[str, Any]] = {}

    def add_node(self, node_id: str, metadata: Optional[Dict[str, Any]] = None):
        if node_id not in self.adj:
            self.adj[node_id] = []
            self.node_metadata[node_id] = metadata or {}

    def add_edge(
        self,
        u: str,
        v: str,
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
        bidirectional: bool = True
    ):
        self.add_node(u)
        self.add_node(v)
        self.adj[u].append((v, weight, metadata or {}))
        if bidirectional:
            self.adj[v].append((u, weight, metadata or {}))

    def get_neighbors(self, node_id: str) -> List[Tuple[str, float]]:
        return [(nbr, w) for nbr, w, _ in self.adj.get(node_id, [])]

    def bfs_recommendations(self, start_node: str, max_depth: int = 2) -> List[Dict[str, Any]]:
        """
        Explores network up to max_depth using Breadth-First Search (BFS).
        Finds providers connected via shared project categories or peers.
        Time Complexity: O(V + E)
        """
        if start_node not in self.adj:
            return []

        visited: Set[str] = {start_node}
        queue = deque([(start_node, 0)])
        recommendations = []

        while queue:
            curr, depth = queue.popleft()

            if depth >= max_depth:
                continue

            for neighbor, weight, meta in self.adj.get(curr, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))
                    recommendations.append({
                        "node_id": neighbor,
                        "distance_degree": depth + 1,
                        "weight": weight,
                        "metadata": self.node_metadata.get(neighbor, meta)
                    })

        return recommendations

    def dijkstra_best_path(self, start_node: str, target_node: str) -> Optional[Tuple[float, List[str]]]:
        """
        Computes the optimal path between start_node and target_node using Dijkstra's algorithm.
        Time Complexity: O((V + E) log V)
        """
        if start_node not in self.adj or target_node not in self.adj:
            return None

        # Min-Heap stores (cost, current_node, path)
        pq: List[Tuple[float, str, List[str]]] = [(0.0, start_node, [start_node])]
        min_costs: Dict[str, float] = {start_node: 0.0}

        while pq:
            curr_cost, curr_node, path = heapq.heappop(pq)

            if curr_node == target_node:
                return curr_cost, path

            if curr_cost > min_costs.get(curr_node, float("inf")):
                continue

            for neighbor, weight, _ in self.adj.get(curr_node, []):
                # Ensure positive weights for Dijkstra
                edge_cost = max(0.1, weight)
                new_cost = curr_cost + edge_cost

                if new_cost < min_costs.get(neighbor, float("inf")):
                    min_costs[neighbor] = new_cost
                    heapq.heappush(pq, (new_cost, neighbor, path + [neighbor]))

        return None
