# Organization/models/organization_form_link.py
from extensions import db
import uuid
from datetime import datetime

class OrganizationFormLink(db.Model):
    __tablename__ = "organization_form_links"

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.String(100), db.ForeignKey("organizations.org_id"), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    organization = db.relationship("Organization", backref="form_links")
