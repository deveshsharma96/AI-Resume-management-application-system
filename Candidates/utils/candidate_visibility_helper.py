# Candidates/utils/candidate_visibility_helper.py
"""
from extensions import db
from Candidates.models.candidate_visibility import CandidateVisibility
from Candidates.models.candidate_visibility_target import CandidateVisibilityTarget
from Organization.models.team_member import TeamMember
from Organization.models.team import Team


def create_default_candidate_visibility(cand_id, creator_user):
    creator_email = creator_user.email
    org_id = getattr(creator_user, "org_id", None)

    team_mapping = TeamMember.query.filter_by(
        user_email=creator_email
    ).first()

    owner_team_id = None
    owner_team_type = None

    if team_mapping:
        team = Team.query.filter_by(team_id=team_mapping.team_id).first()
        if team:
            owner_team_id = team.team_id
            owner_team_type = team.team_type  # internal / external

    visibility = CandidateVisibility(
        cand_id=cand_id,
        shared_by_email=creator_email,
        owner_id=creator_email,
        org_id=org_id,
        owner_team_id=owner_team_id,
        owner_team_type=owner_team_type,
        visibility_type="private"
    )

    db.session.add(visibility)
    db.session.flush()

    # ✅ Creator always sees
    creator_target = CandidateVisibilityTarget(
        visibility_id=visibility.id,
        target_type="user",
        target_id=creator_email
    )
    db.session.add(creator_target)

    # ✅ External team → auto team visibility
    if owner_team_type == "external" and owner_team_id:
        team_target = CandidateVisibilityTarget(
            visibility_id=visibility.id,
            target_type="team",
            target_id=owner_team_id
        )
        db.session.add(team_target)

    db.session.commit()
    return visibility
"""


from extensions import db
from Candidates.models.candidate_visibility import CandidateVisibility
from Candidates.models.candidate_visibility_target import CandidateVisibilityTarget
from Organization.models.team_member import TeamMember
from Organization.models.team import Team
def create_default_candidate_visibility(
    cand_id,
    creator_user=None,
    org_id=None,
    source="system"
):
    owner_team_id = None
    owner_team_type = None

    # ---------------- CASE 1: Logged-in user ----------------
    if creator_user:

        # ✅ SAFE ACCESS (dict + ORM compatible)
        if isinstance(creator_user, dict):
            creator_email = creator_user.get("email") or creator_user.get("user_id")
            org_id = creator_user.get("org_id", org_id)
        else:
            creator_email = creator_user.email
            org_id = getattr(creator_user, "org_id", org_id)

        # ---------------- TEAM MAPPING ----------------
        team_mapping = TeamMember.query.filter_by(
            user_email=creator_email
        ).first()

        if team_mapping:
            team = Team.query.filter_by(team_id=team_mapping.team_id).first()
            if team:
                owner_team_id = team.team_id
                owner_team_type = team.team_type

        # ---------------- VISIBILITY ----------------
        visibility = CandidateVisibility(
            cand_id=cand_id,
            shared_by_email=creator_email,
            owner_id=creator_email,
            org_id=org_id,
            owner_team_id=owner_team_id,
            owner_team_type=owner_team_type,
            visibility_type="private"
        )

        db.session.add(visibility)
        db.session.flush()

        # creator sees candidate
        db.session.add(
            CandidateVisibilityTarget(
                visibility_id=visibility.id,
                target_type="user",
                target_id=creator_email
            )
        )

        

    # ---------------- CASE 2: Public Org Form ----------------
    else:
        visibility = CandidateVisibility(
            cand_id=cand_id,
            shared_by_email="system",
            owner_id="system",
            org_id=org_id,
            visibility_type="organization"
        )

        db.session.add(visibility)
        db.session.flush()

    db.session.commit()
    return visibility