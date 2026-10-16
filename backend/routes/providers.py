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
    auth_header = request.headers.get("Authorization", "").strip()
    if auth_header:
        clean = auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else auth_header
        if clean.isdigit():
            return int(clean)
        if "_" in clean:
            try:
                return int(clean.split("_")[-1])
            except ValueError:
                pass

    x_uid = request.headers.get("X-User-Id", "").strip()
    if x_uid.isdigit():
        return int(x_uid)

    q_uid = request.args.get("user_id", "").strip()
    if q_uid.isdigit():
        return int(q_uid)

    user_id = session.get("user_id")
    if user_id:
        return user_id

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
    full_name = data.get("full_name") or data.get("name") or data.get("fullName")
    email = data.get("email")
    title = data.get("professional_title") or data.get("title")
    category = data.get("category")
    bio = data.get("bio") or data.get("description")
    price = data.get("price") or data.get("starting_price")
    availability = data.get("availability")
    phone = data.get("phone")
    location = data.get("location")
    experience = data.get("experience_years") or data.get("experience")
    payment_upi = data.get("payment_upi")
    payment_account = data.get("payment_account")
    payment_qr = data.get("payment_qr")
    profile_photo = data.get("profile_photo") or data.get("profilePhoto")
    cover_photo = data.get("cover_photo") or data.get("coverPhoto")
    skills_input = data.get("skills")

    if full_name and str(full_name).strip():
        db.execute("UPDATE users SET full_name = ? WHERE id = ?", (str(full_name).strip(), user_id))

    if email and "@" in str(email):
        db.execute("UPDATE users SET email = ? WHERE id = ?", (str(email).strip().lower(), user_id))

    if profile_photo and str(profile_photo).strip():
        db.execute("UPDATE users SET profile_photo = ? WHERE id = ?", (profile_photo, user_id))

    # Ensure profile row exists
    db.execute("INSERT OR IGNORE INTO provider_profiles (user_id) VALUES (?)", (user_id,))
    
    db.execute(
        """
        UPDATE provider_profiles
        SET title = COALESCE(NULLIF(?, ''), title),
            category = COALESCE(NULLIF(?, ''), category),
            bio = COALESCE(NULLIF(?, ''), bio),
            starting_price = COALESCE(?, starting_price),
            experience_years = COALESCE(?, experience_years),
            availability = COALESCE(NULLIF(?, ''), availability),
            phone = COALESCE(NULLIF(?, ''), phone),
            location = COALESCE(NULLIF(?, ''), location),
            profile_photo = COALESCE(NULLIF(?, ''), profile_photo),
            cover_photo = COALESCE(NULLIF(?, ''), cover_photo),
            payment_upi = COALESCE(NULLIF(?, ''), payment_upi),
            payment_account = COALESCE(NULLIF(?, ''), payment_account),
            payment_qr = COALESCE(NULLIF(?, ''), payment_qr)
        WHERE user_id = ?
        """,
        (title, category, bio, price, experience, availability, phone, location, profile_photo, cover_photo, payment_upi, payment_account, payment_qr, user_id)
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


# --- PORTFOLIO PROJECTS ---
@providers_bp.route("/portfolio", methods=["GET", "POST"])
def provider_portfolio():
    user_id = get_auth_user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Authentication required."}), 401

    db = get_db()
    prof_row = db.execute("SELECT id FROM provider_profiles WHERE user_id = ?", (user_id,)).fetchone()
    prof_id = prof_row["id"] if prof_row else user_id

    if request.method == "GET":
        rows = db.execute(
            "SELECT id, title, description, technologies, project_url, created_at FROM portfolio_projects WHERE provider_id = ? OR provider_id = ? ORDER BY id DESC",
            (user_id, prof_id)
        ).fetchall()
        projects = []
        for r in rows:
            techs = [t.strip() for t in (r["technologies"] or "").split(",") if t.strip()]
            projects.append({
                "id": r["id"],
                "title": r["title"],
                "description": r["description"],
                "technologies": techs,
                "project_url": r["project_url"],
                "created_at": r["created_at"]
            })
        return jsonify({"success": True, "projects": projects, "portfolio": projects}), 200

    # POST new portfolio project
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    description = str(data.get("description", "")).strip()
    techs = data.get("technologies", [])
    project_url = str(data.get("project_url", "")).strip()

    if isinstance(techs, list):
        tech_str = ", ".join(techs)
    else:
        tech_str = str(techs).strip()

    if not title or not description:
        return jsonify({"success": False, "message": "Project title and description are required."}), 400

    cursor = db.execute(
        """
        INSERT INTO portfolio_projects (provider_id, title, description, technologies, project_url)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, title, description, tech_str, project_url)
    )
    # Increment completed_projects count in provider profile
    db.execute(
        "UPDATE provider_profiles SET completed_projects = completed_projects + 1 WHERE user_id = ?",
        (user_id,)
    )
    db.commit()

    new_id = cursor.lastrowid
    return jsonify({
        "success": True,
        "message": "Portfolio project added successfully.",
        "project": {
            "id": new_id,
            "title": title,
            "description": description,
            "technologies": [t.strip() for t in tech_str.split(",") if t.strip()],
            "project_url": project_url
        }
    }), 201


@providers_bp.route("/portfolio/<int:project_id>", methods=["DELETE"])
def delete_portfolio_project(project_id):
    user_id = get_auth_user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Authentication required."}), 401

    db = get_db()
    prof_row = db.execute("SELECT id FROM provider_profiles WHERE user_id = ?", (user_id,)).fetchone()
    prof_id = prof_row["id"] if prof_row else user_id

    cursor = db.execute("DELETE FROM portfolio_projects WHERE id = ? AND (provider_id = ? OR provider_id = ?)", (project_id, user_id, prof_id))
    db.commit()

    if cursor.rowcount == 0:
        return jsonify({"success": False, "message": "Project not found or not owned by you."}), 404

    return jsonify({"success": True, "message": "Project removed from portfolio."}), 200


# --- REVIEWS ---
@providers_bp.route("/<int:provider_id>/reviews", methods=["GET", "POST"])
def provider_reviews_handler(provider_id):
    db = get_db()
    # Resolve both profile_id and user_id for resilient matching
    prof_row = db.execute("SELECT id, user_id FROM provider_profiles WHERE id = ? OR user_id = ?", (provider_id, provider_id)).fetchone()
    resolved_prov_id = prof_row["id"] if prof_row else provider_id
    resolved_user_id = prof_row["user_id"] if prof_row else provider_id

    if request.method == "GET":
        rows = db.execute(
            """
            SELECT r.id, r.rating, r.comment, r.created_at, u.full_name as student_name
            FROM reviews r
            JOIN users u ON r.student_id = u.id
            WHERE r.provider_id = ? OR r.provider_id = ?
            ORDER BY r.created_at DESC
            """,
            (resolved_prov_id, resolved_user_id)
        ).fetchall()
        reviews = [dict(r) for r in rows]
        return jsonify({"success": True, "reviews": reviews}), 200

    # POST student review for this provider
    student_id = get_auth_user_id()
    if not student_id:
        return jsonify({"success": False, "message": "You must be logged in as student to review."}), 401

    data = request.get_json(silent=True) or {}
    try:
        rating = int(data.get("rating", 5))
    except (ValueError, TypeError):
        rating = 5
    rating = max(1, min(5, rating))
    comment = str(data.get("comment", "") or data.get("review", "")).strip()

    db.execute(
        "INSERT INTO reviews (provider_id, student_id, rating, comment) VALUES (?, ?, ?, ?)",
        (resolved_prov_id, student_id, rating, comment)
    )

    # Recalculate and update provider rating in profile
    avg_row = db.execute("SELECT AVG(rating) as avg_r FROM reviews WHERE provider_id = ? OR provider_id = ?", (resolved_prov_id, resolved_user_id)).fetchone()
    if avg_row and avg_row["avg_r"]:
        new_avg = round(float(avg_row["avg_r"]), 1)
        db.execute("UPDATE provider_profiles SET rating = ? WHERE id = ? OR user_id = ?", (new_avg, resolved_prov_id, resolved_user_id))

    db.commit()
    return jsonify({"success": True, "message": "Review submitted successfully!"}), 201


@providers_bp.route("/reviews", methods=["GET"])
def get_current_provider_reviews():
    user_id = get_auth_user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Authentication required."}), 401
    return provider_reviews_handler(user_id)


# --- SERVICES ---
@providers_bp.route("/services", methods=["GET", "POST"])
def provider_services_handler():
    user_id = get_auth_user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Authentication required."}), 401

    db = get_db()
    if request.method == "GET":
        rows = db.execute("SELECT * FROM services WHERE provider_id = ? ORDER BY id DESC", (user_id,)).fetchall()
        return jsonify({"success": True, "services": [dict(r) for r in rows]}), 200

    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    category = str(data.get("category", "Web Development")).strip()
    description = str(data.get("description", "")).strip()
    price = int(data.get("price", 1500))
    delivery_days = int(data.get("delivery_days", 7))

    if not title:
        return jsonify({"success": False, "message": "Service title is required."}), 400

    cursor = db.execute(
        """
        INSERT INTO services (provider_id, title, category, description, price, delivery_days)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, title, category, description, price, delivery_days)
    )
    db.commit()
    return jsonify({"success": True, "message": "Service created successfully.", "id": cursor.lastrowid}), 201


@providers_bp.route("/services/<int:service_id>", methods=["PUT", "DELETE"])
def provider_service_detail_handler(service_id):
    user_id = get_auth_user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Authentication required."}), 401

    db = get_db()
    row = db.execute("SELECT * FROM services WHERE id = ? AND provider_id = ?", (service_id, user_id)).fetchone()
    if not row:
        return jsonify({"success": False, "message": "Service not found or unauthorized."}), 404

    if request.method == "DELETE":
        db.execute("DELETE FROM services WHERE id = ?", (service_id,))
        db.commit()
        return jsonify({"success": True, "message": "Service deleted successfully."}), 200

    # PUT update
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", row["title"])).strip()
    category = str(data.get("category", row["category"])).strip()
    description = str(data.get("description", row["description"])).strip()
    price = int(data.get("price", row["price"]))
    delivery_days = int(data.get("delivery_days", row["delivery_days"]))

    db.execute(
        """
        UPDATE services
        SET title = ?, category = ?, description = ?, price = ?, delivery_days = ?
        WHERE id = ?
        """,
        (title, category, description, price, delivery_days, service_id)
    )
    db.commit()
    return jsonify({"success": True, "message": "Service updated successfully."}), 200


# --- CERTIFICATIONS ---
@providers_bp.route("/certifications", methods=["GET", "POST"])
def provider_certifications_handler():
    user_id = get_auth_user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Authentication required."}), 401

    db = get_db()
    if request.method == "GET":
        rows = db.execute("SELECT * FROM certifications WHERE provider_id = ? ORDER BY id DESC", (user_id,)).fetchall()
        return jsonify({"success": True, "certifications": [dict(r) for r in rows]}), 200

    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    issuer = str(data.get("issuer", "")).strip()
    issue_year = str(data.get("issue_year", "2025")).strip()
    credential_url = str(data.get("credential_url", "")).strip()

    if not name or not issuer:
        return jsonify({"success": False, "message": "Certification name and issuer are required."}), 400

    cursor = db.execute(
        """
        INSERT INTO certifications (provider_id, name, issuer, issue_year, credential_url)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, name, issuer, issue_year, credential_url)
    )
    db.commit()
    return jsonify({"success": True, "message": "Certification added successfully.", "id": cursor.lastrowid}), 201


# --- SKILLS MANAGEMENT ---
@providers_bp.route("/skills", methods=["GET", "POST"])
def provider_skills_handler():
    user_id = get_auth_user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Authentication required."}), 401

    db = get_db()
    # Resolve provider_profile_id
    prof_row = db.execute("SELECT id FROM provider_profiles WHERE user_id = ?", (user_id,)).fetchone()
    if not prof_row:
        db.execute("INSERT OR IGNORE INTO provider_profiles (user_id) VALUES (?)", (user_id,))
        db.commit()
        prof_row = db.execute("SELECT id FROM provider_profiles WHERE user_id = ?", (user_id,)).fetchone()
    
    prov_prof_id = prof_row["id"] if prof_row else user_id

    if request.method == "GET":
        rows = db.execute(
            """
            SELECT ps.id, s.id as skill_id, s.name, 'Expert' as level
            FROM provider_skills ps
            JOIN skills s ON ps.skill_id = s.id
            WHERE ps.provider_id = ?
            ORDER BY s.name ASC
            """,
            (prov_prof_id,)
        ).fetchall()
        return jsonify({"success": True, "skills": [dict(r) for r in rows]}), 200

    # POST - add skill
    data = request.get_json(silent=True) or {}
    skill_name = str(data.get("name", "")).strip()
    level = str(data.get("level", "Intermediate")).strip()

    if not skill_name:
        return jsonify({"success": False, "message": "Skill name is required."}), 400

    db.execute("INSERT OR IGNORE INTO skills (name) VALUES (?)", (skill_name,))
    s_row = db.execute("SELECT id FROM skills WHERE LOWER(name) = LOWER(?)", (skill_name,)).fetchone()
    if s_row:
        skill_id = s_row["id"]
        cursor = db.execute(
            "INSERT OR IGNORE INTO provider_skills (provider_id, skill_id) VALUES (?, ?)",
            (prov_prof_id, skill_id)
        )
        db.commit()
        return jsonify({
            "success": True,
            "message": f"Skill '{skill_name}' added successfully.",
            "skill": {
                "id": cursor.lastrowid or skill_id,
                "name": skill_name,
                "level": level
            }
        }), 201

    return jsonify({"success": False, "message": "Could not save skill."}), 400


@providers_bp.route("/skills/<int:skill_entry_id>", methods=["PUT", "DELETE"])
def provider_skill_item_handler(skill_entry_id):
    user_id = get_auth_user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Authentication required."}), 401

    db = get_db()
    prof_row = db.execute("SELECT id FROM provider_profiles WHERE user_id = ?", (user_id,)).fetchone()
    prov_prof_id = prof_row["id"] if prof_row else user_id

    if request.method == "DELETE":
        # Delete by provider_skills.id OR skill_id
        db.execute(
            "DELETE FROM provider_skills WHERE provider_id = ? AND (id = ? OR skill_id = ?)",
            (prov_prof_id, skill_entry_id, skill_entry_id)
        )
        db.commit()
        return jsonify({"success": True, "message": "Skill removed successfully."}), 200

    # PUT
    data = request.get_json(silent=True) or {}
    new_name = str(data.get("name", "")).strip()
    if new_name:
        db.execute("INSERT OR IGNORE INTO skills (name) VALUES (?)", (new_name,))
        s_row = db.execute("SELECT id FROM skills WHERE LOWER(name) = LOWER(?)", (new_name,)).fetchone()
        if s_row:
            db.execute("UPDATE provider_skills SET skill_id = ? WHERE id = ? AND provider_id = ?", (s_row["id"], skill_entry_id, prov_prof_id))
            db.commit()
    return jsonify({"success": True, "message": "Skill updated successfully."}), 200


# --- EARNINGS & TRANSACTIONS ---
@providers_bp.route("/earnings", methods=["GET"])
def provider_earnings():
    user_id = get_auth_user_id()
    if not user_id:
        return jsonify({
            "success": True,
            "total_earnings": 0.0,
            "available_balance": 0.0,
            "pending_payments": 0.0
        }), 200

    db = get_db()
    requests = db.execute(
        """
        SELECT id, project_title, offered_budget, status, payment_status, created_at, updated_at
        FROM collaboration_requests
        WHERE provider_id = ? OR provider_id = (SELECT id FROM provider_profiles WHERE user_id = ?)
        ORDER BY id DESC
        """,
        (user_id, user_id)
    ).fetchall()

    total_earnings = 0.0
    pending_payments = 0.0

    for r in requests:
        amount = float(r["offered_budget"] or 0)
        status_val = str(r["status"] or "").lower()
        pay_status = str(r["payment_status"] or "").lower()

        if pay_status == "paid" or status_val == "completed":
            total_earnings += amount
        elif status_val in ("pending", "accepted", "in_progress") or pay_status in ("pending", "unpaid"):
            if status_val not in ("rejected", "cancelled"):
                pending_payments += amount

    available_balance = total_earnings

    return jsonify({
        "success": True,
        "total_earnings": round(float(total_earnings), 2),
        "available_balance": round(float(available_balance), 2),
        "pending_payments": round(float(pending_payments), 2)
    }), 200


@providers_bp.route("/transactions", methods=["GET"])
def provider_transactions():
    user_id = get_auth_user_id()
    if not user_id:
        return jsonify({
            "success": True,
            "transactions": []
        }), 200

    db = get_db()
    requests = db.execute(
        """
        SELECT id, project_title, offered_budget, status, payment_status, created_at, updated_at
        FROM collaboration_requests
        WHERE provider_id = ? OR provider_id = (SELECT id FROM provider_profiles WHERE user_id = ?)
        ORDER BY id DESC
        """,
        (user_id, user_id)
    ).fetchall()

    transactions = []
    for r in requests:
        status_val = str(r["status"] or "").lower()
        pay_status = str(r["payment_status"] or "").lower()

        if pay_status == "paid" or status_val == "completed":
            mapped_status = "completed"
        elif status_val in ("accepted", "in_progress"):
            mapped_status = "processing"
        elif status_val == "pending":
            mapped_status = "pending"
        elif status_val in ("rejected", "cancelled"):
            mapped_status = "failed"
        else:
            mapped_status = "pending"

        transactions.append({
            "transaction_id": f"TXN-EDUMATCH-{int(r['id']):05d}",
            "order_title": r["project_title"] or "Project Mentorship",
            "date": r["created_at"] or r["updated_at"] or "",
            "amount": round(float(r["offered_budget"] or 0), 2),
            "status": mapped_status
        })

    return jsonify({
        "success": True,
        "transactions": transactions
    }), 200
