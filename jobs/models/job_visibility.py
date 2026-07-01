from extensions import db
from datetime import datetime


class JobVisibility(db.Model):
    __tablename__ = "job_visibility"

    id = db.Column(db.Integer, primary_key=True)

    job_id = db.Column(
        db.String(20),
        db.ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    org_id = db.Column(db.String(50), nullable=False, index=True)

    # Owner info (copied from Job for safety + fast querying)
    owner_type = db.Column(db.String(50), nullable=False)
    owner_id = db.Column(db.String(50), nullable=False)

    # Who shared it
    shared_by_type = db.Column(db.String(50), nullable=False)
    shared_by_id = db.Column(db.String(50), nullable=False)

    # private / organization / custom
    visibility_type = db.Column(db.String(20), default="private")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    targets = db.relationship(
        "JobVisibilityTarget",
        backref="visibility",
        cascade="all, delete-orphan",
        lazy=True
    )
