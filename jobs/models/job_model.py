from extensions import db
from datetime import datetime
import string
import random


def generate_job_id(length=12):
    """Generate random job ID."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))

class Job(db.Model):
    __tablename__ = "jobs"

    job_id = db.Column(db.String(20), primary_key=True, default=generate_job_id)
    org_id = db.Column(db.String(50), db.ForeignKey('organizations.org_id'), nullable=False)

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)

    Job_status = db.Column(db.String(20), default="draft")  # draft, published, closed

    location = db.Column(db.String(100))
    work_mode = db.Column(db.Text, nullable=True)
    job_type = db.Column(db.String(50))      

    contract_duration = db.Column(db.String(50), nullable=True)

    job_public_link = db.Column(db.String(255), nullable=True)
    min_notice_period = db.Column(db.String(50), nullable=True)
    max_notice_period = db.Column(db.String(50), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by_type = db.Column(db.String(30), nullable=False, index=True)
    created_by_id = db.Column(db.String(50), nullable=False, index=True)

    hiring_manager_id = db.Column(
        db.String(50),
        nullable=True,
        index=True
    )

    hiring_manager_name = db.Column(
        db.String(255),
        nullable=True
    )
    is_private = db.Column(db.Boolean, default=True, index=True)

    # Relationships
    skill_requirements = db.relationship(
        "JobSkillRequirement",
        uselist=False,
        backref="job",
        cascade="all, delete-orphan"
    )

    experience = db.relationship("JobExperienceRequirement", backref="job", uselist=False, cascade="all, delete-orphan")
    salary = db.relationship(
        "JobSalaryRange",
        backref="job",
        uselist=False,
        cascade="all, delete-orphan"
    )


    journeys = db.relationship(
        "JobCandidateJourney",
        backref="job",
        cascade="all, delete-orphan",
        passive_deletes=True
    )


