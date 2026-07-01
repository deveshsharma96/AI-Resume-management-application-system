from extensions import db

class JobSkillRequirement(db.Model):
    __tablename__ = "job_skill_requirements"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(
        db.String(20),
        db.ForeignKey("jobs.job_id"),
        nullable=False,
        unique=True  # 🔑 ONE row per job
    )

    mandatory_skills = db.Column(db.Text)   # comma-separated
    optional_skills = db.Column(db.Text)    # comma-separated
