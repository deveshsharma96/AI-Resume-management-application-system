# Candidates/models/interview.py
from extensions import db
from datetime import datetime

class Interview(db.Model):
    __tablename__ = "interviews"

    interview_id = db.Column(db.Integer, primary_key=True)
    journey_id = db.Column(db.Integer, db.ForeignKey("job_candidate_journeys.journey_id"), nullable=False)

    platform = db.Column(db.String(50), nullable=True)
    meeting_link = db.Column(db.Text, nullable=True)




    # round and sub-round are stored to keep in sync with JobCandidateJourney
    interview_round = db.Column(db.Integer, default=0, nullable=False)
    interview_sub_round = db.Column(db.Integer, default=0, nullable=False)



    scheduled_at = db.Column(db.DateTime, nullable=True)   # scheduled datetime (UTC)
    duration_minutes = db.Column(db.Integer, nullable=True) # optional
    interviewer = db.Column(db.String(255), nullable=True)
    location = db.Column(db.String(255), nullable=True)     # could be 'Zoom' or address

    status = db.Column(db.String(50), default="scheduled")  # scheduled, completed, cancelled
    result = db.Column(db.String(50), nullable=True)        # selected/rejected/completed (per round)
    created_by = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationship backref optional (not required)
