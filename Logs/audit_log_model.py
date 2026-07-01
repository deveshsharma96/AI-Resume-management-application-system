from extensions import db
from datetime import datetime

class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(120), nullable=False)   # email or ID
    user_name = db.Column(db.String(120), nullable=False) # name
    user_role = db.Column(db.String(50), nullable=False)  # admin, recruiter, superadmin
    action = db.Column(db.String(200), nullable=False)
    entity_type = db.Column(db.String(100))
    entity_id = db.Column(db.String(50))
    data = db.Column(db.JSON)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
