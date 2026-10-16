
from backend.database.connection import get_db


def create_service(provider_id, title, description="", price=0):
    """Create a service offered by a provider."""
    title = str(title or "").strip()
    description = str(description or "").strip()

    if not title:
        raise ValueError("Service title is required.")

    if len(title) > 200:
        raise ValueError("Service title must be 200 characters or fewer.")

    try:
        price = float(price)
    except (TypeError, ValueError):
        raise ValueError("Price must be a valid number.")

    if price < 0:
        raise ValueError("Price cannot be negative.")

    db = get_db()

    provider = db.execute(
        """
        SELECT id FROM provider_profiles
        WHERE id = ? OR user_id = ?
        LIMIT 1
        """,
        (provider_id, provider_id)
    ).fetchone()

    if not provider:
        raise ValueError("Provider profile not found.")

    cursor = db.execute(
        """
        INSERT INTO services (provider_id, title, description, price)
        VALUES (?, ?, ?, ?)
        """,
        (provider["id"], title, description, price)
    )

    db.commit()
    return cursor.lastrowid


def get_service_by_id(service_id):
    """Retrieve one service by its ID."""
    db = get_db()

    row = db.execute(
        "SELECT * FROM services WHERE id = ?",
        (service_id,)
    ).fetchone()

    return dict(row) if row else None


def get_services_by_provider(provider_id):
    """Retrieve services belonging to a provider."""
    db = get_db()

    profile = db.execute(
        """
        SELECT id FROM provider_profiles
        WHERE id = ? OR user_id = ?
        LIMIT 1
        """,
        (provider_id, provider_id)
    ).fetchone()

    if not profile:
        return []

    rows = db.execute(
        """
        SELECT * FROM services
        WHERE provider_id = ?
        ORDER BY id DESC
        """,
        (profile["id"],)
    ).fetchall()

    return [dict(row) for row in rows]


def delete_service(service_id, provider_id):
    """Delete a service belonging to the specified provider."""
    db = get_db()

    profile = db.execute(
        """
        SELECT id FROM provider_profiles
        WHERE id = ? OR user_id = ?
        LIMIT 1
        """,
        (provider_id, provider_id)
    ).fetchone()

    if not profile:
        return False

    cursor = db.execute(
        """
        DELETE FROM services
        WHERE id = ? AND provider_id = ?
        """,
        (service_id, profile["id"])
    )

    db.commit()
    return cursor.rowcount > 0
