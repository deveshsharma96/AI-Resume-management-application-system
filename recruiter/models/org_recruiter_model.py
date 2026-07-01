from extensions import db
from Organization.models.team import Team
from Organization.models.team_member import TeamMember

class OrgRecruiter(db.Model):
    __tablename__ = "org_recruiter"

    recruiter_id = db.Column(db.Integer, primary_key=True)
    global_recruiter_id = db.Column(
        db.Integer,
        db.ForeignKey("recruiter.recruiter_id"),
        nullable=True
    )
    org_id = db.Column(db.String(255), db.ForeignKey('organizations.org_id'))

    # -------- Personal Details --------
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    team_id = db.Column(db.String(50), db.ForeignKey("teams.team_id", ondelete="SET NULL"), nullable=True)

    dob = db.Column(db.String(20))
    gender = db.Column(db.String(20))

    pending_email = db.Column(db.String(255), nullable=True)
    pending_phone = db.Column(db.String(20), nullable=True)

    # -------- Experience --------
    total_experience = db.Column(db.Float)

    # -------- Current Address --------
    current_full_address = db.Column(db.Text, nullable=True)
    current_location = db.Column(db.JSON, nullable=True)
    current_pincode = db.Column(db.String(10), nullable=True)

    # -------- Permanent Address --------
    same_as_current = db.Column(db.Boolean, default=False)
    permanent_full_address = db.Column(db.Text, nullable=True)
    permanent_location = db.Column(db.JSON, nullable=True)
    permanent_pincode = db.Column(db.String(10), nullable=True)


    password_hash = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)

    # -------- Secondary Emails & Phones --------
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

    # -------- Relationships --------
    documents = db.relationship("Documents", backref="org_recruiter", lazy=True)
    education = db.relationship("EducationRecruiterAdmin", backref="recruiter", lazy=True)
    work_history = db.relationship("WorkHistoryEmployee", backref="recruiter", lazy=True)
    
    # Use uselist=False to make team a single object instead of a list
    team = db.relationship("Team", backref="recruiters", lazy=True, uselist=False)

    # -------- Class / Static Methods --------
    @classmethod
    def find_by_email(cls, email):
        return cls.query.filter_by(email=email).first()

    @staticmethod
    def find_by_email_static(email):
        return OrgRecruiter.query.filter_by(email=email).first()

    @property
    def role(self):
        return "org_recruiter"

    @property
    def user_id(self):
        return self.email

    # -------- Team Info --------
    @property
    def team_name(self):
        """
        Returns the name of the team if assigned, else None
        """
        if self.team_id:
            team_obj = Team.query.get(self.team_id)
            return team_obj.team_name if team_obj else None
        return None

    @property
    def team_members(self):
        """
        Returns a list of members in the same team
        """
        if not self.team_id:
            return []

        members = TeamMember.query.filter_by(team_id=self.team_id).all()
        return [
            {
                "id": m.id,
                "email": m.user_email,
                "role": m.user_role,
                "added_at": m.added_at.isoformat()
            }
            for m in members
        ]
