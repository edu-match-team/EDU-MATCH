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
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer edumatch_token_"):
        try:
            return int(auth_header.split("_")[-1])
        except ValueError:
            pass
    elif auth_header.startswith("Bearer "):
        token_val = auth_header.split(" ", 1)[1].strip()
        parts = token_val.split("_")
        try:
            return int(parts[-1])
        except (ValueError, IndexError):
            pass

    x_uid = request.headers.get("X-User-Id", "").strip()
    if x_uid.isdigit():
        return int(x_uid)

    user_id = session.get("user_id")
    if user_id:
        return user_id

    return None


@chat_bp.route("/api/chat/conversations", methods=["GET"])
@chat_bp.route("/api/student/conversations", methods=["GET"])
@chat_bp.route("/api/provider/conversations", methods=["GET"])
def list_conversations():
    user_id = get_authenticated_user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Not logged in."}), 401

    db = get_db()
    cur_user_row = db.execute(
        """
        SELECT u.id, u.full_name, u.role,
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

    cur_role = (cur_user_row["role"] if cur_user_row else "").lower()
    raw_convs = get_user_conversations(user_id)
    formatted = []
    for c in raw_convs:
        other_role = (c.get("other_user_role") or "").lower()

        # Enforce strict role isolation:
        # A student only ever sees providers in their chat list.
        # A provider only ever sees students in their chat list.
        if request.path.startswith("/api/student") or (cur_role == "student" and not request.path.startswith("/api/provider")):
            if other_role != "provider":
                continue
        elif request.path.startswith("/api/provider") or (cur_role == "provider" and not request.path.startswith("/api/student")):
            if other_role != "student":
                continue

        # Strict connection check:
        # Only show users with at least 1 visible message OR an active pending/accepted/in_progress collaboration request
        vis_count = int(c.get("visible_message_count") or 0)
        has_msg = vis_count > 0 and bool(c.get("last_message"))
        has_active_req = db.execute(
            """
            SELECT 1 FROM collaboration_requests 
            WHERE ((student_id = ? AND provider_id = ?) OR (student_id = ? AND provider_id = ?))
              AND status IN ('pending', 'accepted', 'in_progress')
            LIMIT 1
            """,
            (user_id, c["other_user_id"], c["other_user_id"], user_id)
        ).fetchone()

        active_q = request.args.get("conversation_id") or request.args.get("conv_id")
        if not (has_msg or has_active_req):
            if not (active_q and str(active_q) == str(c["id"])):
                continue

        u_row = db.execute(
            """
            SELECT u.id, u.full_name, u.email, u.role,
                   COALESCE(
                       NULLIF(u.profile_photo, ''),
                       NULLIF((SELECT profile_photo FROM student_profiles WHERE user_id = u.id), ''),
                       NULLIF((SELECT profile_photo FROM provider_profiles WHERE user_id = u.id), ''),
                       ''
                   ) AS photo,
                   COALESCE((SELECT institution FROM student_profiles WHERE user_id = u.id), '') AS institution,
                   COALESCE((SELECT degree FROM student_profiles WHERE user_id = u.id), '') AS degree,
                   COALESCE((SELECT skills FROM student_profiles WHERE user_id = u.id), '') AS skills,
                   COALESCE((SELECT bio FROM student_profiles WHERE user_id = u.id), '') AS bio,
                   COALESCE((SELECT phone FROM student_profiles WHERE user_id = u.id), '') AS phone
            FROM users u WHERE u.id = ?
            """,
            (c["other_user_id"],)
        ).fetchone()
        photo = u_row["photo"] if u_row else ""
        formatted.append({
            "id": c["id"],
            "conversation_id": c["id"],
            "other_user_id": c["other_user_id"],
            "other_user_name": c["other_user_name"],
            "other_user_role": c["other_user_role"].capitalize(),
            "other_user_photo": photo,
            "student_profile": {
                "id": c["other_user_id"],
                "full_name": c["other_user_name"],
                "name": c["other_user_name"],
                "photo": photo,
                "profile_photo": photo,
                "institution": u_row["institution"] if u_row else "",
                "college": u_row["institution"] if u_row else "",
                "degree": u_row["degree"] if u_row else "",
                "skills": u_row["skills"] if u_row else "",
                "bio": u_row["bio"] if u_row else "",
                "phone": u_row["phone"] if u_row else "",
                "email": u_row["email"] if u_row else ""
            } if u_row and u_row["role"] == "student" else None,
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
    # Check if target_id is directly a user in users table
    target = get_user_by_id(target_id)
    if not target:
        # Check if target_id was a provider_profiles.id
        p_row = db.execute("SELECT user_id FROM provider_profiles WHERE id = ?", (target_id,)).fetchone()
        if p_row:
            target_id = p_row["user_id"]
            target = get_user_by_id(target_id)
    if not target:
        # Check if target_id was a student_profiles.id
        s_row = db.execute("SELECT user_id FROM student_profiles WHERE id = ?", (target_id,)).fetchone()
        if s_row:
            target_id = s_row["user_id"]
            target = get_user_by_id(target_id)

    if not target:
        return jsonify({"success": False, "message": "User not found."}), 404

    conv_id = get_or_create_conversation(user_id, target_id)
    u_photo = db.execute(
        """
        SELECT COALESCE(
            NULLIF(u.profile_photo, ''),
            NULLIF((SELECT profile_photo FROM student_profiles WHERE user_id = u.id), ''),
            NULLIF((SELECT profile_photo FROM provider_profiles WHERE user_id = u.id), ''),
            ''
        ) AS photo
        FROM users u WHERE u.id = ?
        """,
        (target["id"],)
    ).fetchone()

    return jsonify({
        "success": True,
        "conversation_id": conv_id,
        "recipient": {
            "id": target["id"],
            "name": target["full_name"],
            "role": target["role"],
            "photo": u_photo["photo"] if u_photo else ""
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

    other_user_id = c["user2_id"] if c["user1_id"] == user_id else c["user1_id"]

    if request.method == "GET":
        raw_msgs = get_messages(conv_id, user_id)
        formatted = []
        for m in raw_msgs:
            formatted.append({
                "id": m["id"],
                "conversation_id": m["conversation_id"],
                "sender_id": m["sender_id"],
                "sender_name": m["sender_name"],
                "sender_role": m.get("sender_role", ""),
                "sender_photo": m.get("sender_photo", ""),
                "is_mine": (m["sender_id"] == user_id),
                "message": m["message_text"],
                "is_deleted": m.get("is_deleted", False),
                "created_at": m["created_at"]
            })

        other_row = db.execute(
            """
            SELECT u.id, u.full_name, u.email, u.role,
                   COALESCE(
                       NULLIF(u.profile_photo, ''),
                       NULLIF((SELECT profile_photo FROM student_profiles WHERE user_id = u.id), ''),
                       NULLIF((SELECT profile_photo FROM provider_profiles WHERE user_id = u.id), ''),
                       ''
                   ) as photo,
                   COALESCE((SELECT institution FROM student_profiles WHERE user_id = u.id), '') AS institution,
                   COALESCE((SELECT degree FROM student_profiles WHERE user_id = u.id), '') AS degree,
                   COALESCE((SELECT specialization FROM student_profiles WHERE user_id = u.id), '') AS specialization,
                   COALESCE((SELECT year FROM student_profiles WHERE user_id = u.id), '') AS year,
                   COALESCE((SELECT skills FROM student_profiles WHERE user_id = u.id), '') AS skills,
                   COALESCE((SELECT location FROM student_profiles WHERE user_id = u.id), '') AS location,
                   COALESCE((SELECT bio FROM student_profiles WHERE user_id = u.id), '') AS bio,
                   COALESCE((SELECT phone FROM student_profiles WHERE user_id = u.id), '') AS phone,
                   COALESCE((SELECT github FROM student_profiles WHERE user_id = u.id), '') AS github,
                   COALESCE((SELECT linkedin FROM student_profiles WHERE user_id = u.id), '') AS linkedin,
                   COALESCE((SELECT portfolio FROM student_profiles WHERE user_id = u.id), '') AS portfolio
            FROM users u WHERE u.id = ?
            """,
            (other_user_id,)
        ).fetchone()

        other_dict = dict(other_row) if other_row else {}
        if other_dict:
            other_dict["name"] = other_dict["full_name"]
            other_dict["profile_photo"] = other_dict["photo"]
            raw_s = other_dict.get("skills") or ""
            other_dict["skills_list"] = [s.strip() for s in raw_s.split(",") if s.strip()] if isinstance(raw_s, str) else []

        return jsonify({
            "success": True,
            "messages": formatted,
            "current_user": {"id": user_id},
            "other_user": other_dict
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
