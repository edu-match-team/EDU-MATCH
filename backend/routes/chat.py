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
    db = get_db()
    formatted = []
    for c in raw_convs:
        u_row = db.execute(
            """
            SELECT COALESCE(
                NULLIF(u.profile_photo, ''),
                NULLIF((SELECT profile_photo FROM student_profiles WHERE user_id = u.id), ''),
                NULLIF((SELECT profile_photo FROM provider_profiles WHERE user_id = u.id), ''),
                ''
            ) AS photo
            FROM users u WHERE u.id = ?
            """,
            (c["other_user_id"],)
        ).fetchone()
        photo = u_row["photo"] if u_row else ""
        formatted.append({
            "id": c["id"],
            "participant": {
                "id": c["other_user_id"],
                "name": c["other_user_name"],
                "role": c["other_user_role"].capitalize(),
                "photo": photo
            },
            "project_title": "Academic Project Collaboration",
            "last_message": c["last_message"] or "Start conversation",
            "updated_at": c["updated_at"]
        })

    cur_user_row = db.execute(
        """
        SELECT u.id, u.full_name,
               COALESCE(
                   NULLIF(u.profile_photo, ''),
                   NULLIF((SELECT profile_photo FROM student_profiles WHERE user_id = u.id), ''),
                   NULLIF((SELECT profile_photo FROM provider_profiles WHERE user_id = u.id), ''),
                   ''
               ) AS photo
        FROM users u WHERE u.id = ?
        """,
        (user_id,)
    ).fetchone()

    return jsonify({
        "success": True,
        "conversations": formatted,
        "current_user": {
            "id": user_id,
            "name": cur_user_row["full_name"] if cur_user_row else "User",
            "photo": cur_user_row["photo"] if cur_user_row else ""
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
            "role": target["role"],
            "photo": target["profile_photo"] if "profile_photo" in target.keys() else ""
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
                "sender_photo": m.get("sender_photo", ""),
                "message": m["message_text"],
                "is_deleted": m.get("is_deleted", False),
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

    # Trigger instant notification to recipient
    other_user_id = c["user2_id"] if c["user1_id"] == user_id else c["user1_id"]
    try:
        from backend.database.queries import create_notification
        sender = get_user_by_id(user_id)
        s_name = sender["full_name"] if sender else "EduMatch User"
        recipient = get_user_by_id(other_user_id)
        chat_link = "/student/chat.html" if recipient and recipient["role"] == "student" else "/provider/chat.html"
        create_notification(
            user_id=other_user_id,
            title=f"New Message from {s_name}",
            message=text[:80] + ("..." if len(text) > 80 else ""),
            link=chat_link
        )
    except Exception as e:
        print(f"[Notification] Chat error: {e}")

    # Sync message to Supabase in the background / try block
    try:
        from backend.database.supabase_client import sync_message_to_supabase
        sync_message_to_supabase(conv_id, user_id, text)
    except Exception as e:
        print(f"[Supabase Sync] Message error: {e}")

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


@chat_bp.route("/api/chat/messages/<int:msg_id>", methods=["DELETE"])
@chat_bp.route("/api/student/messages/<int:msg_id>", methods=["DELETE"])
@chat_bp.route("/api/provider/messages/<int:msg_id>", methods=["DELETE"])
def delete_chat_message(msg_id):
    user_id = get_authenticated_user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Not logged in."}), 401

    data = request.get_json(silent=True) or {}
    delete_for = data.get("delete_for", "everyone")  # "everyone" or "me"

    from backend.database.queries import delete_message_for_everyone, delete_message_for_user

    if delete_for == "everyone":
        success = delete_message_for_everyone(msg_id, user_id)
        if not success:
            return jsonify({"success": False, "message": "Only the sender can delete a message for everyone."}), 403
        return jsonify({"success": True, "message": "Message deleted for everyone."}), 200
    else:
        success = delete_message_for_user(msg_id, user_id)
        return jsonify({"success": True, "message": "Message deleted for you."}), 200


@chat_bp.route("/api/chat/conversations/<int:conv_id>/clear", methods=["DELETE", "POST"])
@chat_bp.route("/api/student/conversations/<int:conv_id>/clear", methods=["DELETE", "POST"])
@chat_bp.route("/api/provider/conversations/<int:conv_id>/clear", methods=["DELETE", "POST"])
def clear_chat_conversation(conv_id):
    user_id = get_authenticated_user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Not logged in."}), 401

    from backend.database.queries import clear_conversation_for_user
    clear_conversation_for_user(conv_id, user_id)
    return jsonify({"success": True, "message": "Conversation cleared successfully."}), 200
