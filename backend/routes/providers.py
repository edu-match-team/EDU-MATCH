from flask import Blueprint, jsonify, request, session
from backend.database.queries import get_all_providers_with_skills, get_provider_details, get_user_by_id
from backend.database.connection import get_db

providers_bp = Blueprint("providers", __name__, url_prefix="/api/providers")


@providers_bp.route("", methods=["GET"])
def list_providers():
    query = request.args.get("q", "").strip().lower()
    category = request.args.get("category", "").strip().lower()
    skill_filter = request.args.get("skill", "").strip().lower()

    all_provs = get_all_providers_with_skills()
    filtered = []

    for p in all_provs:
        # Search query matching name, title, description, or skills
        if query:
            name_match = query in p["name"].lower()
            title_match = query in p["title"].lower()
            desc_match = query in p["description"].lower()
            skills_match = any(query in s.lower() for s in p["skills"])
            if not (name_match or title_match or desc_match or skills_match):
                continue

        # Category matching
        if category and category not in ("all", ""):
            if p["category"].lower() != category:
                continue

        # Skill matching
        if skill_filter and skill_filter not in ("all", ""):
            if not any(skill_filter in s.lower() for s in p["skills"]):
                continue

        filtered.append(p)

    return jsonify({
        "success": True,
        "count": len(filtered),
        "providers": filtered
    }), 200


@providers_bp.route("/<int:provider_id>", methods=["GET"])
def provider_detail(provider_id):
    p = get_provider_details(provider_id)
    if not p:
        return jsonify({"success": False, "message": "Provider not found."}), 404

    return jsonify({"success": True, "provider": p}), 200


def get_auth_user_id():
    user_id = session.get("user_id")
    if user_id:
        return user_id

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer edumatch_token_"):
        try:
            return int(auth_header.split("_")[-1])
        except ValueError:
            pass
    return None


@providers_bp.route("/profile", methods=["GET", "PUT"])
def provider_own_profile():
    user_id = get_auth_user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Not authenticated. Please log in."}), 401

    db = get_db()
    if request.method == "GET":
        p = get_provider_details(user_id)
        if not p:
            # Ensure provider profile row exists
            db.execute("INSERT OR IGNORE INTO provider_profiles (user_id) VALUES (?)", (user_id,))
            db.commit()
            p = get_provider_details(user_id)
        return jsonify({"success": True, "profile": p}), 200

    # PUT update
    data = request.get_json(silent=True) or {}
    full_name = data.get("full_name") or data.get("name")
    title = data.get("professional_title") or data.get("title")
    category = data.get("category")
    bio = data.get("bio") or data.get("description")
    price = data.get("price") or data.get("starting_price")
    availability = data.get("availability")
    phone = data.get("phone")
    experience = data.get("experience_years") or data.get("experience")
    payment_upi = data.get("payment_upi")
    payment_account = data.get("payment_account")
    payment_qr = data.get("payment_qr")
    skills_input = data.get("skills")

    if full_name:
        db.execute("UPDATE users SET full_name = ? WHERE id = ?", (str(full_name).strip(), user_id))

    # Ensure profile row exists
    db.execute("INSERT OR IGNORE INTO provider_profiles (user_id) VALUES (?)", (user_id,))
    
    db.execute(
        """
        UPDATE provider_profiles
        SET title = COALESCE(?, title),
            category = COALESCE(?, category),
            bio = COALESCE(?, bio),
            starting_price = COALESCE(?, starting_price),
            experience_years = COALESCE(?, experience_years),
            availability = COALESCE(?, availability),
            phone = COALESCE(?, phone),
            payment_upi = COALESCE(?, payment_upi),
            payment_account = COALESCE(?, payment_account),
            payment_qr = COALESCE(?, payment_qr)
        WHERE user_id = ?
        """,
        (title, category, bio, price, experience, availability, phone, payment_upi, payment_account, payment_qr, user_id)
    )

    # Update skills if provided
    if skills_input is not None:
        p_row = db.execute("SELECT id FROM provider_profiles WHERE user_id = ?", (user_id,)).fetchone()
        if p_row:
            prov_profile_id = p_row["id"]
            db.execute("DELETE FROM provider_skills WHERE provider_id = ?", (prov_profile_id,))
            if isinstance(skills_input, str):
                skill_names = [s.strip() for s in skills_input.split(",") if s.strip()]
            elif isinstance(skills_input, list):
                skill_names = [str(s).strip() for s in skills_input if str(s).strip()]
            else:
                skill_names = []

            for s_name in skill_names:
                db.execute("INSERT OR IGNORE INTO skills (name) VALUES (?)", (s_name,))
                sk_row = db.execute("SELECT id FROM skills WHERE LOWER(name) = LOWER(?)", (s_name,)).fetchone()
                if sk_row:
                    db.execute("INSERT OR IGNORE INTO provider_skills (provider_id, skill_id) VALUES (?, ?)", (prov_profile_id, sk_row["id"]))

    db.commit()

    updated = get_provider_details(user_id)
    return jsonify({
        "success": True, 
        "message": "Profile updated successfully.",
        "profile": updated
    }), 200


@providers_bp.route("/skills", methods=["GET"])
def get_skills():
    db = get_db()
    rows = db.execute("SELECT id, name FROM skills ORDER BY name ASC").fetchall()
    return jsonify({
        "success": True,
        "skills": [dict(r) for r in rows]
    }), 200
