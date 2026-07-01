

# recruiter/models/recruiter_model.py
from extensions import db
from datetime import datetime
import string
import random

def generate_rec_id(length=10):
    """Generate a random alphanumeric recruiter ID."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))

class Recruiter(db.Model):
    __tablename__ = 'recruiters'

    rec_id = db.Column('recruiter_id', db.String(10), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    org_id = db.Column('organization_id', db.String(10), db.ForeignKey('organizations.org_id'), nullable=False)
    designation = db.Column(db.String(100), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_email_verified = db.Column('email_verified', db.Boolean, default=False)
    is_phone_verified = db.Column('phone_verified', db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def create(data):
        """Create a new recruiter."""
        recruiter = Recruiter(
            rec_id=data.get("rec_id") or generate_rec_id(),
            org_id=data.get("org_id"),
            name=data.get("name"),
            email=data.get("email"),
            phone=data.get("phone"),
            designation=data.get("designation"),
            password_hash=data.get("password_hash"),
            is_email_verified=data.get("is_email_verified", False),
            is_phone_verified=data.get("is_phone_verified", False),
            created_at=datetime.utcnow()
        )
        db.session.add(recruiter)
        db.session.commit()
        return recruiter

    @staticmethod
    def find_by_rec_id(rec_id):
        return Recruiter.query.filter_by(rec_id=rec_id).first()

    @staticmethod
    def find_by_email(email):
        return Recruiter.query.filter_by(email=email).first()

    @staticmethod
    def find_by_phone(phone):
        return Recruiter.query.filter_by(phone=phone).first()

    @staticmethod
    def email_exists(email):
        return Recruiter.query.filter_by(email=email).first() is not None

    @staticmethod
    def phone_exists(phone):
        return Recruiter.query.filter_by(phone=phone).first() is not None
    
    @property
    def role(self):
        return "recruiter"
    
    @property
    def user_id(self):
        return self.email
