# NOTE:
# Phone verification is temporarily disabled.
# Phone numbers are stored but not OTP-verified.

from flask import Blueprint, request, jsonify
from extensions import db
from Organization.models.organization import Organization
from Organization.models.super_admin import SuperAdmin
from Organization.models.otp import OTP
from Organization.utils.email_utils import send_verification_code,send_organization_registration_email
from Logs.log_helper import create_log
import datetime
from recruiter.models.recruiter_model import Recruiter
from common.utils.otp_rate_limiter import check_otp_limit
from sqlalchemy.exc import IntegrityError


organization_bp = Blueprint("organization_bp", __name__)

# ------------------ Helper: Clean expired OTPs ------------------
def cleanup_expired_otps():
    OTP.delete_expired()

# ------------------ Send Email OTP ------------------
@organization_bp.route("/send-otp", methods=["POST"])
def send_otp():
    cleanup_expired_otps()

    data = request.get_json()
    email = data.get("email")
    org_id = data.get("org_id")  # Optional
    otp_type = data.get("otp_type", "registration")

    # 🌐 Get client IP (supports proxy / load balancer)
    ip_address = request.headers.get(
        "X-Forwarded-For",
        request.remote_addr
    )

    if not email:
        return jsonify({"error": "Email is required"}), 400

    email = email.strip().lower()

    # ------------------------------------------------
    # 🔎 EMAIL VALIDATION RULES
    # ------------------------------------------------

    # 1️⃣ Check Recruiter table
    if Recruiter.query.filter_by(email=email).first():
        return jsonify({
            "error": "Email already registered as Recruiter"
        }), 400

    # 2️⃣ Check Organization table
    existing_org = Organization.query.filter_by(email=email).first()
    if existing_org:
        # If updating existing org, allow same org_id
        if not org_id or existing_org.org_id != org_id:
            return jsonify({
                "error": "Email already registered as Organization"
            }), 400

    # 3️⃣ Check SuperAdmin table
    if SuperAdmin.query.filter_by(email=email).first():
        return jsonify({
            "error": "Email already registered as SuperAdmin"
        }), 400

    # ------------------ 🔐 OTP RATE LIMIT CHECK ------------------
    allowed, error_message = check_otp_limit(
        email=email,
        ip=ip_address,
        otp_type=otp_type
    )
    if not allowed:
        return jsonify({
            "error": error_message
        }), 429


    # ------------------ Create OTP ------------------
    otp_record = OTP.create(
        email=email,
        otp_type=otp_type,
        expiry_minutes=5
    )

    send_verification_code(
        email,
        otp_record.otp,
        purpose="registration"
    )

    # ------------------ Logging ------------------
    create_log(
        user=None,
        action="send_otp",
        entity_type="Organization",
        entity_id=email,
        data={
            "otp_type": otp_type,
            "ip": ip_address
        }
    )

    return jsonify({
        "message": "OTP sent to email",
        "email": email,
        "expires_in": 300
    }), 200

# ------------------ Verify Email OTP ------------------
@organization_bp.route("/verify-otp", methods=["POST"])
def verify_otp_route():
    data = request.get_json()
    email = data.get("email")
    otp_value = data.get("otp")
    otp_type = data.get("otp_type", "registration")

    if not email or not otp_value:
        return jsonify({"error": "Email and OTP are required"}), 400

    success, message = OTP.verify(email=email, otp=otp_value, otp_type=otp_type)

    # Logging
    create_log(
        user=None,
        action="verify_otp",
        entity_type="SuperAdmin",
        entity_id=email,
        data={"otp_type": otp_type, "success": success}
    )

    status_code = 200 if success else 400
    return jsonify({"message": message}), status_code


# ------------------ Send Phone OTP ------------------
"""

@organization_bp.route("/send-phone-otp", methods=["POST"])
def send_phone_otp():
    cleanup_expired_otps()
    data = request.get_json()
    phone = data.get("phone")
    otp_type = data.get("otp_type", "registration")

    if not phone:
        return jsonify({"error": "Phone number is required"}), 400

    otp_record = OTP.create(phone=phone, otp_type=otp_type, expiry_minutes=5)
    from Organization.utils.sms_utils import send_sms_code
    print(f"[SMS] Sending OTP to {phone}")

    success = send_sms_code(phone, otp_record.otp)

    if not success:
        return jsonify({"error": "Failed to send SMS"}), 500

    # Logging
    create_log(
        user=None,
        action="send_phone_otp",
        entity_type="SuperAdmin",
        entity_id=phone,
        data={"otp_type": otp_type}
    )

    return jsonify({"message": "OTP sent to phone", "expires_in": 300}), 200


# ------------------ Verify Phone OTP ------------------
@organization_bp.route("/verify-phone-otp", methods=["POST"])
def verify_phone_otp_route():
    data = request.get_json()
    phone = data.get("phone")
    otp_value = data.get("otp")
    otp_type = data.get("otp_type", "registration")

    if not phone or not otp_value:
        return jsonify({"error": "Phone and OTP are required"}), 400

    success, message = OTP.verify(phone=phone, otp=otp_value, otp_type=otp_type)

    # Logging
    create_log(
        user=None,
        action="verify_phone_otp",
        entity_type="SuperAdmin",
        entity_id=phone,
        data={"otp_type": otp_type, "success": success}
    )

    status_code = 200 if success else 400
    return jsonify({"message": message}), status_code
    
"""

@organization_bp.route("/register", methods=["POST"])
def register_organization():
    try:
        data = request.get_json(force=True) or {}

        required_fields = ["org_name", "email", "phone", "address"]

        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"{field} is required"}), 400

        email = data["email"].strip().lower()
        phone = data["phone"].strip()

        # ------------------------------------------------
        # ✅ EMAIL OTP VERIFIED CHECK
        # ------------------------------------------------
        email_otp_verified = OTP.query.filter_by(
            email=email,
            verified=True,
            otp_type="registration"
        ).first()

        if not email_otp_verified:
            return jsonify({"error": "Email not verified"}), 400
        
        # Check that phone OTP is verified
        """
        phone_otp_verified = OTP.query.filter_by(
            phone=data["phone"], verified=True, otp_type='registration'
        ).first()
        if not phone_otp_verified:
            return jsonify({"error": "Phone not verified"}), 400
        """

        # ------------------------------------------------
        # 🔎 DUPLICATE EMAIL CHECK
        # ------------------------------------------------
        if Organization.query.filter_by(email=email).first():
            return jsonify({
                "error": "Email already registered as Organization"
            }), 400

        # ------------------------------------------------
        # 📱 DUPLICATE PHONE CHECK  ✅ (THIS IS WHAT YOU NEEDED)
        # ------------------------------------------------
        if Organization.query.filter_by(phone=phone).first():
            return jsonify({
                "error": "Phone number already registered as Organization"
            }), 400

        # Optional cross-table validation (recommended)
        if Recruiter.query.filter_by(phone=phone).first():
            return jsonify({
                "error": "Phone already registered as Recruiter"
            }), 400

        if SuperAdmin.query.filter_by(phone=phone).first():
            return jsonify({
                "error": "Phone already registered as SuperAdmin"
            }), 400

        # ------------------------------------------------
        # 🏢 CREATE ORGANIZATION
        # ------------------------------------------------
        org = Organization.create(data)

        org.email_verified = True
        org.phone_verified = False  # Phone verification disabled

        db.session.commit()

        # ------------------------------------------------
        # 📧 SEND REGISTRATION EMAIL
        # ------------------------------------------------
        try:
            send_organization_registration_email(
                email,
                data["org_name"],
                org.org_id
            )
        except Exception as e:
            print(f"[WARNING] Failed to send registration email: {e}")

        return jsonify({
            "message": "Organization registered successfully",
            "org_id": org.org_id
        }), 201

    except IntegrityError as e:
        db.session.rollback()
        error_msg = str(e.orig)

        if "email" in error_msg:
            return jsonify({"error": "Email already exists"}), 400
        elif "phone" in error_msg:
            return jsonify({"error": "Phone already exists"}), 400
        else:
            return jsonify({"error": "Duplicate entry detected"}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ------------------ Get All Organizations ------------------
@organization_bp.route("/all", methods=["GET"])
def get_all_organizations():
    orgs = Organization.get_all()
    result = [
        {
            "org_id": org.org_id,
            "org_name": org.org_name,
            "email": org.email,
            "phone": org.phone,
            "address": org.address,
            "email_verified": org.email_verified,
            "phone_verified": org.phone_verified,
            "created_at": org.created_at
        } for org in orgs
    ]
    return jsonify(result), 200

