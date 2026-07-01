from extensions import db






class GlobalRecruiter(db.Model):
    __tablename__ = "recruiter"

    recruiter_id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # -------- Global Identity --------
    name = db.Column(db.String(100), nullable=False)

    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)

    password_hash = db.Column(db.String(255))

    # -------- Verification --------
    email_verified = db.Column(db.Boolean, default=False)
    phone_verified = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())

    # -------- Relationships --------
    organizations = db.relationship(
        "OrganizationRecruiter",
        backref="recruiter",
        lazy=True,
        cascade="all, delete-orphan"
    )
    
    
    
    
    

    @classmethod
    def find_by_email(cls, email):
        return cls.query.filter_by(email=email).first()

    def __repr__(self):
        return f"<Recruiter {self.email}>"



    @property
    def user_id(self):
        return self.recruiter_id
    

    