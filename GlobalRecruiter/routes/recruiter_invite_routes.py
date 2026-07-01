from flask import Blueprint, request, jsonify
from extensions import db
from GlobalRecruiter.models.recruiters import GlobalRecruiter
from GlobalRecruiter.models.organization_recruiter import OrganizationRecruiter
from GlobalRecruiter.services.recruiter_role_service import RecruiterRoleService


recruiter_v2_bp = Blueprint("recruiter_v2_bp", __name__)

# --------------------------------------------------
# 2️⃣ List Recruiters For Organization
# --------------------------------------------------

@recruiter_v2_bp.route("/v2/org/<org_id>/recruiters", methods=["GET"])
def list_org_recruiters(org_id):

    mappings = OrganizationRecruiter.query.filter_by(
        org_id=org_id,
        status="ACTIVE"
    ).all()

    result = []

    for m in mappings:

        recruiter = m.recruiter

        if not recruiter:
            continue

        if m.recruiter_type == "INTERNAL":
            recruiter_type = "INTERNAL"

        elif m.status == "INVITED":
            recruiter_type = "INVITED"

        elif m.recruiter_type == "EXTERNAL":
            recruiter_type = "SHARED"

        else:
            recruiter_type = "UNKNOWN"

        result.append({
            "recruiter_id": recruiter.recruiter_id,
            "name": recruiter.name,
            "email": recruiter.email,
            "phone": recruiter.phone,
            "role": "org_recruiter",
            "recruiter_type": m.recruiter_type,
            "type": recruiter_type,

            # 🔥 Optional (future-ready for collaboration tracking)
            "source_org": m.org_id
        })

    return jsonify(result), 200


# --------------------------------------------------
# 3️⃣ Remove Recruiter From Organization
# --------------------------------------------------

@recruiter_v2_bp.route(
    "/v2/org/<org_id>/recruiter/<int:recruiter_id>",
    methods=["DELETE"]
)
def remove_recruiter_from_org(org_id, recruiter_id):

    mapping = OrganizationRecruiter.query.filter_by(
        recruiter_id=recruiter_id,
        org_id=org_id,
        status="ACTIVE"
    ).first()

    if not mapping:
        return jsonify({
            "error": "Recruiter not found in this organization"
        }), 404

    # ❌ Internal recruiters cannot be removed
    if mapping.recruiter_type == "INTERNAL":
        return jsonify({
            "error": "Cannot remove INTERNAL recruiter"
        }), 400

    # ❌ Shared recruiters cannot be removed directly
    if mapping.recruiter_type == "EXTERNAL" and mapping.status == "ACTIVE":
        return jsonify({
            "error": "Shared recruiters cannot be removed directly"
        }), 400

    try:
        # Soft delete invited recruiter
        mapping.status = "DISABLED"

        db.session.commit()

        return jsonify({
            "message": "Recruiter disabled in organization"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400