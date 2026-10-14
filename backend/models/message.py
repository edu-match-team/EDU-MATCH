
from backend.database.connection import get_db


def create_message(sender_id, receiver_id, content):
    """Create a chat message between two users."""
    content = str(content or "").strip()

    if not content:
        raise ValueError("Message cannot be empty.")

    if len(content) > 5000:
        raise ValueError("Message cannot exceed 5000 characters.")

    db = get_db()

    for user_id in (sender_id, receiver_id):
        user = db.execute(
            "SELECT id FROM users WHERE id = ? AND is_active = 1",
            (user_id,)
        ).fetchone()

        if not user:
            raise ValueError("Sender or receiver not found or inactive.")

    cursor = db.execute(
        """
        INSERT INTO messages (sender_id, receiver_id, content, created_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (sender_id, receiver_id, content)
    )

    db.commit()
    return cursor.lastrowid


def get_message_by_id(message_id):
    """Retrieve a message by its ID."""
    db = get_db()

    row = db.execute(
        "SELECT * FROM messages WHERE id = ?",
        (message_id,)
    ).fetchone()

    return dict(row) if row else None


def get_conversation(user1_id, user2_id):
    """Retrieve messages exchanged between two users."""
    db = get_db()

    rows = db.execute(
        """
        SELECT *
        FROM messages
        WHERE (sender_id = ? AND receiver_id = ?)
           OR (sender_id = ? AND receiver_id = ?)
        ORDER BY created_at ASC, id ASC
        """,
        (user1_id, user2_id, user2_id, user1_id)
    ).fetchall()

    return [dict(row) for row in rows]


def delete_message(message_id, sender_id):
    """Allow the original sender to delete their message."""
    db = get_db()

    cursor = db.execute(
        "DELETE FROM messages WHERE id = ? AND sender_id = ?",
        (message_id, sender_id)
    )

    db.commit()
    return cursor.rowcount > 0