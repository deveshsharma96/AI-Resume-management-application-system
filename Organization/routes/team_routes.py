

from flask import Blueprint, request, jsonify
from extensions import db

# Models
from Organization.models.team import Team
from Organization.models.team_member import TeamMember
from Organization.models.super_admin import SuperAdmin
from recruiter.models.admin_model import Admin

# New Global Recruiter Architecture
from GlobalRecruiter.models.recruiters import GlobalRecruiter
from GlobalRecruiter.models.organization_recruiter import OrganizationRecruiter

from Logs.log_helper import create_log
from Candidates.models.candidate import Candidate
from auth.utils.jwt_required import jwt_required
from flask import g

team_bp = Blueprint("team_bp", __name__)

def find_user(email, org_id=None):

    # 1️⃣ SuperAdmin
    super_admin = SuperAdmin.query.filter_by(email=email).first()
    if super_admin:
        return {
            "name": super_admin.name,
            "email": super_admin.email,
            "role": "superadmin"
        }

    # 2️⃣ Admin
    admin = Admin.query.filter_by(email=email).first()
    if admin:
        return {
            "name": admin.name,
            "email": admin.email,
            "role": "admin"
        }

    # 3️⃣ Global Recruiter
    recruiter = GlobalRecruiter.query.filter_by(email=email).first()
    if recruiter:

        if org_id:
            mapping = OrganizationRecruiter.query.filter_by(
                recruiter_id=recruiter.recruiter_id,
                org_id=org_id,
                status="ACTIVE"
            ).first()

            if not mapping:
                return None

            role = "org_recruiter"
            recruiter_type = mapping.recruiter_type.lower()

        else:
            role = "recruiter"

        return {
            "name": recruiter.name,
            "email": recruiter.email,
            "role": "org_recruiter",
            "recruiter_type": recruiter_type
        }

    return {
        "name": recruiter.name,
        "email": recruiter.email,
        "role": "recruiter"
    }



# --------------------------------------------------------
# CREATE TEAM
# --------------------------------------------------------
@team_bp.route("/create-team", methods=["POST"])
@jwt_required
def create_team():

    data = request.get_json()

    team_name = data.get("team_name")
    description = data.get("description", "")
    team_type = data.get("team_type", "internal")

    actor_email = g.current_user["user_id"]
    org_id = g.current_user["org_id"]
    actor_role = g.current_user["role"]

    if not team_name:
        return jsonify({"error": "team_name is required"}), 400

    if team_type not in ["internal", "external"]:
        return jsonify({"error": "team_type must be either internal or external"}), 400

    if actor_role not in ["superadmin", "admin","recruiter"]:
        return jsonify({"error": "Not authorized"}), 403

    team = Team(
        team_name=team_name,
        org_id=org_id,
        created_by=actor_email,
        description=description,
        team_type=team_type
    )

    db.session.add(team)
    db.session.commit()

    create_log(
        actor_email,
        action="team_created",
        entity_type="Team",
        entity_id=team.team_id,
        data={"team_name": team_name, "team_type": team_type}
    )

    return jsonify({
        "message": "Team created successfully",
        "team": team.to_dict()
    }), 201


# --------------------------------------------------------
# GET ALL USERS OF ORG
# --------------------------------------------------------

@team_bp.route("/org-users/<string:org_id>", methods=["GET"])
@jwt_required
def get_org_users(org_id):

    users = []

    # SuperAdmin
    super_admin = SuperAdmin.query.filter_by(org_id=org_id).first()
    if super_admin:
        users.append({
            "name": super_admin.name,
            "email": super_admin.email,
            "role": "superadmin",
            "org_id": org_id
        })

    # Admins
    admins = Admin.query.filter_by(org_id=org_id).all()
    for a in admins:
        users.append({
            "name": a.name,
            "email": a.email,
            "role": "admin",
            "org_id": org_id
        })

    # Recruiters
    mappings = OrganizationRecruiter.query.filter_by(
        org_id=org_id,
        status="ACTIVE"
    ).all()

    for m in mappings:
        recruiter = m.recruiter
        if recruiter:
            users.append({
                "name": recruiter.name,
                "email": recruiter.email,
                "role": "org_recruiter",
                "recruiter_type": m.recruiter_type.lower(),
                "org_id": org_id
            })

    return jsonify({"users": users}), 200


# --------------------------------------------------------
# GET ALL TEAMS
# --------------------------------------------------------
@team_bp.route("/allteams/<string:org_id>", methods=["GET"])
@jwt_required
def get_teams(org_id):

    teams = Team.query.filter_by(org_id=org_id).all()

    return jsonify([team.to_dict() for team in teams]), 200


# --------------------------------------------------------
# GET TEAM DETAILS
# --------------------------------------------------------
@team_bp.route("/team/<string:team_id>", methods=["GET"])
@jwt_required
def get_team_details(team_id):

    team = Team.query.filter_by(team_id=team_id).first()

    if not team:
        return jsonify({"error": "Team not found"}), 404

    members = TeamMember.query.filter_by(team_id=team_id).all()

    return jsonify({
        "team": team.to_dict(),
        "members": [m.to_dict() for m in members]
    }), 200

# --------------------------------------------------------
# ADD TEAM MEMBER
# --------------------------------------------------------
@team_bp.route("/team/add-member", methods=["POST"])
@jwt_required
def add_team_member():

    data = request.get_json()

    team_id = data.get("team_id")
    user_email = data.get("user_email")
    recruiter_id = data.get("recruiter_id")

    actor_email = g.current_user["user_id"]
    org_id = g.current_user["org_id"]

    if not team_id or (not user_email and not recruiter_id):
        return jsonify({
            "error": "team_id and user_email or recruiter_id required"
        }), 400

    team = Team.query.filter_by(team_id=team_id).first()

    if not team:
        return jsonify({"error": "Team not found"}), 404

    added_by_user = find_user(actor_email, org_id)

    if not added_by_user:
        return jsonify({"error": "Unauthorized"}), 403

    # --------------------------------------------------
    # 🔹 HANDLE RECRUITER BY ID OR EMAIL
    # --------------------------------------------------
    if recruiter_id:
        recruiter = GlobalRecruiter.query.get(recruiter_id)

        if not recruiter:
            return jsonify({"error": "Recruiter not found"}), 404

        user_email = recruiter.email
        user_name = recruiter.name

    else:
        user = find_user(user_email, team.org_id)

        if not user:
            return jsonify({"error": "User not active in this organization"}), 404

        user_name = user["name"]

    # --------------------------------------------------
    # 🔹 GET MAPPING (VERY IMPORTANT)
    # --------------------------------------------------
    mapping = OrganizationRecruiter.query.filter_by(
        org_id=team.org_id,
        status="ACTIVE"
    ).join(
        GlobalRecruiter,
        OrganizationRecruiter.recruiter_id == GlobalRecruiter.recruiter_id
    ).filter(
        GlobalRecruiter.email == user_email
    ).first()

    if not mapping:
        return jsonify({
            "error": "Recruiter not part of this organization"
        }), 400

    # --------------------------------------------------
    # 🔥 RULE ENFORCEMENT
    # --------------------------------------------------
    # EXTERNAL recruiter ❌ INTERNAL team
    if mapping.recruiter_type == "EXTERNAL" and team.team_type == "internal":
        return jsonify({
            "error": "External recruiters cannot be added to internal team"
        }), 400

    # --------------------------------------------------
    # 🔹 CHECK IF ALREADY EXISTS
    # --------------------------------------------------
    existing = TeamMember.query.filter_by(
        team_id=team_id,
        user_email=user_email
    ).first()

    if existing:
        return jsonify({"error": "User already a team member"}), 400

    # --------------------------------------------------
    # 🔹 CREATE TEAM MEMBER
    # --------------------------------------------------
    member = TeamMember(
        team_id=team_id,
        user_email=user_email,
        user_role="org_recruiter",
        recruiter_type=mapping.recruiter_type,   # 🔥 correct role from mapping
        user_name=user_name
    )

    db.session.add(member)
    db.session.commit()

    # --------------------------------------------------
    # 🔹 LOGGING
    # --------------------------------------------------
    create_log(
        actor_email,
        action="team_member_added",
        entity_type="Team",
        entity_id=team_id,
        data={"user_added": user_email}
    )

    return jsonify({"message": "Member added successfully"}), 201

# --------------------------------------------------------
# REMOVE TEAM MEMBER
# --------------------------------------------------------
@team_bp.route("/team/remove-member", methods=["POST"])
@jwt_required
def remove_team_member():

    data = request.get_json()

    team_id = data.get("team_id")
    user_email = data.get("user_email")

    actor_email = g.current_user["user_id"]

    if not all([team_id, user_email]):
        return jsonify({"error": "team_id and user_email required"}), 400

    member = TeamMember.query.filter_by(
        team_id=team_id,
        user_email=user_email
    ).first()

    if not member:
        return jsonify({"error": "Member not found"}), 404

    db.session.delete(member)
    db.session.commit()

    create_log(
        actor_email,
        action="team_member_removed",
        entity_type="Team",
        entity_id=team_id,
        data={"user_removed": user_email}
    )

    return jsonify({"message": "Member removed successfully"}), 200


# --------------------------------------------------------
# TEAM CANDIDATES
# --------------------------------------------------------
@team_bp.route("/team-candidates/<string:team_id>", methods=["GET"])
@jwt_required
def get_team_candidates(team_id):

    team = Team.query.filter_by(team_id=team_id).first()

    if not team:
        return jsonify({"error": "Team not found"}), 404

    if team.team_type == "internal":

        candidates = Candidate.query.filter_by(
            org_id=team.org_id
        ).all()

    else:

        candidates = Candidate.query.filter_by(
            added_by_team_id=team_id
        ).all()

    return jsonify({
        "team_id": team_id,
        "team_type": team.team_type,
        "total_candidates": len(candidates),
        "candidates": [c.to_dict() for c in candidates]
    }), 200


# --------------------------------------------------------
# GET MY TEAMS (IMPORTANT)
# --------------------------------------------------------
@team_bp.route("/my-teams", methods=["GET"])
@jwt_required
def get_my_teams():

    user_email = g.current_user["user_id"]
    org_id = g.current_user["org_id"]

    # 🔹 Get all team memberships of this user
    memberships = TeamMember.query.filter_by(
        user_email=user_email
    ).all()

    team_ids = [m.team_id for m in memberships]

    if not team_ids:
        return jsonify([]), 200

    # 🔹 Get only those teams
    teams = Team.query.filter(
        Team.team_id.in_(team_ids),
        Team.org_id == org_id
    ).all()

    return jsonify([team.to_dict() for team in teams]), 200




@team_bp.route("/edit-team/<string:team_id>", methods=["PUT"])
@jwt_required
def edit_team(team_id):

    data = request.get_json()

    team_name = data.get("team_name")
    description = data.get("description")
    team_type = data.get("team_type")

    actor_email = g.current_user["user_id"]
    org_id = g.current_user["org_id"]
    actor_role = g.current_user["role"]

    # ---------------------------
    # 🔐 AUTHORIZATION
    # ---------------------------
    if actor_role not in ["superadmin", "admin", "recruiter"]:
        return jsonify({"error": "Not authorized"}), 403

    # ---------------------------
    # 🔍 FIND TEAM
    # ---------------------------
    team = Team.query.filter_by(team_id=team_id).first()

    if not team:
        return jsonify({"error": "Team not found"}), 404

    # ---------------------------
    # 🔐 ORG VALIDATION
    # ---------------------------
    if team.org_id != org_id:
        return jsonify({"error": "Access denied for this organization"}), 403

    # ---------------------------
    # 🧾 UPDATE FIELDS
    # ---------------------------
    if team_name:
        team.team_name = team_name

    if description is not None:
        team.description = description

    if team_type:
        if team_type not in ["internal", "external"]:
            return jsonify({"error": "team_type must be internal or external"}), 400
        team.team_type = team_type

    db.session.commit()

    # ---------------------------
    # 📝 LOGGING
    # ---------------------------
    create_log(
        actor_email,
        action="team_updated",
        entity_type="Team",
        entity_id=team_id,
        data={
            "team_name": team.team_name,
            "team_type": team.team_type
        }
    )

    return jsonify({
        "message": "Team updated successfully",
        "team": team.to_dict()
    }), 200