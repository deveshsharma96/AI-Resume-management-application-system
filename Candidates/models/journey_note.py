# Candidates/models/journey_note.py

from extensions import db
from datetime import datetime
class JourneyNote(db.Model):
    __tablename__ = "journey_notes"

    note_id = db.Column(db.Integer, primary_key=True)
    journey_id = db.Column(db.Integer, db.ForeignKey("job_candidate_journeys.journey_id"), nullable=False)
    interview_id = db.Column(db.Integer, db.ForeignKey("interviews.interview_id"), nullable=True)

    stage = db.Column(db.String(100), nullable=True)
    note = db.Column(db.Text, nullable=False)

    created_by = db.Column(db.String(50), nullable=False)  # ✅ ADD THIS

    visible_to_candidate = db.Column(db.Boolean, default=False)
    visible_to_recruiter = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)