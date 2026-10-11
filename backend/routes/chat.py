from flask import Blueprint, jsonify, request, session
from backend.database.queries import (
    get_user_conversations,
    get_messages,
    add_message,
    get_or_create_conversation,
    get_user_by_id
)
from backend.database.connection import get_db

chat_bp = Blueprint("chat", __name__)


def get_authenticated_user_id():
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


@chat_bp.route("/api/chat/conversations", methods=["GET"])
@chat_bp.route("/api/student/conversations", methods=["GET"])
@chat_bp.route("/api/provider/conversations", methods=["GET"])
def list_conversations():
    user_id = get_authenticated_user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Not logged in."}), 401

    raw_convs = get_user_conversations(user_id)
    formatted = []
    for c in raw_convs:
        formatted.append({
            "id": c["id"],
            "participant": {
                "id": c["other_user_id"],
                "name": c["other_user_name"],
                "role": c["other_user_role"].capitalize()
            },
            "project_title": "Academic Project Collaboration",
            "last_message": c["last_message"] or "Start conversation",
            "updated_at": c["updated_at"]
        })

    user = get_user_by_id(user_id)
    return jsonify({
        "success": True,
        "conversations": formatted,
        "current_user": {
            "id": user_id,
            "name": user["full_name"] if user else "User"
        }
    }), 200


@chat_bp.route("/api/chat/start", methods=["POST"])
def start_conversation():
    user_id = get_authenticated_user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Not logged in."}), 401

    data = request.get_json(silent=True) or {}
    raw_id = data.get("other_user_id") or data.get("provider_id") or data.get("student_id")
    if not raw_id:
        return jsonify({"success": False, "message": "Recipient user ID is required."}), 400

    try:
        target_id = int(raw_id)
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid recipient user ID."}), 400

    db = get_db()
    # Check if target_id is actually a provider_profiles.id
    if "provider_id" in data or not get_user_by_id(target_id):
        p_row = db.execute("SELECT user_id FROM provider_profiles WHERE id = ?", (target_id,)).fetchone()
        if p_row:
            target_id = p_row["user_id"]

    target = get_user_by_id(target_id)
    if not target:
        return jsonify({"success": False, "message": "User not found."}), 404

    conv_id = get_or_create_conversation(user_id, target_id)
    return jsonify({
        "success": True,
        "conversation_id": conv_id,
        "recipient": {
            "id": target["id"],
            "name": target["full_name"],
            "role": target["role"]
        }
    }), 200


@chat_bp.route("/api/chat/conversations/<int:conv_id>/messages", methods=["GET", "POST"])
@chat_bp.route("/api/student/conversations/<int:conv_id>/messages", methods=["GET", "POST"])
@chat_bp.route("/api/provider/conversations/<int:conv_id>/messages", methods=["GET", "POST"])
def conversation_messages(conv_id):
    user_id = get_authenticated_user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Not logged in."}), 401

    db = get_db()
    c = db.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
    if not c or (c["user1_id"] != user_id and c["user2_id"] != user_id):
        return jsonify({"success": False, "message": "Unauthorized conversation access."}), 403

    if request.method == "GET":
        raw_msgs = get_messages(conv_id, user_id)
        formatted = []
        for m in raw_msgs:
            formatted.append({
                "id": m["id"],
                "conversation_id": m["conversation_id"],
                "sender_id": m["sender_id"],
                "sender_name": m["sender_name"],
                "message": m["message_text"],
                "created_at": m["created_at"]
            })
        return jsonify({
            "success": True,
            "messages": formatted,
            "current_user": {"id": user_id}
        }), 200

    # POST send message
    data = request.get_json(silent=True) or {}
    text = str(data.get("message", "")).strip()
    if not text:
        return jsonify({"success": False, "message": "Message text cannot be empty."}), 400

    msg = add_message(conv_id, user_id, text)
    return jsonify({
        "success": True,
        "message": {
            "id": msg["id"],
            "conversation_id": conv_id,
            "sender_id": user_id,
            "message": text,
            "created_at": "Just now"
        }
    }), 201
