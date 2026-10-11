from flask import Blueprint, jsonify, request, session
from backend.database.connection import get_db
from backend.database.queries import create_requirement, get_requirements_by_student

students_bp = Blueprint("students", __name__, url_prefix="/api/students")


@students_bp.route("/profile", methods=["GET", "PUT"])
def student_profile():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Not logged in."}), 401

    db = get_db()
    if request.method == "GET":
        row = db.execute(
            """
            SELECT u.id, u.full_name, u.email, u.role, sp.institution, sp.degree, sp.bio, sp.phone, sp.interests
            FROM users u
            LEFT JOIN student_profiles sp ON u.id = sp.user_id
            WHERE u.id = ?
            """,
            (user_id,)
        ).fetchone()

        if not row:
            return jsonify({"success": False, "message": "User not found."}), 404

        return jsonify({"success": True, "profile": dict(row)}), 200

    # PUT
    data = request.get_json(silent=True) or {}
    institution = data.get("institution")
    degree = data.get("degree")
    bio = data.get("bio")
    phone = data.get("phone")
    interests = data.get("interests")

    # Upsert
    db.execute(
        """
        INSERT INTO student_profiles (user_id, institution, degree, bio, phone, interests)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            institution = COALESCE(excluded.institution, student_profiles.institution),
            degree = COALESCE(excluded.degree, student_profiles.degree),
            bio = COALESCE(excluded.bio, student_profiles.bio),
            phone = COALESCE(excluded.phone, student_profiles.phone),
            interests = COALESCE(excluded.interests, student_profiles.interests)
        """,
        (user_id, institution, degree, bio, phone, interests)
    )
    db.commit()

    return jsonify({"success": True, "message": "Student profile updated successfully."}), 200


@students_bp.route("/requirements", methods=["GET", "POST"])
def student_requirements():
    user_id = session.get("user_id")
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

    return jsonify({
        "success": True,
        "message": "Requirement posted successfully.",
        "requirement_id": req_id
    }), 201
