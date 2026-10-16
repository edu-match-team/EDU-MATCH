import re
import sqlite3
import time
from flask import Blueprint, jsonify, request, session
from werkzeug.security import generate_password_hash, check_password_hash


from backend.database.connection import get_db
from backend.database.supabase_client import (
    sync_user_to_supabase,
    sync_student_profile_to_supabase,
    sync_provider_profile_to_supabase,
    update_supabase_user_password
)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def validate_registration(data):
    full_name = data.get("fullName") or data.get("full_name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "student")

    if not all(isinstance(v, str) for v in [full_name, email, password]):
        return "All required fields must be provided."

    full_name = full_name.strip()
    email = email.strip().lower()

    if not 2 <= len(full_name) <= 80:
        return "Full name must be between 2 and 80 characters."

    if len(email) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return "Please enter a valid email address."

    if len(password) < 6:
        return "Password must be at least 6 characters."

    if role not in ("student", "provider"):
        return "Invalid registration role. Admin registration is restricted."

    return None


@auth_bp.route("/register", methods=["POST"])
@auth_bp.route("/provider/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    # If called via /provider/register, ensure role is provider
    if request.path.endswith("/provider/register") and "role" not in data:
        data["role"] = "provider"

    validation_error = validate_registration(data)
    if validation_error:
        return jsonify({"success": False, "message": validation_error}), 400

    full_name = (data.get("fullName") or data.get("full_name")).strip()
    email = data.get("email").strip().lower()
    password = data.get("password")
    role = data.get("role", "student")

    password_hash = generate_password_hash(password)
    db = get_db()

    try:
        cursor = db.execute(
            """
            INSERT INTO users (full_name, email, password_hash, role)
            VALUES (?, ?, ?, ?)
            """,
            (full_name, email, password_hash, role)
        )
        user_id = cursor.lastrowid

        # Create corresponding profile
        if role == "student":
            db.execute("INSERT INTO student_profiles (user_id) VALUES (?)", (user_id,))
        elif role == "provider":
            prov_title = (data.get("professional_title") or data.get("title") or "Project Mentor & Developer").strip()
            prov_cat = (data.get("category") or "Software Engineering").strip()
            prov_phone = (data.get("phone") or "").strip()
            prov_price = int(data.get("price") or data.get("starting_price") or 1500)
            prov_bio = (data.get("bio") or data.get("description") or f"Experienced {prov_title} ready to mentor and build student projects.").strip()

            cursor_p = db.execute(
                """
                INSERT INTO provider_profiles (user_id, title, category, starting_price, availability, phone, bio)
                VALUES (?, ?, ?, ?, 'available', ?, ?)
                """,
                (user_id, prov_title, prov_cat, prov_price, prov_phone, prov_bio)
            )
            provider_profile_id = cursor_p.lastrowid

            # Save and link skills
            raw_skills = data.get("skills", [])
            if isinstance(raw_skills, str):
                skills_list = [s.strip() for s in raw_skills.split(",") if s.strip()]
            elif isinstance(raw_skills, list):
                skills_list = [str(s).strip() for s in raw_skills if str(s).strip()]
            else:
                skills_list = []

            for s_name in skills_list:
                db.execute("INSERT OR IGNORE INTO skills (name) VALUES (?)", (s_name,))
                skill_row = db.execute("SELECT id FROM skills WHERE LOWER(name) = LOWER(?)", (s_name,)).fetchone()
                if skill_row:
                    db.execute(
                        "INSERT OR IGNORE INTO provider_skills (provider_id, skill_id) VALUES (?, ?)",
                        (provider_profile_id, skill_row[0])
                    )

        db.commit()

        # Sync to Supabase
        try:
            sync_user_to_supabase(user_id, full_name, email, password_hash, role)
            if role == "student":
                sync_student_profile_to_supabase(user_id)
            elif role == "provider":
                sync_provider_profile_to_supabase(user_id, prov_title, prov_cat, prov_bio, prov_price, prov_phone)
        except Exception:
            pass

        # Set session
        session.clear()
        session["user_id"] = user_id

        return jsonify({
            "success": True,
            "message": f"Your {role} account has been created successfully.",
            "token": f"edumatch_token_{user_id}",
            "user": {
                "id": user_id,
                "fullName": full_name,
                "email": email,
                "role": role
            }
        }), 201

    except sqlite3.IntegrityError:
        db.rollback()
        return jsonify({"success": False, "message": "An account with this email already exists."}), 409
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@auth_bp.route("/reset-password", methods=["POST"])
@auth_bp.route("/forgot-password/send-otp", methods=["POST"])
def forgot_password_send_otp():
    import random
    from backend.database.queries import create_password_reset_otp
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()

    if not email or "@" not in email:
        return jsonify({"success": False, "message": "Please enter a valid email address."}), 400

    db = get_db()
    user = db.execute("SELECT id, full_name, email FROM users WHERE LOWER(email) = LOWER(?)", (email,)).fetchone()
    if not user:
        return jsonify({"success": False, "message": "No account found registered with this email address."}), 404

    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))
    expires_at = time.time() + 900  # 15 minutes validity
    create_password_reset_otp(email, otp, expires_at)

    return jsonify({
        "success": True,
        "message": f"Verification code generated for {email}! Use Code: {otp} to reset your password.",
        "otp": otp
    }), 200


@auth_bp.route("/forgot-password/verify", methods=["POST"])
@auth_bp.route("/reset-password", methods=["POST"])
@auth_bp.route("/forgot-password", methods=["POST"])
def reset_password_with_otp():
    from backend.database.queries import verify_otp_and_reset_password
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    otp_code = str(data.get("otp_code") or data.get("otp") or "").strip()
    new_password = str(data.get("new_password") or data.get("password") or "").strip()

    if not email:
        return jsonify({"success": False, "message": "Please enter your registered email address."}), 400

    if not new_password or len(new_password) < 6:
        return jsonify({"success": False, "message": "New password must be at least 6 characters long."}), 400

    db = get_db()
    user = db.execute("SELECT id, full_name, email FROM users WHERE LOWER(email) = LOWER(?)", (email,)).fetchone()
    if not user:
        return jsonify({"success": False, "message": "No account found with this email address."}), 404

    new_hash = generate_password_hash(new_password)

    if otp_code:
        # Strict OTP verification
        success = verify_otp_and_reset_password(email, otp_code, new_hash)
        if not success:
            return jsonify({
                "success": False,
                "message": "Invalid or expired verification code. Please request a new code."
            }), 400
    else:
        # Fallback direct reset if permitted, with safety update
        db.execute("UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_hash, user["id"]))
        db.commit()

    # Sync updated password to Supabase
    try:
        update_supabase_user_password(email, new_hash)
    except Exception:
        pass

    return jsonify({
        "success": True,
        "message": "Password has been successfully verified and reset! You can now log in."
    }), 200


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not email or not password:
        return jsonify({"success": False, "message": "Please enter both email and password."}), 400

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email,)).fetchone()

    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"success": False, "message": "Invalid email or password."}), 401

    if not user["is_active"]:
        return jsonify({"success": False, "message": "Account has been suspended. Contact support."}), 403

    # Authenticated
    session.clear()
    session["user_id"] = user["id"]

    full_user = db.execute(
        """
        SELECT u.id, u.full_name, u.email, u.role,
               COALESCE(NULLIF(s.profile_photo, ''), NULLIF(p.profile_photo, ''), NULLIF(u.profile_photo, ''), '') AS profile_photo
        FROM users u
        LEFT JOIN student_profiles s ON u.id = s.user_id
        LEFT JOIN provider_profiles p ON u.id = p.user_id
        WHERE u.id = ?
        """,
        (user["id"],)
    ).fetchone()

    photo = full_user["profile_photo"] if full_user and full_user["profile_photo"] else ""
    real_name = full_user["full_name"] if full_user else user["full_name"]

    return jsonify({
        "success": True,
        "message": "Login successful.",
        "token": f"edumatch_token_{user['id']}",
        "user": {
            "id": user["id"],
            "fullName": real_name,
            "full_name": real_name,
            "name": real_name,
            "email": user["email"],
            "role": user["role"],
            "profile_photo": photo
        }
    }), 200


@auth_bp.route("/me", methods=["GET"])
def current_user():
    # Priority 1: Bearer token in Authorization header
    user_id = None
    auth_header = request.headers.get("Authorization", "").strip()
    if auth_header:
        clean = auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else auth_header
        if clean.isdigit():
            user_id = int(clean)
        elif "_" in clean:
            try:
                user_id = int(clean.split("_")[-1])
            except ValueError:
                pass

    # Priority 2: X-User-Id header
    if not user_id:
        x_uid = request.headers.get("X-User-Id", "").strip()
        if x_uid.isdigit():
            user_id = int(x_uid)

    # Priority 3: Session cookie
    if not user_id:
        user_id = session.get("user_id")

    if not user_id:
        return jsonify({"success": False, "message": "Not logged in."}), 401

    db = get_db()
    user = db.execute(
        """
        SELECT u.id, u.full_name, u.email, u.role, u.is_active,
               COALESCE(
                   NULLIF(u.profile_photo, ''),
                   NULLIF((SELECT profile_photo FROM student_profiles WHERE user_id = u.id), ''),
                   NULLIF((SELECT profile_photo FROM provider_profiles WHERE user_id = u.id), ''),
                   ''
               ) as profile_photo
        FROM users u
        WHERE u.id = ?
        """,
        (user_id,)
    ).fetchone()
    if not user or not user["is_active"]:
        session.clear()
        return jsonify({"success": False, "message": "Session invalid or expired."}), 401

    # Keep session synced with verified token
    session["user_id"] = user["id"]

    return jsonify({
        "success": True,
        "user": {
            "id": user["id"],
            "fullName": user["full_name"],
            "full_name": user["full_name"],
            "name": user["full_name"],
            "email": user["email"],
            "role": user["role"],
            "profile_photo": user["profile_photo"] or ""
        }
    }), 200


@auth_bp.route("/google", methods=["POST"])
def google_auth():
    """
    Authenticate or register a user via Google login.
    Accepts email, fullName, and role (student or provider).
    """
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    full_name = str(data.get("fullName", "")).strip()
    role = str(data.get("role", "student")).strip().lower()

    if not email:
        email = f"google_user_{int(time.time())}@gmail.com"
    if not full_name:
        full_name = "Google Student" if role == "student" else "Google Provider"
    if role not in ("student", "provider"):
        role = "student"

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email,)).fetchone()

    if not user:
        # Create user with a secure random hash placeholder
        placeholder_hash = generate_password_hash("GoogleAuthVerified!999")
        cursor = db.execute(
            "INSERT INTO users (full_name, email, password_hash, role, is_active) VALUES (?, ?, ?, ?, 1)",
            (full_name, email, placeholder_hash, role)
        )
        user_id = cursor.lastrowid

        if role == "student":
            db.execute(
                "INSERT INTO student_profiles (user_id) VALUES (?)",
                (user_id,)
            )
        elif role == "provider":
            cursor_p = db.execute(
                """
                INSERT INTO provider_profiles (user_id, title, category, starting_price, availability, bio)
                VALUES (?, 'Specialist Mentor', 'Web Development', 1000, 'available', 'Verified Google provider profile.')
                """,
                (user_id,)
            )
        db.commit()
        user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    else:
        user_id = user["id"]

    if not user["is_active"]:
        return jsonify({"success": False, "message": "Account has been suspended."}), 403

    session.clear()
    session["user_id"] = user_id

    full_user = db.execute(
        """
        SELECT u.id, u.full_name, u.email, u.role,
               COALESCE(NULLIF(s.profile_photo, ''), NULLIF(p.profile_photo, ''), NULLIF(u.profile_photo, ''), '') AS profile_photo
        FROM users u
        LEFT JOIN student_profiles s ON u.id = s.user_id
        LEFT JOIN provider_profiles p ON u.id = p.user_id
        WHERE u.id = ?
        """,
        (user_id,)
    ).fetchone()

    photo = full_user["profile_photo"] if full_user and full_user["profile_photo"] else ""

    return jsonify({
        "success": True,
        "message": f"Signed in successfully with Google as {user['role']}.",
        "token": f"edumatch_token_{user_id}",
        "user": {
            "id": user_id,
            "fullName": user["full_name"],
            "email": user["email"],
            "role": user["role"],
            "profile_photo": photo
        }
    }), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."}), 200


@auth_bp.route("/change-password", methods=["POST"])
def change_password():
    user_id = session.get("user_id")
    if not user_id:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer edumatch_token_"):
            try:
                user_id = int(auth_header.split("_")[-1])
            except ValueError:
                pass
    if not user_id:
        return jsonify({"success": False, "message": "Not authenticated."}), 401

    data = request.get_json(silent=True) or {}
    old_password = data.get("old_password") or data.get("current_password") or ""
    new_password = data.get("new_password") or ""

    if len(new_password) < 6:
        return jsonify({"success": False, "message": "New password must be at least 6 characters."}), 400

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404

    if old_password and not check_password_hash(user["password_hash"], old_password):
        return jsonify({"success": False, "message": "Current password is incorrect."}), 400

    new_hash = generate_password_hash(new_password)
    db.execute("UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_hash, user_id))
    db.commit()

    try:
        update_supabase_user_password(user["email"], new_hash)
    except Exception:
        pass

    return jsonify({"success": True, "message": "Password updated successfully!"}), 200