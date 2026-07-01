
from flask import Blueprint, request, jsonify
from flask import g

from extensions import db

from Candidates.models.candidate import Candidate
from Candidates.models.candidate_visibility import CandidateVisibility
from Candidates.models.candidate_visibility_target import (
    CandidateVisibilityTarget
)

from Organization.models.team_member import TeamMember
from Organization.models.team import Team

from recruiter.models.org_recruiter_model import OrgRecruiter
from recruiter.models.admin_model import Admin

from Organization.models.super_admin import SuperAdmin

from Organization.utils.email_utils import (
    send_candidate_shared_email
)

from GlobalRecruiter.models.organization_recruiter import (
    OrganizationRecruiter
)

from GlobalRecruiter.models.recruiters import (
    GlobalRecruiter
)

from auth.utils.jwt_required import jwt_required

from Candidates.utils.visibility_query import (
    get_visible_candidates_query
)

from Logs.log_helper import create_log


# New candidate auto share settings
from Candidates.services.candidate_share_service import (
    share_candidate_service
)


candidate_visibility_bp = Blueprint(
    "candidate_visibility_bp",
    __name__,
    url_prefix="/api/candidate/sharing"
)


# =====================================================
# HELPER
# =====================================================

def get_current_user():

    if not hasattr(g, "current_user"):
        return None

    return g.current_user


# =====================================================
# SHARE CANDIDATE
# =====================================================

@candidate_visibility_bp.route("/share", methods=["POST"])
@jwt_required
def share_candidate():

    current_user = get_current_user()

    if not current_user:
        return jsonify({
            "error": "Unauthorized"
        }), 401

    data = request.get_json()

    cand_id = data.get("cand_id")
    cand_ids = data.get("cand_ids", [])

    if cand_id:
        cand_ids = [cand_id]

    result = share_candidate_service(
        current_user=current_user,
        cand_ids=cand_ids,
        targets=data.get("targets", []),
        notify=data.get("notify", False),
        target_org_id=data.get("target_org_id")
    )

    if result.get("error"):
        return jsonify(result), 400

    return jsonify(result), 200


# =====================================================
# SEARCH USERS FOR SHARING
# =====================================================

@candidate_visibility_bp.route("/search-users", methods=["GET"])
@jwt_required
def search_users_for_sharing():

    current_user = get_current_user()

    if not current_user:
        return jsonify({
            "error": "Unauthorized"
        }), 401

    org_id = current_user["org_id"]

    q = request.args.get(
        "q",
        ""
    ).strip().lower()

    users = []

    def add_user(u, role):

        if (
            q
            and q not in u.email.lower()
            and q not in u.name.lower()
        ):
            return

        users.append({
            "name": u.name,
            "email": u.email,
            "role": role
        })
        
   
    # -------------------------------------------------
    # SUPER ADMIN
    # -------------------------------------------------

    sa = SuperAdmin.query.filter_by(
        org_id=org_id
    ).first()

    if sa:
        add_user(sa, "superadmin")

    # -------------------------------------------------
    # ADMINS
    # -------------------------------------------------

    admins = Admin.query.filter_by(
        org_id=org_id
    ).all()

    for admin in admins:
        add_user(admin, "admin")

    # -------------------------------------------------
    # RECRUITERS
    # -------------------------------------------------

    recruiters = OrgRecruiter.query.filter_by(
        org_id=org_id
    ).all()

    for recruiter in recruiters:

        tm = TeamMember.query.filter_by(
            user_email=recruiter.email
        ).first()

        if tm:

            team = Team.query.filter_by(
                team_id=tm.team_id,
                org_id=org_id
            ).first()

            # Hide external team recruiters
            if team and team.team_type == "external":
                continue

        add_user(
            recruiter,
            "org_recruiter"
        )

    return jsonify({
        "actor_role": current_user["role"],
        "users": users
    }), 200




