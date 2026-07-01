
"""
from extensions import db
from datetime import datetime

class JobCandidate(db.Model):
    __tablename__ = "job_candidates"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(20), db.ForeignKey("jobs.job_id"), nullable=False)
    cand_id = db.Column(db.String(10), db.ForeignKey("candidates.cand_id"), nullable=False)

    status = db.Column(db.String(50), default="submitted")  # submitted, shortlisted, rejected, hired
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    candidate = db.relationship("Candidate", backref="job_applications", lazy=True)
    job = db.relationship("Job", backref="candidate_applications", lazy=True)
"""


from extensions import db
from datetime import datetime

class JobCandidate(db.Model):
    __tablename__ = "job_candidates"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(20), db.ForeignKey("jobs.job_id"), nullable=False)
    cand_id = db.Column(db.String(10), db.ForeignKey("candidates.cand_id"), nullable=False)

    # Full ATS status flow
    status = db.Column(
        db.String(50),
        default="submitted"
        # Allowed: submitted, screened, shortlisted, interview_scheduled, interviewed, offered, hired, rejected
    )
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    candidate = db.relationship("Candidate", backref="job_applications", lazy=True)
    job = db.relationship("Job", backref="candidate_applications", lazy=True)
