"""
Supabase Client & Synchronization Module for EduMatch
Connects Student, Provider, and Admin across Supabase PostgreSQL and SQLite.
"""

import json
import logging
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, Any, List, Optional

logger = logging.getLogger("supabase_client")

SUPABASE_URL = "https://pxfsmjtzsvqnciewmjas.supabase.co"
SUPABASE_KEY = "sb_publishable_isk7dGKCEDgJx7UAITr05g_uNcIB-yA"

def supabase_request(endpoint: str, data: Optional[Any] = None, method: str = "GET", params: str = "") -> Optional[Any]:
    """
    Execute a REST request to Supabase PostgREST endpoint.
    Fails gracefully if network is unavailable so local DB keeps working.
    """
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    if params:
        url = f"{url}?{params}"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation"
    }

    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = response.read().decode("utf-8")
            return json.loads(res_data) if res_data else {}
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        logger.warning(f"Supabase HTTP {e.code} on {endpoint}: {err_msg}")
        return None
    except Exception as e:
        logger.warning(f"Supabase request failed on {endpoint}: {e}")
        return None


def sync_user_to_supabase(user_id: int, full_name: str, email: str, password_hash: str, role: str) -> None:
    payload = {
        "id": user_id,
        "full_name": full_name,
        "email": email.strip().lower(),
        "password_hash": password_hash,
        "role": role,
        "is_active": True
    }
    supabase_request("users", payload, method="POST")


def update_supabase_user_password(email: str, new_password_hash: str) -> None:
    payload = {"password_hash": new_password_hash}
    supabase_request("users", payload, method="PATCH", params=f"email=eq.{urllib.parse.quote(email.strip().lower())}")


def sync_student_profile_to_supabase(user_id: int, institution: str = "", degree: str = "", bio: str = "", phone: str = "", interests: str = "") -> None:
    payload = {
        "user_id": user_id,
        "institution": institution,
        "degree": degree,
        "bio": bio,
        "phone": phone,
        "interests": interests
    }
    supabase_request("student_profiles", payload, method="POST")


def sync_provider_profile_to_supabase(user_id: int, title: str, category: str, bio: str, price: int, phone: str = "") -> None:
    payload = {
        "user_id": user_id,
        "title": title,
        "category": category,
        "bio": bio,
        "starting_price": price,
        "availability": "available",
        "phone": phone
    }
    supabase_request("provider_profiles", payload, method="POST")


def sync_requirement_to_supabase(req_id: int, student_id: int, title: str, category: str, description: str, skills: str, budget: int, deadline: str, complexity: str) -> None:
    payload = {
        "id": req_id,
        "student_id": student_id,
        "title": title,
        "category": category,
        "description": description,
        "required_skills": skills,
        "budget": budget,
        "deadline": deadline,
        "complexity": complexity,
        "status": "open"
    }
    supabase_request("requirements", payload, method="POST")


def sync_collaboration_request_to_supabase(req_id: int, student_id: int, provider_id: int, project_title: str, message: str, budget: int, status: str = "pending", requirement_id: Optional[int] = None) -> None:
    payload = {
        "id": req_id,
        "student_id": student_id,
        "provider_id": provider_id,
        "requirement_id": requirement_id,
        "project_title": project_title,
        "message": message,
        "offered_budget": budget,
        "status": status
    }
    supabase_request("collaboration_requests", payload, method="POST")


def update_supabase_request_status(req_id: int, status: str) -> None:
    supabase_request("collaboration_requests", {"status": status}, method="PATCH", params=f"id=eq.{req_id}")


def sync_message_to_supabase(conversation_id: int, sender_id: int, message_text: str, attachment_url: str = "") -> None:
    payload = {
        "conversation_id": conversation_id,
        "sender_id": sender_id,
        "message_text": message_text,
        "attachment_url": attachment_url
    }
    supabase_request("messages", payload, method="POST")


def create_supabase_notification(user_id: int, title: str, message: str, link: str = "") -> None:
    payload = {
        "user_id": user_id,
        "title": title,
        "message": message,
        "link": link
    }
    supabase_request("notifications", payload, method="POST")
