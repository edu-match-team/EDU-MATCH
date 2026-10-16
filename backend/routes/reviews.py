
from flask import Blueprint, jsonify, request

from backend.database.connection import get_db
from backend.models.review import (
    create_review,
    get_reviews_for_provider,
)
from backend.routes.providers import get_auth_user_id

reviews_bp = Blueprint("reviews", __name__, url_prefix="/api/reviews")


@reviews_bp.route("/provider/<int:provider_id>", methods=["GET"])
def list_provider_reviews(provider_id):
    reviews = get_reviews_for_provider(provider_id)

    if reviews is None:
        return jsonify({
            "success": False,
            "message": "Provider not found.",
        }), 404

    average = round(
        sum(review["rating"] for review in reviews) / len(reviews), 1
    ) if reviews else 0

    return jsonify({
        "success": True,
        "count": len(reviews),
        "average_rating": average,
        "reviews": reviews,
    }), 200


@reviews_bp.route("/provider/<int:provider_id>", methods=["POST"])
def submit_provider_review(provider_id):
    student_id = get_auth_user_id()

    if not student_id:
        return jsonify({
            "success": False,
            "message": "Please log in to submit a review.",
        }), 401

    db = get_db()
    student = db.execute(
        "SELECT role, is_active FROM users WHERE id = ?",
        (student_id,),
    ).fetchone()

    if not student or student["role"] != "student" or not student["is_active"]:
        return jsonify({
            "success": False,
            "message": "Only active student accounts can submit reviews.",
        }), 403

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "message": "Send a JSON object with a rating and optional comment.",
        }), 400

    rating = data.get("rating")
    comment = data.get("comment", data.get("review", ""))

    if isinstance(rating, str) and rating.isdigit():
        rating = int(rating)

    if isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5:
        return jsonify({
            "success": False,
            "message": "Rating must be a whole number from 1 to 5.",
        }), 400

    if not isinstance(comment, str):
        return jsonify({
            "success": False,
            "message": "Comment must be text.",
        }), 400

    try:
        review_id = create_review(
            provider_id=provider_id,
            student_id=student_id,
            rating=rating,
            comment=comment,
        )
    except ValueError as error:
        return jsonify({
            "success": False,
            "message": str(error),
        }), 400

    return jsonify({
        "success": True,
        "message": "Review submitted successfully.",
        "review_id": review_id,
    }), 201
