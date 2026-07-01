from flask import Blueprint, request, jsonify, g
from Organization.models.organization import Organization
from auth.utils.jwt_required import jwt_required
from datetime import datetime
from extensions import db
from GlobalRecruiter.models.organization_recruiter import OrganizationRecruiter
from recruiter.models.org_recruiter_model import OrgRecruiter

org_management_bp = Blueprint("org_management_bp", __name__)

# ----------------------------------------
# VIEW ORGANIZATION DETAILS (Superadmin)
# ----------------------------------------
@org_management_bp.route("/organization/view", methods=["GET"])
@jwt_required
def view_organization():

    # 🔐 Extract user from JWT
    actor_role = g.current_user["role"]
    org_id = g.current_user["org_id"]

    # ❌ Only superadmin allowed
    if actor_role != "superadmin":
        return jsonify({"error": "Only superadmin can view organization details"}), 403

    # ✅ Always take org_id from token (NOT from query)
    org = Organization.query.filter_by(org_id=org_id).first()

    if not org:
        return jsonify({"error": "Organization not found"}), 404

    return jsonify({
        "message": "Organization details fetched successfully",
        "data": {
            "org_id": org.org_id,
            "org_name": org.org_name,
            "email": org.email,
            "phone": org.phone,
            "address": org.address,
            "email_verified": org.email_verified,
            "phone_verified": org.phone_verified,
            "created_at": org.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
    }), 200





@org_management_bp.route("/organization/delete", methods=["DELETE"])
@jwt_required
def delete_organization():

    actor_role = g.current_user["role"]
    org_id = g.current_user["org_id"]
    actor_email = g.current_user["user_id"]

    # 🔐 Only superadmin allowed
    if actor_role != "superadmin":
        return jsonify({
            "error": "Only superadmin can delete organization"
        }), 403

    # ----------------------------------------
    # FIND ORGANIZATION
    # ----------------------------------------
    org = Organization.query.filter_by(
        org_id=org_id
    ).first()

    if not org:
        return jsonify({
            "error": "Organization not found"
        }), 404

    # ----------------------------------------
    # ALREADY DELETED
    # ----------------------------------------
    if org.is_deleted:
        return jsonify({
            "error": "Organization already deleted"
        }), 400

    # ----------------------------------------
    # SOFT DELETE ORGANIZATION
    # ----------------------------------------
    org.is_deleted = True
    org.deleted_at = datetime.utcnow()

    # ----------------------------------------
    # DISABLE ALL RECRUITERS
    # ----------------------------------------
    mappings = OrganizationRecruiter.query.filter_by(
        org_id=org_id
    ).all()

    for mapping in mappings:

        # Disable org mapping
        mapping.status = "DISABLED"

        # Disable recruiter login
        org_recruiter = OrgRecruiter.query.filter_by(
            global_recruiter_id=mapping.recruiter_id,
            org_id=org_id
        ).first()

        if org_recruiter:
            org_recruiter.is_active = False

    # ----------------------------------------
    # COMMIT
    # ----------------------------------------
    try:

        db.session.commit()

    except Exception as e:

        db.session.rollback()

        return jsonify({
            "error": "Failed to delete organization",
            "details": str(e)
        }), 500

    # ----------------------------------------
    # SUCCESS RESPONSE
    # ----------------------------------------
    return jsonify({
        "message": "Organization marked for deletion. It will be permanently deleted after 30 days."
    }), 200


from recruiter.models.admin_model import Admin


@org_management_bp.route("/admins/list", methods=["GET"])
@jwt_required
def list_admins():

    actor_role = g.current_user["role"]
    org_id = g.current_user["org_id"]

    # ----------------------------------------
    # ONLY SUPERADMIN
    # ----------------------------------------
    if actor_role != "superadmin":
        return jsonify({
            "error": "Only superadmin can view admins"
        }), 403

    # ----------------------------------------
    # GET ALL ADMINS OF THIS ORG
    # ----------------------------------------
    admins = Admin.query.filter_by(
        org_id=org_id
    ).all()

    admins_data = []

    for admin in admins:

        admins_data.append({

            "admin_id": admin.admin_id,

            "name": admin.name,

            "email": admin.email,

            "phone": admin.phone,

            "is_active": True,

            "email_verified": admin.email_verified,

            "phone_verified": admin.phone_verified,

            "is_onboarding_completed": admin.is_onboarding_completed,

            "invite_status": admin.invite_status,

            "invite_sent_at": (
                admin.invite_sent_at.strftime("%Y-%m-%d %H:%M:%S")
                if admin.invite_sent_at else None
            ),

            "invite_expiry_at": (
                admin.invite_expiry_at.strftime("%Y-%m-%d %H:%M:%S")
                if admin.invite_expiry_at else None
            )
        })

    # ----------------------------------------
    # RESPONSE
    # ----------------------------------------
    return jsonify({
        "message": "Admins fetched successfully",
        "count": len(admins_data),
        "data": admins_data
    }), 200