import pytest
import json
import uuid
from backend.app import create_app
from backend.database.queries import get_or_create_conversation

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_student_profile_photo_and_completion(client):
    uid = uuid.uuid4().hex[:8]
    # 1. Register student
    reg_res = client.post("/api/auth/register", json={
        "fullName": "Om Student",
        "email": f"om.{uid}@edumatch.edu",
        "password": "Password123!",
        "role": "student"
    })
    assert reg_res.status_code == 201
    user_data = reg_res.get_json()["user"]
    user_id = user_data["id"]
    token = f"edumatch_token_{user_id}"

    # 2. Update student profile with photo
    photo_data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    put_res = client.put(
        "/api/students/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "fullName": "Om Student Updated",
            "college": "Delhi Technological University",
            "degree": "B.Tech Computer Science",
            "specialization": "AI & ML",
            "year": "3rd Year",
            "skills": "Python, Flask, PyTorch",
            "bio": "Passionate about AI projects and research.",
            "profilePhoto": photo_data
        }
    )
    assert put_res.status_code == 200

    # 3. Check /api/auth/me returns updated photo and name
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.get_json()["user"]
    assert me_data["fullName"] == "Om Student Updated"
    assert me_data["profile_photo"] == photo_data

    # 4. Check /api/students/profile returns updated photo and fields
    prof_res = client.get("/api/students/profile", headers={"Authorization": f"Bearer {token}"})
    assert prof_res.status_code == 200
    prof = prof_res.get_json()["profile"]
    assert prof["profile_photo"] == photo_data
    assert prof["college"] == "Delhi Technological University"


def test_provider_profile_photo_and_chat_deletion(client):
    uid = uuid.uuid4().hex[:8]
    # 1. Register provider
    reg_res = client.post("/api/auth/register", json={
        "fullName": "Dr. Sarah Mentor",
        "email": f"sarah.{uid}@edumatch.edu",
        "password": "Password123!",
        "role": "provider"
    })
    assert reg_res.status_code == 201
    prov_id = reg_res.get_json()["user"]["id"]
    prov_token = f"edumatch_token_{prov_id}"

    # 2. Update provider profile with photo
    photo_data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    put_res = client.put(
        "/api/provider/profile",
        headers={"Authorization": f"Bearer {prov_token}"},
        json={
            "full_name": "Dr. Sarah Mentor",
            "professional_title": "Senior AI Researcher & Mentor",
            "bio": "Experienced in Deep Learning and NLP projects.",
            "skills": "Python, TensorFlow, NLP",
            "profile_photo": photo_data
        }
    )
    assert put_res.status_code == 200

    # 3. Check /api/provider/profile returns the photo
    p_get = client.get("/api/provider/profile", headers={"Authorization": f"Bearer {prov_token}"})
    assert p_get.status_code == 200
    p_data = p_get.get_json()["profile"]
    assert p_data["profile_photo"] == photo_data

    # 4. Register a student to chat with
    st_res = client.post("/api/auth/register", json={
        "fullName": "Student Alice",
        "email": f"alice.{uid}@edumatch.edu",
        "password": "Password123!",
        "role": "student"
    })
    student_id = st_res.get_json()["user"]["id"]
    student_token = f"edumatch_token_{student_id}"

    # 5. Start conversation
    conv_res = client.post("/api/chat/start", headers={"Authorization": f"Bearer {student_token}"}, json={
        "other_user_id": prov_id
    })
    assert conv_res.status_code == 200
    conv_id = conv_res.get_json()["conversation_id"]

    # 6. Send message from provider
    msg_res = client.post(
        f"/api/provider/conversations/{conv_id}/messages",
        headers={"Authorization": f"Bearer {prov_token}"},
        json={"message": "Hello Alice, I have reviewed your project proposal!"}
    )
    assert msg_res.status_code == 201
    msg_id = msg_res.get_json()["message"]["id"]

    # 7. Check message appears in GET
    msgs_get = client.get(
        f"/api/student/conversations/{conv_id}/messages",
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert msgs_get.status_code == 200
    msgs = msgs_get.get_json()["messages"]
    assert len(msgs) == 1
    assert msgs[0]["message"] == "Hello Alice, I have reviewed your project proposal!"
    assert not msgs[0]["is_deleted"]

    # 8. Delete message for everyone from provider
    del_res = client.delete(
        f"/api/provider/messages/{msg_id}",
        headers={"Authorization": f"Bearer {prov_token}"},
        json={"delete_for": "everyone"}
    )
    assert del_res.status_code == 200

    # 9. Verify message shows as deleted for everyone
    msgs_after = client.get(
        f"/api/student/conversations/{conv_id}/messages",
        headers={"Authorization": f"Bearer {student_token}"}
    )
    msgs_list = msgs_after.get_json()["messages"]
    assert len(msgs_list) == 1
    assert msgs_list[0]["is_deleted"] is True
    assert "deleted" in msgs_list[0]["message"].lower()

    # 10. Clear conversation
    clear_res = client.delete(
        f"/api/chat/conversations/{conv_id}/clear",
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert clear_res.status_code == 200

    # 11. Verify student sees 0 messages after clear
    msgs_cleared = client.get(
        f"/api/student/conversations/{conv_id}/messages",
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert len(msgs_cleared.get_json()["messages"]) == 0
