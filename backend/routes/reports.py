
from flask import Blueprint, jsonify, request
import sqlite3

from backend.database.connection import get_db
from backend.routes.requests import get_auth_user_id
from backend.models.report import (
    create_report,
    get_all_reports,
    get_report_by_id,
    update_report_status,
)

reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")


def is_admin(user_id):
    """Return True only when the logged-in user is an admin."""
    if not user_id:
        return False

    db = get_db()
    user = db.execute(
        "SELECT role FROM users WHERE id = ? AND is_active = 1",
        (user_id,),
    ).fetchone()

    return user is not None and user["role"] == "admin"


@reports_bp.route("", methods=["POST"])
def submit_report():
    """Allow a logged-in user to submit a report."""
    user_id = get_auth_user_id()

    if not user_id:
        return jsonify({
            "success": False,
            "message": "Please log in to submit a report."
        }), 401

    data = request.get_json(silent=True) or {}

    reason = data.get("reason", "")
    description = data.get("description", "")
    reported_user_id = data.get("reported_user_id")

    try:
        if reported_user_id is not None:
            reported_user_id = int(reported_user_id)
            if reported_user_id <= 0:
                raise ValueError("Invalid reported user ID.")

        report_id = create_report(
            reporter_id=user_id,
            reason=reason,
            description=description,
            reported_user_id=reported_user_id,
        )

        return jsonify({
            "success": True,
            "message": "Report submitted successfully.",
            "report_id": report_id,
        }), 201

    except ValueError as error:
        return jsonify({
            "success": False,
            "message": str(error),
        }), 400

    except (sqlite3.IntegrityError, TypeError):
        return jsonify({
            "success": False,
            "message": "Invalid report data or user ID.",
        }), 400


@reports_bp.route("", methods=["GET"])
def list_reports():
    """Allow administrators to view reports, optionally by status."""
    user_id = get_auth_user_id()

    if not user_id:
        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    if not is_admin(user_id):
        return jsonify({
            "success": False,
            "message": "Administrator access required."
        }), 403

    status = request.args.get("status")

    try:
        reports = get_all_reports(status=status)
        return jsonify({
            "success": True,
            "reports": reports,
        }), 200

    except ValueError as error:
        return jsonify({
            "success": False,
            "message": str(error),
        }), 400


@reports_bp.route("/<int:report_id>", methods=["GET"])
def report_details(report_id):
    """Allow administrators to view one report."""
    user_id = get_auth_user_id()

    if not user_id:
        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    if not is_admin(user_id):
        return jsonify({
            "success": False,
            "message": "Administrator access required."
        }), 403

    report = get_report_by_id(report_id)

    if report is None:
        return jsonify({
            "success": False,
            "message": "Report not found."
        }), 404

    return jsonify({
        "success": True,
        "report": report,
    }), 200


@reports_bp.route("/<int:report_id>/status", methods=["PATCH"])
def change_report_status(report_id):
    """Allow administrators to update a report's status."""
    user_id = get_auth_user_id()

    if not user_id:
        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    if not is_admin(user_id):
        return jsonify({
            "success": False,
            "message": "Administrator access required."
        }), 403

    data = request.get_json(silent=True) or {}
    status = data.get("status")

    if not isinstance(status, str):
        return jsonify({
            "success": False,
            "message": "A valid status is required."
        }), 400

    status = status.strip().lower()

    try:
        updated = update_report_status(report_id, status)

        if not updated:
            return jsonify({
                "success": False,
                "message": "Report not found."
            }), 404

        return jsonify({
            "success": True,
            "message": "Report status updated successfully.",
        }), 200

    except ValueError as error:
        return jsonify({
            "success": False,
            "message": str(error),
        }), 400
