"""

from Organization.models.otp import OTP
from recruiter.models.recruiter_model import Recruiter
from extensions import db

def generate_otp(length=6):
    return OTP.generate_otp(length)

def save_otp(contact, otp_type="registration"):
    
    if "@" in contact:
        return OTP.create(email=contact, otp_type=otp_type).otp
    else:
        return OTP.create(phone=contact, otp_type=otp_type).otp

def verify_otp(contact, otp=None, otp_type="registration"):
    
    if "@" in contact:  # EMAIL
        if otp:
            success, message = OTP.verify(email=contact, otp=otp, otp_type=otp_type)
            if success:
                recruiter = Recruiter.find_by_email(contact)
                if recruiter:
                    recruiter.is_email_verified = True
                    db.session.commit()
            return success, message
        else:
            record = OTP.query.filter_by(email=contact, verified=True, otp_type=otp_type).first()
            return (record is not None, "Email verified" if record else "Email not verified")
    else:  # PHONE
        if otp:
            success, message = OTP.verify(phone=contact, otp=otp, otp_type=otp_type)
            if success:
                recruiter = Recruiter.find_by_phone(contact)
                if recruiter:
                    recruiter.is_phone_verified = True
                    db.session.commit()
            return success, message
        else:
            record = OTP.query.filter_by(phone=contact, verified=True, otp_type=otp_type).first()
            return (record is not None, "Phone verified" if record else "Phone not verified")

def send_sms_otp(phone, otp_value):
    
    print(f"[DEBUG] Sending OTP {otp_value} to phone {phone}")
    # TODO: integrate actual SMS API here
    return True

"""


from Organization.models.otp import OTP
from recruiter.models.recruiter_model import Recruiter
from extensions import db


# -----------------------------------------------------------
# Generate OTP (wrapper)
# -----------------------------------------------------------
def generate_otp(length=6):
    """Generate a numeric OTP of given length."""
    return OTP.generate_otp(length)


# -----------------------------------------------------------
# Save OTP (Email or Phone)
# -----------------------------------------------------------
def save_otp(contact, otp_type="registration"):
    """
    Save OTP for recruiter/admin/org_recruiter flows.

    contact: email or phone
    otp_type: registration | email_change | phone_change | login | verification
    """

    if not contact:
        raise ValueError("Contact is required")

    contact = contact.strip()

    if "@" in contact:
        # Normalize email
        contact = contact.lower()
        otp_record = OTP.create(
            email=contact,
            otp_type=otp_type
        )
        return otp_record.otp
    else:
        # Normalize phone
        otp_record = OTP.create(
            phone=contact,
            otp_type=otp_type
        )
        return otp_record.otp


# -----------------------------------------------------------
# Verify OTP (Email or Phone)
# -----------------------------------------------------------
def verify_otp(contact, otp=None, otp_type="registration"):
    """
    Verify OTP for recruiter/admin/org_recruiter flows.

    IMPORTANT:
    - Auto-verification of recruiter happens ONLY for registration
    - email_change / phone_change just verify OTP, nothing else
    """

    if not contact:
        return False, "Contact is required"

    contact = contact.strip()
    otp = otp.strip() if otp else otp

    # ---------------- EMAIL ----------------
    if "@" in contact:
        contact = contact.lower()

        if otp:
            success, message = OTP.verify(
                email=contact,
                otp=otp,
                otp_type=otp_type
            )

            # Auto-mark recruiter verified ONLY during registration
            if success and otp_type == "registration":
                recruiter = Recruiter.find_by_email(contact)
                if recruiter:
                    recruiter.is_email_verified = True
                    db.session.commit()

            return success, message

        # Check already verified
        record = OTP.query.filter_by(
            email=contact,
            verified=True,
            otp_type=otp_type
        ).first()

        return (
            record is not None,
            "Email verified" if record else "Email not verified"
        )

    # ---------------- PHONE ----------------
    else:
        if otp:
            success, message = OTP.verify(
                phone=contact,
                otp=otp,
                otp_type=otp_type
            )

            # Auto-mark recruiter verified ONLY during registration
            if success and otp_type == "registration":
                recruiter = Recruiter.find_by_phone(contact)
                if recruiter:
                    recruiter.is_phone_verified = True
                    db.session.commit()

            return success, message

        # Check already verified
        record = OTP.query.filter_by(
            phone=contact,
            verified=True,
            otp_type=otp_type
        ).first()

        return (
            record is not None,
            "Phone verified" if record else "Phone not verified"
        )


# -----------------------------------------------------------
# Send SMS OTP (stub)
# -----------------------------------------------------------
def send_sms_otp(phone, otp_value):
    """
    Sends OTP via SMS to the given phone number.
    Replace with actual SMS provider logic.
    """
    print(f"[DEBUG] Sending OTP {otp_value} to phone {phone}")
    return True
