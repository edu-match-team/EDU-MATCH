from flask import Blueprint, jsonify, request, session
from backend.database.queries import (
    create_collaboration_request,
    get_requests_for_provider,
    get_requests_for_student,
    update_request_status,
    get_user_by_id,
    get_or_create_conversation,
    create_notification
)
from backend.database.connection import get_db
from backend.database.supabase_client import (
    sync_collaboration_request_to_supabase,
    update_supabase_request_status,
    create_supabase_notification
)

from dsa.sorting import merge_sort
from dsa.priority_queue import PriorityQueue, top_k_elements

requests_bp = Blueprint("requests", __name__, url_prefix="/api/requests")


def get_auth_user_id():
    auth_header = request.headers.get("Authorization", "").strip()
    if auth_header:
        clean = auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else auth_header
        if clean.isdigit():
            return int(clean)
        if "_" in clean:
            try:
                return int(clean.split("_")[-1])
            except ValueError:
                pass

    x_uid = request.headers.get("X-User-Id", "").strip()
    if x_uid.isdigit():
        return int(x_uid)

    q_uid = request.args.get("user_id", "").strip()
    if q_uid.isdigit():
        return int(q_uid)

    user_id = session.get("user_id")
    if user_id:
        return int(user_id)

    return None


@requests_bp.route("", methods=["POST"])
def send_request():
    user_id = get_auth_user_id()
    if not user_id:
        return jsonify({"success": False, "message": "You must be logged in to send requests."}), 401

    data = request.get_json(silent=True) or {}
    provider_id = data.get("provider_id")
    project_title = str(data.get("project_title", "")).strip()
    message = str(data.get("message", "")).strip()
    
    try:
        budget = int(data.get("offered_budget", 2000))
    except (ValueError, TypeError):
        budget = 2000

    if not provider_id or not project_title or not message:
        return jsonify({"success": False, "message": "Provider, project title, and message are required."}), 400

    provider = get_user_by_id(provider_id)
    if not provider or provider["role"] != "provider":
        return jsonify({"success": False, "message": "Selected provider does not exist."}), 404

    req_id = create_collaboration_request(
        student_id=user_id,
        provider_id=provider_id,
        project_title=project_title,
        message=message,
        offered_budget=budget,
        requirement_id=data.get("requirement_id")
    )

    # Automatically create conversation so they can immediately chat
    get_or_create_conversation(user_id, provider_id)

    # Sync to Supabase
    try:
        sync_collaboration_request_to_supabase(
            req_id=req_id,
            student_id=user_id,
            provider_id=provider_id,
            project_title=project_title,
            message=message,
            budget=budget,
            status="pending",
            requirement_id=data.get("requirement_id")
        )
        student_user = get_user_by_id(user_id)
        s_name = student_user["full_name"] if student_user else "A student"
        create_notification(
            user_id=provider_id,
            title="New Project Order / Request",
            message=f"{s_name} sent you a project request: '{project_title}' (Budget: ₹{budget:,}).",
            link="/provider/requests.html"
        )
        create_supabase_notification(
            user_id=provider_id,
            title="New Project Order / Request",
            message=f"{s_name} sent you a project request: '{project_title}' (Budget: ₹{budget}).",
            link="/provider/requests.html"
        )
    except Exception:
        pass

    return jsonify({
        "success": True,
        "message": "Collaboration request sent successfully!",
        "request_id": req_id
    }), 201


@requests_bp.route("", methods=["GET"])
def get_my_requests():
    user_id = get_auth_user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Not logged in."}), 401

    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404

    if user["role"] == "provider":
        reqs = get_requests_for_provider(user_id)
    else:
        reqs = get_requests_for_student(user_id)

    return jsonify({"success": True, "requests": reqs}), 200


@requests_bp.route("/my", methods=["GET"])
@requests_bp.route("/projects/my", methods=["GET"])
def get_my_projects():
    """
    Returns unified project requests for student:
    - Collaboration requests sent to providers
    - Submitted project requirements (mapped to pending/open)
    Uses DSA Merge Sort (O(N log N)) and Priority Queue (Heap) for ranking.
    Ensures Pending, In Progress, Completed, and Total Requests counts are always accurate!
    """
    user_id = get_auth_user_id()
    db = get_db()

    if not user_id:
        return jsonify({
            "success": True,
            "projects": [],
            "requests": [],
            "stats": {
                "total_requests": 0,
                "pending": 0,
                    "in_progress": 0,
                    "completed": 0
                },
                "dsa_metadata": {
                    "sorting_algorithm": "Merge Sort (Divide-and-Conquer)",
                    "time_complexity": "O(N log N)",
                    "items_processed": 0
                }
            }), 200

    # 1. Collaboration requests sent to providers
    collab_rows = db.execute("""
        SELECT cr.id, cr.project_title as title, cr.project_title as project_name,
               cr.message as description, cr.offered_budget as budget,
               cr.status, cr.created_at, cr.updated_at,
               u.full_name as provider_name, cr.provider_id,
               'collaboration_request' as item_type,
               cr.deliverable_url, cr.deliverable_note
        FROM collaboration_requests cr
        LEFT JOIN users u ON (cr.provider_id = u.id OR cr.provider_id IN (SELECT id FROM provider_profiles WHERE user_id = u.id))
        WHERE cr.student_id = ?
        ORDER BY cr.created_at DESC
    """, (user_id,)).fetchall()

    # Deduplicate collaboration requests: drop identical provider + project_title duplicates
    seen_collabs = set()
    deduped_collabs = []
    active_project_titles = set()

    for r in collab_rows:
        d = dict(r)
        p_title = (d.get("title") or "").strip().lower()
        st = str(d.get("status") or "").lower()
        if st in ("pending", "accepted", "in_progress", "completed"):
            active_project_titles.add(p_title)

        dedup_key = (d.get("provider_id"), p_title, st)
        if dedup_key in seen_collabs:
            continue
        seen_collabs.add(dedup_key)
        deduped_collabs.append(d)

    # 2. General student project requirements
    # Exclude open requirements that already have an active collaboration request with a provider
    req_rows = db.execute("""
        SELECT r.id, r.title, r.title as project_name,
               r.description, r.budget,
               CASE WHEN r.status = 'open' THEN 'pending' ELSE r.status END as status,
               r.created_at, r.created_at as updated_at,
               'Open (Seeking Provider)' as provider_name, NULL as provider_id,
               'requirement' as item_type,
               NULL as deliverable_url, NULL as deliverable_note
        FROM requirements r
        WHERE r.student_id = ?
          AND LOWER(r.status) = 'open'
          AND r.id NOT IN (
              SELECT requirement_id FROM collaboration_requests 
              WHERE student_id = ? AND requirement_id IS NOT NULL
          )
        ORDER BY r.created_at DESC
    """, (user_id, user_id)).fetchall()

    # Filter out requirements where student already has an active provider collaboration request with the same title
    filtered_reqs = []
    for r in req_rows:
        d = dict(r)
        p_title = (d.get("title") or "").strip().lower()
        if p_title not in active_project_titles:
            filtered_reqs.append(d)

    combined = deduped_collabs + filtered_reqs

    # DSA Algorithm 1: Stable Merge Sort for guaranteed O(N log N) ordering
    sorted_projects = merge_sort(
        combined,
        key=lambda x: str(x.get("created_at") or ""),
        reverse=True
    )

    # DSA Algorithm 2: Binary Max-Heap Priority Queue for top-budget/urgency scheduling
    priority_scheduled = top_k_elements(
        sorted_projects,
        k=min(5, len(sorted_projects)),
        key=lambda x: float(x.get("budget") or 0)
    )

    pending_cnt = sum(1 for x in sorted_projects if str(x.get("status", "")).lower() in ("pending", "open"))
    progress_cnt = sum(1 for x in sorted_projects if str(x.get("status", "")).lower() in ("in_progress", "accepted"))
    completed_cnt = sum(1 for x in sorted_projects if str(x.get("status", "")).lower() == "completed")

    return jsonify({
        "success": True,
        "projects": sorted_projects,
        "requests": sorted_projects,
        "priority_scheduled": priority_scheduled,
        "stats": {
            "total_requests": len(sorted_projects),
            "pending": pending_cnt,
            "in_progress": progress_cnt,
            "completed": completed_cnt
        },
        "dsa_metadata": {
            "sorting_algorithm": "Merge Sort (Divide-and-Conquer)",
            "sorting_time_complexity": "O(N log N)",
            "sorting_space_complexity": "O(N)",
            "priority_scheduler": "Binary Max-Heap Priority Queue (O(N log K))",
            "items_processed": len(sorted_projects)
        }
    }), 200


@requests_bp.route("/student-requirements", methods=["GET"])
def get_open_student_requirements():
    """
    Allows providers to browse open student requirements/project requests.
    Excludes requirements that are already accepted, in-progress, completed,
    or where the current provider has already submitted a proposal.
    """
    db = get_db()
    current_user_id = get_auth_user_id()

    if current_user_id:
        rows = db.execute("""
            SELECT r.id, r.student_id, r.title, r.category, r.description,
                   r.required_skills, r.budget, r.deadline, r.complexity,
                   r.status, r.created_at,
                   u.full_name as student_name, u.email as student_email
            FROM requirements r
            JOIN users u ON r.student_id = u.id
            WHERE u.is_active = 1 
              AND LOWER(r.status) = 'open'
              AND r.id NOT IN (
                  SELECT requirement_id FROM collaboration_requests 
                  WHERE requirement_id IS NOT NULL 
                    AND status IN ('accepted', 'in_progress', 'completed')
              )
              AND r.id NOT IN (
                  SELECT requirement_id FROM collaboration_requests 
                  WHERE requirement_id IS NOT NULL 
                    AND provider_id = ?
              )
            ORDER BY r.created_at DESC
        """, (current_user_id,)).fetchall()
    else:
        rows = db.execute("""
            SELECT r.id, r.student_id, r.title, r.category, r.description,
                   r.required_skills, r.budget, r.deadline, r.complexity,
                   r.status, r.created_at,
                   u.full_name as student_name, u.email as student_email
            FROM requirements r
            JOIN users u ON r.student_id = u.id
            WHERE u.is_active = 1 
              AND LOWER(r.status) = 'open'
              AND r.id NOT IN (
                  SELECT requirement_id FROM collaboration_requests 
                  WHERE requirement_id IS NOT NULL 
                    AND status IN ('accepted', 'in_progress', 'completed')
              )
            ORDER BY r.created_at DESC
        """).fetchall()

    requirements = []
    for row in rows:
        skills = [s.strip() for s in (row["required_skills"] or "").split(",") if s.strip()]
        requirements.append({
            "id": row["id"],
            "student_id": row["student_id"],
            "title": row["title"],
            "category": row["category"],
            "description": row["description"],
            "skills": skills,
            "budget": row["budget"],
            "deadline": row["deadline"] or "Flexible",
            "complexity": row["complexity"] or "Intermediate",
            "status": row["status"],
            "created_at": row["created_at"],
            "student_name": row["student_name"],
            "student_email": row["student_email"]
        })

    return jsonify({"success": True, "requirements": requirements}), 200


@requests_bp.route("/propose", methods=["POST"])
def provider_propose_on_requirement():
    """
    When a provider expresses interest or accepts a student requirement:
    Sends an offer/proposal to the student.
    The student sees it and has the option to Give Project to Provider or decline!
    """
    user_id = get_auth_user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Not logged in."}), 401

    provider = get_user_by_id(user_id)
    if not provider or provider["role"] != "provider":
        return jsonify({"success": False, "message": "Only verified providers can propose on requirements."}), 403

    data = request.get_json(silent=True) or {}
    req_id = data.get("requirement_id")
    message = str(data.get("message") or f"Hi! I am interested in building your project. Let's collaborate!").strip()

    db = get_db()
    req_row = db.execute("SELECT * FROM requirements WHERE id = ?", (req_id,)).fetchone()
    if not req_row:
        return jsonify({"success": False, "message": "Requirement not found."}), 404

    student_id = req_row["student_id"]
    budget = req_row["budget"]
    title = req_row["title"]

    # Check if this provider has already proposed on this requirement
    existing_prop = db.execute(
        "SELECT id FROM collaboration_requests WHERE requirement_id = ? AND provider_id = ?",
        (req_id, user_id)
    ).fetchone()
    if existing_prop:
        return jsonify({
            "success": False,
            "message": "You have already submitted a proposal for this project requirement."
        }), 409

    # Create collaboration request with status 'pending' (from provider proposal)
    collab_id = create_collaboration_request(
        student_id=student_id,
        provider_id=user_id,
        project_title=title,
        message=f"[Provider Proposal] {message}",
        offered_budget=budget,
        requirement_id=req_id
    )

    # Establish conversation
    get_or_create_conversation(student_id, user_id)

    # Notify student
    try:
        create_notification(
            user_id=student_id,
            title="Provider Proposed on Your Project!",
            message=f"{provider['full_name']} wants to build '{title}'. You can accept and assign the project!",
            link="/student/orders.html"
        )
        sync_collaboration_request_to_supabase(
            req_id=collab_id,
            student_id=student_id,
            provider_id=user_id,
            project_title=title,
            message=f"[Provider Proposal] {message}",
            budget=budget,
            status="pending",
            requirement_id=req_id
        )
        create_supabase_notification(
            user_id=student_id,
            title="Provider Proposed on Your Project!",
            message=f"{provider['full_name']} wants to build '{title}'. You can accept and give the project!",
            link="/student/orders.html"
        )
    except Exception:
        pass

    return jsonify({
        "success": True,
        "message": f"Proposal sent to {req_row['title']} successfully! The student will be notified.",
        "request_id": collab_id
    }), 201


@requests_bp.route("/<int:request_id>/status", methods=["PUT", "PATCH"])
def change_status(request_id):
    user_id = get_auth_user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Not logged in."}), 401

    data = request.get_json(silent=True) or {}
    new_status = data.get("status")

    if new_status not in ("accepted", "rejected", "completed", "in_progress", "cancelled"):
        return jsonify({"success": False, "message": "Invalid status transition."}), 400

    db = get_db()
    # Check if user is either provider or student on this request
    req_row = db.execute("SELECT * FROM collaboration_requests WHERE id = ?", (request_id,)).fetchone()
    if not req_row:
        return jsonify({"success": False, "message": "Request not found."}), 404

    if req_row["provider_id"] != user_id and req_row["student_id"] != user_id:
        return jsonify({"success": False, "message": "Unauthorized."}), 403

    if new_status in ("accepted", "in_progress"):
        new_status = "in_progress"

    db.execute(
        "UPDATE collaboration_requests SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (new_status, request_id)
    )

    req_id = req_row.get("requirement_id")
    if not req_id and req_row.get("project_title"):
        match_req = db.execute(
            "SELECT id FROM requirements WHERE student_id = ? AND LOWER(title) = LOWER(?) LIMIT 1",
            (req_row["student_id"], req_row["project_title"])
        ).fetchone()
        req_id = match_req["id"] if match_req else None

    if req_id:
        if new_status == "in_progress":
            # Update parent requirement to in_progress so it is closed to all other providers
            db.execute("UPDATE requirements SET status = 'in_progress' WHERE id = ?", (req_id,))
            # Reject other pending proposals for the same requirement
            db.execute(
                "UPDATE collaboration_requests SET status = 'rejected', updated_at = CURRENT_TIMESTAMP WHERE (requirement_id = ? OR (student_id = ? AND LOWER(project_title) = LOWER(?))) AND id != ? AND status = 'pending'",
                (req_id, req_row["student_id"], req_row["project_title"], request_id)
            )
        elif new_status == "completed":
            # Mark requirement as completed
            db.execute("UPDATE requirements SET status = 'completed' WHERE id = ?", (req_id,))
            # Increment completed_projects in provider_profiles
            db.execute(
                "UPDATE provider_profiles SET completed_projects = completed_projects + 1 WHERE user_id = ? OR id = ?",
                (req_row["provider_id"], req_row["provider_id"])
            )

    if new_status == "completed" and not req_id:
        # Increment provider completed_projects for direct service orders
        db.execute(
            "UPDATE provider_profiles SET completed_projects = completed_projects + 1 WHERE user_id = ? OR id = ?",
            (req_row["provider_id"], req_row["provider_id"])
        )

    db.commit()
    invalidate_matching_cache()

    # Sync status to Supabase and SQLite notifications
    try:
        other_user_id = req_row["student_id"] if user_id == req_row["provider_id"] else req_row["provider_id"]
        updater = get_user_by_id(user_id)
        updater_name = updater["full_name"] if updater else "Partner"
        dest_link = "/student/orders.html" if user_id == req_row["provider_id"] else "/provider/requests.html"
        create_notification(
            user_id=other_user_id,
            title=f"Project Request {new_status.title()}",
            message=f"{updater_name} updated status of '{req_row['project_title']}' to {new_status}.",
            link=dest_link
        )
        update_supabase_request_status(request_id, new_status)
        create_supabase_notification(
            user_id=other_user_id,
            title=f"Project Request {new_status.title()}",
            message=f"{updater_name} updated status of '{req_row['project_title']}' to {new_status}.",
            link=dest_link
        )
    except Exception:
        pass

    return jsonify({
        "success": True,
        "message": f"Collaboration request marked as {new_status}."
    }), 200
