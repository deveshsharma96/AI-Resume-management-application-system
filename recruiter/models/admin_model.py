from extensions import db

class Admin(db.Model):
    __tablename__ = "admins"

    admin_id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.String(50), db.ForeignKey('organizations.org_id'), nullable=False)

    # -------- Personal Details --------
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    dob = db.Column(db.String(20))
    gender = db.Column(db.String(20))

    pending_email = db.Column(db.String(255), nullable=True)
    pending_phone = db.Column(db.String(20), nullable=True)

    # -------- Experience --------
    total_experience = db.Column(db.Float)

    # -------- Current Address --------
    current_full_address = db.Column(db.Text, nullable=True)
    current_location = db.Column(db.JSON, nullable=True)   # ✅ SAME AS RECRUITER
    current_pincode = db.Column(db.String(10), nullable=True)

    # -------- Permanent Address --------
    same_as_current = db.Column(db.Boolean, default=False)
    permanent_full_address = db.Column(db.Text, nullable=True)
    permanent_location = db.Column(db.JSON, nullable=True) # ✅ SAME AS RECRUITER
    permanent_pincode = db.Column(db.String(10), nullable=True)

    password_hash = db.Column(db.String(200))


    email_2 = db.Column(db.String(120), unique=True, nullable=True)
    email_3 = db.Column(db.String(120), unique=True, nullable=True)

    phone_2 = db.Column(db.String(20), unique=True, nullable=True)
    phone_3 = db.Column(db.String(20), unique=True, nullable=True)

    email_verified = db.Column(db.Boolean, default=False)
    email_2_verified = db.Column(db.Boolean, default=False)
    email_3_verified = db.Column(db.Boolean, default=False)

    phone_verified = db.Column(db.Boolean, default=False)
    phone_2_verified = db.Column(db.Boolean, default=False)
    phone_3_verified = db.Column(db.Boolean, default=False)
    is_onboarding_completed = db.Column(db.Boolean, default=False)
    invite_status = db.Column(
        db.String(30),
        default="PENDING"
    )

    invite_sent_at = db.Column(db.DateTime, nullable=True)

    invite_expiry_at = db.Column(db.DateTime, nullable=True)

    invite_attempts = db.Column(db.Integer, default=1)

    documents = db.relationship("Documents", backref="admin", lazy=True)
    education = db.relationship("EducationRecruiterAdmin", backref="admin", lazy=True)
    work_history = db.relationship("WorkHistoryEmployee", backref="admin", lazy=True)

    @classmethod
    def find_by_email(cls, email):
        return cls.query.filter_by(email=email).first()
    
    @property
    def role(self):
        return "admin"
    @staticmethod
    def find_by_email(email):
        return Admin.query.filter_by(email=email).first()
    
    @property
    def user_id(self):
        return self.email
