
import string
import random
from extensions import db

def generate_org_id(length=6):
    chars = string.ascii_lowercase + string.digits
    return "org_" + ''.join(random.choices(chars, k=length))

class Organization(db.Model):
    __tablename__ = 'organizations'

    org_id = db.Column(db.String(20), primary_key=True)  # Random alphanumeric PK
    org_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    address = db.Column(db.String(255), nullable=False)
    email_verified = db.Column(db.Boolean, default=False)
    phone_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime, nullable=True)

    @staticmethod
    def create(data):
        if "org_id" not in data or not data["org_id"]:
            data["org_id"] = generate_org_id()  # auto-generate random org_id

        new_org = Organization(
            org_id=data["org_id"],
            org_name=data["org_name"],
            email=data["email"],
            phone=data["phone"],
            address=data["address"]
        )
        db.session.add(new_org)
        db.session.commit()
        return new_org

    @staticmethod
    def find_by_email(email):
        return Organization.query.filter_by(email=email).first()

    @staticmethod
    def get_all():
        return Organization.query.all()

    @staticmethod
    def get_by_id(org_id):
        return Organization.query.filter_by(org_id=org_id).first()
