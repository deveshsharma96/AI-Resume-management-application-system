# NOTE:
# Phone verification is temporarily disabled for SuperAdmin.
# Phone numbers are stored but not OTP-verified.

from flask import Blueprint, request, jsonify,current_app
from sqlalchemy.exc import IntegrityError
from extensions import db
from Organization.models.organization import Organization
from Organization.models.otp import OTP
from Organization.models.super_admin import SuperAdmin
from recruiter.models.recruiter_model import Recruiter
from Organization.models.organization_form_link import OrganizationFormLink
from Logs.audit_log_model import AuditLog
from common.utils.password_utils import validate_password
from werkzeug.security import generate_password_hash
import uuid
import json
from datetime import datetime
from auth.utils.jwt_required import jwt_required
from flask import g

super_admin_bp = Blueprint("super_admin_bp", __name__)

# ------------------ Helper: Validate Email Uniqueness ------------------
def validate_superadmin_email(email, org_id=None):
    if Recruiter.query.filter_by(email=email).first():
        return False, "Email already registered as Recruiter"

    org_record = Organization.query.filter_by(email=email).first()
    if org_record:
        if org_id and org_record.org_id == org_id:
            return True, None
        else:
            return False, "Email already registered as Organization"

    if SuperAdmin.query.filter_by(email=email).first():
        return False, "Email already registered as SuperAdmin"

    return True, None


# ------------------ SuperAdmin Registration ------------------
@super_admin_bp.route("/register", methods=["POST"])
def register_super_admin():
    data = request.get_json()
    required_fields = ["name", "email", "phone", "password", "confirm_password", "org_id"]

    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    if data["password"] != data["confirm_password"]:
        return jsonify({"error": "Passwords do not match"}), 400
    # ---------------- Password Strength Validation ----------------
    is_valid, password_error = validate_password(data["password"])
    if not is_valid:
        return jsonify({"error": password_error}), 400


    admin_email = data["email"]
    admin_phone = data["phone"]
    org_id = data["org_id"]

    email_verified = OTP.query.filter_by(email=admin_email, verified=True, otp_type='registration').first()
    if not email_verified:
        return jsonify({"error": "SuperAdmin email not verified"}), 400

    """phone_verified = OTP.query.filter_by(phone=admin_phone, verified=True, otp_type='registration').first()
    if not phone_verified:
        return jsonify({"error": "SuperAdmin phone not verified"}), 400
    """
    is_valid, msg = validate_superadmin_email(admin_email, org_id)
    if not is_valid:
        return jsonify({"error": msg}), 400
    
    
    password_hash = generate_password_hash(data["password"])

    admin = SuperAdmin.create({
        "org_id": org_id,
        "name": data["name"],
        "email": admin_email,
        "phone": admin_phone,
        "password_hash": generate_password_hash(data["password"]),
        "email_verified": True,
        "phone_verified": False
    })

    return jsonify({
        "message": "Super Admin registered successfully",
        "admin_email": admin_email,
        "org_id": org_id
    }), 201
"""

@super_admin_bp.route("/generate-form-link", methods=["POST"])
@jwt_required
def generate_form_link():
    from Logs.log_helper import create_log

    data = request.get_json(silent=True)

    if isinstance(data, str):
        try:
            import json
            data = json.loads(data)
        except:
            return jsonify({"error": "Invalid JSON format"}), 400

    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be JSON object"}), 400

    org_id = data.get("org_id")
    if not org_id:
        return jsonify({"error": "org_id is required"}), 400

    # ---------------------------
    # 🔥 1. Identify logged in SuperAdmin
    # ---------------------------
    superadmin_email = request.headers.get("X-User-Email")

    superadmin = SuperAdmin.query.filter_by(email=superadmin_email).first()

    # If somehow not found, create placeholder for logging (prevents Unknown User)
    if not superadmin:
        superadmin = SuperAdmin(
            name="Unknown User",
            email=superadmin_email,
            role="superadmin"
        )

    # ---------------------------
    #  2. Check existing link
    # ---------------------------
    existing_link = OrganizationFormLink.query.filter_by(org_id=org_id).first()
    frontend_base = f"{current_app.config['FRONTEND_BASE_URL']}/#/candidateform"

    if existing_link:
        form_url = f"{frontend_base}?token={existing_link.token}"

        # Log existing link return
        create_log(
            user=superadmin,
            action="FORM_LINK_ALREADY_EXISTS",
            entity_type="FormLink",
            entity_id=org_id,
            data={
                "token": existing_link.token,
                "org_id": org_id,
                "message": "Existing form link returned",
                "is_active": existing_link.is_active
            }
        )

        return jsonify({
            "message": "Form link already exists",
            "form_link": form_url
        }), 201

    # ---------------------------
    #  3. Create New Link
    # ---------------------------
    new_link = OrganizationFormLink(
        org_id=org_id,
        token=str(uuid.uuid4()),
        is_active=True
    )
    db.session.add(new_link)
    db.session.commit()

    form_url = f"{frontend_base}?token={new_link.token}"

    # Log new link generation
    create_log(
        user=superadmin,
        action="GENERATE_FORM_LINK",
        entity_type="FormLink",
        entity_id=org_id,
        data={
            "token": new_link.token,
            "org_id": org_id,
            "message": "Form link generated",
            "is_active": True
        }
    )

    return jsonify({
        "message": "Form link generated successfully",
        "form_link": form_url
    }), 201


# ------------------ Get Existing Form Link ------------------
@super_admin_bp.route("/get-form-link/<org_id>", methods=["GET"])
@jwt_required
def get_form_link(org_id):
    link = OrganizationFormLink.query.filter_by(org_id=org_id).first()

    if not link:
        return jsonify({"error": "No form link found for this organization"}), 404

    frontend_base = f"{current_app.config['FRONTEND_BASE_URL']}/#/candidateform"
    form_url = f"{frontend_base}?token={link.token}"

    return jsonify({
        "message": "Form link retrieved successfully",
        "form_link": form_url
    }), 200

    
    """
@super_admin_bp.route("/generate-form-link", methods=["POST"])
@jwt_required
def generate_form_link():
    from Logs.log_helper import create_log
    from flask import g
    from recruiter.models.recruiter_model import Recruiter
    import uuid

    data = request.get_json(silent=True)

    if isinstance(data, str):
        try:
            import json
            data = json.loads(data)
        except:
            return jsonify({"error": "Invalid JSON format"}), 400

    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be JSON object"}), 400

    org_id = data.get("org_id")
    if not org_id:
        return jsonify({"error": "org_id is required"}), 400

    # -----------------------------------
    # ✅ AUTHORIZATION (FIXED)
    # -----------------------------------
    current_user = getattr(g, "current_user", None)

    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    user_email = current_user.get("user_id")
    user_role = current_user.get("role")

    if user_role not in ["superadmin", "recruiter"]:
        return jsonify({"error": "Unauthorized"}), 403

    # -----------------------------------
    # ✅ GET USER
    # -----------------------------------
    user = SuperAdmin.query.filter_by(email=user_email).first()

    if not user:
        user = Recruiter.query.filter_by(email=user_email).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    # -----------------------------------
    # CHECK EXISTING LINK
    # -----------------------------------
    existing_link = OrganizationFormLink.query.filter_by(org_id=org_id).first()
    frontend_base = f"{current_app.config['FRONTEND_BASE_URL']}/#/candidateform"

    if existing_link:
        form_url = f"{frontend_base}?token={existing_link.token}"

        create_log(
            user=user,
            action="FORM_LINK_ALREADY_EXISTS",
            entity_type="FormLink",
            entity_id=org_id,
            data={
                "token": existing_link.token,
                "org_id": org_id,
                "message": "Existing form link returned",
                "is_active": existing_link.is_active
            }
        )

        return jsonify({
            "message": "Form link already exists",
            "form_link": form_url
        }), 200

    # -----------------------------------
    # CREATE NEW LINK
    # -----------------------------------
    new_link = OrganizationFormLink(
        org_id=org_id,
        token=str(uuid.uuid4()),
        is_active=True
    )
    db.session.add(new_link)
    db.session.commit()

    form_url = f"{frontend_base}?token={new_link.token}"

    create_log(
        user=user,
        action="GENERATE_FORM_LINK",
        entity_type="FormLink",
        entity_id=org_id,
        data={
            "token": new_link.token,
            "org_id": org_id,
            "message": "Form link generated",
            "is_active": True
        }
    )

    return jsonify({
        "message": "Form link generated successfully",
        "form_link": form_url
    }), 201



@super_admin_bp.route("/get-form-link/<org_id>", methods=["GET"])
@jwt_required
def get_form_link(org_id):
    from flask import g

    current_user = getattr(g, "current_user", None)

    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    user_role = current_user.get("role")

    if user_role not in ["superadmin", "recruiter"]:
        return jsonify({"error": "Unauthorized"}), 403

    link = OrganizationFormLink.query.filter_by(org_id=org_id).first()

    if not link:
        return jsonify({"error": "No form link found for this organization"}), 404

    frontend_base = f"{current_app.config['FRONTEND_BASE_URL']}/#/candidateform"
    form_url = f"{frontend_base}?token={link.token}"

    return jsonify({
        "message": "Form link retrieved successfully",
        "form_link": form_url
    }), 200