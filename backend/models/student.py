
from backend.database.connection import get_db


def get_student_by_id(student_id):
    """Retrieve a student's account details."""
    db = get_db()

    row = db.execute(
        """
        SELECT id, full_name, email, role, is_active, created_at
        FROM users
        WHERE id = ? AND role = 'student'
        """,
        (student_id,)
    ).fetchone()

    return dict(row) if row else None


def get_student_profile(student_id):
    """Retrieve a student's profile and account details."""
    db = get_db()

    student = db.execute(
        """
        SELECT u.id, u.full_name, u.email, u.role, u.is_active,
               s.*
        FROM users u
        LEFT JOIN student_profiles s ON s.user_id = u.id
        WHERE u.id = ? AND u.role = 'student'
        """,
        (student_id,)
    ).fetchone()

    return dict(student) if student else None


def update_student_name(student_id, full_name):
    """Update a student's display name."""
    full_name = str(full_name or "").strip()

    if not full_name:
        raise ValueError("Student name is required.")

    if len(full_name) > 150:
        raise ValueError("Student name is too long.")

    db = get_db()

    cursor = db.execute(
        """
        UPDATE users
        SET full_name = ?
        WHERE id = ? AND role = 'student'
        """,
        (full_name, student_id)
    )

    db.commit()
    return cursor.rowcount > 0
