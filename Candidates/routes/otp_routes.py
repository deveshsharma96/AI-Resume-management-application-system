# NOTE:
# Phone OTP and phone verification are temporarily disabled.
# Only email OTP verification is active.

from flask import Blueprint, request, jsonify
from extensions import db
from Organization.models.otp import OTP
from datetime import datetime
from Organization.utils.email_utils import send_verification_code
#from Organization.utils.sms_utils import send_sms_code
from common.utils.otp_rate_limiter import check_otp_limit


otp_bp = Blueprint("otp", __name__, url_prefix="/api/otp")


# -----------------------------------------
# SEND EMAIL OTP
# -----------------------------------------

@otp_bp.route("/send-email-otp", methods=["POST"])
def send_email_otp():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    ip_address = request.headers.get(
        "X-Forwarded-For",
        request.remote_addr
    ).split(",")[0].strip()

    if not email:
        return jsonify({"error": "Email is required"}), 400
    
    #  OTP RATE LIMIT CHECK (Candidate Form)
    allowed, error_message = check_otp_limit(
        email=email,
        ip=ip_address,
        otp_type="verification"
    )
    if not allowed:
        return jsonify({
            "error": error_message
        }), 429

    # Generate OTP
    otp = OTP.generate_otp()

    # Save OTP in DB
    OTP.create(
        email=email,
        otp=otp,
        otp_type="verification",
        expiry_minutes=10
    )

    send_verification_code(
        email,
        otp,
        purpose="registration"
    )

    return jsonify({
        "status": "success",
        "message": f"OTP sent to {email}"
    }), 200

"""
# -----------------------------------------
# SEND PHONE OTP
# -----------------------------------------
@otp_bp.route("/send-phone-otp", methods=["POST"])
def send_phone_otp():
    data = request.json
    phone = data.get("phone")

    if not phone:
        return jsonify({"error": "Phone number is required"}), 400

    # Generate OTP
    otp = OTP.generate_otp()

    # Save OTP in DB
    OTP.create(
        phone=phone,
        otp=otp,
        otp_type="verification",
        expiry_minutes=10
    )

    # Send OTP SMS
    send_sms_code(phone, otp)

    return jsonify({
        "status": "success",
        "message": f"OTP sent to {phone}"
    }), 200

"""
# -----------------------------------------
# VERIFY EMAIL OTP
# -----------------------------------------
@otp_bp.route("/verify-email-otp", methods=["POST"])
def verify_email_otp():
    data = request.json
    email = data.get("email")
    otp_code = data.get("otp")

    if not email or not otp_code:
        return jsonify({"error": "Email and OTP are required"}), 400

    success, message = OTP.verify(
        email=email,
        otp=otp_code,
        otp_type="verification"
    )

    if not success:
        return jsonify({"error": message}), 400

    return jsonify({
        "status": "success",
        "message": "Email verified successfully"
    }), 200

"""
# -----------------------------------------
# VERIFY PHONE OTP
# -----------------------------------------
@otp_bp.route("/verify-phone-otp", methods=["POST"])
def verify_phone_otp():
    data = request.json
    phone = data.get("phone")
    otp_code = data.get("otp")

    if not phone or not otp_code:
        return jsonify({"error": "Phone and OTP are required"}), 400

    success, message = OTP.verify(
        phone=phone,
        otp=otp_code,
        otp_type="verification"
    )

    if not success:
        return jsonify({"error": message}), 400

    return jsonify({
        "status": "success",
        "message": "Phone verified successfully"
    }), 200

    """