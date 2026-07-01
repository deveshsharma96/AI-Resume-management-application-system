from extensions import db
from datetime import datetime

class RefreshToken(db.Model):

    __tablename__ = "refresh_tokens"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.String(255), nullable=False)
    org_id = db.Column(db.String(100), nullable=True)
    role = db.Column(db.String(50), nullable=True)

    token = db.Column(db.String(500), nullable=False)

    expires_at = db.Column(db.DateTime, nullable=False)

    revoked = db.Column(db.Boolean, default=False)