import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash

DB_PATH = Path(__file__).resolve().parent / "edumatch.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

def seed_database():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    # 1. Execute Schema
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        cursor.executescript(f.read())
    print("Schema initialized.")

    # 2. Add Base Technology Skills
    skills_list = [
        "Python", "Machine Learning", "Flask", "React", "JavaScript", 
        "HTML", "CSS", "SQLite", "MySQL", "Deep Learning", 
        "Data Analytics", "NLP", "Pandas", "Scikit-Learn", "Django",
        "FastAPI", "Docker", "Git", "C++", "Java", "Node.js", "Express",
        "Next.js", "TypeScript", "Tailwind CSS", "MongoDB", "PostgreSQL",
        "Computer Vision", "Cybersecurity", "Cloud Computing"
    ]
    for skill in skills_list:
        cursor.execute("INSERT OR IGNORE INTO skills (name) VALUES (?)", (skill,))
    conn.commit()
    print(f"Base skills list initialized ({len(skills_list)} skills).")

    # 3. Create Admin Account (if not exists)
    admin_email = "vishwajeet@edumatch.edu"
    cursor.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(?)", (admin_email,))
    if not cursor.fetchone():
        cursor.execute(
            """
            INSERT INTO users (full_name, email, password_hash, role)
            VALUES (?, ?, ?, ?)
            """,
            ("Vishwajeet", admin_email, generate_password_hash("Admin123!"), "admin")
        )
        print("Admin account created: vishwajeet@edumatch.edu / Admin123!")
    else:
        print("Admin account exists.")

    # NO demo students or demo providers are seeded.
    # Only real students and providers registered by users will be in the system.

    conn.commit()
    conn.close()
    print("Database initialization completed successfully. No demo data added.")

if __name__ == "__main__":
    seed_database()
