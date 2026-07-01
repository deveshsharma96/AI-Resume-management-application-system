from extensions import db

class EducationRecruiterAdmin(db.Model):
    __tablename__ = "education_recruiter_admin"

    edu_id = db.Column(db.Integer, primary_key=True)
    user_type = db.Column(db.String(20))  # "admin" or "org_recruiter"

    admin_id = db.Column(db.Integer, db.ForeignKey("admins.admin_id"), nullable=True)
    recruiter_id = db.Column(db.Integer, db.ForeignKey("org_recruiter.recruiter_id"), nullable=True)

    # -------- Education Details --------
    degree = db.Column(db.String(100))       # B.Sc, M.Sc, etc.
    score = db.Column(db.String(20))         # 8.5 CGPA, 85%, etc.
    major = db.Column(db.String(100))
    minor = db.Column(db.String(100))
    start_year = db.Column(db.Integer)
    end_year = db.Column(db.Integer)

    start_month = db.Column(db.String(20))   # Ex: "January"
    end_month = db.Column(db.String(20))     # Ex: "June"


    
