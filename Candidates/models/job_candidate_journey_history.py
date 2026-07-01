# Candidates/models/job_candidate_journey_history.py

from extensions import db
from datetime import datetime


class JobCandidateJourneyHistory(db.Model):
    __tablename__ = "job_candidate_journey_history"

    id = db.Column(db.Integer, primary_key=True)

    journey_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "job_candidate_journeys.journey_id",
            ondelete="CASCADE"
        ),
        nullable=False
    )

    old_status = db.Column(db.String(50))
    new_status = db.Column(db.String(50))

    old_interview_round = db.Column(db.Integer)
    new_interview_round = db.Column(db.Integer)

    old_interview_sub_round = db.Column(db.Integer)
    new_interview_sub_round = db.Column(db.Integer)

    old_interview_result = db.Column(db.String(50))
    new_interview_result = db.Column(db.String(50))

    changed_by = db.Column(db.String(50), nullable=False)

    is_undone = db.Column(
        db.Boolean,
        default=False
    )

    undone_by = db.Column(
        db.String(50),
        nullable=True
    )

    undone_at = db.Column(
        db.DateTime,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )




    