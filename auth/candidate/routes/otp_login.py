from flask import Blueprint, request, jsonify
from extensions import db


from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from flask import current_app

from auth.candidate.models.candidate_user import CandidateUser
from Organization.models.otp import OTP
from Organization.utils.email_utils import send_verification_code
# from auth.utils.auth_utils import generate_token



#----------- New  LOGIN CANDIDATE ----------------
from werkzeug.security import check_password_hash
from Security.jwt_config import generate_candidate_access_token


# =========================================================
# New Candidate PASSWORD LOGIN
# =========================================================

candidate_password_login_bp = Blueprint(
    "candidate_password_login_bp",
    __name__,
    url_prefix="/api/auth/candidate/login/password"
)

@candidate_password_login_bp.route("/", methods=["POST"])
def login_with_password():

    data = request.get_json() or {}
    email = (data.get("email") or "").lower().strip()
    password = data.get("password")


    if not email or not password:
        return jsonify({
            "status": "error",
            "message": "Email and password are required"
        }), 400

    user = CandidateUser.query.filter_by(
        email=email,
        is_active=True
    ).first()

    if not user:
        return jsonify({
            "status": "error",
            "message": "Account not found"
        }), 404

    if not check_password_hash(user.password_hash, password):
        return jsonify({
            "status": "error",
            "message": "Invalid credentials"
        }), 401

    token = generate_candidate_access_token(user.user_id, user.email)

    return jsonify({
        "status": "success",
        "message": "Login successful",
        "token": token,
        "candidate": {
            "user_id": user.user_id,
            "email": user.email
        }
    }), 200




# =========================================================
# OTP LOGIN
# =========================================================


candidate_otp_bp = Blueprint(
    "candidate_otp_bp",
    __name__,
    url_prefix="/api/auth/candidate/login/otp"
)

# -------------------------------------------------
# 1️⃣ SEND OTP
# -------------------------------------------------
@candidate_otp_bp.route("/send", methods=["POST"])
def send_candidate_otp():
    data = request.get_json(force=True)
    email = data.get("email")

    if not email:
        return jsonify({
            "status": "error",
            "message": "Email is required"
        }), 400

    # Invalidate previous login OTPs
    OTP.invalidate_all(email=email, otp_type="login")

    # Create new OTP
    otp_record = OTP.create(
        email=email,
        otp_type="login",
        expiry_minutes=5
    )

    send_verification_code(
        to_email=email,
        code=otp_record.otp,
        purpose="login"
    )


    return jsonify({
        "status": "success",
        "message": "OTP sent successfully"
    }), 200

@candidate_otp_bp.route("/verify", methods=["POST"])
def verify_candidate_otp():
    data = request.get_json(force=True)
    email = data.get("email")
    otp = data.get("otp")

    if not email or not otp:
        return jsonify({
            "status": "error",
            "message": "Email and OTP are required"
        }), 400

    # 1️⃣ Verify OTP
    is_valid, msg = OTP.verify(
        email=email,
        otp=otp,
        otp_type="login"
    )

    if not is_valid:
        return jsonify({
            "status": "error",
            "message": msg
        }), 401

    # 2️⃣ Check if CandidateUser exists
    candidate = CandidateUser.query.filter_by(email=email).first()

    if not candidate:
        return jsonify({
            "status": "error",
            "message": "Candidate account does not exist. Please apply first."
        }), 404

    # # 3️⃣ Optional: ensure candidate is linked to at least one org
    # from auth.candidate.models.candidate_org import CandidateOrg

    # org_link = CandidateOrg.query.filter_by(
    #     candidate_user_id=candidate.user_id
    # ).first()

    # if not org_link:
    #     return jsonify({
    #         "status": "error",
    #         "message": "Candidate not associated with any organization."
    #     }), 403
    
    
    
    # 3️⃣ News Optional org mapping check
    # Candidate can login even without organization

    from auth.candidate.models.candidate_org import CandidateOrg

    org_link = CandidateOrg.query.filter_by(
        candidate_user_id=candidate.user_id
    ).first()

    candidate_org_id = None

    if org_link:
        candidate_org_id = org_link.organization_id
    
    

    # 4️⃣ Generate login token
    token_payload = {
        "user_id": candidate.user_id,
        "email": candidate.email,
        "role": "candidate"
    }

    # token = generate_candidate_access_token(
    #     candidate.user_id,
    #     candidate.email
    # )
    
    #New
    token = generate_candidate_access_token(
        candidate.user_id,
        candidate.email
    )

    # return jsonify({
    #     "status": "success",
    #     "message": "Login successful",
    #     "token": token,
    #     "candidate": candidate.to_dict()
    # }), 200
    
    
    #New
    return jsonify({
        "status": "success",
        "message": "Login successful",
        "token": token,
        "candidate": {
            **candidate.to_dict(),
            "organization_id": candidate_org_id
        }
    }), 200



@candidate_otp_bp.route("/google", methods=["POST"])
def google_login():

    data = request.get_json(force=True)
    token = data.get("id_token")

    if not token:
        return jsonify({
            "status": "error",
            "message": "Google ID token required"
        }), 400

    try:
        # Verify token with Google
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            current_app.config["GOOGLE_CLIENT_ID"]
        )

        email = idinfo.get("email")

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Invalid Google token"
        }), 401

    # 🔍 Check if candidate exists
    candidate = CandidateUser.query.filter_by(email=email).first()

    if not candidate:
        return jsonify({
            "status": "error",
            "message": "Candidate account does not exist. Please apply first."
        }), 404

    # Optional: Check org mapping
    from auth.candidate.models.candidate_org import CandidateOrg

    org_link = CandidateOrg.query.filter_by(
        candidate_user_id=candidate.user_id
    ).first()

    if not org_link:
        return jsonify({
            "status": "error",
            "message": "Candidate not associated with any organization."
        }), 403

    # Generate your system JWT
    token_payload = {
        "user_id": candidate.user_id,
        "email": candidate.email,
        "role": "candidate"
    }

    system_token = generate_candidate_access_token(
        candidate.user_id,
        candidate.email
    )

    return jsonify({
        "status": "success",
        "message": "Login successful",
        "token": system_token,
        "candidate": candidate.to_dict()
    }), 200