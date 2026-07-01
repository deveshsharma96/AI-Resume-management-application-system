from extensions import db
from datetime import datetime

class JobCandidateJourney(db.Model):
    __tablename__ = "job_candidate_journeys"

    journey_id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(
        db.String(50),
        db.ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False
    )

    cand_id = db.Column(db.String(10), db.ForeignKey("candidates.cand_id"), nullable=False)

    status = db.Column(db.String(50), default="shared")  # journey status
    interview_round = db.Column(db.Integer, default=0)
    interview_sub_round = db.Column(db.Integer, default=0)
    interview_result = db.Column(db.String(50), nullable=True)  # selected/rejected/completed

    added_by = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    visible_to_recruiter = db.Column(db.Boolean, default=True)
    visible_to_candidate = db.Column(db.Boolean, default=False)


    
  