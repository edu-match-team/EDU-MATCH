from flask import Blueprint, jsonify, request
from backend.database.queries import get_all_providers_with_skills
from dsa.matching import match_and_rank_providers

matching_bp = Blueprint("matching", __name__, url_prefix="/api/matching")


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

    # 3. Fetch candidate providers from SQLite
    all_providers = get_all_providers_with_skills()

    # 4. Execute DSA Matching & Ranking Algorithm
    ranked_results = match_and_rank_providers(
        providers=all_providers,
        required_skills=required_skills,
        student_budget=budget,
        strict_budget=strict_budget,
        category=category
    )

    return jsonify({
        "success": True,
        "count": len(ranked_results),
        "total_evaluated": len(all_providers),
        "results": ranked_results,
        "dsa_metadata": {
            "algorithm": "Multi-Criteria Composite Match Scoring & Stable Merge Sort",
            "scoring_formula": "TotalScore = (0.55 * SkillScore) + (0.20 * BudgetScore) + (0.15 * AvailabilityScore) + (0.10 * RatingScore)",
            "time_complexity": "O(N * M + N log N) where N is provider count and M is skill count",
            "space_complexity": "O(N) auxiliary space",
            "data_structures_used": ["Hash Sets for O(1) skill intersection", "Dynamic Array / List", "Divide-and-Conquer Merge Sort"]
        }
    }), 200


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

