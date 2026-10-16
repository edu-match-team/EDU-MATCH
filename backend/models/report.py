
from backend.database.connection import get_db


VALID_STATUSES = {"pending", "reviewing", "resolved", "dismissed"}


def create_report(reporter_id, reason, description, reported_user_id=None):
    """Save a new report to the database."""

    reason = reason.strip() if isinstance(reason, str) else ""
    description = (
        description.strip() if isinstance(description, str) else ""
    )

    if not reason or not description:
        raise ValueError("Reason and description are required.")

    if len(reason) > 100 or len(description) > 3000:
        raise ValueError("Report information is too long.")

    db = get_db()

    cursor = db.execute(
        """
        INSERT INTO reports
            (reporter_id, reported_user_id, reason, description)
        VALUES (?, ?, ?, ?)
        """,
        (reporter_id, reported_user_id, reason, description),
    )

    db.commit()
    return cursor.lastrowid


def get_report_by_id(report_id):
    """Retrieve a report by its ID."""

    db = get_db()

    report = db.execute(
        "SELECT * FROM reports WHERE id = ?",
        (report_id,),
    ).fetchone()

    return dict(report) if report else None


def get_all_reports(status=None):
    """Retrieve reports, optionally filtered by status."""

    db = get_db()

    if status is not None:
        if status not in VALID_STATUSES:
            raise ValueError("Invalid report status.")

        rows = db.execute(
            """
            SELECT * FROM reports
            WHERE status = ?
            ORDER BY created_at DESC
            """,
            (status,),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM reports ORDER BY created_at DESC"
        ).fetchall()

    return [dict(row) for row in rows]


def update_report_status(report_id, status):
    """Update a report's moderation status."""

    if status not in VALID_STATUSES:
        raise ValueError("Invalid report status.")

    db = get_db()

    cursor = db.execute(
        """
        UPDATE reports
        SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (status, report_id),
    )

    db.commit()
    return cursor.rowcount > 0
