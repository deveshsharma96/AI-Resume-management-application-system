from extensions import db
from datetime import datetime


class DeviceToken(db.Model):
    __tablename__ = "device_tokens"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.String(50),
        nullable=False
    )

    token = db.Column(
        db.Text,
        nullable=False
    )

    platform = db.Column(
        db.String(20),
        nullable=False
    )  # android / ios / web

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )