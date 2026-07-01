from flask import Blueprint, request, jsonify, current_app
from extensions import db

from recruiter.models.hiring_manager_model import HiringManager

from Organization.utils.email_utils import send_hiring_manager_invitation_email
from auth.utils.jwt_required import jwt_required
from flask import g
from jobs.models.job_model import Job

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from common.utils.password_utils import validate_password

from config import Config

from datetime import datetime, timedelta

import jwt
import json


SECRET_KEY = Config.SECRET_KEY

hiring_manager_bp = Blueprint(
    "hiring_manager_bp",
    __name__
)


# ---------------------------------------------------------
# INVITE HIRING MANAGER
# ---------------------------------------------------------
@hiring_manager_bp.route(
    "/superadmin/invite-hiring-manager",
    methods=["POST"]
)
@jwt_required
def invite_hiring_manager():

    try:

        # -------------------------------------------------
        # Parse Request
        # -------------------------------------------------
        try:
            data = request.get_json(force=True)

        except Exception:

            try:
                data = json.loads(
                    request.data.decode("utf-8") or "{}"
                )

            except Exception:
                data = {}

        name = data.get("name")
        email = data.get("email")
        phone = data.get("phone")
        current_user = g.current_user

        org_id = current_user.get("org_id")

        # -------------------------------------------------
        # Validation
        # -------------------------------------------------
        if not all([name, email, phone]):

            return jsonify({
                "error": "Missing required fields"
            }), 400

        # -------------------------------------------------
        # Duplicate Check
        # -------------------------------------------------
        existing_user = HiringManager.query.filter_by(
            email=email,
            org_id=org_id
        ).first()

        # -------------------------------------------------
        # Already Exists
        # -------------------------------------------------
        if existing_user:

            # onboarding already completed
            if existing_user.is_onboarding_completed:

                return jsonify({
                    "error": "Hiring manager already exists"
                }), 400

            # resend invite
            payload = {
                "email": existing_user.email,
                "role": "hiring_manager",
                "org_id": existing_user.org_id,
                "type": "invite",
                "exp": datetime.utcnow() + timedelta(hours=24)
            }

            token = jwt.encode(
                payload,
                SECRET_KEY,
                algorithm="HS256"
            )

            if isinstance(token, bytes):
                token = token.decode()

            try:

                send_hiring_manager_invitation_email(
                    email,
                    token
                )

            except Exception as e:

                current_app.logger.warning(
                    f"Invite resend failed: {e}"
                )

            return jsonify({
                "message": "Invite resent successfully",
                "token": token
            }), 200

        # -------------------------------------------------
        # Create Hiring Manager
        # -------------------------------------------------
        user = HiringManager(
            name=name,
            email=email,
            phone=phone,
            org_id=org_id,

            email_verified=False,
            phone_verified=False,

            is_onboarding_completed=False
        )

        db.session.add(user)
        db.session.commit()

        # -------------------------------------------------
        # Generate Invite Token
        # -------------------------------------------------
        payload = {
            "email": email,
            "role": "hiring_manager",
            "org_id": org_id,
            "type": "invite",
            "exp": datetime.utcnow() + timedelta(hours=24)
        }

        token = jwt.encode(
            payload,
            SECRET_KEY,
            algorithm="HS256"
        )

        if isinstance(token, bytes):
            token = token.decode()

        # -------------------------------------------------
        # Send Invite Email
        # -------------------------------------------------
        try:

            send_hiring_manager_invitation_email(
                email,
                token
            )

        except Exception as e:

            current_app.logger.warning(
                f"Invitation email failed: {e}"
            )

        return jsonify({
            "message": "Invite sent successfully",
            "token": token
        }), 200

    except Exception as e:

        db.session.rollback()

        current_app.logger.exception(
            "Error in invite_hiring_manager"
        )

        return jsonify({
            "error": str(e)
        }), 500


# ---------------------------------------------------------
# VALIDATE TOKEN
# ---------------------------------------------------------
@hiring_manager_bp.route(
    "/hiring-manager/validate-token",
    methods=["GET"]
)
def validate_hiring_manager_token():

    try:

        token = request.args.get("token")

        if not token:

            return jsonify({
                "error": "Token missing"
            }), 400

        # -------------------------------------------------
        # Decode Token
        # -------------------------------------------------
        try:

            decoded = jwt.decode(
                token,
                SECRET_KEY,
                algorithms=["HS256"]
            )

        except jwt.ExpiredSignatureError:

            return jsonify({
                "valid": False,
                "error": "Token expired"
            }), 400

        except jwt.InvalidTokenError:

            return jsonify({
                "valid": False,
                "error": "Invalid token"
            }), 400

        email = decoded.get("email")
        org_id = decoded.get("org_id")

        # -------------------------------------------------
        # Find User
        # -------------------------------------------------
        user = HiringManager.query.filter_by(
            email=email,
            org_id=org_id
        ).first()

        if not user:

            return jsonify({
                "valid": False,
                "error": "User not found"
            }), 404

        # -------------------------------------------------
        # Prefill Data
        # -------------------------------------------------
        prefill = {
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "org_id": user.org_id,
            "is_onboarding_completed":
                user.is_onboarding_completed
        }

        return jsonify({
            "valid": True,
            "data": decoded,
            "prefill": prefill
        }), 200

    except Exception as e:

        current_app.logger.exception(
            "Error in validate_hiring_manager_token"
        )

        return jsonify({
            "error": str(e)
        }), 500


# ---------------------------------------------------------
# COMPLETE REGISTRATION
# ---------------------------------------------------------
@hiring_manager_bp.route(
    "/hiring-manager/complete-registration",
    methods=["POST"]
)
def complete_hiring_manager_registration():

    try:

        # -------------------------------------------------
        # Parse Request
        # -------------------------------------------------
        try:

            data = request.get_json(force=True)

        except Exception:

            try:
                data = json.loads(
                    request.data.decode("utf-8") or "{}"
                )

            except Exception:
                data = {}

        token = data.get("token")

        password = data.get("password")

        confirm_password = data.get(
            "confirm_password"
        )

        if not token:

            return jsonify({
                "error": "Token missing"
            }), 400

        # -------------------------------------------------
        # Decode Token
        # -------------------------------------------------
        try:

            decoded = jwt.decode(
                token,
                SECRET_KEY,
                algorithms=["HS256"]
            )

        except jwt.ExpiredSignatureError:

            return jsonify({
                "error": "Token expired"
            }), 400

        except jwt.InvalidTokenError:

            return jsonify({
                "error": "Invalid token"
            }), 400

        email = decoded.get("email")
        org_id = decoded.get("org_id")

        # -------------------------------------------------
        # Find User
        # -------------------------------------------------
        user = HiringManager.query.filter_by(
            email=email,
            org_id=org_id
        ).first()

        if not user:

            return jsonify({
                "error": "User not found"
            }), 404

        # -------------------------------------------------
        # Password Validation
        # -------------------------------------------------
        if not password or not confirm_password:

            return jsonify({
                "error": "Password is required"
            }), 400

        if password != confirm_password:

            return jsonify({
                "error": "Passwords do not match"
            }), 400

        is_valid, password_error = validate_password(
            password
        )

        if not is_valid:

            return jsonify({
                "error": password_error
            }), 400

        # -------------------------------------------------
        # Update User
        # -------------------------------------------------
        user.password_hash = generate_password_hash(
            password
        )

        user.email_verified = True

        user.is_onboarding_completed = True

        db.session.commit()

        return jsonify({
            "message":
                "Hiring manager registration completed successfully"
        }), 200

    except Exception as e:

        db.session.rollback()

        current_app.logger.exception(
            "Error in complete_hiring_manager_registration"
        )

        return jsonify({
            "error": str(e)
        }), 500
    



# ---------------------------------------------------------
# GET HIRING MANAGERS
# ---------------------------------------------------------
@hiring_manager_bp.route(
    "/hiring-managers",
    methods=["GET"]
)
@jwt_required
def get_hiring_managers():

    current_user = g.current_user

    if not current_user:
        return jsonify({
            "error": "Unauthorized"
        }), 401

    try:

        org_id = current_user.get("org_id")

        # -------------------------------------------------
        # Fetch Hiring Managers
        # -------------------------------------------------
        hiring_managers = (
            HiringManager.query
            .filter_by(org_id=org_id)
            .order_by(HiringManager.created_at.desc())
            .all()
        )

        data = []

        for hm in hiring_managers:

            assigned_jobs_count = Job.query.filter(
                Job.hiring_manager_id == hm.manager_id
            ).count()

            data.append({
                "manager_id": hm.manager_id,
                "name": hm.name,
                "email": hm.email,
                "phone": hm.phone,

                "is_onboarding_completed":
                    hm.is_onboarding_completed,

                "email_verified":
                    hm.email_verified,

                "created_at":
                    hm.created_at,

                "assigned_jobs_count":
                    assigned_jobs_count
            })

        return jsonify({
            "count": len(data),
            "data": data
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500