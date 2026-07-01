from flask import Blueprint, request, jsonify

from auth.utils.jwt_required import jwt_required
from auth.utils.current_actor import get_current_actor

from Notifications.models.reminder import Reminder

from extensions import db


reminder_bp = Blueprint(
    "reminder_bp",
    __name__
)


# ---------------- CREATE REMINDER ---------------- #

@reminder_bp.route("/create", methods=["POST"])
@jwt_required
def create_reminder():

    current_user = get_current_actor()

    if not current_user:
        return jsonify({
            "error": "Unauthorized"
        }), 401

    data = request.get_json()

    candidate_id = data.get("candidate_id")
    title = data.get("title")
    description = data.get("description")
    reminder_date = data.get("reminder_date")

    if not candidate_id:
        return jsonify({
            "error": "candidate_id is required"
        }), 400

    if not title:
        return jsonify({
            "error": "title is required"
        }), 400

    if not reminder_date:
        return jsonify({
            "error": "reminder_date is required"
        }), 400

    reminder = Reminder(
        candidate_id=candidate_id,
        created_by=current_user.get("user_id"),
        title=title,
        description=description,
        reminder_date=reminder_date
    )

    db.session.add(reminder)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Reminder created successfully",
        "data": reminder.to_dict()
    }), 201


# ---------------- GET CANDIDATE REMINDERS ---------------- #

@reminder_bp.route(
    "/candidate/<string:candidate_id>",
    methods=["GET"]
)
@jwt_required
def get_candidate_reminders(candidate_id):

    current_user = get_current_actor()

    if not current_user:
        return jsonify({
            "error": "Unauthorized"
        }), 401

    reminders = Reminder.query.filter_by(
        candidate_id=candidate_id
    ).order_by(
        Reminder.reminder_date.asc()
    ).all()

    return jsonify({
        "success": True,
        "count": len(reminders),
        "data": [
            reminder.to_dict()
            for reminder in reminders
        ]
    }), 200


# ---------------- MARK REMINDER COMPLETE ---------------- #

@reminder_bp.route(
    "/<int:reminder_id>/complete",
    methods=["PATCH"]
)
@jwt_required
def complete_reminder(reminder_id):

    current_user = get_current_actor()

    if not current_user:
        return jsonify({
            "error": "Unauthorized"
        }), 401

    reminder = Reminder.query.get(reminder_id)

    if not reminder:
        return jsonify({
            "error": "Reminder not found"
        }), 404

    reminder.is_completed = True

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Reminder marked as completed"
    }), 200


# ---------------- DELETE REMINDER ---------------- #

@reminder_bp.route(
    "/<int:reminder_id>",
    methods=["DELETE"]
)
@jwt_required
def delete_reminder(reminder_id):

    current_user = get_current_actor()

    if not current_user:
        return jsonify({
            "error": "Unauthorized"
        }), 401

    reminder = Reminder.query.get(reminder_id)

    if not reminder:
        return jsonify({
            "error": "Reminder not found"
        }), 404

    db.session.delete(reminder)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Reminder deleted successfully"
    }), 200


