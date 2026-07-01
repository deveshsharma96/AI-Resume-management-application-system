from extensions import db

class JobSalaryRange(db.Model):
    __tablename__ = "job_salary_ranges"

    id = db.Column(db.Integer, primary_key=True)

    job_id = db.Column(
        db.String(20),
        db.ForeignKey("jobs.job_id"),
        nullable=False,
        unique=True
    )

    min_salary = db.Column(db.Float, nullable=False)
    max_salary = db.Column(db.Float, nullable=False)

    currency = db.Column(db.String(10), default="INR")
    salary_type = db.Column(
        db.String(20),
        default="annual"
    )  # annual / monthly / hourly
