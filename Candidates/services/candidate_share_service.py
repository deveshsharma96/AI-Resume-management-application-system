# Candidates/services/candidate_share_service.py
#New candidate shgare service



from extensions import db

from Candidates.models.candidate import Candidate
from Candidates.models.candidate_visibility import CandidateVisibility
from Candidates.models.candidate_visibility_target import (
    CandidateVisibilityTarget
)

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

from Candidates.utils.visibility_query import (
    get_visible_candidates_query
)

from Logs.log_helper import create_log


def share_candidate_service(
    current_user,
    cand_ids,
    targets,
    notify=False,
    target_org_id=None
):

    source_org_id = current_user["org_id"]

    if not cand_ids or not targets:
        return {
            "error": "cand_id or cand_ids and targets are required"
        }

    user = current_user
    user_email = current_user["user_id"]

    # ---------------------------------------------------
    # ✅ STEP 1: ALLOWED ORGS
    # ---------------------------------------------------

    allowed_orgs = [source_org_id]

    global_recruiter = GlobalRecruiter.query.filter_by(
        email=user_email
    ).first()

    org_links = []

    if global_recruiter:
        org_links = OrganizationRecruiter.query.filter_by(
            recruiter_id=global_recruiter.recruiter_id
        ).all()

    for link in org_links:

        if link.org_id not in allowed_orgs:
            allowed_orgs.append(link.org_id)

    if (
        target_org_id
        and target_org_id not in allowed_orgs
    ):
        return {
            "error": "Unauthorized org access"
        }

    # ---------------------------------------------------
    # ✅ STEP 2: ORGS TO SHARE
    # ---------------------------------------------------

    orgs_to_share = [source_org_id]

    if (
        target_org_id
        and target_org_id != source_org_id
    ):
        orgs_to_share.append(target_org_id)

    shared_results = []
    skipped = []

    # ===================================================
    # LOOP OVER CANDIDATES
    # ===================================================

    for cand_id in cand_ids:

        # -----------------------------------------------
        # PERMISSION CHECK
        # -----------------------------------------------

        visible_query = get_visible_candidates_query(
            user,
            source_org_id
        )

        candidate = visible_query.filter(
            Candidate.cand_id == cand_id
        ).first()

        if not candidate:

            skipped.append({
                "cand_id": cand_id,
                "reason": "No permission"
            })

            continue

        added_targets = []

        # -----------------------------------------------
        # LOOP OVER ORGS
        # -----------------------------------------------

        for org_id in orgs_to_share:

            visibility = CandidateVisibility.query.filter_by(
                cand_id=cand_id,
                org_id=org_id
            ).first()

            # -------------------------------------------
            # CREATE VISIBILITY IF NOT EXISTS
            # -------------------------------------------

            if not visibility:

                visibility = CandidateVisibility(
                    cand_id=cand_id,
                    org_id=org_id,
                    owner_id=user_email,
                    shared_by_email=user_email,
                    visibility_type="private"
                )

                db.session.add(visibility)
                db.session.flush()

            # -------------------------------------------
            # LOOP OVER TARGETS
            # -------------------------------------------

            for target in targets:

                t_type = target.get(
                    "type",
                    ""
                ).strip().lower()

                t_value = target.get("value")

                # =======================================
                # ORGANIZATION SHARE
                # =======================================

                if t_type in ["organization", "org"]:

                    visibility.visibility_type = "organization"

                    recruiters = OrgRecruiter.query.filter_by(
                        org_id=t_value
                    ).all()

                    for recruiter in recruiters:

                        # skip self
                        if recruiter.email == user_email:
                            continue

                        exists = CandidateVisibilityTarget.query.filter_by(
                            visibility_id=visibility.id,
                            target_type="user",
                            target_id=recruiter.email
                        ).first()

                        if exists:
                            continue

                        db.session.add(
                            CandidateVisibilityTarget(
                                visibility_id=visibility.id,
                                target_type="user",
                                target_id=recruiter.email
                            )
                        )

                        added_targets.append({
                            "type": "user",
                            "id": recruiter.email
                        })

                    continue

                # =======================================
                # TEAM VALIDATION
                # =======================================

                if t_type == "team":

                    team_obj = Team.query.filter_by(
                        team_id=t_value,
                        org_id=org_id
                    ).first()

                    if not team_obj:
                        continue

                    # external org rule
                    if org_id != source_org_id:

                        if team_obj.team_type != "internal":
                            continue

                # =======================================
                # USER VALIDATION
                # =======================================

                if t_type == "user":

                    target_global_recruiter = (
                        GlobalRecruiter.query.filter_by(
                            email=t_value
                        ).first()
                    )

                    user_exists = (

                        OrgRecruiter.query.filter_by(
                            email=t_value,
                            org_id=org_id
                        ).first()

                        or

                        (
                            OrganizationRecruiter.query.filter_by(
                                recruiter_id=target_global_recruiter.recruiter_id,
                                org_id=org_id
                            ).first()

                            if target_global_recruiter
                            else None
                        )
                    )

                    if not user_exists:
                        continue

                # =======================================
                # DUPLICATE CHECK
                # =======================================

                exists = CandidateVisibilityTarget.query.filter_by(
                    visibility_id=visibility.id,
                    target_type=t_type,
                    target_id=t_value
                ).first()

                if exists:
                    continue

                # =======================================
                # SAVE TARGET
                # =======================================

                db.session.add(

                    CandidateVisibilityTarget(
                        visibility_id=visibility.id,
                        target_type=t_type,
                        target_id=t_value
                    )
                )

                added_targets.append({
                    "type": t_type,
                    "id": t_value
                })

        # ===================================================
        # NO TARGETS ADDED
        # ===================================================

        if not added_targets:

            skipped.append({
                "cand_id": cand_id,
                "reason": "Already shared"
            })

            continue

        # ===================================================
        # SUCCESS RESULT
        # ===================================================

        shared_results.append({
            "cand_id": cand_id,
            "shared_with": added_targets
        })

        # ===================================================
        # EMAIL NOTIFICATION
        # ===================================================

        if notify:

            for target in targets:

                if target.get("type") != "user":
                    continue

                target_email = target.get("value")

                target_user = (

                    SuperAdmin.find_by_email(target_email)

                    or

                    Admin.find_by_email(target_email)

                    or

                    OrgRecruiter.find_by_email(target_email)

                    or

                    GlobalRecruiter.find_by_email(target_email)
                )

                if not target_user:
                    continue

                try:

                    send_candidate_shared_email(
                        to_email=target_user.email,
                        to_name=getattr(
                            target_user,
                            "name",
                            "Recruiter"
                        ),
                        candidate_name=candidate.name,
                        candidate_email=candidate.email,
                        shared_by_name=user.get(
                            "name",
                            "Recruiter"
                        ),
                        shared_by_email=user_email
                    )

                except Exception as e:

                    print(
                        f"[WARN] Email failed: {e}"
                    )

        # ===================================================
        # LOG
        # ===================================================

        create_log(
            current_user["user_id"],
            action="share_candidate",
            entity_type="Candidate",
            entity_id=cand_id,
            data={
                "shared_with": added_targets,
                "notify": notify
            }
        )

    # =======================================================
    # FINAL COMMIT
    # =======================================================

    db.session.commit()

    return {
        "message": "Sharing completed",
        "shared": shared_results,
        "skipped": skipped
    }