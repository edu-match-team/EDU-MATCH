
from backend.database.connection import get_db


def create_certification(provider_id, name, issuing_organization="",
                         issue_date=None, expiry_date=None,
                         credential_url=""):
    """Add a certification to a provider's profile."""
    name = str(name or "").strip()
    issuing_organization = str(issuing_organization or "").strip()
    credential_url = str(credential_url or "").strip()

    if not name:
        raise ValueError("Certification name is required.")

    if len(name) > 200:
        raise ValueError("Certification name must be 200 characters or fewer.")

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
        INSERT INTO certifications
            (provider_id, name, issuing_organization,
             issue_date, expiry_date, credential_url)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            provider["id"], name, issuing_organization,
            issue_date, expiry_date, credential_url
        )
    )

    db.commit()
    return cursor.lastrowid


def get_certifications_by_provider(provider_id):
    """Retrieve a provider's certifications."""
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
        return []

    rows = db.execute(
        """
        SELECT * FROM certifications
        WHERE provider_id = ?
        ORDER BY id DESC
        """,
        (provider["id"],)
    ).fetchall()

    return [dict(row) for row in rows]


def delete_certification(certification_id, provider_id):
    """Delete a certification owned by the specified provider."""
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
        return False

    cursor = db.execute(
        """
        DELETE FROM certifications
        WHERE id = ? AND provider_id = ?
        """,
        (certification_id, provider["id"])
    )

    db.commit()
    return cursor.rowcount > 0
