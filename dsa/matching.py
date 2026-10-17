"""
DSA Matching & Intelligent Search Engine for EduMatch
Module: dsa.matching
Author: Vishu & Team (BCA AI & Data Science)

Calculates matching suitability between a student's search queries, required skills,
and candidate providers using:
1. Trie & Multi-Token Text Relevance (Title, Role, Skills, Bio, Services)
2. Graph-Based Domain & Concept Expansion (e.g. AI <-> ML <-> NLP, App <-> Mobile <-> Flutter)
3. Set Theory (Skill Intersection & Jaccard Similarity)
4. Multi-Criteria Composite Scoring
5. Binary Max-Heap Priority Queue for O(N log N) Heap Ranking
"""

import re
from typing import List, Dict, Any, Optional, Set
from dsa.priority_queue import PriorityQueue

# Graph of related concept clusters for semantic domain expansion
CONCEPT_GRAPH: Dict[str, Set[str]] = {
    "ai": {"artificial intelligence", "machine learning", "ml", "deep learning", "nlp", "tensorflow", "pytorch", "neural", "computer vision", "senior ai", "researcher"},
    "ml": {"machine learning", "ai", "deep learning", "nlp", "tensorflow", "scikit", "pandas", "data science"},
    "app": {"app development", "mobile app", "android", "flutter", "react native", "ios", "application", "mobile developer"},
    "web": {"web developer", "web development", "frontend", "backend", "full stack", "html", "css", "javascript", "react", "flask", "django", "node"},
    "python": {"flask", "django", "machine learning", "data science", "fastapi", "pandas", "numpy"},
    "data": {"data science", "data analysis", "pandas", "sql", "analytics", "visualization", "machine learning"},
    "senior": {"lead", "mentor", "expert", "senior developer", "researcher", "architect"}
}


def normalize_token(text: str) -> str:
    """Normalize text: strip, lowercase, remove punctuation."""
    return re.sub(r"[^\w\s]", "", str(text or "")).strip().lower()


def get_expanded_concepts(query: str) -> Set[str]:
    """Expands query tokens using the CONCEPT_GRAPH."""
    norm_q = normalize_token(query)
    tokens = [t for t in norm_q.split() if t]
    concepts = set(tokens)
    if norm_q:
        concepts.add(norm_q)

    for token in tokens:
        if token in CONCEPT_GRAPH:
            concepts.update(CONCEPT_GRAPH[token])
        for k, related in CONCEPT_GRAPH.items():
            if token in k or k in token:
                concepts.update(related)
    return concepts


def calculate_query_relevance(provider: Dict[str, Any], query: str) -> float:
    """
    Computes text relevance score (0.0 to 100.0) between search query and provider profile.
    Checks:
    - Provider Name (exact/partial)
    - Professional Title / Role (highest priority)
    - Skills & Technologies
    - Services Offered
    - Bio / Description
    """
    if not query or not query.strip():
        return 100.0  # No query filter active -> full baseline score

    q_clean = normalize_token(query)
    q_tokens = [t for t in q_clean.split() if t]
    if not q_tokens:
        return 100.0

    p_name = normalize_token(provider.get("name") or provider.get("full_name") or "")
    p_title = normalize_token(provider.get("title") or provider.get("role") or provider.get("professional_title") or "")
    p_category = normalize_token(provider.get("category") or "")
    p_bio = normalize_token(provider.get("bio") or provider.get("description") or "")

    raw_skills = provider.get("skills", [])
    if isinstance(raw_skills, str):
        raw_skills = [s.strip() for s in raw_skills.split(",") if s.strip()]
    skills_joined = normalize_token(" ".join(raw_skills))

    services_text = ""
    for s in provider.get("services", []):
        services_text += " " + normalize_token(s.get("title", "")) + " " + normalize_token(s.get("description", ""))

    all_provider_text = f"{p_name} {p_title} {p_category} {skills_joined} {services_text} {p_bio}"

    score = 0.0

    # 1. Exact Phrase Match in Title (e.g., "senior ai" in "Senior AI Researcher & Mentor")
    if q_clean in p_title:
        score += 80.0
    elif q_clean in p_name:
        score += 75.0
    elif q_clean in skills_joined:
        score += 70.0
    elif q_clean in services_text:
        score += 65.0
    elif q_clean in all_provider_text:
        score += 50.0

    # 2. Token Coverage (What percentage of user query words match title, name, skills)
    matched_title_tokens = sum(1 for t in q_tokens if t in p_title)
    matched_all_tokens = sum(1 for t in q_tokens if t in all_provider_text)

    # Title token match gets high reward
    score += (matched_title_tokens / len(q_tokens)) * 40.0
    # Overall token coverage
    score += (matched_all_tokens / len(q_tokens)) * 25.0

    # 3. Concept Graph Semantic Expansion
    expanded = get_expanded_concepts(query)
    concept_hits = sum(1 for c in expanded if c in all_provider_text)
    if concept_hits > 0:
        score += min(20.0, concept_hits * 5.0)

    # Cap between 0 and 100
    return min(100.0, score)


def calculate_match_score(
    provider: Dict[str, Any],
    query_or_skills: Any = None,
    required_skills: Optional[List[str]] = None,
    student_budget: Optional[float] = None,
    strict_budget: bool = False,
    query: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Evaluates a single provider against student requirements & search query.
    Backward compatible with positional required_skills list or query string.
    """
    if isinstance(query_or_skills, (list, tuple, set)):
        req_skills_list = list(query_or_skills)
        active_query = query or ""
    elif isinstance(query_or_skills, str):
        active_query = query_or_skills
        req_skills_list = required_skills or []
    else:
        active_query = query or ""
        req_skills_list = required_skills or []

    prov_price = float(provider.get("starting_price") or provider.get("price") or 0)

    # 1. Strict Budget Filter
    if strict_budget and student_budget is not None and student_budget > 0:
        if prov_price > student_budget:
            return None

    # 2. Query Relevance
    has_active_query = bool(active_query and active_query.strip())
    query_relevance = calculate_query_relevance(provider, active_query) if has_active_query else 100.0

    # If the user typed a specific query and the provider has zero relevance, heavily penalize
    if has_active_query and query_relevance < 15.0:
        query_relevance = 5.0

    # 3. Skill Overlap via Set Theory
    prov_skills_raw = provider.get("skills", [])
    if isinstance(prov_skills_raw, str):
        prov_skills_raw = [s.strip() for s in prov_skills_raw.split(",") if s.strip()]

    prov_skill_set = {normalize_token(s) for s in prov_skills_raw if s}
    req_skills_clean = [normalize_token(s) for s in req_skills_list if s]
    req_skill_set = set(req_skills_clean)

    matching_skills_set = set()
    for req in req_skill_set:
        for prov_s in prov_skill_set:
            if req in prov_s or prov_s in req:
                matching_skills_set.add(prov_s)

    if req_skill_set:
        skill_score = (len(matching_skills_set) / len(req_skill_set)) * 100.0
    else:
        skill_score = 100.0 if not has_active_query else query_relevance

    # 4. Budget Compatibility Score (0 to 100)
    if student_budget and student_budget > 0:
        if prov_price <= student_budget:
            ratio = prov_price / student_budget
            budget_score = max(40.0, 100.0 - (ratio * 35.0))
        else:
            budget_score = max(0.0, 100.0 - ((prov_price - student_budget) / student_budget * 100.0))
    else:
        budget_score = 80.0

    # 5. Availability Score (0 to 100)
    availability_str = str(provider.get("availability", "available")).lower()
    if availability_str == "available":
        availability_score = 100.0
    elif availability_str == "limited":
        availability_score = 65.0
    else:
        availability_score = 30.0

    # 6. Rating Bonus (0 to 5 mapped to 0 to 100)
    rating = float(provider.get("rating", 5.0) or 5.0)
    rating_score = min(100.0, (rating / 5.0) * 100.0)

    # 7. Composite Score Calculation
    if has_active_query:
        # Heavy weight on query relevance so exact title/keyword matches rank top
        total_score = (
            (0.55 * query_relevance) +
            (0.20 * skill_score) +
            (0.12 * budget_score) +
            (0.08 * availability_score) +
            (0.05 * rating_score)
        )
    else:
        # Standard matching formula
        total_score = (
            (0.55 * skill_score) +
            (0.20 * budget_score) +
            (0.15 * availability_score) +
            (0.10 * rating_score)
        )

    total_score = round(min(99.0, max(15.0, total_score)), 1)

    result_data = dict(provider)
    result_data.update({
        "match_score": total_score,
        "query_relevance": round(query_relevance, 1),
        "skill_score": round(skill_score, 1),
        "budget_score": round(budget_score, 1),
        "availability_score": round(availability_score, 1),
        "matching_skills": list(matching_skills_set),
        "matching_skill_count": len(matching_skills_set),
        "total_required_skills": len(req_skill_set)
    })
    return result_data


def match_and_rank_providers(
    providers: List[Dict[str, Any]],
    query_or_skills: Any = None,
    required_skills: Optional[List[str]] = None,
    student_budget: Optional[float] = None,
    strict_budget: bool = False,
    category: Optional[str] = None,
    query: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Evaluates candidate providers and ranks them using a Binary Max-Heap Priority Queue (Heap Sort).
    Time Complexity: O(N log N)
    """
    if isinstance(query_or_skills, (list, tuple, set)):
        req_skills_list = list(query_or_skills)
        active_query = query or ""
    elif isinstance(query_or_skills, str):
        active_query = query_or_skills
        req_skills_list = required_skills or []
    else:
        active_query = query or ""
        req_skills_list = required_skills or []

    eligible = []
    category_norm = category.strip().lower() if category else None

    for prov in providers:
        # Filter out inactive or non-providers
        if str(prov.get("role", "")).lower() == "student":
            continue

        # Category Filter (if specified and not 'all')
        if category_norm and category_norm not in ("all", ""):
            prov_cat = str(prov.get("category", "")).strip().lower()
            if prov_cat and prov_cat != category_norm:
                continue

        eval_res = calculate_match_score(
            prov,
            query=active_query,
            required_skills=req_skills_list,
            student_budget=student_budget,
            strict_budget=strict_budget
        )
        if eval_res is not None:
            eligible.append(eval_res)

    # DSA Priority Queue: Insert all into Max-Heap and extract in order
    pq = PriorityQueue(key=lambda x: x["match_score"])
    for cand in eligible:
        pq.push(cand)

    ranked: List[Dict[str, Any]] = []
    while not pq.is_empty():
        ranked.append(pq.pop())

    return ranked
