from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash
from backend.database.queries import get_admin_stats, get_user_by_email, get_user_by_id
from backend.database.connection import get_db

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def verify_admin_access():
    user_id = session.get("user_id")
    # Also support auth header if token passed
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer edumatch_token_"):
        try:
            user_id = int(auth_header.split("_")[-1])
        except ValueError:
            pass

    if not user_id:
        return None

    user = get_user_by_id(user_id)
    if user and user["role"] == "admin":
        return user
    return None


@admin_bp.route("/login", methods=["POST"])
def admin_login():
    data = request.get_json(silent=True) or {}
    identifier = str(data.get("email", "") or data.get("username", "")).strip().lower()
    password = str(data.get("password", ""))

    if not identifier or not password:
        return jsonify({"success": False, "message": "Admin identifier and password are required."}), 400

    # Retrieve admin account strictly for Vishwajeet
    db = get_db()
    user = db.execute(
        """
        SELECT * FROM users 
        WHERE role = 'admin' 
          AND (LOWER(email) = ? OR LOWER(full_name) = ?)
        """,
        (identifier, identifier)
    ).fetchone()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"success": False, "message": "Invalid administrator credentials. Access restricted to Vishwajeet only."}), 401

    if user["full_name"].strip().lower() != "vishwajeet":
        return jsonify({"success": False, "message": "Unauthorized. Only Administrator Vishwajeet is permitted to log in."}), 403

    session.clear()
    session["user_id"] = user["id"]

    return jsonify({
        "success": True,
        "message": "Welcome Administrator Vishwajeet.",
        "token": f"edumatch_token_{user['id']}",
        "user": {
            "id": user["id"],
            "fullName": user["full_name"],
            "email": user["email"],
            "role": "admin"
        }
    }), 200


@admin_bp.route("/dashboard", methods=["GET"])
def admin_dashboard_data():
    admin = verify_admin_access()
    if not admin:
        return jsonify({"success": False, "message": "Administrator privileges required."}), 403

    stats = get_admin_stats()
    return jsonify({
        "success": True,
        "admin": {
            "id": admin["id"],
            "name": admin["full_name"],
            "email": admin["email"],
            "role": "admin"
        },
        "stats": {
            "total_users": stats["total_users"],
            "total_students": stats["total_students"],
            "total_providers": stats["total_providers"],
            "total_orders": stats["total_requests"],
            "total_requirements": stats["total_requirements"],
            "active_services": 15,
            "total_disputes": 0
        },
        "recent_activity": [
            {"title": "Student Registered", "details": "Vishwajeet Rawat registered on EduMatch", "created_at": "Recent"},
            {"title": "DSA Match Executed", "details": "Student searched for Machine Learning & Python providers", "created_at": "Recent"},
            {"title": "Provider Verified", "details": "Aarav Sharma added verified ML credentials", "created_at": "Recent"}
        ],
        "order_summary": [
            {"status": "Pending", "count": stats["total_requests"]},
            {"status": "Active", "count": 2},
            {"status": "Completed", "count": 5}
        ],
        "recent_disputes": []
    }), 200


@admin_bp.route("/stats", methods=["GET"])
def platform_stats():
    admin = verify_admin_access()
    if not admin:
        return jsonify({"success": False, "message": "Administrator privileges required."}), 403

    stats = get_admin_stats()
    return jsonify({"success": True, "stats": stats}), 200


@admin_bp.route("/users", methods=["GET"])
def list_all_users():
    admin = verify_admin_access()
    if not admin:
        return jsonify({"success": False, "message": "Administrator privileges required."}), 403

    db = get_db()
    rows = db.execute(
        """
        SELECT id, full_name, email, role, is_active, created_at
        FROM users
        ORDER BY created_at DESC
        """
    ).fetchall()

    return jsonify({
        "success": True,
        "users": [dict(r) for r in rows]
    }), 200


@admin_bp.route("/users/<int:user_id>/status", methods=["PUT"])
def toggle_user_status(user_id):
    admin = verify_admin_access()
    if not admin:
        return jsonify({"success": False, "message": "Administrator privileges required."}), 403

    data = request.get_json(silent=True) or {}
    is_active = 1 if data.get("is_active", True) else 0

    db = get_db()
    db.execute("UPDATE users SET is_active = ? WHERE id = ?", (is_active, user_id))
    db.commit()

    return jsonify({"success": True, "message": "User status updated successfully."}), 200
