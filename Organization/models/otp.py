
from extensions import db
import datetime
import random

class OTP(db.Model):
    __tablename__ = "otps"

    id = db.Column(db.Integer, primary_key=True)

    # Candidate or organization (optional)
    org_id = db.Column(db.String(50), nullable=True)
    cand_id = db.Column(db.String(50), nullable=True)

    # Email / Phone linked to this OTP
    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(20), nullable=True)

    # OTP Code
    otp = db.Column(db.String(6), nullable=False)

    otp_type = db.Column(
        db.Enum(
            'registration', 'login', 'verification','email_change',
            'phone_change','reset_password',  # <-- add here
            name='otp_type_enum'
        ),
        nullable=False
    )


    verified = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # -----------------------------------------------------------
    # Generate OTP Code
    # -----------------------------------------------------------
    @staticmethod
    def generate_otp(length=6):
        return ''.join([str(random.randint(0, 9)) for _ in range(length)])

    # -----------------------------------------------------------
    # Create OTP (Email or Phone)
    # -----------------------------------------------------------
    @staticmethod
    def create(email=None, phone=None, otp_type='registration',
               org_id=None, cand_id=None, otp=None, expiry_minutes=5):

        if not otp:
            otp = OTP.generate_otp()

        expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=expiry_minutes)

        new_otp = OTP(
            email=email,
            phone=phone,
            otp=otp,
            otp_type=otp_type,
            org_id=org_id,
            cand_id=cand_id,
            expires_at=expires_at,
            verified=False
        )

        db.session.add(new_otp)
        db.session.commit()

        return new_otp

    # -----------------------------------------------------------
    # Verify OTP
    # -----------------------------------------------------------
    @staticmethod
    def verify(email=None, phone=None, otp=None, otp_type=None):
        if not otp or not otp_type:
            return False, "OTP and OTP type are required"

        query = OTP.query.filter_by(
            otp=otp,
            otp_type=otp_type,
            verified=False
        )

        if email:
            query = query.filter_by(email=email)
        if phone:
            query = query.filter_by(phone=phone)

        record = query.first()

        if not record:
            return False, "Invalid OTP"

        if datetime.datetime.utcnow() > record.expires_at:
            return False, "OTP expired"

        record.verified = True
        db.session.commit()

        return True, "OTP verified"


    # -----------------------------------------------------------
    # Clean expired OTPs
    # -----------------------------------------------------------
    @staticmethod
    def delete_expired():
        now = datetime.datetime.utcnow()
        OTP.query.filter(OTP.expires_at < now).delete()
        db.session.commit()

    # -----------------------------------------------------------
    # Invalidate all OTPs of a given type
    # -----------------------------------------------------------
    @staticmethod
    def invalidate_all(email=None, phone=None, otp_type=None):
        query = OTP.query

        if email:
            query = query.filter_by(email=email)
        if phone:
            query = query.filter_by(phone=phone)
        if otp_type:
            query = query.filter_by(otp_type=otp_type)

        query.update({"verified": True})
        db.session.commit()



       
