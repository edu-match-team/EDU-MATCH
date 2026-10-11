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

    # 2. Add Skills
    skills_list = [
        "Python", "Machine Learning", "Flask", "React", "JavaScript", 
        "HTML", "CSS", "SQLite", "MySQL", "Deep Learning", 
        "Data Analytics", "NLP", "Pandas", "Scikit-Learn", "Django",
        "FastAPI", "Docker", "Git", "C++", "Java"
    ]
    for skill in skills_list:
        cursor.execute("INSERT OR IGNORE INTO skills (name) VALUES (?)", (skill,))
    conn.commit()

    # Helper function to get skill ID
    def get_skill_id(name):
        res = cursor.execute("SELECT id FROM skills WHERE LOWER(name) = LOWER(?)", (name,)).fetchone()
        return res[0] if res else None

    # 3. Create Admin Account (if not exists)
    admin_email = "admin@edumatch.edu"
    cursor.execute("SELECT id FROM users WHERE email = ?", (admin_email,))
    if not cursor.fetchone():
        cursor.execute(
            """
            INSERT INTO users (full_name, email, password_hash, role)
            VALUES (?, ?, ?, ?)
            """,
            ("Platform Administrator", admin_email, generate_password_hash("Admin123!"), "admin")
        )
        print("Admin user created (admin@edumatch.edu / Admin123!)")

    # 4. Create Demo Student Account
    student_email = "vishu@edumatch.edu"
    cursor.execute("SELECT id FROM users WHERE email = ?", (student_email,))
    student_row = cursor.fetchone()
    if not student_row:
        cursor.execute(
            """
            INSERT INTO users (full_name, email, password_hash, role)
            VALUES (?, ?, ?, ?)
            """,
            ("Vishwajeet Rawat", student_email, generate_password_hash("Student123!"), "student")
        )
        s_user_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO student_profiles (user_id, institution, degree, bio, phone, interests)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (s_user_id, "ABC Institute of Technology", "BCA - Artificial Intelligence & Data Science",
             "Looking for skilled project partners to build my academic projects.", "+91 9876543210",
             "Machine Learning, Web Development, Data Science")
        )
        print("Demo student created (vishu@edumatch.edu / Student123!)")
    else:
        s_user_id = student_row[0]

    # 5. Create Demo Providers
    providers_data = [
        {
            "name": "Aarav Sharma",
            "email": "aarav.ml@edumatch.edu",
            "password": "Provider123!",
            "title": "Machine Learning & Python Specialist",
            "category": "Artificial Intelligence",
            "bio": "Experienced ML developer with 3+ years helping college students build real-world classification, forecasting, and NLP projects.",
            "experience": 3,
            "starting_price": 2500,
            "completed_projects": 16,
            "rating": 4.9,
            "availability": "available",
            "phone": "+91 9811223344",
            "skills": ["Python", "Machine Learning", "Flask", "Pandas", "Scikit-Learn"]
        },
        {
            "name": "Priya Patel",
            "email": "priya.web@edumatch.edu",
            "password": "Provider123!",
            "title": "Full-Stack Web & Database Architect",
            "category": "Web Development",
            "bio": "Specialized in Python Flask, SQLite, and responsive frontends for student capstone and semester projects.",
            "experience": 4,
            "starting_price": 1800,
            "completed_projects": 24,
            "rating": 4.8,
            "availability": "available",
            "phone": "+91 9822334455",
            "skills": ["Python", "Flask", "HTML", "CSS", "JavaScript", "SQLite", "React"]
        },
        {
            "name": "Rohan Verma",
            "email": "rohan.ai@edumatch.edu",
            "password": "Provider123!",
            "title": "Data Science & Deep Learning Engineer",
            "category": "Data Science",
            "bio": "Passionate about Computer Vision, NLP, and neural networks. Dedicated mentor for academic project implementations.",
            "experience": 3,
            "starting_price": 3200,
            "completed_projects": 12,
            "rating": 5.0,
            "availability": "limited",
            "phone": "+91 9833445566",
            "skills": ["Python", "Deep Learning", "Machine Learning", "Data Analytics", "NLP"]
        },
        {
            "name": "Sneha Iyer",
            "email": "sneha.ui@edumatch.edu",
            "password": "Provider123!",
            "title": "Modern Frontend & UI/UX Developer",
            "category": "Web Development",
            "bio": "Crafting clean, accessible, modern web interfaces and single-page apps. Great for dashboard and portfolio projects.",
            "experience": 2,
            "starting_price": 1500,
            "completed_projects": 10,
            "rating": 4.7,
            "availability": "available",
            "phone": "+91 9844556677",
            "skills": ["HTML", "CSS", "JavaScript", "React"]
        },
        {
            "name": "Vikram Das",
            "email": "vikram.backend@edumatch.edu",
            "password": "Provider123!",
            "title": "Python Backend & API Systems Developer",
            "category": "Software Engineering",
            "bio": "Robust REST API and database integration. Experience with Django, FastAPI, Flask, and distributed architectures.",
            "experience": 4,
            "starting_price": 2800,
            "completed_projects": 19,
            "rating": 4.9,
            "availability": "available",
            "phone": "+91 9855667788",
            "skills": ["Python", "Django", "FastAPI", "Flask", "Docker", "SQLite"]
        }
    ]

    for p in providers_data:
        cursor.execute("SELECT id FROM users WHERE email = ?", (p["email"],))
        p_row = cursor.fetchone()
        if not p_row:
            cursor.execute(
                """
                INSERT INTO users (full_name, email, password_hash, role)
                VALUES (?, ?, ?, ?)
                """,
                (p["name"], p["email"], generate_password_hash(p["password"]), "provider")
            )
            u_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO provider_profiles (
                    user_id, title, category, bio, experience_years, starting_price,
                    completed_projects, rating, availability, phone
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (u_id, p["title"], p["category"], p["bio"], p["experience"],
                 p["starting_price"], p["completed_projects"], p["rating"],
                 p["availability"], p["phone"])
            )
            prov_id = cursor.lastrowid
            for s_name in p["skills"]:
                s_id = get_skill_id(s_name)
                if s_id:
                    cursor.execute(
                        "INSERT OR IGNORE INTO provider_skills (provider_id, skill_id) VALUES (?, ?)",
                        (prov_id, s_id)
                    )
            print(f"Provider created: {p['name']} ({p['email']})")

    # 6. Sample Student Requirement
    cursor.execute("SELECT id FROM requirements WHERE student_id = ?", (s_user_id,))
    if not cursor.fetchone():
        cursor.execute(
            """
            INSERT INTO requirements (
                student_id, title, category, description, required_skills, budget, deadline, complexity, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                s_user_id,
                "Student Attendance & Performance Predictor",
                "Artificial Intelligence",
                "A machine learning web system that predicts student outcomes based on attendance and marks using Python and Flask.",
                "Python, Machine Learning, Flask",
                3000,
                "2026-11-30",
                "Intermediate",
                "open"
            )
        )
        req_id = cursor.lastrowid
        print(f"Sample requirement created (ID: {req_id})")

    conn.commit()
    conn.close()
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
