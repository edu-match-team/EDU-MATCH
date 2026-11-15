import json
import pytest
from backend.app import create_app
from backend.database.connection import get_db

@pytest.fixture
def client_and_app():
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        with app.test_client() as client:
            yield client, app

def test_complete_requirement_and_order_lifecycle(client_and_app):
    client, app = client_and_app
    # 1. Setup clean student and provider accounts in DB
    db = get_db()
    # Create test student
    cur = db.execute(
        "INSERT INTO users (full_name, email, password_hash, role) VALUES ('Lifecycle Student', 'lifecyclestudent@edumatch.edu', 'hash', 'student')"
    )
    student_id = cur.lastrowid

    # Create test provider 1
    cur = db.execute(
        "INSERT INTO users (full_name, email, password_hash, role) VALUES ('Lifecycle Provider', 'lifecycleprovider@edumatch.edu', 'hash', 'provider')"
    )
    provider_id = cur.lastrowid
    db.execute(
        "INSERT INTO provider_profiles (user_id, completed_projects, title) VALUES (?, 0, 'Full Stack Mentor')",
        (provider_id,)
    )

    # Create test provider 2 (to test exclusivity)
    cur = db.execute(
        "INSERT INTO users (full_name, email, password_hash, role) VALUES ('Other Provider', 'otherprovider@edumatch.edu', 'hash', 'provider')"
    )
    provider2_id = cur.lastrowid
    db.execute(
        "INSERT INTO provider_profiles (user_id, completed_projects, title) VALUES (?, 0, 'Backend Mentor')",
        (provider2_id,)
    )
    db.commit()

    try:
        # Step 1: Student submits project requirement with deadline, budget, complexity, skills
        req_res = client.post(
            "/api/students/requirements",
            headers={"X-User-Id": str(student_id)},
            json={
                "title": "Automated Student Record System",
                "category": "Web Development",
                "description": "Need a complete database record management app with authentication.",
                "skills": ["Python", "Flask", "SQLite"],
                "complexity": "Intermediate",
                "budget": 5000,
                "deadline": "2026-11-30"
            }
        )
        assert req_res.status_code == 201
        req_data = req_res.get_json()
        assert req_data["success"] is True
        requirement_id = req_data["requirement_id"]

        # Verify student received notification
        notifs_res = client.get(f"/api/notifications?user_id={student_id}")
        assert notifs_res.status_code == 200
        notifs_data = notifs_res.get_json()
        assert len(notifs_data["notifications"]) >= 1
        assert "Requirement" in notifs_data["notifications"][0]["title"]

        # Step 2: Provider browses open requirements
        prov_reqs_res = client.get(
            "/api/provider/requirements",
            headers={"X-User-Id": str(provider_id)}
        )
        assert prov_reqs_res.status_code == 200
        open_reqs = prov_reqs_res.get_json()["requirements"]
        target = next((r for r in open_reqs if r["id"] == requirement_id), None)
        assert target is not None
        assert target["title"] == "Automated Student Record System"
        assert target["budget"] == 5000
        assert target["student_name"] == "Lifecycle Student"
        assert target["deadline"] == "2026-11-30"

        # Step 3: Provider accepts requirement
        propose_res = client.post(
            "/api/provider/propose",
            headers={"X-User-Id": str(provider_id)},
            json={
                "requirement_id": requirement_id,
                "message": "Accepted project! Ready to build.",
                "action": "accept"
            }
        )
        assert propose_res.status_code == 201
        propose_data = propose_res.get_json()
        assert propose_data["status"] == "in_progress"
        collab_id = propose_data["request_id"]

        # Step 4: Exclusivity - Provider 2 should NOT see this requirement anymore!
        prov2_reqs_res = client.get(
            "/api/provider/requirements",
            headers={"X-User-Id": str(provider2_id)}
        )
        open_reqs_p2 = prov2_reqs_res.get_json()["requirements"]
        assert all(r["id"] != requirement_id for r in open_reqs_p2)

        # Step 5: Student side: check orders. It is In Progress with assigned provider!
        st_orders_res = client.get(
            f"/api/projects/my?user_id={student_id}",
            headers={"X-User-Id": str(student_id)}
        )
        assert st_orders_res.status_code == 200
        st_projects = st_orders_res.get_json()["projects"]
        in_prog = next((p for p in st_projects if p["id"] == collab_id or p["title"] == "Automated Student Record System"), None)
        assert in_prog is not None
        assert in_prog["status"] == "in_progress"
        assert in_prog["provider_name"] == "Lifecycle Provider"
        assert in_prog["provider_id"] == provider_id

        # Step 6: Provider submits deliverable code link and completes project
        deliv_res = client.patch(
            f"/api/provider/orders/{collab_id}/deliverable",
            headers={"X-User-Id": str(provider_id)},
            json={
                "deliverable_url": "https://github.com/edumatch/student-records",
                "deliverable_note": "Includes full Flask app, SQLite schemas, and test suite."
            }
        )
        assert deliv_res.status_code == 200

        # Step 7: Verify completed counts updated on both provider and student sides
        # Provider profile completed_projects incremented
        prov_row = db.execute("SELECT completed_projects FROM provider_profiles WHERE user_id = ?", (provider_id,)).fetchone()
        assert prov_row["completed_projects"] >= 1

        # Student side orders shows completed with deliverable details
        st_orders_res2 = client.get(
            f"/api/projects/my?user_id={student_id}",
            headers={"X-User-Id": str(student_id)}
        )
        st_data2 = st_orders_res2.get_json()
        assert st_data2["stats"]["completed"] >= 1
        comp_item = next(p for p in st_data2["projects"] if p["id"] == collab_id or p["title"] == "Automated Student Record System")
        assert comp_item["status"] == "completed"
        assert comp_item["deliverable_url"] == "https://github.com/edumatch/student-records"
        assert "Includes full Flask app" in comp_item["deliverable_note"]

        # Step 8: Test Delete/Cancel functionality for a pending requirement
        del_req_res = client.post(
            "/api/students/requirements",
            headers={"X-User-Id": str(student_id)},
            json={
                "title": "Pending Project To Delete",
                "category": "AI / ML",
                "description": "Will be deleted immediately.",
                "skills": ["Python"],
                "complexity": "Beginner",
                "budget": 1000,
                "deadline": "2026-12-01"
            }
        )
        to_delete_id = del_req_res.get_json()["requirement_id"]
        # Delete it
        del_action_res = client.delete(
            f"/api/requests/{to_delete_id}?item_type=requirement",
            headers={"X-User-Id": str(student_id)}
        )
        assert del_action_res.status_code == 200
        # Verify it no longer exists
        check_row = db.execute("SELECT * FROM requirements WHERE id = ?", (to_delete_id,)).fetchone()
        assert check_row is None

    finally:
        # Cleanup test accounts and records
        db.execute("DELETE FROM notifications WHERE user_id IN (?, ?, ?)", (student_id, provider_id, provider2_id))
        db.execute("DELETE FROM messages WHERE sender_id IN (?, ?)", (student_id, provider_id))
        db.execute("DELETE FROM conversations WHERE user1_id IN (?, ?) OR user2_id IN (?, ?)", (student_id, provider_id, student_id, provider_id))
        db.execute("DELETE FROM collaboration_requests WHERE student_id = ? OR provider_id = ?", (student_id, provider_id))
        db.execute("DELETE FROM requirements WHERE student_id = ?", (student_id,))
        db.execute("DELETE FROM provider_profiles WHERE user_id IN (?, ?)", (provider_id, provider2_id))
        db.execute("DELETE FROM users WHERE id IN (?, ?, ?)", (student_id, provider_id, provider2_id))
        db.commit()
