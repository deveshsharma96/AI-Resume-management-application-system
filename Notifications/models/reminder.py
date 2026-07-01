from extensions import db
from datetime import datetime


class Reminder(db.Model):
    __tablename__ = "Reminders"

    id = db.Column(db.Integer, primary_key=True)

    # candidate reference
    candidate_id = db.Column(
        db.String(50),
        nullable=False
    )

    # user who created reminder
    created_by = db.Column(
        db.String(50),
        nullable=False
    )

    # reminder details
    title = db.Column(
        db.String(255),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    reminder_date = db.Column(
        db.DateTime,
        nullable=False
    )

    # reminder status
    is_completed = db.Column(
        db.Boolean,
        default=False
    )

    # prevent duplicate notifications
    notification_sent = db.Column(
        db.Boolean,
        default=False
    )

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
            "candidate_id": self.candidate_id,
            "created_by": self.created_by,
            "title": self.title,
            "description": self.description,
            "reminder_date": self.reminder_date.isoformat() if self.reminder_date else None,
            "is_completed": self.is_completed,
            "notification_sent": self.notification_sent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }