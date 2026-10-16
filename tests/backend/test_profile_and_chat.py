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


def test_chat_alignment_and_student_profile_sync(client):
    uid = uuid.uuid4().hex[:8]
    # 1. Register student
    s_reg = client.post("/api/auth/register", json={
        "fullName": "Rohan Sharma",
        "email": f"rohan.{uid}@edumatch.edu",
        "password": "Password123!",
        "role": "student"
    })
    assert s_reg.status_code == 201
    s_id = s_reg.get_json()["user"]["id"]
    s_token = f"edumatch_token_{s_id}"

    # 2. Register provider
    p_reg = client.post("/api/auth/register", json={
        "fullName": "Vishwajeet Rawat",
        "email": f"vishwajeet.{uid}@edumatch.edu",
        "password": "Password123!",
        "role": "provider"
    })
    assert p_reg.status_code == 201
    p_id = p_reg.get_json()["user"]["id"]
    p_token = f"edumatch_token_{p_id}"

    # 3. Student sets up initial profile
    client.put(
        "/api/students/profile",
        headers={"Authorization": f"Bearer {s_token}"},
        json={
            "fullName": "Rohan Sharma",
            "college": "BITS Pilani",
            "degree": "B.E. Computer Science",
            "year": "4th Year",
            "skills": "React, Python, Machine Learning",
            "bio": "Building autonomous AI agents.",
            "phone": "+91 9876543210"
        }
    )

    # 4. Start conversation
    conv_id = get_or_create_conversation(s_id, p_id)

    # 5. Student sends message
    s_msg_res = client.post(
        f"/api/student/conversations/{conv_id}/messages",
        headers={"Authorization": f"Bearer {s_token}"},
        json={"message": "Hi, I need assistance on my capstone project."}
    )
    assert s_msg_res.status_code == 201

    # 6. Provider sends reply
    p_msg_res = client.post(
        f"/api/provider/conversations/{conv_id}/messages",
        headers={"Authorization": f"Bearer {p_token}"},
        json={"message": "Hello Rohan! I can definitely help with your capstone."}
    )
    assert p_msg_res.status_code == 201

    # 7. Check from Provider's view
    p_get = client.get(
        f"/api/provider/conversations/{conv_id}/messages",
        headers={"Authorization": f"Bearer {p_token}"}
    )
    assert p_get.status_code == 200
    p_data = p_get.get_json()
    p_msgs = p_data["messages"]
    assert len(p_msgs) == 2

    # Verify alignment flags for Provider
    # s_msg was sent by student -> is_mine should be False
    assert p_msgs[0]["is_mine"] is False
    assert p_msgs[0]["sender_id"] == s_id
    # p_msg was sent by provider -> is_mine should be True
    assert p_msgs[1]["is_mine"] is True
    assert p_msgs[1]["sender_id"] == p_id

    # Verify student profile returned in other_user
    other_u = p_data["other_user"]
    assert other_u["id"] == s_id
    assert other_u["institution"] == "BITS Pilani"
    assert "React" in other_u["skills"]
    assert other_u["phone"] == "+91 9876543210"

    # 8. Check from Student's view
    s_get = client.get(
        f"/api/student/conversations/{conv_id}/messages",
        headers={"Authorization": f"Bearer {s_token}"}
    )
    assert s_get.status_code == 200
    s_data = s_get.get_json()
    s_msgs = s_data["messages"]
    # Verify alignment flags for Student
    assert s_msgs[0]["is_mine"] is True
    assert s_msgs[1]["is_mine"] is False

    # 9. Student updates profile with new university and bio
    client.put(
        "/api/students/profile",
        headers={"Authorization": f"Bearer {s_token}"},
        json={
            "fullName": "Rohan Sharma",
            "college": "Stanford University",
            "degree": "M.S. Artificial Intelligence",
            "year": "1st Year",
            "skills": "LLMs, PyTorch, LangChain, React",
            "bio": "Graduate AI researcher at Stanford.",
            "phone": "+1 650 123 4567"
        }
    )

    # 10. Provider re-fetches messages -> other_user immediately reflects student's updated profile!
    p_get2 = client.get(
        f"/api/provider/conversations/{conv_id}/messages",
        headers={"Authorization": f"Bearer {p_token}"}
    )
    other_u2 = p_get2.get_json()["other_user"]
    assert other_u2["institution"] == "Stanford University"
    assert other_u2["degree"] == "M.S. Artificial Intelligence"
    assert "LLMs" in other_u2["skills"]
    assert other_u2["phone"] == "+1 650 123 4567"

    # 11. Check public student profile endpoint
    st_prof_pub = client.get(f"/api/students/profile/{s_id}", headers={"Authorization": f"Bearer {p_token}"})
    assert st_prof_pub.status_code == 200
    assert st_prof_pub.get_json()["profile"]["institution"] == "Stanford University"

