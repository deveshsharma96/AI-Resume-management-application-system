from extensions import db
from datetime import datetime
import uuid


class HiringManager(db.Model):
    __tablename__ = "hiring_managers"

    id = db.Column(db.Integer, primary_key=True)

    manager_id = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        default=lambda: f"HM-{uuid.uuid4().hex[:8].upper()}"
    )

    org_id = db.Column(
        db.String(50),
        nullable=False
    )

    name = db.Column(
        db.String(255),
        nullable=False
    )

    email = db.Column(
        db.String(255),
        nullable=False
    )

    phone = db.Column(
        db.String(20)
    )

    password_hash = db.Column(db.Text)

    is_onboarding_completed = db.Column(
        db.Boolean,
        default=False
    )

    email_verified = db.Column(
        db.Boolean,
        default=False
    )

    phone_verified = db.Column(
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


    @property
    def role(self):
        return "hiring_manager"


    @classmethod
    def find_by_email(cls, email):
        return cls.query.filter_by(email=email).first()
    @property
    def user_id(self):
        return self.manager_id