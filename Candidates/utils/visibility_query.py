# Candidates/utils/visibility_query.py

from extensions import db
from Candidates.models.candidate import Candidate
from Candidates.models.candidate_visibility import CandidateVisibility
from Candidates.models.candidate_visibility_target import CandidateVisibilityTarget
from Organization.models.team_member import TeamMember
from Organization.models.team import Team
from recruiter.models.admin_model import Admin
from Organization.models.super_admin import SuperAdmin



def get_visible_candidates_query(user, org_id):

    org_id = str(org_id).strip()

    # ------------------------------------------------
    # Admin / SuperAdmin → see all except blacklisted
    # ------------------------------------------------
    if isinstance(user, dict):

        role = user.get("role")
        
        if role == "hiring_manager":

            from jobs.models.job_hiring_manager import (
                JobHiringManager
            )

            from Candidates.models.job_candidate_journey import (
                JobCandidateJourney
            )

            manager_id = user.get("user_id")

            # --------------------------------------------
            # Assigned Jobs
            # --------------------------------------------
            assigned_jobs_subquery = (
                db.session.query(
                    JobHiringManager.job_id
                )
                .filter(
                    JobHiringManager.manager_id ==
                    manager_id
                )
            )

            # --------------------------------------------
            # Candidates connected to assigned jobs
            # --------------------------------------------
            visible_candidate_ids = (
                db.session.query(
                    JobCandidateJourney.cand_id
                )
                .filter(
                    JobCandidateJourney.job_id.in_(
                        assigned_jobs_subquery
                    )
                )
            )

            return Candidate.query.filter(
                Candidate.org_id == org_id,

                Candidate.cand_id.in_(
                    visible_candidate_ids
                ),

                db.or_(
                    Candidate.is_blacklisted == False,
                    Candidate.is_blacklisted.is_(None)
                )
            )

        if role in ["superadmin", "admin"]:

            return Candidate.query.filter(
                Candidate.org_id == org_id
            ).filter(
                db.or_(
                    Candidate.is_blacklisted == False,
                    Candidate.is_blacklisted.is_(None)
                )
            )

    elif isinstance(user, (SuperAdmin, Admin)):

        return Candidate.query.filter(
            Candidate.org_id == org_id,
            Candidate.is_blacklisted == False
        )

    # ORIGINAL USER ACCESS
    if isinstance(user, dict):
        user_email = user.get("user_id")
    else:
        user_email = user.email

    # ------------------------------------------------
    # ORIGINAL BASE QUERY
    # ------------------------------------------------
    base = Candidate.query.filter(
        Candidate.org_id == org_id
    )

    # ------------------------------------------------
    # Resolve team + type
    # ------------------------------------------------
    team_member = (
        db.session.query(TeamMember)
        .join(Team, Team.team_id == TeamMember.team_id)
        .filter(
            TeamMember.user_email == user_email,
            Team.org_id == org_id
        )
        .first()
    )

    team_id = team_member.team_id if team_member else None
    team_type = team_member.team.team_type if team_member else None

    # ------------------------------------------------
    # Visible via sharing
    # ------------------------------------------------
    visible_ids = (
        db.session.query(CandidateVisibility.cand_id)
        .outerjoin(CandidateVisibilityTarget)
        .filter(
            CandidateVisibility.org_id == org_id,
            db.or_(

                # 👤 Explicit user share
                db.and_(
                    CandidateVisibilityTarget.target_type == "user",
                    CandidateVisibilityTarget.target_id == user_email
                ),

                # 👥 Team share
                db.and_(
                    CandidateVisibilityTarget.target_type == "team",
                    CandidateVisibilityTarget.target_id == team_id,
                    team_type == "internal"
                ),

                # 🌍 Organization share
                db.and_(
                    CandidateVisibility.visibility_type == "organization",
                    team_type == "internal"
                )
            )
        )
        .subquery()
    )

    # ------------------------------------------------
    # FINAL FILTER
    # ------------------------------------------------
    return base.filter(
        db.or_(
            Candidate.is_blacklisted == False,
            Candidate.is_blacklisted.is_(None)
        ),
        db.or_(

            # Owner always sees
            Candidate.added_by == user_email,

            # Shared candidates
            Candidate.cand_id.in_(visible_ids)
        )
    )