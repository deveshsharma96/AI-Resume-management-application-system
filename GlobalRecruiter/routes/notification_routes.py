from flask import Blueprint, request, jsonify
from GlobalRecruiter.services.notification_service import NotificationService
from GlobalRecruiter.models.notification import Notification
from extensions import db

notification_bp = Blueprint("notification_bp", __name__)


# --------------------------------------------------
# 1️⃣ GET NOTIFICATIONS
# --------------------------------------------------
@notification_bp.route("/v2/notifications", methods=["GET"])
def get_notifications():

    org_id = request.args.get("org_id")

    if not org_id:
        return jsonify({"error": "org_id is required"}), 400

    try:
        data = NotificationService.get_notifications(org_id)

        return jsonify({
            "message": "Notifications fetched successfully",
            "data": data
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# --------------------------------------------------
# 2️⃣ MARK SINGLE NOTIFICATION AS READ
# --------------------------------------------------
@notification_bp.route("/v2/notifications/read/<int:notification_id>", methods=["POST"])
def mark_notification_read(notification_id):

    try:
        notif = Notification.query.get(notification_id)

        if not notif:
            return jsonify({"error": "Notification not found"}), 404

        notif.is_read = True
        db.session.commit()

        return jsonify({
            "message": "Notification marked as read"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# --------------------------------------------------
# 3️⃣ MARK ALL AS READ
# --------------------------------------------------
@notification_bp.route("/v2/notifications/read-all", methods=["POST"])
def mark_all_read():

    org_id = request.json.get("org_id")

    if not org_id:
        return jsonify({"error": "org_id is required"}), 400

    try:
        Notification.query.filter_by(
            org_id=org_id,
            is_read=False
        ).update({"is_read": True})

        db.session.commit()

        return jsonify({
            "message": "All notifications marked as read"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400