from flask import Blueprint, request, jsonify, g
from auth.utils.jwt_required import jwt_required
from extensions import db

from GlobalRecruiter.models.organization_recruiter import OrganizationRecruiter
from recruiter.models.org_recruiter_model import OrgRecruiter
from Organization.models.team_member import TeamMember
from Logs.log_helper import create_log
from Candidates.models.candidate import Candidate
from Candidates.models.candidate_visibility import CandidateVisibility

recruiter_mgmt_bp = Blueprint("recruiter_mgmt_bp", __name__)

# ----------------------------------------
# DELETE RECRUITER FROM ORGANIZATION
# ----------------------------------------
@recruiter_mgmt_bp.route("/recruiter/delete", methods=["DELETE"])
@jwt_required
def delete_recruiter():

    actor_role = g.current_user["role"]
    org_id = g.current_user["org_id"]
    actor_email = g.current_user["user_id"]

    # 🔐 Only superadmin allowed (recommended)
    if actor_role != "superadmin":
        return jsonify({"error": "Only superadmin can remove recruiters"}), 403

    data = request.get_json()
    recruiter_id = data.get("recruiter_id")

    if not recruiter_id:
        return jsonify({"error": "recruiter_id is required"}), 400

    # ----------------------------------------
    # FIND MAPPING
    # ----------------------------------------
    mapping = OrganizationRecruiter.query.filter_by(
        recruiter_id=recruiter_id,
        org_id=org_id
    ).first()

    if not mapping:
        return jsonify({"error": "Recruiter not part of this organization"}), 404

    if mapping.status == "DISABLED":
        return jsonify({"error": "Recruiter already removed"}), 400

    # ----------------------------------------
    # GET ORG RECRUITER PROFILE
    # ----------------------------------------
    org_recruiter = OrgRecruiter.query.filter_by(
        global_recruiter_id=recruiter_id,
        org_id=org_id
    ).first()

    # ----------------------------------------
    # REMOVE FROM TEAM
    # ----------------------------------------
    if org_recruiter:

        # ----------------------------------------
        # EXPIRED/PENDING INVITE DELETE
        # ----------------------------------------
        if not org_recruiter.is_onboarding_completed:
            org_recruiter.invite_status = "DELETED"

        TeamMember.query.filter_by(
            user_email=org_recruiter.email
        ).delete()

    # ----------------------------------------
    # HANDLE CASES (SAFE LOGIC)
    # ----------------------------------------
    recruiter_type = (mapping.recruiter_type or "").upper()

    if recruiter_type == "EXTERNAL":
        # ----------------------------------------
        # REMOVE CANDIDATE VISIBILITY (EXTERNAL ONLY)
        # ----------------------------------------
        if org_recruiter:

            recruiter_email = org_recruiter.email

            # 1️⃣ Remove org-level visibility
            CandidateVisibility.query.filter(
                CandidateVisibility.shared_by_email == recruiter_email,
                CandidateVisibility.org_id == org_id,
                CandidateVisibility.visibility_type == "organization"
            ).delete()

            # 2️⃣ Cleanup candidate org reference (fallback)
            Candidate.query.filter(
                Candidate.added_by == recruiter_email,
                Candidate.org_id == org_id
            ).update({
                "org_id": None
            })

        # Check if recruiter is INTERNAL anywhere else
        internal_mapping = OrganizationRecruiter.query.filter(
            OrganizationRecruiter.recruiter_id == recruiter_id,
            db.func.upper(
                OrganizationRecruiter.recruiter_type
            ) == "INTERNAL",
            OrganizationRecruiter.status == "ACTIVE"
        ).first()

        if internal_mapping:
            # ✅ Shared recruiter → just remove mapping
            mapping.status = "DISABLED"

        else:
            # ✅ Standalone external → disable account
            mapping.status = "DISABLED"
            if org_recruiter:
                org_recruiter.is_active = False

    else:
    # ✅ INTERNAL recruiter

        mapping.status = "DISABLED"

        if org_recruiter:

            org_recruiter.is_active = False

            recruiter_email = org_recruiter.email

            # ----------------------------------------
            # MOVE CANDIDATES TO ORG VISIBILITY
            # ----------------------------------------

            visibility_rows = CandidateVisibility.query.filter(
                CandidateVisibility.shared_by_email == recruiter_email,
                CandidateVisibility.org_id == org_id
            ).all()

            for row in visibility_rows:
                row.visibility_type = "organization"
    # ----------------------------------------
    # LOGGING
    # ----------------------------------------
    create_log(
        actor_email,
        action="recruiter_removed",
        entity_type="Recruiter",
        entity_id=recruiter_id,
        data={"org_id": org_id}
    )

    # ----------------------------------------
    # DB COMMIT SAFETY
    # ----------------------------------------
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": "Failed to remove recruiter",
            "details": str(e)
        }), 500

    return jsonify({
        "message": "Recruiter removed successfully"
    }), 200



@recruiter_mgmt_bp.route("/recruiter/restore", methods=["PUT"])
@jwt_required
def restore_recruiter():

    actor_role = g.current_user["role"]
    org_id = g.current_user["org_id"]
    actor_email = g.current_user["user_id"]

    # 🔐 Only superadmin allowed
    if actor_role != "superadmin":
        return jsonify({
            "error": "Only superadmin can restore recruiters"
        }), 403

    data = request.get_json()
    recruiter_id = data.get("recruiter_id")

    if not recruiter_id:
        return jsonify({
            "error": "recruiter_id is required"
        }), 400

    # ----------------------------------------
    # FIND MAPPING
    # ----------------------------------------
    mapping = OrganizationRecruiter.query.filter_by(
        recruiter_id=recruiter_id,
        org_id=org_id
    ).first()

    if not mapping:
        return jsonify({
            "error": "Recruiter not found in this organization"
        }), 404

    if mapping.status == "ACTIVE":
        return jsonify({
            "error": "Recruiter already active"
        }), 400

    # ----------------------------------------
    # GET ORG RECRUITER
    # ----------------------------------------
    org_recruiter = OrgRecruiter.query.filter_by(
        global_recruiter_id=recruiter_id,
        org_id=org_id
    ).first()

    # ----------------------------------------
    # RESTORE MAPPING
    # ----------------------------------------
    mapping.status = "ACTIVE"

    # ----------------------------------------
    # RESTORE RECRUITER ACCOUNT
    # ----------------------------------------
    if org_recruiter:
        org_recruiter.is_active = True

        recruiter_email = org_recruiter.email

        recruiter_type = (mapping.recruiter_type or "").upper()

        # ----------------------------------------
        # INTERNAL RECRUITER
        # Restore previous visibility
        # ----------------------------------------
        if recruiter_type == "INTERNAL":

            visibility_rows = CandidateVisibility.query.filter(
                CandidateVisibility.shared_by_email == recruiter_email,
                CandidateVisibility.org_id == org_id,
                CandidateVisibility.visibility_type == "organization"
            ).all()

            for row in visibility_rows:
                row.visibility_type = "private"

        # ----------------------------------------
        # EXTERNAL RECRUITER
        # Restore org ownership
        # ----------------------------------------
        elif recruiter_type == "EXTERNAL":

            Candidate.query.filter(
                Candidate.added_by == recruiter_email
            ).update({
                "org_id": org_id
            })

    # ----------------------------------------
    # LOGGING
    # ----------------------------------------
    create_log(
        actor_email,
        action="recruiter_restored",
        entity_type="Recruiter",
        entity_id=recruiter_id,
        data={"org_id": org_id}
    )

    # ----------------------------------------
    # DB COMMIT
    # ----------------------------------------
    try:
        db.session.commit()

    except Exception as e:
        db.session.rollback()

        return jsonify({
            "error": "Failed to restore recruiter",
            "details": str(e)
        }), 500

    return jsonify({
        "message": "Recruiter restored successfully"
    }), 200


@recruiter_mgmt_bp.route("/recruiters/list", methods=["GET"])
@jwt_required
def list_recruiters():

    actor_role = g.current_user["role"]
    org_id = g.current_user["org_id"]

    # ----------------------------------------
    # ONLY SUPERADMIN
    # ----------------------------------------
    if actor_role != "superadmin":
        return jsonify({
            "error": "Only superadmin can view recruiters"
        }), 403

    # ----------------------------------------
    # GET ALL RECRUITERS OF THIS ORG
    # ----------------------------------------
    mappings = OrganizationRecruiter.query.filter_by(
        org_id=org_id
    ).all()

    recruiters_data = []

    for mapping in mappings:

        # ----------------------------------------
        # GET ORG RECRUITER PROFILE
        # ----------------------------------------
        org_recruiter = OrgRecruiter.query.filter_by(
            global_recruiter_id=mapping.recruiter_id,
            org_id=org_id
        ).first()

        recruiters_data.append({

            "recruiter_id": mapping.recruiter_id,

            "name": (
                org_recruiter.name
                if org_recruiter else None
            ),

            "email": (
                org_recruiter.email
                if org_recruiter else None
            ),

            "phone": (
                org_recruiter.phone
                if org_recruiter else None
            ),

            "status": mapping.status,

            "is_active": (
                org_recruiter.is_active
                if org_recruiter else False
            ),

            "recruiter_type": mapping.recruiter_type,

            "team_id": (
                org_recruiter.team_id
                if org_recruiter else None
            ),

            "team_name": (
                org_recruiter.team_name
                if org_recruiter else None
            ),

            "email_verified": (
                org_recruiter.email_verified
                if org_recruiter else False
            ),

            "phone_verified": (
                org_recruiter.phone_verified
                if org_recruiter else False
            ),

            "is_onboarding_completed": (
                org_recruiter.is_onboarding_completed
                if org_recruiter else False
            )
        })

    # ----------------------------------------
    # RESPONSE
    # ----------------------------------------
    return jsonify({
        "message": "Recruiters fetched successfully",
        "count": len(recruiters_data),
        "data": recruiters_data
    }), 200



