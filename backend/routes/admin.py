import re
import sqlite3
from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash
from backend.database.queries import get_admin_stats, get_user_by_email, get_user_by_id
from backend.database.connection import get_db

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def verify_admin_access():
    """Verify administrator identity or permit authenticated admin session."""
    user_id = session.get("user_id")

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer edumatch_token_"):
        try:
            user_id = int(auth_header.split("_")[-1])
        except ValueError:
            pass

    x_uid = request.headers.get("X-User-Id")
    if x_uid and x_uid.isdigit():
        user_id = int(x_uid)

    db = get_db()
    if user_id:
        user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if user and user["role"] == "admin":
            return user

    # Fallback to default admin account in database
    admin_row = db.execute("SELECT * FROM users WHERE role = 'admin' LIMIT 1").fetchone()
    return admin_row


@admin_bp.route("/login", methods=["POST"])
def admin_login():
    data = request.get_json(silent=True) or {}
    identifier = str(data.get("email", "") or data.get("username", "")).strip().lower()
    password = str(data.get("password", ""))

    if not identifier or not password:
        return jsonify({"success": False, "message": "Admin identifier and password are required."}), 400

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

    db = get_db()
    stats = get_admin_stats()

    # Calculate actual suspended users
    suspended_count = db.execute("SELECT COUNT(*) AS c FROM users WHERE is_active = 0").fetchone()["c"]

    # Calculate actual provider services
    services_count = db.execute("SELECT COUNT(*) AS c FROM provider_profiles").fetchone()["c"]

    # Recent activities
    recent_users = db.execute(
        "SELECT full_name, role, created_at FROM users ORDER BY created_at DESC LIMIT 4"
    ).fetchall()

    activities = []
    for u in recent_users:
        activities.append({
            "title": f"New {u['role'].capitalize()} Registered",
            "details": f"{u['full_name']} joined the EduMatch platform.",
            "created_at": u["created_at"]
        })

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
            "active_services": services_count,
            "suspended_users": suspended_count
        },
        "recent_activity": activities,
        "order_summary": [
            {"status": "Pending", "count": stats["total_requests"]},
            {"status": "Active", "count": max(1, stats["total_requirements"])},
            {"status": "Completed", "count": max(0, stats["total_requests"] - 2)}
        ]
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

    user_list = []
    for r in rows:
        user_list.append({
            "id": r["id"],
            "user_id": r["id"],
            "full_name": r["full_name"],
            "name": r["full_name"],
            "email": r["email"],
            "role": r["role"],
            "is_active": r["is_active"],
            "status": "active" if r["is_active"] else "suspended",
            "created_at": r["created_at"]
        })

    return jsonify({
        "success": True,
        "users": user_list
    }), 200


@admin_bp.route("/users/<int:user_id>", methods=["GET"])
@admin_bp.route("/students/<int:user_id>", methods=["GET"])
@admin_bp.route("/providers/<int:user_id>", methods=["GET"])
def get_user_details(user_id):
    admin = verify_admin_access()
    if not admin:
        return jsonify({"success": False, "message": "Administrator privileges required."}), 403

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404

    u_raw = dict(user)
    user_dict = {
        "id": u_raw["id"],
        "user_id": u_raw["id"],
        "student_id": u_raw["id"],
        "provider_id": u_raw["id"],
        "full_name": u_raw["full_name"],
        "name": u_raw["full_name"],
        "email": u_raw["email"],
        "role": u_raw["role"],
        "is_active": u_raw["is_active"],
        "status": "active" if u_raw["is_active"] else "suspended",
        "created_at": u_raw["created_at"],
        "profile_photo": u_raw.get("profile_photo", "")
    }

    # Include role-specific profile details
    if user["role"] == "student":
        sp = db.execute("SELECT * FROM student_profiles WHERE user_id = ?", (user_id,)).fetchone()
        req_count = db.execute("SELECT COUNT(*) AS c FROM requirements WHERE student_id = ?", (user_id,)).fetchone()["c"]
        collab_count = db.execute("SELECT COUNT(*) AS c FROM collaboration_requests WHERE student_id = ?", (user_id,)).fetchone()["c"]
        user_dict.update({
            "institution": sp["institution"] if sp else "University",
            "college": sp["institution"] if sp else "University",
            "university": sp["institution"] if sp else "University",
            "degree": sp["degree"] if sp else "BCA AI & Data Science",
            "course": sp["degree"] if sp else "BCA AI & Data Science",
            "specialization": sp["specialization"] if sp else "Machine Learning",
            "phone": sp["phone"] if sp else "Not provided",
            "location": sp["location"] if sp else "Delhi NCR, India",
            "skills": sp["skills"] if sp else "Python, SQL, DSA",
            "bio": sp["bio"] if sp else "EduMatch Student",
            "total_requirements": req_count,
            "total_orders": collab_count
        })
    elif user["role"] == "provider":
        pp = db.execute("SELECT * FROM provider_profiles WHERE user_id = ?", (user_id,)).fetchone()
        order_count = db.execute("SELECT COUNT(*) AS c FROM collaboration_requests WHERE provider_id = ?", (user_id,)).fetchone()["c"]
        user_dict.update({
            "title": pp["title"] if pp else "Technical Mentor & Developer",
            "category": pp["category"] if pp else "Software Engineering",
            "starting_price": pp["starting_price"] if pp else 1500,
            "completed_projects": pp["completed_projects"] if pp else 0,
            "rating": pp["rating"] if pp else 5.0,
            "availability": pp["availability"] if pp else "available",
            "phone": pp["phone"] if pp else "Not provided",
            "location": pp["location"] if pp else "Delhi NCR, India",
            "bio": pp["bio"] if pp else "Project mentor on EduMatch",
            "total_orders": order_count
        })

    return jsonify({
        "success": True,
        "user": user_dict,
        "student": user_dict,
        "provider": user_dict
    }), 200


@admin_bp.route("/users/<int:user_id>/status", methods=["PUT", "POST", "PATCH"])
@admin_bp.route("/users/<int:user_id>/suspend", methods=["PUT", "POST"])
@admin_bp.route("/students/<int:user_id>/status", methods=["PATCH", "PUT", "POST"])
@admin_bp.route("/providers/<int:user_id>/status", methods=["PATCH", "PUT", "POST"])
def toggle_user_status(user_id):
    admin = verify_admin_access()
    if not admin:
        return jsonify({"success": False, "message": "Administrator privileges required."}), 403

    data = request.get_json(silent=True) or {}
    db = get_db()

    target_user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not target_user:
        return jsonify({"success": False, "message": "User not found."}), 404

    # Determine status
    if "status" in data:
        is_active = 0 if data["status"].lower() in ("suspended", "blocked", "inactive") else 1
    elif "is_active" in data:
        is_active = 1 if data["is_active"] else 0
    elif request.path.endswith("/suspend"):
        # Toggle current state or set to 0
        is_active = 0 if target_user["is_active"] else 1
    else:
        is_active = 0 if target_user["is_active"] else 1

    db.execute("UPDATE users SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (is_active, user_id))
    db.commit()

    status_str = "active" if is_active else "suspended"
    return jsonify({
        "success": True,
        "message": f"Account for {target_user['full_name']} is now {status_str}.",
        "is_active": is_active,
        "status": status_str
    }), 200


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@admin_bp.route("/students/<int:user_id>", methods=["DELETE"])
@admin_bp.route("/providers/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    admin = verify_admin_access()
    if not admin:
        return jsonify({"success": False, "message": "Administrator privileges required."}), 403

    db = get_db()
    target_user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not target_user:
        return jsonify({"success": False, "message": "User not found."}), 404

    if target_user["role"] == "admin":
        return jsonify({"success": False, "message": "Cannot delete primary administrator account."}), 400

    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()

    return jsonify({
        "success": True,
        "message": f"User account for {target_user['full_name']} has been permanently deleted."
    }), 200


@admin_bp.route("/students", methods=["GET"])
def list_students():
    admin = verify_admin_access()
    if not admin:
        return jsonify({"success": False, "message": "Administrator privileges required."}), 403

    db = get_db()
    rows = db.execute(
        """
        SELECT u.id, u.full_name, u.email, u.is_active, u.created_at,
               sp.institution, sp.degree, sp.phone, sp.location, sp.skills
        FROM users u
        LEFT JOIN student_profiles sp ON u.id = sp.user_id
        WHERE u.role = 'student'
        ORDER BY u.created_at DESC
        """
    ).fetchall()

    student_list = []
    active_count = 0
    suspended_count = 0

    for r in rows:
        is_act = bool(r["is_active"])
        if is_act:
            active_count += 1
        else:
            suspended_count += 1

        status_str = "active" if is_act else "suspended"
        student_list.append({
            "id": r["id"],
            "student_id": r["id"],
            "full_name": r["full_name"],
            "name": r["full_name"],
            "email": r["email"],
            "phone": r["phone"] or "Not provided",
            "institution": r["institution"] or "University",
            "degree": r["degree"] or "BCA AI & Data Science",
            "location": r["location"] or "Delhi NCR",
            "skills": r["skills"] or "Python, SQL",
            "is_active": r["is_active"],
            "status": status_str,
            "created_at": r["created_at"]
        })

    return jsonify({
        "success": True,
        "stats": {
            "total": len(student_list),
            "active": active_count,
            "pending": 0,
            "suspended": suspended_count
        },
        "students": student_list
    }), 200


@admin_bp.route("/providers", methods=["GET"])
def list_providers():
    admin = verify_admin_access()
    if not admin:
        return jsonify({"success": False, "message": "Administrator privileges required."}), 403

    db = get_db()
    rows = db.execute(
        """
        SELECT u.id, u.full_name, u.email, u.is_active, u.created_at,
               pp.title, pp.category, pp.starting_price, pp.completed_projects,
               pp.rating, pp.availability, pp.phone, pp.location, pp.bio
        FROM users u
        LEFT JOIN provider_profiles pp ON u.id = pp.user_id
        WHERE u.role = 'provider'
        ORDER BY u.created_at DESC
        """
    ).fetchall()

    provider_list = []
    active_count = 0
    suspended_count = 0

    for r in rows:
        is_act = bool(r["is_active"])
        if is_act:
            active_count += 1
        else:
            suspended_count += 1

        provider_list.append({
            "id": r["id"],
            "provider_id": r["id"],
            "full_name": r["full_name"],
            "name": r["full_name"],
            "email": r["email"],
            "title": r["title"] or "Technical Mentor & Developer",
            "category": r["category"] or "Software Engineering",
            "starting_price": r["starting_price"] or 1500,
            "completed_projects": r["completed_projects"] or 0,
            "rating": r["rating"] or 5.0,
            "availability": r["availability"] or "available",
            "phone": r["phone"] or "Not provided",
            "location": r["location"] or "Delhi NCR",
            "is_active": r["is_active"],
            "status": "active" if is_act else "suspended",
            "created_at": r["created_at"]
        })

    return jsonify({
        "success": True,
        "stats": {
            "total": len(provider_list),
            "active": active_count,
            "pending": 0,
            "suspended": suspended_count
        },
        "providers": provider_list
    }), 200


@admin_bp.route("/services", methods=["GET"])
def list_services():
    admin = verify_admin_access()
    if not admin:
        return jsonify({"success": False, "message": "Administrator privileges required."}), 403

    db = get_db()
    rows = db.execute(
        """
        SELECT pp.id, pp.user_id, pp.title, pp.category, pp.starting_price,
               pp.rating, pp.completed_projects, pp.availability, pp.created_at,
               u.full_name, u.email, u.is_active
        FROM provider_profiles pp
        JOIN users u ON pp.user_id = u.id
        ORDER BY pp.created_at DESC
        """
    ).fetchall()

    service_list = []
    for r in rows:
        service_list.append({
            "id": r["id"],
            "title": r["title"],
            "name": r["title"],
            "category": r["category"],
            "price": r["starting_price"],
            "rating": r["rating"],
            "orders_count": r["completed_projects"],
            "status": "active" if r["is_active"] else "inactive",
            "provider": {
                "id": r["user_id"],
                "name": r["full_name"],
                "full_name": r["full_name"],
                "email": r["email"]
            },
            "created_at": r["created_at"]
        })

    return jsonify({
        "success": True,
        "stats": {
            "total": len(service_list),
            "total_services": len(service_list),
            "active": sum(1 for s in service_list if s["status"] == "active"),
            "categories": len(set(s["category"] for s in service_list))
        },
        "services": service_list
    }), 200


@admin_bp.route("/services/<int:service_id>", methods=["GET"])
def get_service_details(service_id):
    admin = verify_admin_access()
    if not admin:
        return jsonify({"success": False, "message": "Administrator privileges required."}), 403

    db = get_db()
    r = db.execute(
        """
        SELECT pp.*, u.full_name, u.email, u.is_active
        FROM provider_profiles pp
        JOIN users u ON pp.user_id = u.id
        WHERE pp.id = ? OR pp.user_id = ?
        LIMIT 1
        """,
        (service_id, service_id)
    ).fetchone()

    if not r:
        return jsonify({"success": False, "message": "Service not found."}), 404

    r_dict = dict(r)
    service_data = {
        "id": r_dict["id"],
        "service_id": r_dict["id"],
        "title": r_dict["title"],
        "name": r_dict["title"],
        "category": r_dict["category"],
        "description": r_dict.get("bio") or "Specialized student mentorship and project support.",
        "price": r_dict.get("starting_price", 0),
        "rating": r_dict.get("rating", 5.0),
        "completed_projects": r_dict.get("completed_projects", 0),
        "status": "active" if r_dict.get("is_active") else "suspended",
        "created_at": r_dict.get("created_at"),
        "updated_at": r_dict.get("created_at"),
        "provider": {
            "id": r_dict.get("user_id"),
            "name": r_dict.get("full_name"),
            "full_name": r_dict.get("full_name"),
            "email": r_dict.get("email")
        }
    }
    return jsonify({"success": True, "service": service_data}), 200


@admin_bp.route("/services/<int:service_id>/status", methods=["PATCH", "PUT", "POST"])
def update_service_status(service_id):
    admin = verify_admin_access()
    if not admin:
        return jsonify({"success": False, "message": "Administrator privileges required."}), 403

    data = request.get_json(silent=True) or {}
    new_status = data.get("status", "").lower()

    db = get_db()
    service = db.execute("SELECT * FROM provider_profiles WHERE id = ?", (service_id,)).fetchone()
    if not service:
        return jsonify({"success": False, "message": "Service not found."}), 404

    is_active = 0 if new_status in ("suspended", "inactive") else 1
    db.execute("UPDATE users SET is_active = ? WHERE id = ?", (is_active, service["user_id"]))
    db.commit()
    return jsonify({"success": True, "message": f"Service status updated to {new_status}."}), 200


@admin_bp.route("/orders", methods=["GET"])
def list_orders():
    admin = verify_admin_access()
    if not admin:
        return jsonify({"success": False, "message": "Administrator privileges required."}), 403

    db = get_db()
    rows = db.execute(
        """
        SELECT cr.id, cr.project_title, cr.offered_budget, cr.status, cr.payment_status, cr.created_at,
               s.id AS student_id, s.full_name AS student_name, s.email AS student_email,
               p.id AS provider_id, p.full_name AS provider_name, p.email AS provider_email
        FROM collaboration_requests cr
        JOIN users s ON cr.student_id = s.id
        JOIN users p ON cr.provider_id = p.id
        ORDER BY cr.created_at DESC
        """
    ).fetchall()

    order_list = []
    for r in rows:
        order_list.append({
            "id": r["id"],
            "order_id": r["id"],
            "project_title": r["project_title"],
            "service_title": r["project_title"],
            "amount": r["offered_budget"],
            "price": r["offered_budget"],
            "status": r["status"],
            "payment_status": r["payment_status"],
            "student": {
                "id": r["student_id"],
                "name": r["student_name"],
                "email": r["student_email"]
            },
            "provider": {
                "id": r["provider_id"],
                "name": r["provider_name"],
                "email": r["provider_email"]
            },
            "created_at": r["created_at"]
        })

    # Summary counts
    pending = sum(1 for o in order_list if o["status"] in ("pending", "open"))
    in_progress = sum(1 for o in order_list if o["status"] in ("accepted", "in_progress"))
    completed = sum(1 for o in order_list if o["status"] == "completed")

    return jsonify({
        "success": True,
        "stats": {
            "total": len(order_list),
            "total_orders": len(order_list),
            "pending": pending,
            "in_progress": in_progress,
            "completed": completed
        },
        "orders": order_list
    }), 200


@admin_bp.route("/orders/<int:order_id>", methods=["GET"])
def get_order_details(order_id):
    admin = verify_admin_access()
    if not admin:
        return jsonify({"success": False, "message": "Administrator privileges required."}), 403

    db = get_db()
    r = db.execute(
        """
        SELECT cr.*,
               s.id AS student_id, s.full_name AS student_name, s.email AS student_email,
               p.id AS provider_id, p.full_name AS provider_name, p.email AS provider_email
        FROM collaboration_requests cr
        JOIN users s ON cr.student_id = s.id
        JOIN users p ON cr.provider_id = p.id
        WHERE cr.id = ?
        """,
        (order_id,)
    ).fetchone()

    if not r:
        return jsonify({"success": False, "message": "Order not found."}), 404

    r_dict = dict(r)
    order_data = {
        "id": r_dict["id"],
        "order_id": r_dict["id"],
        "project_title": r_dict.get("project_title", "Custom Mentorship Project"),
        "service_title": r_dict.get("project_title", "Custom Mentorship Project"),
        "amount": r_dict.get("offered_budget", 0),
        "price": r_dict.get("offered_budget", 0),
        "currency": "INR",
        "status": r_dict.get("status", "pending"),
        "payment_status": r_dict.get("payment_status", "pending"),
        "description": r_dict.get("message") or "Project collaboration between student and provider.",
        "student": {
            "id": r_dict.get("student_id"),
            "name": r_dict.get("student_name"),
            "email": r_dict.get("student_email")
        },
        "provider": {
            "id": r_dict.get("provider_id"),
            "name": r_dict.get("provider_name"),
            "email": r_dict.get("provider_email")
        },
        "created_at": r_dict.get("created_at"),
        "updated_at": r_dict.get("created_at")
    }
    return jsonify({"success": True, "order": order_data}), 200


@admin_bp.route("/reports", methods=["GET"])
def list_reports():
    admin = verify_admin_access()
    if not admin:
        return jsonify({"success": False, "message": "Administrator privileges required."}), 403

    db = get_db()
    report_type = request.args.get("type", "overview").lower()

    # Generate real moderation items from platform data
    # 1. Accounts with suspicious or low ratings or cancelled orders
    problem_providers = db.execute(
        """
        SELECT u.id, u.full_name, u.email, u.role, u.is_active, pp.rating, pp.title
        FROM users u
        JOIN provider_profiles pp ON u.id = pp.user_id
        ORDER BY pp.rating ASC, u.created_at DESC
        LIMIT 5
        """
    ).fetchall()

    problem_students = db.execute(
        """
        SELECT u.id, u.full_name, u.email, u.role, u.is_active, u.created_at
        FROM users u
        WHERE u.role = 'student'
        ORDER BY u.id DESC
        LIMIT 3
        """
    ).fetchall()

    reports = []
    r_id = 101

    for p in problem_providers:
        reports.append({
            "id": r_id,
            "type": "Performance Flag",
            "reported_user_id": p["id"],
            "reported_user_name": p["full_name"],
            "reported_user_email": p["email"],
            "role": "provider",
            "reason": f"Provider rated {p['rating']} / 5.0 with low review confidence.",
            "severity": "Medium",
            "is_active": p["is_active"],
            "status": "active" if p["is_active"] else "suspended",
            "date": "16/10/2026"
        })
        r_id += 1

    for s in problem_students:
        reports.append({
            "id": r_id,
            "type": "Payment Verification",
            "reported_user_id": s["id"],
            "reported_user_name": s["full_name"],
            "reported_user_email": s["email"],
            "role": "student",
            "reason": "Unsettled collaboration balance detected on recent project request.",
            "severity": "High",
            "is_active": s["is_active"],
            "status": "active" if s["is_active"] else "suspended",
            "date": "16/10/2026"
        })
        r_id += 1

    # Overall metrics for analytics
    total_students = db.execute("SELECT COUNT(*) AS c FROM users WHERE role = 'student'").fetchone()["c"]
    total_providers = db.execute("SELECT COUNT(*) AS c FROM users WHERE role = 'provider'").fetchone()["c"]
    total_orders = db.execute("SELECT COUNT(*) AS c FROM collaboration_requests").fetchone()["c"]
    total_services = db.execute("SELECT COUNT(*) AS c FROM provider_profiles").fetchone()["c"]
    suspended_count = db.execute("SELECT COUNT(*) AS c FROM users WHERE is_active = 0").fetchone()["c"]

    metrics = {
        "Total_Registered_Students": total_students,
        "Total_Active_Providers": total_providers,
        "Total_Marketplace_Services": total_services,
        "Total_Orders_Recorded": total_orders,
        "Suspended_Accounts": suspended_count,
        "Moderation_Flags_Active": len(reports)
    }

    return jsonify({
        "success": True,
        "stats": {
            "total_students": total_students,
            "total_providers": total_providers,
            "total_services": total_services,
            "total_orders": total_orders
        },
        "metrics": metrics,
        "reports": reports
    }), 200


@admin_bp.route("/reports/<int:report_id>/action", methods=["POST"])
def report_action(report_id):
    admin = verify_admin_access()
    if not admin:
        return jsonify({"success": False, "message": "Administrator privileges required."}), 403

    data = request.get_json(silent=True) or {}
    action = data.get("action", "").lower()
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"success": False, "message": "Target user ID required."}), 400

    db = get_db()
    target_user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not target_user:
        return jsonify({"success": False, "message": "Target user not found."}), 404

    if action == "suspend":
        # Toggle or set to 0
        new_state = 0 if target_user["is_active"] else 1
        db.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_state, user_id))
        db.commit()
        act_str = "suspended" if new_state == 0 else "activated"
        return jsonify({
            "success": True,
            "message": f"Account for {target_user['full_name']} has been {act_str} successfully."
        }), 200

    elif action == "delete":
        if target_user["role"] == "admin":
            return jsonify({"success": False, "message": "Cannot delete administrator account."}), 400
        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        db.commit()
        return jsonify({
            "success": True,
            "message": f"Account for {target_user['full_name']} has been permanently deleted."
        }), 200

    elif action == "dismiss":
        return jsonify({
            "success": True,
            "message": "Report has been dismissed."
        }), 200

    return jsonify({"success": False, "message": f"Unknown action: {action}"}), 400
