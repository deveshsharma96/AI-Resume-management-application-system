

# models/super_admin.py
import string, random
from extensions import db
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

def generate_admin_id(length=6):
    """Generate a random alphanumeric string for admin_id"""
    chars = string.ascii_letters + string.digits
    return "adm_"+''.join(random.choices(chars, k=length))

class SuperAdmin(db.Model):
    __tablename__ = "super_admins"

    admin_id = db.Column(db.String(10), primary_key=True)
    org_id = db.Column(db.String(50), nullable=False) 
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    designation = db.Column(db.String(100), default="")
    password_hash = db.Column(db.String(255), nullable=False)
    email_verified = db.Column(db.Boolean, default=False)
    phone_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    @staticmethod
    def create(data):
        admin_id = generate_admin_id()
        while SuperAdmin.query.filter_by(admin_id=admin_id).first():
            admin_id = generate_admin_id()

        new_admin = SuperAdmin(
            admin_id=admin_id,
            org_id=data.get("org_id"),
            name=data.get("name"),
            email=data.get("email"),
            phone=data.get("phone"),
            designation=data.get("designation", ""),
            password_hash=data.get("password_hash"),  # ✅ ACCEPT HASH
            email_verified=data.get("email_verified", False),
            phone_verified=data.get("phone_verified", False)
        )

        db.session.add(new_admin)
        db.session.commit()
        return new_admin


    @staticmethod
    def find_by_email(email):
        return SuperAdmin.query.filter_by(email=email).first()

    @staticmethod
    def email_exists(email):
        return db.session.query(SuperAdmin.query.filter_by(email=email).exists()).scalar()

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def role(self):
        return "superadmin"
    
    @property
    def user_id(self):
        return self.email

