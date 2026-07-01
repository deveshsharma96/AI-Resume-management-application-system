from GlobalRecruiter.models.notification import Notification
from extensions import db


class NotificationService:

    @staticmethod
    def create_notification(org_id, type, message, data=None):

        notif = Notification(
            org_id=org_id,
            type=type,
            message=message,
            data=data or {}
        )

        db.session.add(notif)
        db.session.commit()

        return notif


    @staticmethod
    def get_notifications(org_id):

        records = Notification.query.filter_by(
            org_id=org_id
        ).order_by(Notification.created_at.desc()).limit(50).all()

        result = []

        for r in records:
            result.append({
                "id": r.id,
                "type": r.type,
                "message": r.message,
                "data": r.data,
                "created_at": str(r.created_at),
                "is_read": r.is_read
            })

        return result