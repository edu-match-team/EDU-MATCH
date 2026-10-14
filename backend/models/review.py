
from backend.database.connection import get_db


def create_review(provider_id, student_id, rating, comment=""):
    """Save a student's review of a provider."""
    if isinstance(rating, bool) or not isinstance(rating, int):
        raise ValueError("Rating must be a whole number from 1 to 5.")

    if not 1 <= rating <= 5:
        raise ValueError("Rating must be between 1 and 5.")

    comment = str(comment or "").strip()

    if len(comment) > 2000:
        raise ValueError("Review comment must be 2000 characters or fewer.")

    db = get_db()

    # Confirm that the reviewer is a student.
    student = db.execute(
        "SELECT id FROM users WHERE id = ? AND role = 'student' AND is_active = 1",
        (student_id,),
    ).fetchone()

    if not student:
        raise ValueError("Only active student accounts can submit reviews.")

    # Resolve either a provider user ID or provider profile ID.
    provider = db.execute(
        """
        SELECT u.id AS user_id, p.id AS profile_id
        FROM provider_profiles p
        JOIN users u ON u.id = p.user_id
        WHERE (u.id = ? OR p.id = ?)
          AND u.role = 'provider'
          AND u.is_active = 1
        LIMIT 1
        """,
        (provider_id, provider_id),
    ).fetchone()

    if not provider:
        raise ValueError("Provider not found.")

    cursor = db.execute(
        """
        INSERT INTO reviews (provider_id, student_id, rating, comment)
        VALUES (?, ?, ?, ?)
        """,
        (provider["user_id"], student_id, rating, comment),
    )

    # Recalculate the provider's average rating.
    average = db.execute(
        "SELECT AVG(rating) AS average FROM reviews WHERE provider_id = ?",
        (provider["user_id"],),
    ).fetchone()["average"]

    db.execute(
        "UPDATE provider_profiles SET rating = ? WHERE user_id = ?",
        (round(average, 1), provider["user_id"]),
    )

    db.commit()
    return cursor.lastrowid


def get_reviews_for_provider(provider_id):
    """Return reviews for a provider, newest first."""
    db = get_db()

    provider = db.execute(
        """
        SELECT u.id AS user_id
        FROM users u
        LEFT JOIN provider_profiles p ON p.user_id = u.id
        WHERE u.role = 'provider'
          AND (u.id = ? OR p.id = ?)
        LIMIT 1
        """,
        (provider_id, provider_id),
    ).fetchone()

    if not provider:
        return None

    rows = db.execute(
        """
        SELECT r.id, r.provider_id, r.student_id, r.rating,
               r.comment, r.created_at, u.full_name AS student_name
        FROM reviews r
        JOIN users u ON u.id = r.student_id
        WHERE r.provider_id = ?
        ORDER BY r.created_at DESC, r.id DESC
        """,
        (provider["user_id"],),
    ).fetchall()

    return [dict(row) for row in rows]


def get_review_by_id(review_id):
    """Find a review by its ID."""
    db = get_db()

    row = db.execute(
        "SELECT * FROM reviews WHERE id = ?",
        (review_id,),
    ).fetchone()

    return dict(row) if row else None
