# NOTE:
# Phone verification is temporarily disabled.
# Phone numbers are stored but not OTP-verified.


from flask import Blueprint, request, jsonify
from recruiter.models.recruiter_model import Recruiter
from recruiter.utils.otp_utils import save_otp, verify_otp
from Organization.utils.email_utils import send_verification_code
from werkzeug.security import generate_password_hash
from extensions import db
import random, string 
from Logs.log_helper import create_log
from Organization.models.organization import Organization
from Organization.models.organization import Organization
from Organization.models.super_admin import SuperAdmin
from sqlalchemy.exc import IntegrityError

from common.utils.password_utils import validate_password
from common.utils.otp_rate_limiter import check_otp_limit






#New setting for default candidate share 

from flask import g

from GlobalRecruiter.models.recruiter_default_share_target import (
    RecruiterDefaultShareTarget
)

from auth.utils.jwt_required import jwt_required

from Candidates.services.candidate_share_service import (
    share_candidate_service
)

from Candidates.utils.visibility_query import (
    get_visible_candidates_query
)



















recruiter_bp = Blueprint("recruiter_bp", __name__)

# ------------------ Send Email OTP ------------------
@recruiter_bp.route("/send-email-otp", methods=["POST"])
def send_email_otp():
    data = request.get_json()
    email = data.get("email")
    otp_type = data.get("otp_type", "registration")  # default registration

    ip_address=request.headers.get(
        "X-Forwarded-For",
        request.remote_addr
    )

    if not email:
        return jsonify({"error": "Email is required"}), 400

    if Recruiter.email_exists(email):
        return jsonify({"error": "Email already registered as Recruiter"}), 400

    if Organization.find_by_email(email) or SuperAdmin.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered as Organization or SuperAdmin"}), 400
    

    # ---------------- 🔐 OTP RATE LIMIT CHECK ----------------
    allowed, error_message = check_otp_limit(
        email=email,
        ip=ip_address,
        otp_type=otp_type
    )
    if not allowed:
        return jsonify({
            "error": error_message
        }), 429


    otp_value = save_otp(email, otp_type=otp_type)
    
    send_verification_code(
        email,
        otp_value,
        purpose="registration"
    )

    # Logging
    create_log(
        user=None,
        action="send_email_otp",
        entity_type="Recruiter",
        entity_id=email,
        data={"otp_type": otp_type}
    )

    return jsonify({"message": "OTP sent to email", "email": email, "expires_in": 300}), 200


# ------------------ Verify Email OTP ------------------
@recruiter_bp.route("/verify-email-otp", methods=["POST"])
def verify_email_otp():
    data = request.get_json()
    email = data.get("email")
    otp_value = data.get("otp")
    otp_type = data.get("otp_type", "registration")

    if not email or not otp_value:
        return jsonify({"error": "Email and OTP are required"}), 400

    success, message = verify_otp(email, otp_value, otp_type=otp_type)

    
    create_log(
        user=None,
        action="verify_email_otp",
        entity_type="Recruiter",
        entity_id=email,
        data={"otp_type": otp_type, "success": success}
    )

    status = 200 if success else 400
    return jsonify({"message": message}), status

"""
# ------------------ Send Phone OTP ------------------
@recruiter_bp.route("/send-phone-otp", methods=["POST"])
def send_phone_otp():
    data = request.get_json()
    phone = data.get("phone")
    otp_type = data.get("otp_type", "registration")

    if not phone:
        return jsonify({"error": "Phone number is required"}), 400

    otp_value = save_otp(phone, otp_type=otp_type)
    print(f"[DEBUG] OTP sent to phone {phone}: {otp_value}")

    # Logging
    create_log(
        user=None,
        action="send_phone_otp",
        entity_type="Recruiter",
        entity_id=phone,
        data={"otp_type": otp_type}
    )

    return jsonify({"message": "OTP sent to phone", "expires_in": 300}), 200


# ------------------ Verify Phone OTP ------------------
@recruiter_bp.route("/verify-phone-otp", methods=["POST"])
def verify_phone_otp():
    data = request.get_json()
    phone = data.get("phone")
    otp_value = data.get("otp")
    otp_type = data.get("otp_type", "registration")

    if not phone or not otp_value:
        return jsonify({"error": "Phone and OTP are required"}), 400

    success, message = verify_otp(phone, otp_value, otp_type=otp_type)

    # Logging
    create_log(
        user=None,
        action="verify_phone_otp",
        entity_type="Recruiter",
        entity_id=phone,
        data={"otp_type": otp_type, "success": success}
    )

    status = 200 if success else 400
    return jsonify({"message": message}), status

"""
# ------------------ Register Recruiter ------------------

@recruiter_bp.route("/register", methods=["POST"])
def register_recruiter():
    try:
        # ---------------- Parse JSON Safely ----------------
        try:
            data = request.get_json(force=True)
        except Exception:
            return jsonify({"error": "Invalid JSON input"}), 400

        if not isinstance(data, dict):
            return jsonify({"error": "Invalid JSON input"}), 400

        # ---------------- Validate Required Fields ----------------
        required_fields = ["name", "email", "phone", "password", "confirm_password"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"{field} is required"}), 400
            
        email = data["email"].strip().lower()
        phone = data["phone"].strip()

        if data["password"] != data["confirm_password"]:
            return jsonify({"error": "Password and Confirm Password do not match"}), 400
        
        # ---------------- Password Strength Validation ----------------
        is_valid, password_error = validate_password(data["password"])
        if not is_valid:
            return jsonify({"error": password_error}), 400


        # ---------------- Verify OTP ----------------
        email_verified, _ = verify_otp(data["email"], otp=None)
      # phone_verified, _ = verify_otp(data["phone"], otp=None)
        if not email_verified:
            return jsonify({"error": "Email not verified"}), 400
        
        #if not phone_verified:
        #   return jsonify({"error": "Phone not verified"}), 400
        
        # ---------------- Check Duplicates ----------------
        if Recruiter.email_exists(email):
            return jsonify({"error": "Email already registered"}), 400

        if Recruiter.phone_exists(phone):
            return jsonify({"error": "Phone already registered"}), 400

        # Organization table (cross validation)
        if Organization.query.filter_by(phone=phone).first():
            return jsonify({
                "error": "Phone already registered as Organization"
            }), 400

        # SuperAdmin table (cross validation)
        if SuperAdmin.query.filter_by(phone=phone).first():
            return jsonify({
                "error": "Phone already registered as SuperAdmin"
            }), 400

        # ---------------- Generate IDs ----------------
        def generate_rec_id():
            return f"rec_{''.join(random.choices(string.ascii_lowercase + string.digits, k=6))}"

        def generate_org_id():
            return f"org_{''.join(random.choices(string.ascii_lowercase + string.digits, k=6))}"

        rec_id = generate_rec_id()
        while Recruiter.find_by_rec_id(rec_id):
            rec_id = generate_rec_id()

        org_id = generate_org_id()

        # ---------------- Create Organization ----------------
        org = Organization(
            org_id=org_id,
            org_name=f"{data['name']}_org",
            email=f"{rec_id}@dummy.com",
            phone=str(random.randint(1000000000, 9999999999)),
            address="N/A",
            email_verified=False,
            phone_verified=False
        )
        db.session.add(org)
        db.session.commit()  

        # ---------------- Create Recruiter ----------------
        password_hash = generate_password_hash(data["password"])
        recruiter_doc = {
            "rec_id": rec_id,
            "org_id": org_id,
            "name": data["name"],
            "email": data["email"],
            "phone": data["phone"],
            "designation": data.get("designation"),
            "password_hash": password_hash,
            "is_email_verified": True,
            "is_phone_verified": False
        }
        Recruiter.create(recruiter_doc)

        return jsonify({
            "message": "Recruiter registered successfully",
            "rec_id": rec_id,
            "org_id": org_id
        }), 201

    except Exception as e:
        # Catch all unexpected errors
        return jsonify({
            "error": "Registration failed",
            "details": str(e)
        }), 500
    
    
    
    
    

#New setting for default candidate share

@recruiter_bp.route(
    "/default-share-targets",
    methods=["PUT"]
)
@jwt_required
def update_default_share_targets():

    current_user = g.current_user

    if not current_user:
        return jsonify({
            "error": "Unauthorized"
        }), 401

    recruiter_email = current_user["user_id"]

    data = request.get_json()

    targets = data.get("targets", [])

    if targets is None:
        return jsonify({
            "error": "Invalid targets"
        }), 400

    # =====================================
    # CLEAR OLD SETTINGS
    # =====================================

    RecruiterDefaultShareTarget.query.filter_by(
        recruiter_email=recruiter_email
    ).delete()

    # =====================================
    # SAVE NEW SETTINGS
    # =====================================

    for target in targets:

        t_type = target.get("type")
        t_value = target.get("value")

        share_mode = target.get(
            "share_mode",
            "FUTURE_CANDIDATES"
        )

        if not t_type or not t_value:
            continue

        db.session.add(
            RecruiterDefaultShareTarget(
                recruiter_email=recruiter_email,
                target_type=t_type,
                target_value=t_value,
                share_mode=share_mode
            )
        )

        # =====================================
        # SHARE EXISTING CANDIDATES
        # =====================================

        if share_mode == "EXISTING_AND_FUTURE":

            visible_candidates = get_visible_candidates_query(
                current_user,
                current_user["org_id"]
            ).all()

            cand_ids = []

            for candidate in visible_candidates:

                cand_ids.append(candidate.cand_id)

            if cand_ids:

                share_candidate_service(
                    current_user=current_user,
                    cand_ids=cand_ids,
                    targets=[
                        {
                            "type": t_type,
                            "value": t_value
                        }
                    ],
                    notify=False
                )

    db.session.commit()

    return jsonify({
        "message": "Default share targets updated"
    }), 200
    
    
#New default setting for candidate share  
    
@recruiter_bp.route(
    "/default-share-targets",
    methods=["GET"]
)
@jwt_required
def get_default_share_targets():

    current_user = g.current_user

    recruiter_email = current_user["user_id"]

    rows = RecruiterDefaultShareTarget.query.filter_by(
        recruiter_email=recruiter_email
    ).all()

    targets = []

    for row in rows:

        targets.append({
            "type": row.target_type,
            "value": row.target_value,
            "share_mode": row.share_mode
        })

    return jsonify({
        "targets": targets
    }), 200