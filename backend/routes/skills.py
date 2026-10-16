
from flask import Blueprint, jsonify, request
from backend.database.connection import get_db

skills_bp = Blueprint("skills", __name__, url_prefix="/api/skills")


@skills_bp.route("", methods=["GET"])
def list_skills():
    """List all available skills, optionally filtered by name."""
    db = get_db()
    query = request.args.get("q", "").strip()

    if query:
        rows = db.execute(
            """
            SELECT id, name
            FROM skills
            WHERE name LIKE ?
            ORDER BY name ASC
            """,
            (f"%{query}%",)
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT id, name
            FROM skills
            ORDER BY name ASC
            """
        ).fetchall()

    return jsonify({
        "success": True,
        "count": len(rows),
        "skills": [dict(row) for row in rows]
    }), 200


@skills_bp.route("/<int:skill_id>", methods=["GET"])
def get_skill(skill_id):
    """Get one skill by its ID."""
    db = get_db()

    row = db.execute(
        "SELECT id, name FROM skills WHERE id = ?",
        (skill_id,)
    ).fetchone()

    if not row:
        return jsonify({
            "success": False,
            "message": "Skill not found."
        }), 404

    return jsonify({
        "success": True,
        "skill": dict(row)
    }), 200
