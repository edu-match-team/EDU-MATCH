import sqlite3
import json
import urllib.request
from pathlib import Path

SUPABASE_URL = "https://pxfsmjtzsvqnciewmjas.supabase.co"
SUPABASE_KEY = "sb_publishable_isk7dGKCEDgJx7UAITr05g_uNcIB-yA"

DB_PATH = Path(__file__).resolve().parent / "database" / "edumatch.db"

def supabase_request(endpoint, data=None, method="GET"):
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"HTTP Error {e.code} on {endpoint}: {error_body}")
        return None
    except Exception as e:
        print(f"Error on {endpoint}: {e}")
        return None

def sync():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    print("1. Syncing Users...")
    users = c.execute("SELECT * FROM users").fetchall()
    for u in users:
        payload = {
            "id": u["id"],
            "full_name": u["full_name"],
            "email": u["email"],
            "password_hash": u["password_hash"],
            "role": u["role"],
            "is_active": bool(u["is_active"])
        }
        supabase_request("users", payload, method="POST")

    print("2. Syncing Student Profiles...")
    s_profiles = c.execute("SELECT * FROM student_profiles").fetchall()
    for sp in s_profiles:
        payload = {
            "id": sp["id"],
            "user_id": sp["user_id"],
            "institution": sp["institution"] or "",
            "degree": sp["degree"] or "",
            "bio": sp["bio"] or "",
            "phone": sp["phone"] or "",
            "interests": sp["interests"] or ""
        }
        supabase_request("student_profiles", payload, method="POST")

    print("3. Syncing Provider Profiles...")
    p_profiles = c.execute("SELECT * FROM provider_profiles").fetchall()
    for pp in p_profiles:
        # Check if user exists in users table
        u_check = c.execute("SELECT id FROM users WHERE id = ?", (pp["user_id"],)).fetchone()
        if not u_check:
            continue
        payload = {
            "id": pp["id"],
            "user_id": pp["user_id"],
            "title": pp["title"] or "Developer",
            "category": pp["category"] or "Software Engineering",
            "bio": pp["bio"] or "",
            "experience_years": pp["experience_years"] or 1,
            "starting_price": pp["starting_price"] or 1500,
            "completed_projects": pp["completed_projects"] or 0,
            "rating": float(pp["rating"]) if pp["rating"] else 5.0,
            "availability": pp["availability"] or "available",
            "phone": pp["phone"] or ""
        }
        supabase_request("provider_profiles", payload, method="POST")

    print("4. Syncing Skills...")
    skills = c.execute("SELECT * FROM skills").fetchall()
    for s in skills:
        payload = {"id": s["id"], "name": s["name"]}
        supabase_request("skills", payload, method="POST")

    print("5. Syncing Provider Skills...")
    p_skills = c.execute("SELECT * FROM provider_skills").fetchall()
    for ps in p_skills:
        payload = {
            "id": ps["id"],
            "provider_id": ps["provider_id"],
            "skill_id": ps["skill_id"]
        }
        supabase_request("provider_skills", payload, method="POST")

    print("6. Syncing Requirements...")
    requirements = c.execute("SELECT * FROM requirements").fetchall()
    for r in requirements:
        payload = {
            "id": r["id"],
            "student_id": r["student_id"],
            "title": r["title"],
            "category": r["category"],
            "description": r["description"],
            "required_skills": r["required_skills"],
            "budget": r["budget"],
            "deadline": r["deadline"] or "",
            "complexity": r["complexity"] or "Intermediate",
            "status": r["status"]
        }
        supabase_request("requirements", payload, method="POST")

    print("7. Syncing Collaboration Requests...")
    collab_reqs = c.execute("SELECT * FROM collaboration_requests").fetchall()
    for cr in collab_reqs:
        payload = {
            "id": cr["id"],
            "student_id": cr["student_id"],
            "provider_id": cr["provider_id"],
            "requirement_id": cr["requirement_id"],
            "project_title": cr["project_title"],
            "message": cr["message"],
            "offered_budget": cr["offered_budget"],
            "status": cr["status"]
        }
        supabase_request("collaboration_requests", payload, method="POST")

    print("Sync complete!")

if __name__ == "__main__":
    sync()
