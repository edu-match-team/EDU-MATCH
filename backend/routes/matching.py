from flask import Blueprint, jsonify, request
from backend.database.queries import get_all_providers_with_skills
from dsa.matching import match_and_rank_providers
from dsa.lru_cache import LRUCache
from dsa.graph_matching import CollaborationGraph
from dsa.priority_queue import top_k_elements

matching_bp = Blueprint("matching", __name__, url_prefix="/api/matching")

# DSA Structure 1: High-speed O(1) LRU Cache for search & match queries
match_lru_cache = LRUCache(capacity=64)


@matching_bp.route("/find-matches", methods=["POST"])
def find_matches():
    data = request.get_json(silent=True) or {}
    
    # 1. Parse required skills
    raw_skills = data.get("skills", [])
    if isinstance(raw_skills, str):
        required_skills = [s.strip() for s in raw_skills.split(",") if s.strip()]
    elif isinstance(raw_skills, list):
        required_skills = [str(s).strip() for s in raw_skills if str(s).strip()]
    else:
        required_skills = []

    # 2. Parse budget
    try:
        budget = float(data.get("budget")) if data.get("budget") is not None else None
    except (ValueError, TypeError):
        budget = None

    category = data.get("category", "")
    strict_budget = bool(data.get("strict_budget", False))

    # Check DSA LRU Cache for instant O(1) hit
    cache_key = f"{','.join(sorted(required_skills))}|{budget}|{category}|{strict_budget}"
    cached_payload = match_lru_cache.get(cache_key)
    if cached_payload:
        cached_payload["cached"] = True
        cached_payload["cache_stats"] = match_lru_cache.stats()
        return jsonify(cached_payload), 200

    # 3. Fetch candidate providers from SQLite
    all_providers = get_all_providers_with_skills()

    # 4. Execute DSA Matching & Ranking Algorithm (Set Theory + Merge Sort)
    ranked_results = match_and_rank_providers(
        providers=all_providers,
        required_skills=required_skills,
        student_budget=budget,
        strict_budget=strict_budget,
        category=category
    )

    # DSA Structure 2: Max-Heap Priority Queue for Top-3 Best Fit Providers
    top_3_spotlight = top_k_elements(
        ranked_results,
        k=min(3, len(ranked_results)),
        key=lambda x: float(x.get("match_score", 0))
    )

    response_payload = {
        "success": True,
        "count": len(ranked_results),
        "total_evaluated": len(all_providers),
        "results": ranked_results,
        "top_spotlight": top_3_spotlight,
        "cached": False,
        "cache_stats": match_lru_cache.stats(),
        "dsa_metadata": {
            "algorithm": "Multi-Criteria Composite Match Scoring & Stable Merge Sort",
            "scoring_formula": "TotalScore = (0.55 * SkillScore) + (0.20 * BudgetScore) + (0.15 * AvailabilityScore) + (0.10 * RatingScore)",
            "time_complexity": "O(N * M + N log N) where N is provider count and M is skill count",
            "space_complexity": "O(N) auxiliary space",
            "data_structures_used": [
                "Hash Sets (O(1) skill intersection)",
                "Divide-and-Conquer Merge Sort (O(N log N))",
                "Binary Max-Heap Priority Queue (O(N log K) top-K spotlight)",
                "Doubly-Linked List + Hash Map LRU Cache (O(1) memoization)"
            ]
        }
    }

    # Store in LRU Cache
    match_lru_cache.put(cache_key, dict(response_payload))

    return jsonify(response_payload), 200


@matching_bp.route("/suggestions", methods=["GET"])
def get_search_suggestions():
    """
    Real-time Google-like suggestions powered by SkillTrie (Prefix Tree - O(L)).
    Suggests skills, titles, technologies, and academic project categories.
    """
    from dsa.searching import SkillTrie
    from backend.database.connection import get_db

    query = (request.args.get("q") or "").strip()
    if not query:
        return jsonify({"success": True, "suggestions": []}), 200

    # Build and populate Trie dynamically
    trie = SkillTrie()

    # 1. Base academic project topics & technologies
    seed_keywords = [
        "Python", "Python Machine Learning", "Python Flask Web App", "Python Django", "Pandas",
        "Machine Learning", "ML Model Training", "Data Science", "Data Analysis",
        "Web Development", "Full Stack Web Development", "React", "React Frontend",
        "JavaScript", "HTML & CSS", "Flask", "SQL", "Database Design", "PostgreSQL",
        "Deep Learning", "Artificial Intelligence", "NLP Natural Language Processing",
        "Computer Vision", "App Development", "Android App", "Flutter Mobile App",
        "C++", "C++ Algorithms", "DSA Data Structures", "Java", "PHP",
        "Cyber Security", "Blockchain", "Cloud Computing", "AWS", "IoT Internet of Things",
        "Insight & Analytics", "Instructor & Mentor Support", "Installation & Setup Guide",
        "Instant Chat & Project Collaboration", "Instruction & Code Review", "Inspect Database Schema"
    ]
    for kw in seed_keywords:
        trie.insert(kw, kw)

    # 2. Add all skills from database
    try:
        db = get_db()
        db_skills = db.execute("SELECT name FROM skills").fetchall()
        for row in db_skills:
            trie.insert(row["name"], row["name"])

        # Add provider titles & categories
        prov_rows = db.execute("SELECT DISTINCT title, category FROM provider_profiles").fetchall()
        for pr in prov_rows:
            if pr["title"]:
                trie.insert(pr["title"], pr["title"])
            if pr["category"]:
                trie.insert(pr["category"], pr["category"])
    except Exception:
        pass

    # Lookup prefix in Trie
    matched_suggestions = trie.search_prefix(query)

    # Deduplicate while preserving order and limit to top 8 suggestions
    seen = set()
    unique_suggestions = []
    for item in matched_suggestions:
        if item.lower() not in seen:
            seen.add(item.lower())
            unique_suggestions.append(item)
            if len(unique_suggestions) >= 8:
                break

    return jsonify({
        "success": True,
        "query": query,
        "count": len(unique_suggestions),
        "suggestions": unique_suggestions,
        "dsa_metadata": {
            "data_structure": "Trie (Prefix Tree)",
            "lookup_complexity": "O(L) where L is query length"
        }
    }), 200


@matching_bp.route("/graph-recommendations", methods=["GET"])
def get_graph_recommendations():
    """
    Graph-based Collaborative Filtering using Breadth-First Search (BFS)
    over a Student-Provider Interaction Graph.
    Time Complexity: O(V + E)
    """
    from backend.database.connection import get_db
    db = get_db()

    student_id = request.args.get("student_id", "4")
    graph = CollaborationGraph()

    # Build graph from successful collaboration requests
    try:
        collabs = db.execute("""
            SELECT cr.student_id, cr.provider_id, cr.status, cr.offered_budget, u.full_name as provider_name
            FROM collaboration_requests cr
            JOIN users u ON cr.provider_id = u.id
        """).fetchall()

        for c in collabs:
            s_node = f"S_{c['student_id']}"
            p_node = f"P_{c['provider_id']}"
            weight = 1.0 if c["status"] in ("accepted", "in_progress", "completed") else 2.5
            graph.add_edge(s_node, p_node, weight=weight, metadata={
                "provider_id": c["provider_id"],
                "provider_name": c["provider_name"]
            })
    except Exception:
        pass

    start_node = f"S_{student_id}"
    recommendations = graph.bfs_recommendations(start_node=start_node, max_depth=3)

    return jsonify({
        "success": True,
        "start_node": start_node,
        "recommendations": recommendations,
        "dsa_metadata": {
            "data_structure": "Bipartite Adjacency List Graph",
            "traversal_algorithm": "Breadth-First Search (BFS)",
            "time_complexity": "O(V + E) where V is Users/Providers and E is Collaborations"
        }
    }), 200


@matching_bp.route("/dsa-overview", methods=["GET"])
def get_dsa_overview():
    """
    Live DSA System Monitor:
    Returns details on all 7 Data Structures & Algorithms running in EduMatch.
    """
    return jsonify({
        "success": True,
        "platform": "EduMatch DSA Engine",
        "author": "Vishwajeet Rawat & Team (BCA AI & Data Science)",
        "algorithms_and_structures": [
            {
                "name": "Merge Sort",
                "module": "dsa.sorting",
                "usage": "Chronological request ordering and match score ranking",
                "time_complexity": "O(N log N) Best, Average, Worst",
                "space_complexity": "O(N) auxiliary space",
                "property": "Stable divide-and-conquer"
            },
            {
                "name": "Binary Heap Priority Queue",
                "module": "dsa.priority_queue",
                "usage": "Top-K provider spotlight selection & urgent project scheduling",
                "time_complexity": "O(log N) push/pop, O(N log K) top-K selection",
                "space_complexity": "O(N)",
                "property": "Max-Heap tree array representation"
            },
            {
                "name": "Trie (Prefix Tree)",
                "module": "dsa.searching",
                "usage": "Instant search autocomplete for skills, categories, and technologies",
                "time_complexity": "O(L) where L is string prefix length",
                "space_complexity": "O(ALPHABET_SIZE * N * L)",
                "property": "Retrieval tree with Depth-First Search collect"
            },
            {
                "name": "LRU Cache (Doubly Linked List + Hash Map)",
                "module": "dsa.lru_cache",
                "usage": "Sub-millisecond caching of provider match query payloads",
                "time_complexity": "O(1) get, O(1) put",
                "space_complexity": "O(Capacity)",
                "property": "Sentinel head/tail linked list + dictionary mapping"
            },
            {
                "name": "Hash Table (Separate Chaining)",
                "module": "dsa.hash_table",
                "usage": "O(1) average lookup and profile caching",
                "time_complexity": "O(1) Average, O(N) Worst (with automatic resize at 0.75 load)",
                "space_complexity": "O(N)",
                "property": "Polynomial rolling hash with bucket chaining"
            },
            {
                "name": "Graph (BFS & Dijkstra)",
                "module": "dsa.graph_matching",
                "usage": "Peer recommendations and collaboration distance graph",
                "time_complexity": "BFS: O(V + E), Dijkstra: O((V + E) log V)",
                "space_complexity": "O(V + E)",
                "property": "Weighted Adjacency List"
            },
            {
                "name": "Binary Search",
                "module": "dsa.searching",
                "usage": "Threshold boundary cutoffs in sorted provider lists",
                "time_complexity": "O(log N)",
                "space_complexity": "O(1)",
                "property": "Logarithmic binary division"
            }
        ],
        "live_cache_metrics": match_lru_cache.stats()
    }), 200


