
from flask import Blueprint, jsonify, request
from backend.database.connection import get_db

services_bp = Blueprint(
    "services",
    __name__,
    url_prefix="/api/services"
)


@services_bp.route("", methods=["GET"])
def list_services():
    """List public services with optional search and category filters."""
    db = get_db()

    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    sql = """
        SELECT
            s.id,
            s.provider_id,
            s.title,
            s.category,
            s.description,
            s.price,
            s.delivery_days,
            u.full_name AS provider_name,
            p.title AS provider_title,
            p.rating AS provider_rating
        FROM services s
        LEFT JOIN users u ON u.id = s.provider_id
        LEFT JOIN provider_profiles p ON p.user_id = s.provider_id
        WHERE 1 = 1
    """
    params = []

    if query:
        sql += """
            AND (
                s.title LIKE ?
                OR s.description LIKE ?
                OR s.category LIKE ?
            )
        """
        search = f"%{query}%"
        params.extend([search, search, search])

    if category and category.lower() != "all":
        sql += " AND LOWER(s.category) = LOWER(?)"
        params.append(category)

    sql += " ORDER BY s.id DESC"

    rows = db.execute(sql, params).fetchall()
    services = [dict(row) for row in rows]

    return jsonify({
        "success": True,
        "count": len(services),
        "services": services
    }), 200


@services_bp.route("/<int:service_id>", methods=["GET"])
def get_service(service_id):
    """Get one public service by ID."""
    db = get_db()

    row = db.execute(
        """
        SELECT
            s.id,
            s.provider_id,
            s.title,
            s.category,
            s.description,
            s.price,
            s.delivery_days,
            u.full_name AS provider_name,
            p.title AS provider_title,
            p.rating AS provider_rating
        FROM services s
        LEFT JOIN users u ON u.id = s.provider_id
        LEFT JOIN provider_profiles p ON p.user_id = s.provider_id
        WHERE s.id = ?
        """,
        (service_id,)
    ).fetchone()

    if not row:
        return jsonify({
            "success": False,
            "message": "Service not found."
        }), 404

    return jsonify({
        "success": True,
        "service": dict(row)
    }), 200
