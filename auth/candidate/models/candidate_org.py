from extensions import db
from datetime import datetime
import uuid

def generate_id():
    return str(uuid.uuid4())

class CandidateOrg(db.Model):
    __tablename__ = "candidate_orgs"

    id = db.Column(db.String(36), primary_key=True, default=generate_id)

    candidate_user_id = db.Column(
        db.String(36),
        db.ForeignKey("candidate_users.user_id"),
        nullable=False
    )
    cand_id = db.Column(
        db.String(50),
        db.ForeignKey("candidates.cand_id"),
        nullable=False
    )

    org_id = db.Column(db.String(50), nullable=False)

    source = db.Column(db.String(50))  # public_form / job_apply / recruiter
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
