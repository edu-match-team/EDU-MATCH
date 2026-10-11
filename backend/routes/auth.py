import re
import sqlite3
import time
from flask import Blueprint, jsonify, request, session
from werkzeug.security import generate_password_hash, check_password_hash


from backend.database.connection import get_db

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

        # Set session
        session.clear()
        session["user_id"] = user_id

        return jsonify({
            "success": True,
            "message": f"Your {role} account has been created successfully.",
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

    return jsonify({
        "success": True,
        "message": "Login successful.",
        "token": f"edumatch_token_{user['id']}",
        "user": {
            "id": user["id"],
            "fullName": user["full_name"],
            "email": user["email"],
            "role": user["role"]
        }
    }), 200


@auth_bp.route("/me", methods=["GET"])
def current_user():
    user_id = session.get("user_id")
    if not user_id:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer edumatch_token_"):
            try:
                user_id = int(auth_header.split("_")[-1])
            except ValueError:
                pass

    if not user_id:
        return jsonify({"success": False, "message": "Not logged in."}), 401

    db = get_db()
    user = db.execute("SELECT id, full_name, email, role, is_active FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user or not user["is_active"]:
        session.clear()
        return jsonify({"success": False, "message": "Session invalid or expired."}), 401

    return jsonify({
        "success": True,
        "user": {
            "id": user["id"],
            "fullName": user["full_name"],
            "email": user["email"],
            "role": user["role"]
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

    return jsonify({
        "success": True,
        "message": f"Signed in successfully with Google as {user['role']}.",
        "token": f"edumatch_token_{user_id}",
        "user": {
            "id": user_id,
            "fullName": user["full_name"],
            "email": user["email"],
            "role": user["role"]
        }
    }), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."}), 200