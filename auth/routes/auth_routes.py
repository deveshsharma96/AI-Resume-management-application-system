


from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from extensions import db
import jwt
import secrets
from datetime import datetime, timedelta
from auth.models.refresh_token import RefreshToken
from config import Config

# Models
from recruiter.models.recruiter_model import Recruiter
from GlobalRecruiter.models.organization_recruiter import OrganizationRecruiter
from Organization.models.super_admin import SuperAdmin
from recruiter.models.org_recruiter_model import OrgRecruiter
from recruiter.models.admin_model import Admin
from Organization.models.team_member import TeamMember
from Organization.models.team import Team
from Organization.models.organization import Organization
from recruiter.models.hiring_manager_model import HiringManager

# Email & OTP
from recruiter.utils.email_utils import send_verification_code as send_recruiter_otp
from Organization.utils.email_utils import send_verification_code as send_superadmin_otp
from Organization.models.otp import OTP
from common.utils.otp_rate_limiter import check_otp_limit

# Logging
from Logs.log_helper import create_log

auth_bp = Blueprint("auth_bp", __name__)


# ----------------------------------------------------
# 🔄 Unified user finder
# ----------------------------------------------------
def find_user(email):
    for model in [Recruiter, OrgRecruiter,HiringManager, Admin, SuperAdmin]:
        user = model.find_by_email(email)
        if user:
            return user
    return None


# ----------------------------------------------------
# 🔄 Get team details
# ----------------------------------------------------
def get_team_details(user_email):
    mapping = TeamMember.query.filter_by(user_email=user_email).first()
    if not mapping:
        return None, None

    team = Team.query.filter_by(team_id=mapping.team_id).first()
    if not team:
        return None, None

    return team.team_id, team.team_type


# ----------------------------------------------------
# 🔐 Token Generator
# ----------------------------------------------------
def generate_tokens(user_id, org_id, role,name):

    access_payload = {
        "user_id": user_id,
        "org_id": org_id,
        "name": name, 
        "role": role,
        "type": "access",
        "exp": datetime.utcnow() + timedelta(minutes=15)
    }

    access_token = jwt.encode(
        access_payload,
        Config.SECRET_KEY,
        algorithm="HS256"
    )

    refresh_token_value = secrets.token_urlsafe(64)

    refresh_token = RefreshToken(
        user_id=str(user_id),
        org_id=org_id,
        role=role,
        token=refresh_token_value,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )

    db.session.add(refresh_token)
    db.session.commit()

    return access_token, refresh_token_value

@auth_bp.route("/login-password", methods=["POST"])
def login_password():

    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = find_user(email)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # ----------------------------------------
    # 🚫 BLOCK DISABLED RECRUITER
    # ----------------------------------------
    if hasattr(user, "is_active") and user.is_active is False:
        return jsonify({
            "error": "Your account has been disabled"
        }), 403
    

    # ----------------------------------------
    # 🚫 BLOCK DELETED ORGANIZATION LOGIN
    # ----------------------------------------
    org_id = getattr(user, "org_id", None)

    if org_id:
        org = Organization.query.filter_by(org_id=org_id).first()
        
        if org and org.is_deleted:
            return jsonify({
                "error": "Organization is deactivated. Contact support."
            }), 403

    if not user.password_hash:
        return jsonify({"error": "Password not set"}), 400

    if not check_password_hash(user.password_hash, password):
        create_log(user, "login_password_failed", "User", email)
        return jsonify({"error": "Invalid credentials"}), 400

    create_log(user, "login_password", "User", email)

    # -------------------------------
    # IMPORT MODELS
    # -------------------------------
    from GlobalRecruiter.models.recruiters import GlobalRecruiter
    from recruiter.models.recruiter_model import Recruiter as FreelancerRecruiter

    # -------------------------------
    # GLOBAL RECRUITER LOGIN
    # -------------------------------
    if isinstance(user, GlobalRecruiter):

        mappings = OrganizationRecruiter.query.filter_by(
            recruiter_id=user.recruiter_id,
            status="ACTIVE"
        ).all()

        if not mappings:
            return jsonify({"error": "Recruiter not assigned"}), 403

        internal_mapping = next(
            (m for m in mappings if m.role == "INTERNAL"),
            None
        )

        if not internal_mapping:
            return jsonify({"error": "No INTERNAL org found"}), 403
        
        # ----------------------------------------
        # 🚫 BLOCK DELETED ORGANIZATION (GLOBAL RECRUITER)
        # ----------------------------------------
        org = Organization.query.filter_by(
            org_id=internal_mapping.org_id
        ).first()

        if org and org.is_deleted:
            return jsonify({
                "error": "Organization is deactivated. Contact support."
            }), 403

        access_token, refresh_token = generate_tokens(
            user.email,  # ✅ unified
            internal_mapping.org_id,
            internal_mapping.role,
            user.name
        )

        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": 900,
            "org_id": internal_mapping.org_id,
            "role": internal_mapping.role,
            "name": user.name
        }), 200

    # -------------------------------
    # FREELANCER RECRUITER LOGIN
    # -------------------------------
    elif isinstance(user, FreelancerRecruiter):

        access_token, refresh_token = generate_tokens(
            user.user_id,  # ✅ unified
            user.org_id,
            user.role,
            user.name
        )

        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": 900,
            "org_id": user.org_id,
            "role": user.role,
            "name": user.name
        }), 200
    # -------------------------------
    # HIRING MANAGER LOGIN
    # -------------------------------
    elif isinstance(user, HiringManager):

        access_token, refresh_token = generate_tokens(
            user.manager_id,
            user.org_id,
            user.role,
            user.name
        )

        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": 900,
            "org_id": user.org_id,
            "role": user.role,
            "name": user.name
        }), 200
    # -------------------------------
    # OTHER USERS (ADMIN, SUPERADMIN)
    # -------------------------------
    else:
        # 🔥 BLOCK EXTERNAL RECRUITER WITHOUT TEAM
# ----------------------------------------
        if isinstance(user, OrgRecruiter):

            mapping = OrganizationRecruiter.query.filter_by(
                recruiter_id=user.global_recruiter_id,
                org_id=user.org_id,
                status="ACTIVE"
            ).first()

            if mapping and mapping.recruiter_type == "EXTERNAL":

                team_member = TeamMember.query.filter_by(
                    user_email=user.email
                ).first()

                if not team_member:
                    return jsonify({
                        "error": "Access denied. External recruiter must be in a team."
                    }), 403

        team_id, team_type = get_team_details(email)

        access_token, refresh_token = generate_tokens(
            email,
            getattr(user, "org_id", None),
            user.role,
            getattr(user, "name", None)
        )

        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": 900,
            "org_id": getattr(user, "org_id", None),
            "role": user.role,
            "name": getattr(user, "name", None),
            "team_id": team_id,
            "team_type": team_type
        }), 200

# ----------------------------------------------------
# 🔐 SEND OTP
# ----------------------------------------------------
@auth_bp.route("/send-otp", methods=["POST"])
def send_otp():

    data = request.get_json()
    email = data.get("email")

    ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)

    if not email:
        return jsonify({"error": "Email is required"}), 400

    user = find_user(email)
    if not user:
        return jsonify({"error": "User not found"}), 404

    allowed, error_message = check_otp_limit(
        email=email,
        ip=ip_address,
        otp_type="login"
    )

    if not allowed:
        return jsonify({"error": error_message}), 429

    otp_record = OTP.create(email=email, otp_type="login")

    if isinstance(user, Recruiter):
        send_recruiter_otp(email, otp_record.otp)
    else:
        send_superadmin_otp(email, otp_record.otp)

    create_log(user, "send_otp", "User", email)

    return jsonify({
        "message": "OTP sent successfully",
        "expires_in": 300
    }), 200

@auth_bp.route("/login-otp", methods=["POST"])
def login_otp():

    data = request.get_json()
    email = data.get("email")
    otp_input = data.get("otp")

    if not email or not otp_input:
        return jsonify({"error": "Email and OTP are required"}), 400

    user = find_user(email)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # ----------------------------------------
    # 🚫 BLOCK DISABLED RECRUITER
    # ----------------------------------------
    if hasattr(user, "is_active") and user.is_active is False:
        return jsonify({
            "error": "Your account has been disabled"
        }), 403
    
    org_id = getattr(user, "org_id", None)

    if org_id:
        org = Organization.query.filter_by(org_id=org_id).first()
        
        if org and org.is_deleted:
            return jsonify({
                "error": "Organization is deactivated. Contact support."
            }), 403

    success, message = OTP.verify(email=email, otp=otp_input, otp_type="login")

    if not success:
        create_log(user, "login_otp_failed", "User", email)
        return jsonify({"error": message}), 400

    create_log(user, "login_otp", "User", email)

    from GlobalRecruiter.models.recruiters import GlobalRecruiter
    from recruiter.models.recruiter_model import Recruiter as FreelancerRecruiter

    # -------------------------------
    # GLOBAL RECRUITER LOGIN
    # -------------------------------
    if isinstance(user, GlobalRecruiter):

        mappings = OrganizationRecruiter.query.filter_by(
            recruiter_id=user.recruiter_id,
            status="ACTIVE"
        ).all()

        if not mappings:
            return jsonify({"error": "Recruiter not assigned"}), 403

        internal_mapping = next(
            (m for m in mappings if m.role == "INTERNAL"),
            None
        )

        if not internal_mapping:
            return jsonify({"error": "No INTERNAL org found"}), 403
        
        # ----------------------------------------
        # 🚫 BLOCK DELETED ORGANIZATION (GLOBAL RECRUITER)
        # ----------------------------------------
        org = Organization.query.filter_by(
            org_id=internal_mapping.org_id
        ).first()

        if org and org.is_deleted:
            return jsonify({
                "error": "Organization is deactivated. Contact support."
            }), 403

        access_token, refresh_token = generate_tokens(
            user.email,
            internal_mapping.org_id,
            internal_mapping.role,
            user.name
        )

        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": 900,
            "org_id": internal_mapping.org_id,
            "role": internal_mapping.role,
            "name": user.name
        }), 200

    # -------------------------------
    # FREELANCER RECRUITER LOGIN
    # -------------------------------
    elif isinstance(user, FreelancerRecruiter):

        access_token, refresh_token = generate_tokens(
            user.user_id,
            user.org_id,
            user.role,
            user.name
        )

        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": 900,
            "org_id": user.org_id,
            "role": user.role,
            "name": user.name
        }), 200
    # -------------------------------
    # HIRING MANAGER LOGIN
    # -------------------------------
    elif isinstance(user, HiringManager):

        access_token, refresh_token = generate_tokens(
            user.manager_id,
            user.org_id,
            user.role,
            user.name
        )

        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": 900,
            "org_id": user.org_id,
            "role": user.role,
            "name": user.name
        }), 200
    # -------------------------------
    # OTHER USERS
    # -------------------------------
    else:
        # ----------------------------------------
        # 🔥 BLOCK EXTERNAL RECRUITER WITHOUT TEAM
        # ----------------------------------------
        if isinstance(user, OrgRecruiter):

            mapping = OrganizationRecruiter.query.filter_by(
                recruiter_id=user.global_recruiter_id,
                org_id=user.org_id,
                status="ACTIVE"
            ).first()

            if mapping and mapping.recruiter_type == "EXTERNAL":

                team_member = TeamMember.query.filter_by(
                    user_email=user.email
                ).first()

                if not team_member:
                    return jsonify({
                        "error": "Access denied. External recruiter must be in a team."
                    }), 403

        team_id, team_type = get_team_details(email)

        access_token, refresh_token = generate_tokens(
            email,
            getattr(user, "org_id", None),
            user.role,
            getattr(user, "name", None)
        )

        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": 900,
            "org_id": getattr(user, "org_id", None),
            "role": user.role,
            "name": getattr(user, "name", None),
            "team_id": team_id,
            "team_type": team_type
        }), 200

@auth_bp.route("/refresh-token", methods=["POST"])
def refresh_token():

    data = request.get_json()
    token_value = data.get("refresh_token")

    if not token_value:
        return jsonify({"error": "Refresh token required"}), 400

    token_record = RefreshToken.query.filter_by(
        token=token_value,
        revoked=False
    ).first()

    if not token_record:
        return jsonify({"error": "Invalid refresh token"}), 401

    if token_record.expires_at < datetime.utcnow():
        return jsonify({"error": "Refresh token expired"}), 401

    # -----------------------------------------
    # 1️⃣ Revoke old refresh token
    # -----------------------------------------
    token_record.revoked = True

    # -----------------------------------------
    # 2️⃣ Fetch user (FIX)
    # -----------------------------------------
    user = find_user(token_record.user_id)

    # ----------------------------------------
    # 🚫 BLOCK DELETED ORGANIZATION (REFRESH TOKEN)
    # ----------------------------------------
    org_id = token_record.org_id

    if org_id:
        org = Organization.query.filter_by(org_id=org_id).first()

        if org and org.is_deleted:
            return jsonify({
                "error": "Organization is deactivated. Please login again later."
            }), 403

    # If user is a global recruiter (recruiter_id instead of email)
    if not user:
        user = Recruiter.query.filter(
            (Recruiter.rec_id == token_record.user_id) |
            (Recruiter.email == token_record.user_id)
        ).first()
    # -----------------------------------------
    # 3️⃣ Generate NEW tokens
    # -----------------------------------------
    access_token, new_refresh_token = generate_tokens(
        token_record.user_id,
        token_record.org_id,
        token_record.role,
        getattr(user, "name", None)
    )

    db.session.commit()

    return jsonify({
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "expires_in": 900
    }), 200

# ----------------------------------------------------
# 🚪 LOGOUT
# ----------------------------------------------------
@auth_bp.route("/logout", methods=["POST"])
def logout():

    data = request.get_json()
    token_value = data.get("refresh_token")

    if not token_value:
        return jsonify({"error": "Refresh token required"}), 400

    token_record = RefreshToken.query.filter_by(token=token_value).first()

    if token_record:
        token_record.revoked = True
        db.session.commit()

    return jsonify({"message": "Logged out successfully"}), 200




# ----------------------------------------------------
# 🔐 FORGOT PASSWORD (Send OTP)
# ----------------------------------------------------
@auth_bp.route("/forgot-password/send-otp", methods=["POST"])
def forgot_password_send_otp():

    data = request.get_json()
    email = data.get("email")

    if not email:
        return jsonify({"error": "Email is required"}), 400

    user = find_user(email)
    if not user:
        return jsonify({"error": "User not found"}), 404

    OTP.invalidate_all(email=email, otp_type="reset_password")
    otp_record = OTP.create(email=email, otp_type="reset_password")

    if isinstance(user, Recruiter):
        send_recruiter_otp(email, otp_record.otp, purpose="reset_password")
    else:
        send_superadmin_otp(email, otp_record.otp, purpose="reset_password")

    create_log(user, "forgot_password_send_otp", "User", email)

    return jsonify({
        "message": "OTP sent for password reset",
        "expires_in": 300
    }), 200


# ----------------------------------------------------
# 🔐 RESET PASSWORD
# ----------------------------------------------------
@auth_bp.route("/forgot-password/reset", methods=["POST"])
def forgot_password_reset():

    data = request.get_json()
    email = data.get("email")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")

    if not email or not new_password or not confirm_password:
        return jsonify({"error": "All fields are required"}), 400

    if new_password != confirm_password:
        return jsonify({"error": "Passwords do not match"}), 400

    user = find_user(email)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.password_hash = generate_password_hash(new_password)
    RefreshToken.query.filter_by(
        user_id=str(user.recruiter_id if isinstance(user, Recruiter) else email)
    ).update({"revoked": True})
    db.session.commit()

    OTP.invalidate_all(email=email, otp_type="reset_password")

    create_log(user, "password_reset_success", "User", email)

    return jsonify({
        "message": "Password reset successfully"
    }), 200





# ----------------------------------------------------
# 🔐 VERIFY OTP (Forgot Password)
# ----------------------------------------------------
@auth_bp.route("/forgot-password/verify-otp", methods=["POST"])
def forgot_password_verify_otp():

    data = request.get_json()
    email = data.get("email")
    otp_input = data.get("otp")

    if not email or not otp_input:
        return jsonify({"error": "Email and OTP are required"}), 400

    user = find_user(email)
    if not user:
        return jsonify({"error": "User not found"}), 404

    success, message = OTP.verify(
        email=email,
        otp=otp_input,
        otp_type="reset_password"
    )

    if not success:
        create_log(user, "forgot_password_otp_failed", "User", email)
        return jsonify({"error": message}), 400

    create_log(user, "forgot_password_otp_verified", "User", email)

    return jsonify({
        "message": "OTP verified successfully"
    }), 200