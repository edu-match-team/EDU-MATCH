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


def create_app():
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

    app = Flask(
        __name__,
        static_folder=str(frontend_dir),
        static_url_path=""
    )
    app.config.from_object(Config)

    # Allow CORS from local origins including Vite (5173), Flask (5000), Live Server (5500)
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [
                    "http://127.0.0.1:5000",
                    "http://localhost:5000",
                    "http://127.0.0.1:5173",
                    "http://localhost:5173",
                    "http://127.0.0.1:5500",
                    "http://localhost:5500"
                ]
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

    @app.route("/api/provider/certifications", methods=["GET", "POST"])
    def provider_certifications_alias():
        from backend.routes.providers import provider_certifications_handler
        return provider_certifications_handler()

    @app.route("/api/provider/reviews", methods=["GET"])
    def provider_reviews_alias():
        from backend.routes.providers import get_current_provider_reviews
        return get_current_provider_reviews()

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