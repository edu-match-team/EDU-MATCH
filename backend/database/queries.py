"""
Database Query Helpers for EduMatch
Module: backend.database.queries
"""

import sqlite3
from typing import List, Dict, Any, Optional
from backend.database.connection import get_db


# --- USERS ---
def get_user_by_email(email: str) -> Optional[sqlite3.Row]:
    db = get_db()
    return db.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email.strip(),)).fetchone()


def get_user_by_id(user_id: int) -> Optional[sqlite3.Row]:
    db = get_db()
    return db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


# --- PROVIDERS ---
def get_all_providers_with_skills() -> List[Dict[str, Any]]:
    db = get_db()
    query = """
    SELECT 
        u.id as user_id,
        u.full_name as name,
        u.email,
        p.id as provider_id,
        p.title,
        p.category,
        p.bio as description,
        p.experience_years as experience,
        p.starting_price as price,
        p.completed_projects as projects,
        p.rating,
        p.availability,
        p.phone,
        COALESCE(p.payment_upi, '') as payment_upi,
        COALESCE(p.payment_account, '') as payment_account,
        COALESCE(p.payment_qr, '') as payment_qr,
        GROUP_CONCAT(s.name, ', ') as skills_str
    FROM provider_profiles p
    JOIN users u ON p.user_id = u.id
    LEFT JOIN provider_skills ps ON p.id = ps.provider_id
    LEFT JOIN skills s ON ps.skill_id = s.id
    WHERE u.is_active = 1
    GROUP BY p.id
    """
    rows = db.execute(query).fetchall()
    providers = []
    for r in rows:
        skills = [s.strip() for s in (r["skills_str"] or "").split(",") if s.strip()]
        providers.append({
            "id": r["user_id"],
            "provider_profile_id": r["provider_id"],
            "name": r["name"],
            "full_name": r["name"],
            "email": r["email"],
            "title": r["title"] or "Project Mentor",
            "professional_title": r["title"] or "Project Mentor",
            "role": r["title"] or "Project Mentor",
            "category": r["category"] or "Computer Science",
            "bio": r["description"] or "",
            "description": r["description"] or "Experienced developer and mentor.",
            "experience": r["experience"],
            "experience_years": r["experience"],
            "price": r["price"],
            "starting_price": r["price"],
            "projects": r["projects"],
            "completed_projects": r["projects"],
            "rating": r["rating"],
            "availability": r["availability"],
            "phone": r["phone"] or "",
            "payment_upi": r["payment_upi"] or "",
            "payment_account": r["payment_account"] or "",
            "payment_qr": r["payment_qr"] or "",
            "skills": skills
        })
    return providers


def get_provider_details(provider_user_id: int) -> Optional[Dict[str, Any]]:
    providers = get_all_providers_with_skills()
    for p in providers:
        if p["id"] == provider_user_id:
            return p
    return None


# --- REQUIREMENTS ---
def create_requirement(student_id: int, title: str, category: str, description: str,
                       required_skills: str, budget: int, deadline: str, complexity: str = "Intermediate") -> int:
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO requirements (student_id, title, category, description, required_skills, budget, deadline, complexity)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (student_id, title, category, description, required_skills, budget, deadline, complexity)
    )
    db.commit()
    return cursor.lastrowid


def get_requirements_by_student(student_id: int) -> List[Dict[str, Any]]:
    db = get_db()
    rows = db.execute(
        "SELECT * FROM requirements WHERE student_id = ? ORDER BY created_at DESC",
        (student_id,)
    ).fetchall()
    return [dict(r) for r in rows]


# --- COLLABORATION REQUESTS ---
def create_collaboration_request(student_id: int, provider_id: int, project_title: str,
                                 message: str, offered_budget: int, requirement_id: Optional[int] = None) -> int:
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO collaboration_requests (student_id, provider_id, requirement_id, project_title, message, offered_budget, status)
        VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """,
        (student_id, provider_id, requirement_id, project_title, message, offered_budget)
    )
    db.commit()
    return cursor.lastrowid


def get_requests_for_provider(provider_id: int) -> List[Dict[str, Any]]:
    db = get_db()
    query = """
    SELECT cr.*, u.full_name as student_name, u.email as student_email
    FROM collaboration_requests cr
    JOIN users u ON cr.student_id = u.id
    WHERE cr.provider_id = ?
    ORDER BY cr.created_at DESC
    """
    rows = db.execute(query, (provider_id,)).fetchall()
    return [dict(r) for r in rows]


def get_requests_for_student(student_id: int) -> List[Dict[str, Any]]:
    db = get_db()
    query = """
    SELECT cr.*, u.full_name as provider_name, u.email as provider_email
    FROM collaboration_requests cr
    JOIN users u ON cr.provider_id = u.id
    WHERE cr.student_id = ?
    ORDER BY cr.created_at DESC
    """
    rows = db.execute(query, (student_id,)).fetchall()
    return [dict(r) for r in rows]


def update_request_status(request_id: int, status: str, provider_id: int) -> bool:
    db = get_db()
    cursor = db.execute(
        "UPDATE collaboration_requests SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND provider_id = ?",
        (status, request_id, provider_id)
    )
    db.commit()
    return cursor.rowcount > 0


# --- CONVERSATIONS & MESSAGES ---
def get_or_create_conversation(user1_id: int, user2_id: int) -> int:
    # Always keep lowest id first for consistency
    u1, u2 = sorted([user1_id, user2_id])
    db = get_db()
    row = db.execute(
        "SELECT id FROM conversations WHERE user1_id = ? AND user2_id = ?",
        (u1, u2)
    ).fetchone()
    if row:
        return row["id"]

    cursor = db.execute(
        "INSERT INTO conversations (user1_id, user2_id) VALUES (?, ?)",
        (u1, u2)
    )
    db.commit()
    return cursor.lastrowid


def get_user_conversations(user_id: int) -> List[Dict[str, Any]]:
    db = get_db()
    query = """
    SELECT c.id, c.updated_at,
           CASE WHEN c.user1_id = ? THEN c.user2_id ELSE c.user1_id END as other_user_id,
           u.full_name as other_user_name,
           u.role as other_user_role,
           (SELECT message_text FROM messages WHERE conversation_id = c.id ORDER BY id DESC LIMIT 1) as last_message,
           (SELECT created_at FROM messages WHERE conversation_id = c.id ORDER BY id DESC LIMIT 1) as last_message_time
    FROM conversations c
    JOIN users u ON u.id = (CASE WHEN c.user1_id = ? THEN c.user2_id ELSE c.user1_id END)
    WHERE c.user1_id = ? OR c.user2_id = ?
    ORDER BY c.updated_at DESC
    """
    rows = db.execute(query, (user_id, user_id, user_id, user_id)).fetchall()
    return [dict(r) for r in rows]


def add_message(conversation_id: int, sender_id: int, text: str) -> Dict[str, Any]:
    db = get_db()
    cursor = db.execute(
        "INSERT INTO messages (conversation_id, sender_id, message_text) VALUES (?, ?, ?)",
        (conversation_id, sender_id, text.strip())
    )
    db.execute(
        "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (conversation_id,)
    )
    db.commit()
    return {
        "id": cursor.lastrowid,
        "conversation_id": conversation_id,
        "sender_id": sender_id,
        "message_text": text.strip(),
        "created_at": "Just now"
    }


def get_messages(conversation_id: int, user_id: int) -> List[Dict[str, Any]]:
    db = get_db()
    # Verify participant
    c = db.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
    if not c or (c["user1_id"] != user_id and c["user2_id"] != user_id):
        return []

    rows = db.execute(
        """
        SELECT m.id, m.conversation_id, m.sender_id, m.message_text, m.created_at, u.full_name as sender_name
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE m.conversation_id = ?
        ORDER BY m.id ASC
        """,
        (conversation_id,)
    ).fetchall()
    return [dict(r) for r in rows]


# --- ADMIN STATISTICS ---
def get_admin_stats() -> Dict[str, Any]:
    db = get_db()
    total_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_students = db.execute("SELECT COUNT(*) FROM users WHERE role = 'student'").fetchone()[0]
    total_providers = db.execute("SELECT COUNT(*) FROM users WHERE role = 'provider'").fetchone()[0]
    total_requests = db.execute("SELECT COUNT(*) FROM collaboration_requests").fetchone()[0]
    total_requirements = db.execute("SELECT COUNT(*) FROM requirements").fetchone()[0]
    total_messages = db.execute("SELECT COUNT(*) FROM messages").fetchone()[0]

    return {
        "total_users": total_users,
        "total_students": total_students,
        "total_providers": total_providers,
        "total_requests": total_requests,
        "total_requirements": total_requirements,
        "total_messages": total_messages
    }
