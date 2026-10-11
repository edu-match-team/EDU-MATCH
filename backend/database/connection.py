import sqlite3
from pathlib import Path
from flask import current_app, g

def get_db():
    """
    Return a database connection for the current request.
    Reuse the connection if it already exists in Flask's request context `g`.
    """
    if "db" not in g:
        database_path = Path(current_app.config["DATABASE_PATH"])
        database_path.parent.mkdir(parents=True, exist_ok=True)

        connection = sqlite3.connect(
            str(database_path),
            timeout=30,
            check_same_thread=False
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        connection.execute("PRAGMA cache_size = 10000")
        connection.execute("PRAGMA temp_store = MEMORY")
        g.db = connection

    return g.db


def close_db(error=None):
    """
    Close the connection after the request finishes.
    """
    connection = g.pop("db", None)
    if connection is not None:
        if error is not None:
            connection.rollback()
        connection.close()


def init_database(app):
    """
    Initialize the SQLite database using schema.sql if needed.
    """
    database_path = Path(app.config["DATABASE_PATH"])
    database_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path = database_path.parent / "schema.sql"

    connection = sqlite3.connect(str(database_path), timeout=15)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                connection.executescript(f.read())
        connection.commit()
    finally:
        connection.close()

    app.teardown_appcontext(close_db)