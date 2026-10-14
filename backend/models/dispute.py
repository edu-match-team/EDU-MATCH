
from backend.database.connection import get_db


def create_dispute(student_id, provider_id, reason, description=""):
    """Create a new dispute between a student and a provider."""
    reason = str(reason or "").strip()
    description = str(description or "").strip()

    if not reason:
        raise ValueError("A dispute reason is required.")

    if len(reason) > 200:
        raise ValueError("Reason must be 200 characters or fewer.")

    if len(description) > 5000:
        raise ValueError("Description must be 5000 characters or fewer.")

    db = get_db()

    student = db.execute(
        "SELECT id FROM users WHERE id = ? AND role = 'student'",
        (student_id,)
    ).fetchone()

    if not student:
        raise ValueError("Student not found.")

    provider = db.execute(
        "SELECT id FROM users WHERE id = ? AND role = 'provider'",
        (provider_id,)
    ).fetchone()

    if not provider:
        raise ValueError("Provider not found.")

    cursor = db.execute(
        """
        INSERT INTO disputes
            (student_id, provider_id, reason, description, status, created_at)
        VALUES (?, ?, ?, ?, 'open', CURRENT_TIMESTAMP)
        """,
        (student_id, provider_id, reason, description)
    )

    db.commit()
    return cursor.lastrowid


def get_dispute_by_id(dispute_id):
    """Retrieve one dispute by its ID."""
    db = get_db()

    row = db.execute(
        "SELECT * FROM disputes WHERE id = ?",
        (dispute_id,)
    ).fetchone()

    return dict(row) if row else None


def get_all_disputes():
    """Retrieve all disputes, newest first."""
    db = get_db()

    rows = db.execute(
        "SELECT * FROM disputes ORDER BY created_at DESC, id DESC"
    ).fetchall()

    return [dict(row) for row in rows]


def update_dispute_status(dispute_id, status):
    """Update a dispute's status."""
    allowed_statuses = {"open", "under_review", "resolved", "rejected"}
    status = str(status or "").strip().lower()

    if status not in allowed_statuses:
        raise ValueError("Invalid dispute status.")

    db = get_db()

    cursor = db.execute(
        "UPDATE disputes SET status = ? WHERE id = ?",
        (status, dispute_id)
    )

    db.commit()
    return cursor.rowcount > 0
