from extensions import db
from datetime import datetime


class JobHiringManager(db.Model):

    __tablename__ = "job_hiring_managers"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    job_id = db.Column(
        db.String(50),
        db.ForeignKey(
            "jobs.job_id",
            ondelete="CASCADE"
        ),
        nullable=False
    )

    manager_id = db.Column(
        db.String(50),
        db.ForeignKey(
            "hiring_managers.manager_id",
            ondelete="CASCADE"
        ),
        nullable=False
    )

    assigned_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )