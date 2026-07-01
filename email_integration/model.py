from extensions import db
from datetime import datetime


class EmailIntegration(db.Model):
    __tablename__ = "email_integrations"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.String(255), nullable=False)
    org_id = db.Column(db.String(255))

    email = db.Column(db.String(255), nullable=False)
    provider = db.Column(db.String(50), default="google")

    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text)
    sync_interval = db.Column(db.Integer, default=10)  # in minutes

    expires_at = db.Column(db.DateTime)

    # ✅ ADD THIS (for auto sync later)
    last_synced_at = db.Column(db.DateTime)

    # ✅ ADD THIS (enable/disable integration)
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ✅ OPTIONAL BUT IMPORTANT (avoid duplicates)
    __table_args__ = (
        db.UniqueConstraint("user_id", "email", name="unique_user_email"),
    )

    def is_expired(self):
        if not self.expires_at:
            return True
        return datetime.utcnow() >= self.expires_at