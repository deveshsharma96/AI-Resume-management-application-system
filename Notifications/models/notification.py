from extensions import db
from datetime import datetime


class Notification(db.Model):
    __tablename__ = "Notifications"

    id = db.Column(db.Integer, primary_key=True)

    # receiver user id
    user_id = db.Column(db.String(50), nullable=False)

    # notification content
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)

    # notification type
    notification_type = db.Column(db.String(100), nullable=True)

    # read/unread
    is_read = db.Column(db.Boolean, default=False)

    # optional reference entity
    entity_type = db.Column(db.String(50), nullable=True)
    entity_id = db.Column(db.String(50), nullable=True)

    # frontend redirect url
    action_url = db.Column(db.String(500), nullable=True)

    # extra payload
    extra_data = db.Column(db.JSON, nullable=True)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "message": self.message,
            "notification_type": self.notification_type,
            "is_read": self.is_read,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action_url": self.action_url,
            "extra_data": self.extra_data,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }