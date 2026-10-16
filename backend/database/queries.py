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
        COALESCE(p.location, '') as location,
        COALESCE(NULLIF(p.profile_photo, ''), NULLIF(u.profile_photo, ''), '') as profile_photo,
        COALESCE(p.cover_photo, '') as cover_photo,
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
            "location": r["location"] or "",
            "profile_photo": r["profile_photo"] or "",
            "cover_photo": r["cover_photo"] or "",
            "payment_upi": r["payment_upi"] or "",
            "payment_account": r["payment_account"] or "",
            "payment_qr": r["payment_qr"] or "",
            "skills": skills
        })

    # Attach portfolio projects count and items to each provider
    for p in providers:
        p_projs = db.execute(
            "SELECT id, title, description, technologies, project_url, created_at FROM portfolio_projects WHERE provider_id = ? OR provider_id = ? ORDER BY id DESC",
            (p["id"], p["provider_profile_id"])
        ).fetchall()
        p["portfolio"] = []
        for row in p_projs:
            techs = [t.strip() for t in (row["technologies"] or "").split(",") if t.strip()]
            p["portfolio"].append({
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "technologies": techs,
                "project_url": row["project_url"],
                "created_at": row["created_at"]
            })
        if len(p["portfolio"]) > 0:
            p["projects"] = max(p["projects"], len(p["portfolio"]))
            p["completed_projects"] = p["projects"]

        # Attach published services
        p_services = db.execute(
            "SELECT id, title, category, description, price, delivery_days, created_at FROM services WHERE provider_id = ? OR provider_id = ? ORDER BY id DESC",
            (p["id"], p["provider_profile_id"])
        ).fetchall()
        p["services"] = [dict(s) for s in p_services]
        if len(p["services"]) > 0:
            prices = [s["price"] for s in p["services"] if s.get("price")]
            if prices:
                p["starting_price"] = min(prices)
                p["price"] = min(prices)

    return providers


def get_provider_details(provider_user_id: int) -> Optional[Dict[str, Any]]:
    providers = get_all_providers_with_skills()
    for p in providers:
        if p["id"] == provider_user_id or p.get("provider_profile_id") == provider_user_id:
            # Also fetch real reviews from reviews table
            db = get_db()
            rev_rows = db.execute(
                """
                SELECT r.id, r.rating, r.comment, r.created_at, u.full_name as student_name
                FROM reviews r
                JOIN users u ON r.student_id = u.id
                WHERE r.provider_id = ? OR r.provider_id = ?
                ORDER BY r.created_at DESC
                """,
                (p["id"], p["provider_profile_id"])
            ).fetchall()
            p["reviews"] = [dict(rev) for rev in rev_rows]
            if rev_rows:
                avg_rating = sum(r["rating"] for r in rev_rows) / len(rev_rows)
                p["rating"] = round(avg_rating, 1)
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
        SELECT m.id, m.conversation_id, m.sender_id, m.message_text,
               COALESCE(m.attachment_url, '') as attachment_url,
               COALESCE(m.deleted_for_everyone, 0) as deleted_for_everyone,
               COALESCE(m.deleted_for_sender, 0) as deleted_for_sender,
               COALESCE(m.deleted_for_receiver, 0) as deleted_for_receiver,
               m.created_at, u.full_name as sender_name, u.role as sender_role,
               COALESCE(
                   NULLIF(u.profile_photo, ''),
                   NULLIF((SELECT profile_photo FROM student_profiles WHERE user_id = u.id), ''),
                   NULLIF((SELECT profile_photo FROM provider_profiles WHERE user_id = u.id), ''),
                   ''
               ) as sender_photo
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE m.conversation_id = ?
        ORDER BY m.id ASC
        """,
        (conversation_id,)
    ).fetchall()

    result = []
    for r in rows:
        # Check if deleted for current viewer
        if r["sender_id"] == user_id and r["deleted_for_sender"]:
            continue
        if r["sender_id"] != user_id and r["deleted_for_receiver"]:
            continue

        item = dict(r)
        if r["deleted_for_everyone"]:
            item["message_text"] = "🚫 This message was deleted"
            item["is_deleted"] = True
        else:
            item["is_deleted"] = False
        result.append(item)

    return result


def delete_message_for_everyone(message_id: int, user_id: int) -> bool:
    db = get_db()
    cursor = db.execute(
        "UPDATE messages SET deleted_for_everyone = 1 WHERE id = ? AND sender_id = ?",
        (message_id, user_id)
    )
    db.commit()
    return cursor.rowcount > 0


def delete_message_for_user(message_id: int, user_id: int) -> bool:
    db = get_db()
    m = db.execute("SELECT sender_id FROM messages WHERE id = ?", (message_id,)).fetchone()
    if not m:
        return False
    if m["sender_id"] == user_id:
        db.execute("UPDATE messages SET deleted_for_sender = 1 WHERE id = ?", (message_id,))
    else:
        db.execute("UPDATE messages SET deleted_for_receiver = 1 WHERE id = ?", (message_id,))
    db.commit()
    return True


def clear_conversation_for_user(conversation_id: int, user_id: int) -> bool:
    db = get_db()
    # For messages sent by this user, set deleted_for_sender = 1
    db.execute(
        "UPDATE messages SET deleted_for_sender = 1 WHERE conversation_id = ? AND sender_id = ?",
        (conversation_id, user_id)
    )
    # For messages received by this user, set deleted_for_receiver = 1
    db.execute(
        "UPDATE messages SET deleted_for_receiver = 1 WHERE conversation_id = ? AND sender_id != ?",
        (conversation_id, user_id)
    )
    db.commit()
    return True


# --- NOTIFICATIONS ---
def create_notification(user_id: int, title: str, message: str, link: str = "") -> int:
    db = get_db()
    cursor = db.execute(
        "INSERT INTO notifications (user_id, title, message, link, is_read) VALUES (?, ?, ?, ?, 0)",
        (user_id, title.strip(), message.strip(), link.strip())
    )
    db.commit()
    return cursor.lastrowid


def get_user_notifications(user_id: int, limit: int = 30) -> List[Dict[str, Any]]:
    db = get_db()
    rows = db.execute(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    return [dict(r) for r in rows]


def mark_all_notifications_read(user_id: int) -> bool:
    db = get_db()
    db.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
    db.commit()
    return True


# --- PASSWORD RESET & OTP ---
def create_password_reset_otp(email: str, otp_code: str, expires_at: float) -> int:
    db = get_db()
    # Invalidate previous unused OTPs for this email
    db.execute("UPDATE password_resets SET used = 1 WHERE LOWER(email) = LOWER(?)", (email.strip(),))
    cursor = db.execute(
        "INSERT INTO password_resets (email, otp_code, expires_at, used) VALUES (?, ?, ?, 0)",
        (email.strip().lower(), otp_code.strip(), expires_at)
    )
    db.commit()
    return cursor.lastrowid


def verify_otp_and_reset_password(email: str, otp_code: str, new_password_hash: str) -> bool:
    import time
    db = get_db()
    now = time.time()
    row = db.execute(
        "SELECT id FROM password_resets WHERE LOWER(email) = LOWER(?) AND otp_code = ? AND used = 0 AND expires_at > ? ORDER BY id DESC LIMIT 1",
        (email.strip().lower(), otp_code.strip(), now)
    ).fetchone()

    if not row:
        return False

    # Mark OTP as used
    db.execute("UPDATE password_resets SET used = 1 WHERE id = ?", (row["id"],))
    # Update user password
    db.execute(
        "UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE LOWER(email) = LOWER(?)",
        (new_password_hash, email.strip().lower())
    )
    db.commit()
    return True


# --- ORDERS & DELIVERABLES ---
def get_order_details(order_id: int) -> Optional[Dict[str, Any]]:
    db = get_db()
    row = db.execute(
        """
        SELECT cr.*,
               u_s.full_name as student_name, u_s.email as student_email,
               COALESCE(u_s.profile_photo, '') as student_photo,
               u_p.full_name as provider_name, u_p.email as provider_email,
               COALESCE(u_p.profile_photo, '') as provider_photo,
               r.category as req_category, r.description as req_description,
               r.required_skills as req_skills, r.deadline as req_deadline
        FROM collaboration_requests cr
        JOIN users u_s ON cr.student_id = u_s.id
        JOIN users u_p ON cr.provider_id = u_p.id
        LEFT JOIN requirements r ON cr.requirement_id = r.id
        WHERE cr.id = ?
        """,
        (order_id,)
    ).fetchone()

    if not row:
        return None

    r = dict(row)
    return {
        "id": r["id"],
        "service_title": r["project_title"],
        "project_title": r["project_title"],
        "description": r.get("message") or r.get("req_description") or "",
        "amount": r["offered_budget"],
        "status": r["status"],
        "payment_status": r.get("payment_status") or "unpaid",
        "deliverable_url": r.get("deliverable_url") or "",
        "deliverable_note": r.get("deliverable_note") or "",
        "transaction_id": f"TXN-EDUMATCH-{r['id']:05d}",
        "created_at": r["created_at"],
        "delivery_date": r.get("req_deadline") or r["updated_at"],
        "updated_at": r["updated_at"],
        "student": {
            "id": r["student_id"],
            "name": r["student_name"],
            "email": r["student_email"],
            "photo": r["student_photo"]
        },
        "provider": {
            "id": r["provider_id"],
            "name": r["provider_name"],
            "email": r["provider_email"],
            "photo": r["provider_photo"]
        },
        "requirement": {
            "category": r.get("req_category") or "",
            "skills": r.get("req_skills") or "",
            "deadline": r.get("req_deadline") or ""
        }
    }


def update_order_status_for_provider(order_id: int, provider_id: int, status: str) -> bool:
    db = get_db()
    # provider_id could be user_id or provider_profile.id
    cursor = db.execute(
        """
        UPDATE collaboration_requests 
        SET status = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE id = ? AND (provider_id = ? OR provider_id = (SELECT user_id FROM provider_profiles WHERE id = ?))
        """,
        (status, order_id, provider_id, provider_id)
    )
    if status == "completed":
        # Increment completed_projects in provider_profiles
        db.execute(
            """
            UPDATE provider_profiles 
            SET completed_projects = completed_projects + 1 
            WHERE user_id = ? OR id = ?
            """,
            (provider_id, provider_id)
        )
    db.commit()
    return cursor.rowcount > 0


def update_order_deliverable(order_id: int, provider_id: int, deliverable_url: str, deliverable_note: str) -> bool:
    db = get_db()
    cursor = db.execute(
        """
        UPDATE collaboration_requests
        SET deliverable_url = ?, deliverable_note = ?, status = 'completed', updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND (provider_id = ? OR provider_id = (SELECT user_id FROM provider_profiles WHERE id = ?))
        """,
        (deliverable_url.strip(), deliverable_note.strip(), order_id, provider_id, provider_id)
    )
    if cursor.rowcount > 0:
        db.execute(
            """
            UPDATE provider_profiles 
            SET completed_projects = completed_projects + 1 
            WHERE user_id = ? OR id = ?
            """,
            (provider_id, provider_id)
        )
        db.commit()
        return True
    return False


def update_order_payment_status(order_id: int, provider_id: int, payment_status: str) -> bool:
    db = get_db()
    cursor = db.execute(
        """
        UPDATE collaboration_requests
        SET payment_status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND (provider_id = ? OR provider_id = (SELECT user_id FROM provider_profiles WHERE id = ?))
        """,
        (payment_status, order_id, provider_id, provider_id)
    )
    db.commit()
    return cursor.rowcount > 0


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

