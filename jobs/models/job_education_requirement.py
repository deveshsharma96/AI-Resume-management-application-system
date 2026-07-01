from extensions import db


class JobEducationRequirement(db.Model):
    __tablename__ = "job_education_requirements"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(20), db.ForeignKey('jobs.job_id'), nullable=False)

    education_level = db.Column(db.String(100), nullable=False)  
    # Examples: "Bachelor's", "Master's", "Diploma", etc.
