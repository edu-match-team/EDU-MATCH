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

# Semantic Category Taxonomy & Concept Clusters for Intelligent Project Category Filtering
CATEGORY_SEMANTIC_MAP: Dict[str, Dict[str, Set[str]]] = {
    "web development": {
        "keywords": {"web", "website", "frontend", "backend", "full stack", "fullstack", "react", "html", "css", "flask", "django", "node", "javascript", "typescript", "vue", "angular", "express", "php", "rest api"},
        "skills": {"html", "css", "javascript", "react", "flask", "django", "node.js", "vue", "angular", "bootstrap", "tailwind", "php", "full stack", "frontend", "backend"},
        "titles": {"web developer", "full stack", "frontend developer", "backend developer", "web dev"}
    },
    "app development": {
        "keywords": {"mobile app", "android", "ios", "flutter", "react native", "kotlin", "swift", "apk", "mobile developer", "app developer"},
        "skills": {"flutter", "android", "ios", "react native", "kotlin", "swift", "mobile development"},
        "titles": {"app developer", "mobile developer", "flutter developer", "android developer", "ios developer"}
    },
    "machine learning": {
        "keywords": {"machine learning", "deep learning", "nlp", "computer vision", "tensorflow", "pytorch", "neural network", "scikit", "data science"},
        "skills": {"machine learning", "deep learning", "nlp", "tensorflow", "pytorch", "scikit-learn"},
        "titles": {"ai researcher", "ml engineer", "machine learning researcher"}
    },
    "artificial intelligence": {
        "keywords": {"artificial intelligence", "ai researcher", "deep learning", "nlp", "genai", "llm", "tensorflow", "pytorch", "senior ai"},
        "skills": {"artificial intelligence", "deep learning", "nlp", "tensorflow", "pytorch", "ai"},
        "titles": {"senior ai researcher", "ai researcher", "ai mentor", "artificial intelligence"}
    },
    "data science": {
        "keywords": {"data science", "data analysis", "data analyst", "statistics", "pandas", "visualization", "tableau", "power bi"},
        "skills": {"data science", "data analysis", "pandas", "numpy", "matplotlib", "seaborn", "tableau", "power bi"},
        "titles": {"data analyst", "data scientist"}
    },
    "database": {
        "keywords": {"database", "sql", "mysql", "postgresql", "sqlite", "mongodb", "nosql", "dbms"},
        "skills": {"sql", "mysql", "postgresql", "sqlite", "mongodb", "database design", "database"},
        "titles": {"database", "dba", "sql developer"}
    },
    "dsa": {
        "keywords": {"dsa", "data structures", "algorithms", "competitive programming", "leetcode", "problem solving"},
        "skills": {"dsa", "c++", "algorithms", "data structures", "problem solving"},
        "titles": {"algorithms", "competitive programmer"}
    },
    "cloud computing": {
        "keywords": {"cloud", "aws", "gcp", "azure", "docker", "kubernetes", "devops", "ci/cd"},
        "skills": {"cloud", "aws", "docker", "kubernetes", "devops", "gcp", "azure"},
        "titles": {"cloud engineer", "devops", "cloud architect"}
    },
    "cyber security": {
        "keywords": {"cyber security", "penetration testing", "ethical hacking", "cryptography", "network security", "infosec"},
        "skills": {"cyber security", "network security", "penetration testing", "cryptography"},
        "titles": {"cyber security", "security analyst"}
    },
    "ui/ux design": {
        "keywords": {"ui/ux", "ui", "ux", "figma", "wireframe", "prototype", "design", "user experience"},
        "skills": {"ui/ux design", "figma", "wireframing", "prototyping", "adobe xd"},
        "titles": {"ui/ux designer", "product designer", "ui designer"}
    }
}


def normalize_token(text: str) -> str:
    """Normalize text: strip, lowercase, replace punctuation with space."""
    return re.sub(r"[^\w\s]", " ", str(text or "")).strip().lower()


def matches_term(term: str, text: str) -> bool:
    """Checks if term matches text either as phrase or whole word token."""
    norm_term = normalize_token(term)
    norm_text = normalize_token(text)
    if not norm_term or not norm_text:
        return False
    if " " in norm_term:
        return norm_term in norm_text
    tokens = set(norm_text.split())
    return norm_term in tokens


def check_provider_category_match(provider: Dict[str, Any], selected_category: str) -> (bool, float, str):
    """
    Intelligent Tiered Category Matching.
    Tiers:
    - 'primary': Provider's actual Category or Professional Title directly specializes in this field.
                 Ranks at the TOP (93% - 98% match).
    - 'related': Provider is from a related discipline or has a published service/skill in this field.
                 Ranks below primary matches (70% - 78% match).
    - 'none': Provider has no connection to the category -> Filtered out.
    """
    if not selected_category or str(selected_category).strip().lower() in ("all", ""):
        return True, 0.0, "all"

    target_norm = normalize_token(selected_category)
    sem_cfg = None
    for k, v in CATEGORY_SEMANTIC_MAP.items():
        if k in target_norm or target_norm in k:
            sem_cfg = v
            break

    prov_cat = normalize_token(provider.get("category", ""))
    p_title = normalize_token(provider.get("title", ""))

    # 1. Primary Match: Provider's primary category or professional title matches the requested category
    if matches_term(target_norm, prov_cat):
        return True, 60.0, "primary"

    if matches_term(target_norm, p_title):
        return True, 55.0, "primary"

    if sem_cfg:
        for t in sem_cfg["titles"]:
            if matches_term(t, p_title):
                return True, 50.0, "primary"

    # 2. Related Match: Services offered in this category
    for s in provider.get("services", []):
        s_title = normalize_token(s.get("title", ""))
        s_cat = normalize_token(s.get("category", ""))
        if matches_term(target_norm, s_cat) or matches_term(target_norm, s_title):
            return True, 20.0, "related"
        if sem_cfg:
            for kw in sem_cfg["keywords"]:
                if matches_term(kw, s_title) or matches_term(kw, s_cat):
                    return True, 18.0, "related"

    # 3. Related Match: Technical skills matching
    raw_skills = provider.get("skills", [])
    if isinstance(raw_skills, str):
        raw_skills = [s.strip() for s in raw_skills.split(",") if s.strip()]

    for sk in raw_skills:
        norm_sk = normalize_token(sk)
        if matches_term(target_norm, norm_sk):
            return True, 15.0, "related"
        if sem_cfg:
            for req_sk in sem_cfg["skills"]:
                if matches_term(req_sk, norm_sk):
                    return True, 12.0, "related"

    # 4. Related Match: Bio / Description
    p_bio = normalize_token(provider.get("bio", "") or provider.get("description", ""))
    if sem_cfg:
        for kw in sem_cfg["keywords"]:
            if matches_term(kw, p_bio):
                return True, 8.0, "related"

    return False, 0.0, "none"


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
    query: Optional[str] = None,
    category: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Evaluates a single provider against student requirements, search query, & category.
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

    # 1. Maximum Budget Filter: Providers exceeding the budget must not be shown
    if student_budget is not None and student_budget > 0:
        if prov_price > student_budget:
            return None

    # 2. Intelligent Category Filter & Affinity Bonus
    cat_bonus = 0.0
    cat_tier = "none"
    has_category = bool(category and str(category).strip().lower() not in ("all", ""))
    if has_category:
        is_cat_match, bonus, tier = check_provider_category_match(provider, category)
        if not is_cat_match:
            return None
        cat_bonus = bonus
        cat_tier = tier

    # 3. Query Relevance
    has_active_query = bool(active_query and active_query.strip())
    query_relevance = calculate_query_relevance(provider, active_query) if has_active_query else 100.0

    # If the user typed a specific query and the provider has zero relevance, heavily penalize
    if has_active_query and query_relevance < 15.0:
        query_relevance = 5.0

    # 4. Skill Overlap via Set Theory
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
        # Check if skill is in provider's title or published services
        p_title_norm = normalize_token(provider.get("title", ""))
        services_norm = " ".join([normalize_token(s.get("title", "")) + " " + normalize_token(s.get("description", "")) for s in provider.get("services", [])])
        for req in req_skill_set:
            if req in p_title_norm or req in services_norm:
                matching_skills_set.add(req)

        # STRICT FILTER: If the user specified required skill(s), provider MUST match at least one
        if len(matching_skills_set) == 0:
            return None

        skill_score = (len(matching_skills_set) / len(req_skill_set)) * 100.0
    else:
        skill_score = 100.0 if not has_active_query else query_relevance

    # 5. Budget Compatibility Score (0 to 100)
    if student_budget and student_budget > 0:
        if prov_price <= student_budget:
            ratio = prov_price / student_budget
            budget_score = max(40.0, 100.0 - (ratio * 35.0))
        else:
            budget_score = max(0.0, 100.0 - ((prov_price - student_budget) / student_budget * 100.0))
    else:
        budget_score = 80.0

    # 6. Availability Score (0 to 100)
    availability_str = str(provider.get("availability", "available")).lower()
    if availability_str == "available":
        availability_score = 100.0
    elif availability_str == "limited":
        availability_score = 65.0
    else:
        availability_score = 30.0

    # 7. Rating Bonus (0 to 5 mapped to 0 to 100)
    rating = float(provider.get("rating", 5.0) or 5.0)
    rating_score = min(100.0, (rating / 5.0) * 100.0)

    # 8. Composite Score Calculation
    if has_active_query:
        # Heavy weight on query relevance so exact title/keyword matches rank top
        total_score = (
            (0.50 * query_relevance) +
            (0.20 * skill_score) +
            (0.12 * budget_score) +
            (0.10 * availability_score) +
            (0.08 * rating_score)
        )
    elif has_category:
        if cat_tier == "primary":
            # Primary match (specialist in this category): 92.0% - 98.0%
            total_score = 92.0 + (cat_bonus * 0.08) + ((rating / 5.0) * 2.0)
        else:
            # Related match (offers a secondary service or related skill): 70.0% - 78.0%
            total_score = 68.0 + (cat_bonus * 0.35) + ((rating / 5.0) * 2.0)
    else:
        # Standard matching formula
        total_score = (
            (0.55 * skill_score) +
            (0.20 * budget_score) +
            (0.15 * availability_score) +
            (0.10 * rating_score)
        )

    # Add direct category affinity bonus if category matches and query is active
    if has_category and has_active_query and cat_bonus > 0:
        total_score = min(99.0, total_score + (cat_bonus * 0.15))

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
        "total_required_skills": len(req_skill_set),
        "category_matched": has_category,
        "category_tier": cat_tier,
        "matched_category": (category if has_category else (provider.get("category") or "Software Engineering"))
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
    category_norm = category.strip() if category else None

    for prov in providers:
        # Filter out inactive or non-providers
        if str(prov.get("role", "")).lower() == "student":
            continue

        eval_res = calculate_match_score(
            prov,
            query=active_query,
            required_skills=req_skills_list,
            student_budget=student_budget,
            strict_budget=strict_budget,
            category=category_norm
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
