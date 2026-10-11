from flask import Blueprint, jsonify, request, session
from backend.database.queries import (
    create_collaboration_request,
    get_requests_for_provider,
    get_requests_for_student,
    update_request_status,
    get_user_by_id,
    get_or_create_conversation
)
from backend.database.connection import get_db

requests_bp = Blueprint("requests", __name__, url_prefix="/api/requests")


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


@requests_bp.route("", methods=["POST"])
def send_request():
    user_id = get_auth_user_id()
    if not user_id:
        return jsonify({"success": False, "message": "You must be logged in to send requests."}), 401

    data = request.get_json(silent=True) or {}
    provider_id = data.get("provider_id")
    project_title = str(data.get("project_title", "")).strip()
    message = str(data.get("message", "")).strip()
    
    try:
        budget = int(data.get("offered_budget", 2000))
    except (ValueError, TypeError):
        budget = 2000

    if not provider_id or not project_title or not message:
        return jsonify({"success": False, "message": "Provider, project title, and message are required."}), 400

    provider = get_user_by_id(provider_id)
    if not provider or provider["role"] != "provider":
        return jsonify({"success": False, "message": "Selected provider does not exist."}), 404

    req_id = create_collaboration_request(
        student_id=user_id,
        provider_id=provider_id,
        project_title=project_title,
        message=message,
        offered_budget=budget,
        requirement_id=data.get("requirement_id")
    )

    # Automatically create conversation so they can immediately chat
    get_or_create_conversation(user_id, provider_id)

    return jsonify({
        "success": True,
        "message": "Collaboration request sent successfully!",
        "request_id": req_id
    }), 201


@requests_bp.route("", methods=["GET"])
def get_my_requests():
    user_id = get_auth_user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Not logged in."}), 401

    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404

    if user["role"] == "provider":
        reqs = get_requests_for_provider(user_id)
    else:
        reqs = get_requests_for_student(user_id)

    return jsonify({"success": True, "requests": reqs}), 200


@requests_bp.route("/<int:request_id>/status", methods=["PUT", "PATCH"])
def change_status(request_id):
    user_id = get_auth_user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Not logged in."}), 401

    data = request.get_json(silent=True) or {}
    new_status = data.get("status")

    if new_status not in ("accepted", "rejected", "completed"):
        return jsonify({"success": False, "message": "Invalid status transition."}), 400

    success = update_request_status(request_id, new_status, provider_id=user_id)
    if not success:
        return jsonify({"success": False, "message": "Request not found or unauthorized."}), 403

    return jsonify({
        "success": True,
        "message": f"Collaboration request marked as {new_status}."
    }), 200

