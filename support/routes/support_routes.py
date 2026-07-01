from flask import Blueprint, request, jsonify
from extensions import db
from support.models.support_ticket import SupportTicket
from auth.utils.jwt_required import jwt_required
from flask import g

support_bp = Blueprint("support_bp", __name__, url_prefix="/api/support")

def get_current_user():
    if not hasattr(g, "current_user"):
        return None
    return g.current_user

@support_bp.route("/create", methods=["POST"])
@jwt_required
def create_support_ticket():

    data = request.get_json()

    current_user = get_current_user()
    if not current_user:
        return jsonify({
            "success": False,
            "message": "Unauthorized"
        }), 401

    name = data.get("name")
    email = current_user["user_id"]
    issue_type = data.get("issue_type")
    description = data.get("description")

    # Basic validation
    if not name or not issue_type or not description:
        return jsonify({
            "success": False,
            "message": "All fields are required"
        }), 400

    if issue_type not in ["bug", "feedback"]:
        return jsonify({
            "success": False,
            "message": "Invalid issue type"
        }), 400

    ticket = SupportTicket(
        name=name,
        email=email,
        issue_type=issue_type,
        description=description
    )

    db.session.add(ticket)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Support request submitted successfully"
    }), 201