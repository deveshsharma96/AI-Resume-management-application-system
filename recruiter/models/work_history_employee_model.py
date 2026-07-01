from extensions import db

class WorkHistoryEmployee(db.Model):
    __tablename__ = "work_history_employee"

    work_id = db.Column(db.Integer, primary_key=True)
    user_type = db.Column(db.String(20))  # "admin" or "org_recruiter"

    admin_id = db.Column(db.Integer, db.ForeignKey("admins.admin_id"), nullable=True)
    recruiter_id = db.Column(db.Integer, db.ForeignKey("org_recruiter.recruiter_id"), nullable=True)

    # -------- Work History --------
    organization = db.Column(db.String(150))
    org_start_year = db.Column(db.Integer)
    org_end_year = db.Column(db.Integer)


     # NEW FIELDS
    org_start_month = db.Column(db.String(20))   # Ex: "April"
    org_end_month = db.Column(db.String(20))     # Ex: "July"

    # Nested designations stored as JSON (array of designations)
    designations = db.Column(db.JSON)
    # Example:
    # [
    #   {"designation": "Software Engineer", "start_year": 2018, "end_year": 2020, "responsibilities": "Backend APIs"},
    #   {"designation": "Senior Engineer", "start_year": 2020, "end_year": 2022, "responsibilities": "Team lead"}
    # ]
    
