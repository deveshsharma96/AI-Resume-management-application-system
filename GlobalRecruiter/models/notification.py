from extensions import db
import datetime


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)

    org_id = db.Column(db.String(100), nullable=False)

    type = db.Column(db.String(50), nullable=False)
    message = db.Column(db.String(255), nullable=False)

    data = db.Column(db.JSON, nullable=True)

    is_read = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)