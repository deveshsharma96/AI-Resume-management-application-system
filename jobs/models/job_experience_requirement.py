from extensions import db


class JobExperienceRequirement(db.Model):
    __tablename__ = "job_experience_requirements"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(20), db.ForeignKey("jobs.job_id"), nullable=False, unique=True)

    min_years = db.Column(db.Integer, nullable=False)
    max_years = db.Column(db.Integer, nullable=False)
