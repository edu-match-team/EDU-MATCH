"""
DSA Matching Engine for EduMatch
Module: dsa.matching
Author: Vishu & Team (BCA AI & Data Science)

Calculates matching suitability between a student's project requirements
and candidate project providers using Set Theory, Strict Filtering,
and Multi-Criteria Composite Scoring.

Scoring Formula:
  Skill Score (S) = ( |Provider_Skills ∩ Required_Skills| / |Required_Skills| ) * 100
  Budget Score (B) = 100 - ((Provider_Price / Student_Budget) * 30) (if within budget)
  Availability Score (A) = 100 ('available'), 60 ('limited'), 20 ('busy')

  Total Score = (0.60 * S) + (0.25 * B) + (0.15 * A)
"""

from typing import List, Dict, Any, Optional
from dsa.sorting import merge_sort


def normalize_skill(skill: str) -> str:
    """Normalize skill name: trim whitespace and lowercase."""
    return skill.strip().lower()


def calculate_match_score(
    provider: Dict[str, Any],
    required_skills: List[str],
    student_budget: Optional[float] = None,
    strict_budget: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Evaluates a single provider against student requirements.
    Returns scoring breakdown dictionary, or None if filtered out.
    """
    prov_price = float(provider.get("starting_price") or provider.get("price") or 0)

    # 1. Strict Budget Filter
    if strict_budget and student_budget is not None and student_budget > 0:
        if prov_price > student_budget:
            return None  # Filtered out: exceeds student's maximum budget

    # 2. Skill Overlap via Set Theory
    prov_skills_raw = provider.get("skills", [])
    if isinstance(prov_skills_raw, str):
        prov_skills_raw = [s.strip() for s in prov_skills_raw.split(",") if s.strip()]

    prov_skill_set = {normalize_skill(s) for s in prov_skills_raw}
    req_skill_set = {normalize_skill(s) for s in required_skills}

    matching_skills_set = prov_skill_set.intersection(req_skill_set)
    missing_skills_set = req_skill_set.difference(prov_skill_set)

    if req_skill_set:
        skill_score = (len(matching_skills_set) / len(req_skill_set)) * 100.0
    else:
        skill_score = 100.0  # If no specific skills required, general match

    # 3. Budget Compatibility Score (0 to 100)
    if student_budget and student_budget > 0:
        if prov_price <= student_budget:
            # Under budget is rewarded: higher score if price leaves savings
            ratio = prov_price / student_budget
            budget_score = max(40.0, 100.0 - (ratio * 40.0))
        else:
            budget_score = max(0.0, 100.0 - ((prov_price - student_budget) / student_budget * 100.0))
    else:
        budget_score = 80.0

    # 4. Availability Score (0 to 100)
    availability_str = str(provider.get("availability", "available")).lower()
    if availability_str == "available":
        availability_score = 100.0
    elif availability_str == "limited":
        availability_score = 60.0
    else:
        availability_score = 25.0

    # 5. Rating Bonus (0 to 5 mapped to 0 to 100)
    rating = float(provider.get("rating", 5.0) or 5.0)
    rating_score = min(100.0, (rating / 5.0) * 100.0)

    # 6. Composite Score Calculation
    # Weights: 55% Skills, 20% Budget, 15% Availability, 10% Rating
    total_score = (
        (0.55 * skill_score) +
        (0.20 * budget_score) +
        (0.15 * availability_score) +
        (0.10 * rating_score)
    )
    total_score = round(min(100.0, max(0.0, total_score)), 1)

    result_data = dict(provider)
    result_data.update({
        "match_score": total_score,
        "skill_score": round(skill_score, 1),
        "budget_score": round(budget_score, 1),
        "availability_score": round(availability_score, 1),
        "matching_skills": list(matching_skills_set),
        "missing_skills": list(missing_skills_set),
        "matching_skill_count": len(matching_skills_set),
        "total_required_skills": len(req_skill_set)
    })
    return result_data


def match_and_rank_providers(
    providers: List[Dict[str, Any]],
    required_skills: List[str],
    student_budget: Optional[float] = None,
    strict_budget: bool = False,
    category: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Evaluates all providers and ranks them using O(N log N) Merge Sort.
    """
    eligible = []
    category_norm = category.strip().lower() if category else None

    for prov in providers:
        # Category Filter (if specified and not 'all')
        if category_norm and category_norm not in ("all", ""):
            prov_cat = str(prov.get("category", "")).strip().lower()
            if prov_cat and prov_cat != category_norm:
                continue

        eval_res = calculate_match_score(
            prov,
            required_skills=required_skills,
            student_budget=student_budget,
            strict_budget=strict_budget
        )
        if eval_res is not None:
            eligible.append(eval_res)

    # Rank eligible candidates descending by match_score using Merge Sort
    ranked = merge_sort(eligible, key=lambda x: x["match_score"], reverse=True)
    return ranked
