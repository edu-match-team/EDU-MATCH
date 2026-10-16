from flask import Blueprint, jsonify, request, session
from backend.database.connection import get_db
from backend.database.queries import create_requirement, get_requirements_by_student
from backend.database.supabase_client import (
    sync_requirement_to_supabase,
    sync_student_profile_to_supabase
)

students_bp = Blueprint("students", __name__, url_prefix="/api/students")


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
        return int(user_id)

    return None


def fetch_student_profile(target_id: int):
    db = get_db()
    row = db.execute(
        """
        SELECT u.id as user_id, u.full_name, u.email, u.role,
               COALESCE(NULLIF(sp.profile_photo, ''), NULLIF(u.profile_photo, ''), '') as profile_photo,
               COALESCE(sp.institution, 'University / College') as institution,
               COALESCE(sp.degree, 'Bachelor of Computer Applications') as degree,
               COALESCE(sp.specialization, '') as specialization,
               COALESCE(sp.year, '') as year,
               COALESCE(sp.skills, '') as skills,
               COALESCE(sp.interests, '') as interests,
               COALESCE(sp.location, '') as location,
               COALESCE(sp.bio, '') as bio,
               COALESCE(sp.phone, '') as phone,
               COALESCE(sp.github, '') as github,
               COALESCE(sp.linkedin, '') as linkedin,
               COALESCE(sp.portfolio, '') as portfolio,
               sp.id as student_profile_id
        FROM users u
        LEFT JOIN student_profiles sp ON u.id = sp.user_id
        WHERE u.id = ? OR sp.id = ?
        """,
        (target_id, target_id)
    ).fetchone()
    if not row:
        return None
    p_dict = dict(row)
    p_dict["id"] = p_dict["user_id"]
    p_dict["fullName"] = p_dict["full_name"]
    p_dict["name"] = p_dict["full_name"]
    p_dict["college"] = p_dict["institution"]
    p_dict["profilePhoto"] = p_dict["profile_photo"]
    raw_skills = p_dict.get("skills") or ""
    if isinstance(raw_skills, str):
        p_dict["skills_list"] = [s.strip() for s in raw_skills.split(",") if s.strip()]
    else:
        p_dict["skills_list"] = []
    return p_dict


@students_bp.route("/profile/<int:student_id>", methods=["GET"])
@students_bp.route("/<int:student_id>/profile", methods=["GET"])
def get_specific_student_profile(student_id):
    profile = fetch_student_profile(student_id)
    if not profile:
        return jsonify({"success": False, "message": "Student profile not found."}), 404
    return jsonify({"success": True, "profile": profile}), 200


@students_bp.route("/profile", methods=["GET", "PUT"])
def student_profile():
    user_id = get_auth_user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Not logged in."}), 401

    db = get_db()
    if request.method == "GET":
        p_dict = fetch_student_profile(user_id)
        if not p_dict:
            return jsonify({"success": False, "message": "User not found."}), 404
        return jsonify({"success": True, "profile": p_dict}), 200

    # PUT
    data = request.get_json(silent=True) or {}
    full_name = data.get("fullName") or data.get("full_name")
    institution = data.get("college") or data.get("institution")
    degree = data.get("degree")
    specialization = data.get("specialization")
    year = data.get("year")
    skills = data.get("skills")
    interests = data.get("interests")
    location = data.get("location")
    bio = data.get("bio")
    phone = data.get("phone")
    github = data.get("github")
    linkedin = data.get("linkedin")
    portfolio = data.get("portfolio")
    profile_photo = data.get("profilePhoto") or data.get("profile_photo")

    if full_name:
        db.execute("UPDATE users SET full_name = ? WHERE id = ?", (str(full_name).strip(), user_id))

    if profile_photo and str(profile_photo).strip():
        db.execute("UPDATE users SET profile_photo = ? WHERE id = ?", (profile_photo, user_id))

    # Upsert into student_profiles
    db.execute(
        """
        INSERT INTO student_profiles (user_id, institution, degree, specialization, year, skills, interests, location, bio, phone, github, linkedin, portfolio, profile_photo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            institution = COALESCE(NULLIF(excluded.institution, ''), student_profiles.institution),
            degree = COALESCE(NULLIF(excluded.degree, ''), student_profiles.degree),
            specialization = COALESCE(NULLIF(excluded.specialization, ''), student_profiles.specialization),
            year = COALESCE(NULLIF(excluded.year, ''), student_profiles.year),
            skills = COALESCE(NULLIF(excluded.skills, ''), student_profiles.skills),
            interests = COALESCE(NULLIF(excluded.interests, ''), student_profiles.interests),
            location = COALESCE(NULLIF(excluded.location, ''), student_profiles.location),
            bio = COALESCE(NULLIF(excluded.bio, ''), student_profiles.bio),
            phone = COALESCE(NULLIF(excluded.phone, ''), student_profiles.phone),
            github = COALESCE(NULLIF(excluded.github, ''), student_profiles.github),
            linkedin = COALESCE(NULLIF(excluded.linkedin, ''), student_profiles.linkedin),
            portfolio = COALESCE(NULLIF(excluded.portfolio, ''), student_profiles.portfolio),
            profile_photo = COALESCE(NULLIF(excluded.profile_photo, ''), student_profiles.profile_photo)
        """,
        (user_id, institution, degree, specialization, year, skills, interests, location, bio, phone, github, linkedin, portfolio, profile_photo)
    )
    db.commit()

    # Sync to Supabase
    try:
        sync_student_profile_to_supabase(
            user_id=user_id,
            institution=institution or "",
            degree=degree or "",
            bio=bio or "",
            phone=phone or "",
            interests=interests or ""
        )
    except Exception:
        pass

    return jsonify({"success": True, "message": "Student profile updated successfully.", "profile_photo": profile_photo or ""}), 200


@students_bp.route("/requirements", methods=["GET", "POST"])
def student_requirements():
    user_id = get_auth_user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Not logged in."}), 401

    if request.method == "GET":
        reqs = get_requirements_by_student(user_id)
        return jsonify({"success": True, "requirements": reqs}), 200

    # POST new requirement
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    category = str(data.get("category", "General")).strip()
    description = str(data.get("description", "")).strip()
    skills = data.get("skills", "")
    if isinstance(skills, list):
        skills_str = ", ".join(skills)
    else:
        skills_str = str(skills).strip()

    try:
        budget = int(data.get("budget", 2000))
    except (ValueError, TypeError):
        budget = 2000

    deadline = data.get("deadline", "")
    complexity = data.get("complexity", "Intermediate")

    if not title or not description:
        return jsonify({"success": False, "message": "Title and description are required."}), 400

    req_id = create_requirement(
        student_id=user_id,
        title=title,
        category=category,
        description=description,
        required_skills=skills_str,
        budget=budget,
        deadline=deadline,
        complexity=complexity
    )

    # Sync to Supabase
    try:
        sync_requirement_to_supabase(
            req_id=req_id,
            student_id=user_id,
            title=title,
            category=category,
            description=description,
            skills=skills_str,
            budget=budget,
            deadline=deadline,
            complexity=complexity
        )
    except Exception:
        pass

    return jsonify({
        "success": True,
        "message": "Requirement posted successfully.",
        "requirement_id": req_id
    }), 201
