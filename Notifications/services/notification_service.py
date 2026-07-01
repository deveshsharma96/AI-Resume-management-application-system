from extensions import db

from Notifications.models.notification import Notification


class NotificationService:

    @staticmethod
    def create_notification(
        user_id,
        title,
        message,
        notification_type=None,
        entity_type=None,
        entity_id=None,
        action_url=None,
        extra_data=None
    ):

        try:

            notification = Notification(
                user_id=user_id,
                title=title,
                message=message,
                notification_type=notification_type,
                entity_type=entity_type,
                entity_id=entity_id,
                action_url=action_url,
                extra_data=extra_data
            )

            db.session.add(notification)
            db.session.commit()

            return {
                "success": True,
                "notification": notification.to_dict()
            }

        except Exception as e:

            db.session.rollback()

            return {
                "success": False,
                "error": str(e)
            }