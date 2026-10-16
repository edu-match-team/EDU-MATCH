import sys
from pathlib import Path

# Ensure project root is in sys.path regardless of where Python is launched from
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS

from backend.config import Config
from backend.database.connection import init_database

from backend.routes.auth import auth_bp
from backend.routes.providers import providers_bp
from backend.routes.matching import matching_bp
from backend.routes.students import students_bp
from backend.routes.requests import requests_bp
from backend.routes.chat import chat_bp
from backend.routes.admin import admin_bp
from backend.routes.reports import reports_bp
from backend.routes.reviews import reviews_bp
from backend.routes.skills import skills_bp
from backend.routes.services import services_bp


def create_app():
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

    app = Flask(
        __name__,
        static_folder=str(frontend_dir),
        static_url_path=""
    )
    app.config.from_object(Config)

    # Allow CORS from local origins and devtunnels
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [
                    r"https?://127\.0\.0\.1(:\d+)?",
                    r"https?://localhost(:\d+)?",
                    r"https?://.*\.devtunnels\.ms(:\d+)?",
                    r"https?://.*\.loca\.lt(:\d+)?",
                    r"https?://.*\.ngrok-free\.app(:\d+)?"
                ],
                "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization", "X-User-Id", "Accept"]
            }
        },
        supports_credentials=True
    )

    # Initialize SQLite database
    init_database(app)

    # Register all API Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(providers_bp)
    app.register_blueprint(matching_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(requests_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(reviews_bp)
    app.register_blueprint(skills_bp)
    app.register_blueprint(services_bp)

    # Route alias for provider registration called by frontend /api/provider/register
    @app.route("/api/provider/register", methods=["POST"])
    def provider_register_alias():
        from backend.routes.auth import register
        return register()

    # Route alias for provider profile called by frontend /api/provider/profile
    @app.route("/api/provider/profile", methods=["GET", "PUT"])
    def provider_profile_alias():
        from backend.routes.providers import provider_own_profile
        return provider_own_profile()

    # Route alias for provider requests called by frontend
    @app.route("/api/provider/requests", methods=["GET"])
    def provider_requests_alias():
        from backend.routes.requests import get_my_requests
        return get_my_requests()

    @app.route("/api/provider/requests/<int:req_id>", methods=["PUT", "PATCH"])
    def provider_request_update_alias(req_id):
        from backend.routes.requests import change_status
        return change_status(req_id)

    # Route alias for provider orders called by frontend
    @app.route("/api/provider/orders", methods=["GET"])
    def provider_orders_alias():
        from backend.routes.requests import get_auth_user_id
        from backend.database.queries import get_requests_for_provider
        user_id = get_auth_user_id()
        if not user_id:
            return jsonify({"success": False, "message": "Not authenticated."}), 401
        all_reqs = get_requests_for_provider(user_id)
        # Orders are accepted/in-progress/completed collaboration requests
        orders = []
        for r in all_reqs:
            orders.append({
                "id": r["id"],
                "service_title": r["project_title"],
                "student": {"name": r.get("student_name", "Student")},
                "amount": r["offered_budget"],
                "created_at": r["created_at"],
                "delivery_date": r["updated_at"],
                "status": r["status"]
            })
        return jsonify({"success": True, "orders": orders}), 200

    @app.route("/api/provider/earnings", methods=["GET"])
    @app.route("/provider/earnings", methods=["GET"])
    def provider_earnings_alias():
        from backend.routes.providers import provider_earnings
        return provider_earnings()

    @app.route("/api/provider/transactions", methods=["GET"])
    @app.route("/provider/transactions", methods=["GET"])
    def provider_transactions_alias():
        from backend.routes.providers import provider_transactions
        return provider_transactions()
    @app.route("/api/provider/orders/<int:order_id>", methods=["GET"])
    def provider_order_detail_handler(order_id):
        from backend.database.queries import get_order_details
        order = get_order_details(order_id)
        if not order:
            return jsonify({"success": False, "message": "Order not found."}), 404
        return jsonify({"success": True, "order": order}), 200

    @app.route("/api/provider/orders/<int:order_id>/status", methods=["PATCH", "PUT"])
    def provider_order_status_handler(order_id):
        from backend.routes.requests import get_auth_user_id
        from backend.database.queries import update_order_status_for_provider, get_order_details, create_notification
        user_id = get_auth_user_id()
        if not user_id:
            return jsonify({"success": False, "message": "Not authenticated."}), 401
        data = request.get_json(silent=True) or {}
        new_status = data.get("status", "").strip().lower()
        if not new_status:
            return jsonify({"success": False, "message": "Status required."}), 400

        success = update_order_status_for_provider(order_id, user_id, new_status)
        if not success:
            return jsonify({"success": False, "message": "Unable to update order status."}), 400

        # Send notification to student
        order = get_order_details(order_id)
        if order and order.get("student", {}).get("id"):
            st_id = order["student"]["id"]
            title = f"Order #{order_id} Updated"
            msg = f"Your order '{order['service_title']}' status has been updated to: {new_status.replace('_', ' ').capitalize()}."
            create_notification(st_id, title, msg, "/student/orders.html")

        return jsonify({"success": True, "message": f"Order status updated to {new_status.replace('_', ' ')}."}), 200

    @app.route("/api/provider/orders/<int:order_id>/deliverable", methods=["PATCH", "POST", "PUT"])
    def provider_order_deliverable_handler(order_id):
        from backend.routes.requests import get_auth_user_id
        from backend.database.queries import update_order_deliverable, get_order_details, create_notification
        user_id = get_auth_user_id()
        if not user_id:
            return jsonify({"success": False, "message": "Not authenticated."}), 401
        data = request.get_json(silent=True) or {}
        deliv_url = str(data.get("deliverable_url", "")).strip()
        deliv_note = str(data.get("deliverable_note", "")).strip()
        if not deliv_url:
            return jsonify({"success": False, "message": "Deliverable URL / link is required."}), 400

        success = update_order_deliverable(order_id, user_id, deliv_url, deliv_note)
        if not success:
            return jsonify({"success": False, "message": "Failed to record deliverable."}), 400

        # Notify student
        order = get_order_details(order_id)
        if order and order.get("student", {}).get("id"):
            st_id = order["student"]["id"]
            create_notification(
                st_id,
                f"Project Completed: Deliverable Ready for Order #{order_id}!",
                f"Your provider has uploaded deliverables for '{order['service_title']}'. Access: {deliv_url}",
                "/student/orders.html"
            )

        return jsonify({
            "success": True,
            "message": "Deliverable submitted successfully! Order marked as completed and projects counter updated."
        }), 200

    @app.route("/api/provider/orders/<int:order_id>/payment", methods=["PATCH", "POST", "PUT"])
    def provider_order_payment_handler(order_id):
        from backend.routes.requests import get_auth_user_id
        from backend.database.queries import update_order_payment_status, get_order_details, create_notification
        user_id = get_auth_user_id()
        if not user_id:
            return jsonify({"success": False, "message": "Not authenticated."}), 401
        data = request.get_json(silent=True) or {}
        pay_status = str(data.get("payment_status", "paid")).strip().lower()

        success = update_order_payment_status(order_id, user_id, pay_status)
        if not success:
            return jsonify({"success": False, "message": "Failed to update payment status."}), 400

        order = get_order_details(order_id)
        if order and order.get("student", {}).get("id"):
            st_id = order["student"]["id"]
            create_notification(
                st_id,
                f"Payment Status Updated for Order #{order_id}",
                f"Payment for '{order['service_title']}' has been marked as {pay_status.capitalize()}.",
                "/student/orders.html"
            )

        return jsonify({"success": True, "message": f"Payment status set to {pay_status}."}), 200

    @app.route("/api/provider/orders/<int:order_id>/payment-reminder", methods=["POST"])
    def provider_payment_reminder_handler(order_id):
        from backend.routes.requests import get_auth_user_id
        from backend.database.queries import get_order_details, create_notification
        user_id = get_auth_user_id()
        if not user_id:
            return jsonify({"success": False, "message": "Not authenticated."}), 401

        order = get_order_details(order_id)
        if not order:
            return jsonify({"success": False, "message": "Order not found."}), 404

        st_id = order.get("student", {}).get("id")
        if not st_id:
            return jsonify({"success": False, "message": "Student record missing."}), 400

        create_notification(
            st_id,
            f"⚠️ Urgent: Payment Reminder for Order #{order_id}",
            f"Provider '{order['provider']['name']}' requests settlement of ₹{order['amount']:,} for '{order['service_title']}'. Please verify your payment.",
            "/student/orders.html"
        )
        return jsonify({"success": True, "message": f"Payment reminder notification dispatched to {order['student']['name']}!"}), 200

    @app.route("/api/notifications", methods=["GET"])
    def user_notifications_handler():
        from backend.routes.requests import get_auth_user_id
        from backend.database.queries import get_user_notifications
        user_id = get_auth_user_id()
        if not user_id:
            q_id = request.args.get("user_id")
            if q_id and q_id.isdigit():
                user_id = int(q_id)

        if not user_id:
            return jsonify({"success": True, "notifications": [], "unread_count": 0, "total": 0}), 200

        notifs = get_user_notifications(user_id)
        unread = sum(1 for n in notifs if not n.get("is_read"))
        return jsonify({
            "success": True,
            "notifications": notifs,
            "unread_count": unread,
            "total": len(notifs)
        }), 200

    @app.route("/api/notifications/mark-read", methods=["POST"])
    def user_mark_notifications_read_handler():
        from backend.routes.requests import get_auth_user_id
        from backend.database.queries import mark_all_notifications_read
        user_id = get_auth_user_id()
        if not user_id:
            data = request.get_json(silent=True) or {}
            user_id = data.get("user_id")
        if not user_id:
            q_id = request.args.get("user_id")
            if q_id and q_id.isdigit():
                user_id = int(q_id)

        if user_id:
            mark_all_notifications_read(int(user_id))

        return jsonify({
            "success": True,
            "message": "All notifications marked as read.",
            "unread_count": 0
        }), 200

    # Route aliases for provider portfolio, services, certifications, reviews
    @app.route("/api/provider/portfolio", methods=["GET", "POST"])
    def provider_portfolio_alias():
        from backend.routes.providers import provider_portfolio
        return provider_portfolio()

    @app.route("/api/provider/portfolio/<int:project_id>", methods=["DELETE"])
    def provider_portfolio_delete_alias(project_id):
        from backend.routes.providers import delete_portfolio_project
        return delete_portfolio_project(project_id)

    @app.route("/api/provider/services", methods=["GET", "POST"])
    def provider_services_alias():
        from backend.routes.providers import provider_services_handler
        return provider_services_handler()

    @app.route("/api/provider/services/<int:service_id>", methods=["PUT", "DELETE"])
    def provider_services_detail_alias(service_id):
        from backend.routes.providers import provider_service_detail_handler
        return provider_service_detail_handler(service_id)

    @app.route("/api/provider/certifications", methods=["GET", "POST"])
    def provider_certifications_alias():
        from backend.routes.providers import provider_certifications_handler
        return provider_certifications_handler()

    @app.route("/api/provider/reviews", methods=["GET"])
    def provider_reviews_alias():
        from backend.routes.providers import get_current_provider_reviews
        return get_current_provider_reviews()

    # Route alias for student project requests called by frontend /api/projects/my
    @app.route("/api/projects/my", methods=["GET"])
    def projects_my_alias():
        from backend.routes.requests import get_my_projects
        return get_my_projects()

    # Route aliases for provider skills called by frontend /api/provider/skills
    @app.route("/api/provider/skills", methods=["GET", "POST"])
    def provider_skills_alias():
        from backend.routes.providers import provider_skills_handler
        return provider_skills_handler()

    @app.route("/api/provider/skills/<int:skill_id>", methods=["PUT", "DELETE"])
    def provider_skill_item_alias(skill_id):
        from backend.routes.providers import provider_skill_item_handler
        return provider_skill_item_handler(skill_id)

    # Route alias for open student requirements for providers
    @app.route("/api/provider/requirements", methods=["GET"])
    def provider_student_requirements_alias():
        from backend.routes.requests import get_open_student_requirements
        return get_open_student_requirements()

    # Route alias for provider proposing on student requirement
    @app.route("/api/provider/propose", methods=["POST"])
    def provider_propose_alias():
        from backend.routes.requests import provider_propose_on_requirement
        return provider_propose_on_requirement()

    # Security Headers for production-grade protection
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({
            "success": True,
            "message": "EduMatch Full-Stack API & DSA Engine is operational."
        }), 200

    # Serve the frontend HTML files
    @app.route("/", methods=["GET"])
    def serve_index():
        return send_from_directory(str(frontend_dir), "index.html")

    @app.route("/<path:path>", methods=["GET"])
    def serve_frontend_files(path):
        target = frontend_dir / path
        if target.is_file():
            return send_from_directory(str(frontend_dir), path)
        if (frontend_dir / f"{path}.html").is_file():
            return send_from_directory(str(frontend_dir), f"{path}.html")
        if (target / "index.html").is_file():
            return send_from_directory(str(target), "index.html")
        return jsonify({
            "success": False,
            "message": f"Resource '/{path}' not found."
        }), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify({
            "success": False,
            "message": "An internal server error occurred."
        }), 500

    return app


app = create_app()

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  EduMatch Web Platform is starting on http://127.0.0.1:5000")
    print("  Explore Portals:")
    print("  - Student Login:  http://127.0.0.1:5000/student/login.html")
    print("  - Provider Login: http://127.0.0.1:5000/provider/login.html")
    print("  - Admin Login:    http://127.0.0.1:5000/admin/login.html")
    print("=" * 60 + "\n")
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )