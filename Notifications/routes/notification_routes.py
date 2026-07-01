from flask import Blueprint, jsonify

from auth.utils.jwt_required import jwt_required
from auth.utils.current_actor import get_current_actor

from Notifications.models.notification import Notification

from extensions import db


app_notification_bp = Blueprint(
    "app_notification_bp",
    __name__
)


# ---------------- GET NOTIFICATIONS ---------------- #

@app_notification_bp.route("/", methods=["GET"])
@jwt_required
def get_notifications():

    current_user = get_current_actor()

    if not current_user:
        return jsonify({
            "error": "Unauthorized"
        }), 401

    notifications = Notification.query.filter_by(
        user_id=str(current_user.id)
    ).order_by(
        Notification.created_at.desc()
    ).all()

    return jsonify({
        "success": True,
        "count": len(notifications),
        "data": [
            notification.to_dict()
            for notification in notifications
        ]
    }), 200


# ---------------- UNREAD COUNT ---------------- #

@app_notification_bp.route("/unread-count", methods=["GET"])
@jwt_required
def unread_count():

    current_user = get_current_actor()

    if not current_user:
        return jsonify({
            "error": "Unauthorized"
        }), 401

    count = Notification.query.filter_by(
        user_id=str(current_user.id),
        is_read=False
    ).count()

    return jsonify({
        "success": True,
        "unread_count": count
    }), 200


# ---------------- MARK AS READ ---------------- #

@app_notification_bp.route(
    "/<int:notification_id>/read",
    methods=["PATCH"]
)
@jwt_required
def mark_as_read(notification_id):

    current_user = get_current_actor()

    if not current_user:
        return jsonify({
            "error": "Unauthorized"
        }), 401

    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=str(current_user.id)
    ).first()

    if not notification:
        return jsonify({
            "error": "Notification not found"
        }), 404

    notification.is_read = True

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Notification marked as read"
    }), 200


# ---------------- MARK ALL AS READ ---------------- #

@app_notification_bp.route(
    "/read-all",
    methods=["PATCH"]
)
@jwt_required
def mark_all_as_read():

    current_user = get_current_actor()

    if not current_user:
        return jsonify({
            "error": "Unauthorized"
        }), 401

    notifications = Notification.query.filter_by(
        user_id=str(current_user.id),
        is_read=False
    ).all()

    for notification in notifications:
        notification.is_read = True

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "All notifications marked as read"
    }), 200