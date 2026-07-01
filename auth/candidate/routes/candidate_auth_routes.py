# ---------------- New Candidate Reguster and Login SEND EMAIL OTP ----------------
from flask import Blueprint, request, jsonify
from extensions import db
from auth.candidate.models.candidate_user import CandidateUser

from Organization.utils.email_utils import send_verification_code
from werkzeug.security import generate_password_hash, check_password_hash
from common.utils.password_utils import validate_password
from Security.jwt_config import generate_candidate_token
from Organization.models.otp import OTP




from datetime import datetime
import uuid


import random
import string

candidate_auth_bp = Blueprint(
    "candidate_auth_bp",
    __name__,
    url_prefix="/auth"
)


# ---------------- REGISTER CANDIDATE ----------------
@candidate_auth_bp.route("/register", methods=["POST"])
def register_candidate():

    data = request.get_json(force=True)

    print("DATA TYPE:", type(data))
    print("DATA:", data)

    if not data or not isinstance(data, dict):
        return jsonify({
            "error": "Invalid JSON body"
        }), 400
    
    
    
    email = (data.get("email") or "").lower().strip()

    required = ["email", "password", "confirm_password", "phone"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    if data["password"] != data["confirm_password"]:
        return jsonify({"error": "Passwords do not match"}), 400

    valid, msg = validate_password(data["password"])
    if not valid:
        return jsonify({"error": msg}), 400

    # Ensure OTP verified
    otp_record = OTP.query.filter_by(
    email=email,
    otp_type="verification",
    verified=1
    ).order_by(OTP.created_at.desc()).first()

    if not otp_record:
        return jsonify({"error": "Email not verified. Please verify OTP first."}), 400

    if otp_record.expires_at < datetime.utcnow():
        return jsonify({"error": "OTP verification expired. Please verify again."}), 400

    if CandidateUser.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 400

    profile_data = data.copy()
    profile_data.pop("password", None)
    profile_data.pop("confirm_password", None)

    new_user = CandidateUser(
        user_id=str(uuid.uuid4()),
        email=email,
        phone=data["phone"],
        password_hash=generate_password_hash(data["password"]),
        email_verified=True,
        is_active=True,
        auth_provider="email_password",
        profile_data=profile_data
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        "message": "Candidate registered successfully"
    }), 201

