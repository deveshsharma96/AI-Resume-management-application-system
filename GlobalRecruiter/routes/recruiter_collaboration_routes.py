
"""
from flask import Blueprint, request, jsonify
from GlobalRecruiter.services.recruiter_sharing_service import RecruiterSharingService

collaboration_bp = Blueprint("collaboration_bp", __name__)


# --------------------------------------------------
# 1️⃣ Request Collaboration
# --------------------------------------------------
@collaboration_bp.route("/v2/collaboration/request", methods=["POST"])
def request_collaboration():

    data = request.get_json() or {}

    source_org = data.get("source_org")
    target_org = data.get("target_org")

    if not source_org or not target_org:
        return jsonify({"error": "Missing organization IDs"}), 400

    if source_org == target_org:
        return jsonify({"error": "Source and target org cannot be same"}), 400

    try:
        RecruiterSharingService.create_collaboration(
            source_org,
            target_org
        )
        return jsonify({"message": "Collaboration request created"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# --------------------------------------------------
# 2️⃣ Accept Collaboration
# --------------------------------------------------
@collaboration_bp.route("/v2/collaboration/accept", methods=["POST"])
def accept_collaboration():

    data = request.get_json() or {}

    source_org = data.get("source_org")
    target_org = data.get("target_org")

    if not source_org or not target_org:
        return jsonify({"error": "Missing organization IDs"}), 400

    try:
        RecruiterSharingService.accept_collaboration(
            source_org,
            target_org
        )
        return jsonify({"message": "Collaboration accepted"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# --------------------------------------------------
# 3️⃣ Share Recruiter
# --------------------------------------------------
@collaboration_bp.route("/v2/collaboration/share", methods=["POST"])
def share_recruiter():

    data = request.get_json() or {}

    recruiter_id = data.get("recruiter_id")
    source_org = data.get("source_org")
    target_org = data.get("target_org")

    if not recruiter_id or not source_org or not target_org:
        return jsonify({"error": "Missing required fields"}), 400

    # Validate recruiter_id is integer
    try:
        recruiter_id = int(recruiter_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid recruiter_id"}), 400

    try:
        RecruiterSharingService.share_internal_recruiter(
            recruiter_id=recruiter_id,
            source_org=source_org,
            target_org=target_org
        )

        return jsonify({
            "message": "Recruiter shared successfully"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@collaboration_bp.route("/v2/collaboration/list", methods=["GET"])
def get_collaborations():

    org_id = request.args.get("org_id")

    if not org_id:
        return jsonify({"error": "org_id is required"}), 400

    try:
        data = RecruiterSharingService.get_collaborations(org_id)

        return jsonify({
            "message": "Collaborations fetched successfully",
            "data": data
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400
    


# --------------------------------------------------
# INCOMING
# --------------------------------------------------
@collaboration_bp.route("/v2/collaboration/incoming", methods=["GET"])
def get_incoming():

    org_id = request.args.get("org_id")

    data = RecruiterSharingService.get_incoming(org_id)

    return jsonify(data), 200


# --------------------------------------------------
# OUTGOING
# --------------------------------------------------
@collaboration_bp.route("/v2/collaboration/outgoing", methods=["GET"])
def get_outgoing():

    org_id = request.args.get("org_id")

    data = RecruiterSharingService.get_outgoing(org_id)

    return jsonify(data), 200


# --------------------------------------------------
# ACTIVE
# --------------------------------------------------
@collaboration_bp.route("/v2/collaboration/list", methods=["GET"])
def get_active():

    org_id = request.args.get("org_id")

    data = RecruiterSharingService.get_active(org_id)

    return jsonify(data), 200


# --------------------------------------------------
# SHARED RECRUITERS
# --------------------------------------------------
@collaboration_bp.route("/v2/collaboration/shared-recruiters", methods=["GET"])
def get_shared_recruiters():

    org_id = request.args.get("org_id")

    data = RecruiterSharingService.get_shared_recruiters(org_id)

    return jsonify(data), 200


# --------------------------------------------------
# REJECT
# --------------------------------------------------
@collaboration_bp.route("/v2/collaboration/reject", methods=["POST"])
def reject():

    data = request.get_json()

    RecruiterSharingService.reject_collaboration(
        data.get("source_org"),
        data.get("target_org")
    )

    return jsonify({"message": "Rejected"}), 200


# --------------------------------------------------
# CANCEL
# --------------------------------------------------
@collaboration_bp.route("/v2/collaboration/cancel", methods=["POST"])
def cancel():

    data = request.get_json()

    RecruiterSharingService.cancel_collaboration(
        data.get("source_org"),
        data.get("target_org")
    )

    return jsonify({"message": "Cancelled"}), 200



"""



from flask import Blueprint, request, jsonify
from GlobalRecruiter.services.recruiter_sharing_service import RecruiterSharingService

collaboration_bp = Blueprint("collaboration_bp", __name__)


# --------------------------------------------------
# 1️⃣ Request Collaboration
# --------------------------------------------------
@collaboration_bp.route("/v2/collaboration/request", methods=["POST"])
def request_collaboration():

    data = request.get_json() or {}

    source_org = data.get("source_org")
    target_org = data.get("target_org")

    if not source_org or not target_org:
        return jsonify({"error": "Missing organization IDs"}), 400

    if source_org == target_org:
        return jsonify({"error": "Source and target org cannot be same"}), 400

    try:
        collab = RecruiterSharingService.create_collaboration(
            source_org,
            target_org
        )

        return jsonify({
            "message": "Collaboration request created",
            "collaboration_id": collab.id   # ✅ added
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# --------------------------------------------------
# 2️⃣ Accept Collaboration (UPDATED)
# --------------------------------------------------
@collaboration_bp.route("/v2/collaboration/accept", methods=["POST"])
def accept_collaboration():

    data = request.get_json() or {}

    # ✅ support both (backward compatible)
    collaboration_id = data.get("collaboration_id")
    source_org = data.get("source_org")
    target_org = data.get("target_org")

    try:
        if collaboration_id:
            RecruiterSharingService.accept_collaboration(collaboration_id)
        else:
            # fallback (old frontend support)
            RecruiterSharingService.accept_collaboration_by_org(
                source_org,
                target_org
            )

        return jsonify({"message": "Collaboration accepted"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# --------------------------------------------------
# 3️⃣ Share Recruiter
# --------------------------------------------------
@collaboration_bp.route("/v2/collaboration/share", methods=["POST"])
def share_recruiter():

    data = request.get_json() or {}

    recruiter_id = data.get("recruiter_id")
    source_org = data.get("source_org")
    target_org = data.get("target_org")

    if not recruiter_id or not source_org or not target_org:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        recruiter_id = int(recruiter_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid recruiter_id"}), 400

    try:
        RecruiterSharingService.share_internal_recruiter(
            recruiter_id=recruiter_id,
            source_org=source_org,
            target_org=target_org
        )

        return jsonify({
            "message": "Recruiter shared successfully"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# --------------------------------------------------
# 4️⃣ LIST (KEEPING ORIGINAL)
# --------------------------------------------------
@collaboration_bp.route("/v2/collaboration/list", methods=["GET"])
def get_collaborations():

    org_id = request.args.get("org_id")

    if not org_id:
        return jsonify({"error": "org_id is required"}), 400

    try:
        data = RecruiterSharingService.get_collaborations(org_id)

        return jsonify({
            "message": "Collaborations fetched successfully",
            "data": data
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# --------------------------------------------------
# INCOMING
# --------------------------------------------------
@collaboration_bp.route("/v2/collaboration/incoming", methods=["GET"])
def get_incoming():

    org_id = request.args.get("org_id")

    if not org_id:
        return jsonify({"error": "org_id is required"}), 400

    data = RecruiterSharingService.get_incoming(org_id)

    return jsonify(data), 200


# --------------------------------------------------
# OUTGOING
# --------------------------------------------------
@collaboration_bp.route("/v2/collaboration/outgoing", methods=["GET"])
def get_outgoing():

    org_id = request.args.get("org_id")

    if not org_id:
        return jsonify({"error": "org_id is required"}), 400

    data = RecruiterSharingService.get_outgoing(org_id)

    return jsonify(data), 200


# --------------------------------------------------
# ACTIVE (KEEPING SAME ROUTE BUT SAFE)
# --------------------------------------------------
@collaboration_bp.route("/v2/collaboration/active", methods=["GET"])
def get_active():

    org_id = request.args.get("org_id")

    if not org_id:
        return jsonify({"error": "org_id is required"}), 400

    data = RecruiterSharingService.get_active(org_id)

    return jsonify(data), 200


# --------------------------------------------------
# SHARED RECRUITERS
# --------------------------------------------------
@collaboration_bp.route("/v2/collaboration/shared-recruiters", methods=["GET"])
def get_shared_recruiters():

    org_id = request.args.get("org_id")

    if not org_id:
        return jsonify({"error": "org_id is required"}), 400

    data = RecruiterSharingService.get_shared_recruiters(org_id)

    return jsonify(data), 200


# --------------------------------------------------
# REJECT (UPDATED)
# --------------------------------------------------
@collaboration_bp.route("/v2/collaboration/reject", methods=["POST"])
def reject():

    data = request.get_json() or {}

    collaboration_id = data.get("collaboration_id")

    try:
        if collaboration_id:
            RecruiterSharingService.reject_collaboration(collaboration_id)
        else:
            RecruiterSharingService.reject_collaboration_by_org(
                data.get("source_org"),
                data.get("target_org")
            )

        return jsonify({"message": "Rejected"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# --------------------------------------------------
# CANCEL (UPDATED)
# --------------------------------------------------
@collaboration_bp.route("/v2/collaboration/cancel", methods=["POST"])
def cancel():

    data = request.get_json() or {}

    collaboration_id = data.get("collaboration_id")

    try:
        if collaboration_id:
            RecruiterSharingService.cancel_collaboration(collaboration_id)
        else:
            RecruiterSharingService.cancel_collaboration_by_org(
                data.get("source_org"),
                data.get("target_org")
            )

        return jsonify({"message": "Cancelled"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400