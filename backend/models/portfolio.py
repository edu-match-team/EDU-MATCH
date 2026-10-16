
from backend.database.connection import get_db


def create_portfolio_project(provider_id, title, description="", project_url=""):
    """Create a portfolio project for a provider."""
    title = str(title or "").strip()
    description = str(description or "").strip()
    project_url = str(project_url or "").strip()

    if not title:
        raise ValueError("Project title is required.")

    if len(title) > 200:
        raise ValueError("Project title must be 200 characters or fewer.")

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
        INSERT INTO portfolio
            (provider_id, title, description, project_url)
        VALUES (?, ?, ?, ?)
        """,
        (provider["id"], title, description, project_url)
    )

    db.commit()
    return cursor.lastrowid


def get_portfolio_by_provider(provider_id):
    """Get all portfolio projects for a provider."""
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
        SELECT * FROM portfolio
        WHERE provider_id = ?
        ORDER BY id DESC
        """,
        (profile["id"],)
    ).fetchall()

    return [dict(row) for row in rows]


def delete_portfolio_project(project_id, provider_id):
    """Delete a project belonging to the specified provider."""
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
        DELETE FROM portfolio
        WHERE id = ? AND provider_id = ?
        """,
        (project_id, profile["id"])
    )

    db.commit()
    return cursor.rowcount > 0
