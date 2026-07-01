from extensions import db
from datetime import datetime

class Documents(db.Model):
    __tablename__ = "documents"

    doc_id = db.Column(db.Integer, primary_key=True)

    admin_id = db.Column(
        db.Integer,
        db.ForeignKey("admins.admin_id"),
        nullable=True
    )

    recruiter_id = db.Column(
        db.Integer,
        db.ForeignKey("org_recruiter.recruiter_id"),
        nullable=True
    )

    user_type = db.Column(db.String(20))  # admin / org_recruiter

    # id_proof / address_proof / other
    document_name = db.Column(db.String(50), nullable=False)

    # ✅ Object storage key
    file_key = db.Column(db.String(255), nullable=False)

    # ✅ Metadata
    original_filename = db.Column(db.String(255))
    mime_type = db.Column(db.String(50))
    file_size = db.Column(db.Integer)

    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
