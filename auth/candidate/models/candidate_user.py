from extensions import db
from datetime import datetime
import uuid


def generate_candidate_user_id():
    return str(uuid.uuid4())

class CandidateUser(db.Model):
    __tablename__ = "candidate_users"

    user_id = db.Column(
        db.String(36),
        primary_key=True,
        default=generate_candidate_user_id
    )

    # ---------------- Identity ----------------
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)

    # ---------------- Verification ----------------
    email_verified = db.Column(db.Boolean, default=False)
    phone_verified = db.Column(db.Boolean, default=False)

    # ---------------- Auth ----------------
    auth_provider = db.Column(db.String(20))  # otp / google
    is_active = db.Column(db.Boolean, default=True)
    
    # New Candidate Registration Auth Stores hashed password for secure authentication (no plain text stored)----------------
    password_hash = db.Column(db.String(255), nullable=False)
    
    
    # New Stores additional optional profile details in flexible JSON format
    profile_data = db.Column(db.JSON, nullable=True)

    # ---------------- Meta ----------------
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "email": self.email,
            "phone": self.phone,
            "email_verified": self.email_verified,
            "phone_verified": self.phone_verified,
            "auth_provider": self.auth_provider,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }
