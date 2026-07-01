
from flask import Blueprint, jsonify, request
from extensions import db
from Candidates.models.candidate import Candidate, Skill, WorkHistory,Certification,Degree
from jobs.models.job_candidate_model import JobCandidate
from Candidates.models.job_candidate_journey import JobCandidateJourney
from Logs.log_helper import create_log
from recruiter.models.recruiter_model import Recruiter
from Organization.models.super_admin import SuperAdmin
from recruiter.models.org_recruiter_model import OrgRecruiter
from recruiter.models.admin_model import Admin
from Organization.models.team import Team
from Candidates.utils.visibility_query import get_visible_candidates_query
from Candidates.models.candidate_visibility_target import CandidateVisibilityTarget
from Candidates.models.candidate_visibility import CandidateVisibility
from Candidates.models.export_template import ExportTemplate
import json
import pandas as pd
import tempfile
from flask import send_file
from datetime import datetime
from Candidates.models.resume import Resume
from common.utils.storage_service import generate_presigned_url
from common.models.document_asset import DocumentAsset

from auth.utils.jwt_required import jwt_required
from flask import g




candidates_info_bp = Blueprint("candidates_info_bp", __name__)

# ---------------- Helper: Get current user ----------------
def get_current_user():
    """
    Returns authenticated user from JWT middleware
    """
    if not hasattr(g, "current_user"):
        return None
    return g.current_user

# ---------------- Helper: Get current user's team ----------------
def get_user_team(user):
    team_id = user.get("team_id") if isinstance(user, dict) else getattr(user, "team_id", None)

    if team_id:
        return Team.query.filter_by(team_id=team_id).first()

    return None

# ---------------- Numeric operator helper ----------------
def apply_numeric_filter(query, column, op, val):
    operators = {
        "<": column < val,
        "<=": column <= val,
        "=": db.func.round(column, 2) == round(val, 2),
        "==": db.func.round(column, 2) == round(val, 2),
        ">=": column >= val,
        ">": column > val
    }
    if op in operators:
        return query.filter(operators[op])
    return query

def normalize_location(loc):
    """
    Normalizes location into:
    { country, state, city }
    """
    if not loc:
        return None

    # Already correct format
    if isinstance(loc, dict) and {"country", "state", "city"}.issubset(loc.keys()):
        return {
            "country": loc.get("country"),
            "state": loc.get("state"),
            "city": loc.get("city")
        }

    # Old UI format: {label, value}
    if isinstance(loc, dict) and "label" in loc:
        parts = [p.strip() for p in loc.get("label", "").split(",")]
        return {
            "city": parts[0] if len(parts) > 0 else None,
            "state": parts[1] if len(parts) > 1 else None,
            "country": parts[2] if len(parts) > 2 else None
        }

    # Plain string
    if isinstance(loc, str):
        parts = [p.strip() for p in loc.split(",")]
        return {
            "city": parts[0] if len(parts) > 0 else None,
            "state": parts[1] if len(parts) > 1 else None,
            "country": parts[2] if len(parts) > 2 else None
        }

    return None




# ---------------- GET CANDIDATES ----------------
@candidates_info_bp.route("/candidates", methods=["GET"])
@jwt_required
def get_search_filter_candidates():
    current_user = get_current_user()
    if not current_user:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    try:
        org_id = current_user["org_id"]
        if not org_id:
            return jsonify({"status": "error", "message": "org_id is required"}), 400

        # Filters
        search = request.args.get("search", "").strip()
        status = request.args.get("status")
        domain = request.args.get("domain")
        immediate_joiner = request.args.get("immediate_joiner")
        state = request.args.get("state")
        country = request.args.get("country")
        city = request.args.get("city")
        organization = request.args.get("organization")

        exp_op = request.args.get("exp_op")
        exp_val = request.args.get("exp_val")

        skill_raw = request.args.get("skill")
        skill_exp_op_raw = request.args.get("skill_exp_op")
        skill_exp_val_raw = request.args.get("skill_exp_val")
        current_ctc_op = request.args.get("current_ctc_op")
        current_ctc_val = request.args.get("current_ctc_val")

        expected_ctc_op = request.args.get("expected_ctc_op")
        expected_ctc_val = request.args.get("expected_ctc_val")
        notice_period_op = request.args.get("notice_period_op")
        notice_period_val = request.args.get("notice_period_val")

        submitted_by = request.args.get("submitted_by")
        current_org = request.args.get("current_org")
        previous_org = request.args.get("previous_org")
        internal_team_id = request.args.get("internal_team_id")
        team_only = request.args.get("team_only") == "true"
        if internal_team_id in (None, "", "null", "undefined"):
            internal_team_id = None

        # 🔹 NEW (OPTIONAL) FILTER
        job_id = request.args.get("job_id")

        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 10))

        query = get_visible_candidates_query(
            current_user,
            org_id
        )

        # ------------------------------------------------
        # 🔹 NEW: FILTER ONLY JOB APPLIED CANDIDATES
        # ------------------------------------------------
        if job_id:
            applied_candidates_subq = (
                db.session.query(JobCandidate.cand_id)
                .filter(JobCandidate.job_id == job_id)
                
            )
            query = query.filter(Candidate.cand_id.in_(applied_candidates_subq))

        
        if internal_team_id:

            # 1️⃣ Candidates explicitly shared with this team
            shared_subq = (
                db.session.query(CandidateVisibility.cand_id)
                .join(
                    CandidateVisibilityTarget,
                    CandidateVisibilityTarget.visibility_id == CandidateVisibility.id
                )
                .filter(
                    CandidateVisibilityTarget.target_type == "team",
                    CandidateVisibilityTarget.target_id == internal_team_id
                )
            )

            # 2️⃣ Candidates created by recruiters of this team
            created_by_team_subq = (
                db.session.query(Candidate.cand_id)
                .filter(Candidate.added_by_team_id == internal_team_id)
            )

            # 🔥 UNION both
            query = query.filter(
                db.or_(
                    Candidate.cand_id.in_(shared_subq),
                    Candidate.cand_id.in_(created_by_team_subq)
                )
            )



        # ---------------- BASIC SEARCH ----------------
        if search:
            like = f"%{search}%"
            query = query.filter(
                db.or_(
                    Candidate.name.ilike(like),
                    Candidate.email.ilike(like),
                    Candidate.phone.ilike(like),
                    Candidate.cand_id.ilike(like)
                )
            )

        # ---------------- OTHER FILTERS ----------------
        if status:
            query = query.filter(Candidate.status == status)
        if domain:
            query = query.filter(Candidate.domain.ilike(f"%{domain}%"))
        if immediate_joiner:
            query = query.filter(
                Candidate.immediate_joiner == (immediate_joiner == "true")
            )

        # ---------------- LOCATION FILTER ----------------
        if state:
            query = query.filter(
                db.func.JSON_UNQUOTE(
                    db.func.JSON_EXTRACT(Candidate.current_location, '$.state')
                ) == state
            )
        if country:
            query = query.filter(
                db.func.JSON_UNQUOTE(
                    db.func.JSON_EXTRACT(Candidate.current_location, '$.country')
                ) == country
            )
        if city:
            query = query.filter(
                db.func.JSON_UNQUOTE(
                    db.func.JSON_EXTRACT(Candidate.current_location, '$.city')
                ) == city
            )

        # ---------------- EXPERIENCE FILTER ----------------
        if exp_op and exp_val is not None:
            val = float(exp_val)
            col = db.cast(Candidate.total_experience, db.Float)
            operators = {
                "<": col < val,
                "<=": col <= val,
                "==": col == val,
                ">=": col >= val,
                ">": col > val
            }
            if exp_op in operators:
                query = query.filter(operators[exp_op])

        if current_ctc_op and current_ctc_val is not None:

            value = float(current_ctc_val)

            col = db.cast(
                db.func.nullif(
                    db.func.JSON_UNQUOTE(
                        db.func.JSON_EXTRACT(
                            Candidate.expected_package,
                            '$.current'
                        )
                    ),
                    ''
                ),
                db.Float
            )

            if current_ctc_op == "<":
                query = query.filter(col < value)

            elif current_ctc_op == "<=":
                query = query.filter(col <= value)

            elif current_ctc_op in ["=", "=="]:
                query = query.filter(col == value)

            elif current_ctc_op == ">":
                query = query.filter(col > value)

            elif current_ctc_op == ">=":
                query = query.filter(col >= value)
                

        # ---------------- Expected CTC (expected_package.max) ----------------
        if expected_ctc_op and expected_ctc_val is not None:

            value = float(expected_ctc_val)

            col = db.cast(
                db.func.nullif(
                    db.func.JSON_UNQUOTE(
                        db.func.JSON_EXTRACT(
                            Candidate.expected_package,
                            '$.max'
                        )
                    ),
                    ''
                ),
                db.Float
            )

            if expected_ctc_op == "<":
                query = query.filter(col < value)

            elif expected_ctc_op == "<=":
                query = query.filter(col <= value)

            elif expected_ctc_op in ["=", "=="]:
                query = query.filter(col == value)

            elif expected_ctc_op == ">":
                query = query.filter(col > value)

            elif expected_ctc_op == ">=":
                query = query.filter(col >= value)


        # ---------------- NOTICE PERIOD FILTER ----------------
                # ---------------- NOTICE PERIOD FILTER ----------------
        if notice_period_op and notice_period_val is not None:

            value = float(notice_period_val)

            col = db.cast(
                db.func.nullif(
                    db.func.JSON_UNQUOTE(
                        db.func.JSON_EXTRACT(
                            Candidate.notice_period,
                            '$.expected'
                        )
                    ),
                    ''
                ),
                db.Float
            )

            if notice_period_op == "<":
                query = query.filter(col < value)

            elif notice_period_op == "<=":
                query = query.filter(col <= value)

            elif notice_period_op in ["=", "=="]:
                query = query.filter(col == value)

            elif notice_period_op == ">":
                query = query.filter(col > value)

            elif notice_period_op == ">=":
                query = query.filter(col >= value)

        # ---------------- Submitted By ----------------
        if submitted_by:
            query = query.filter(Candidate.added_by == submitted_by)

        # ---------------- SKILL FILTER ----------------
        skill_list = [s.strip().lower() for s in skill_raw.split(",")] if skill_raw else []
        skill_op_list = skill_exp_op_raw.split(",") if skill_exp_op_raw else []
        skill_val_list = skill_exp_val_raw.split(",") if skill_exp_val_raw else []

        while len(skill_op_list) < len(skill_list):
            skill_op_list.append("")
        while len(skill_val_list) < len(skill_list):
            skill_val_list.append("")

        for i, skill_name in enumerate(skill_list):
            op = skill_op_list[i].strip()
            val = skill_val_list[i].strip()

            if not op or not val:
                query = query.filter(
                    Candidate.skills.any(
                        db.func.lower(Skill.skill_name).ilike(f"%{skill_name}%")
                    )
                )
                continue

            try:
                exp_value = float(val)
            except:
                return jsonify({
                    "status": "error",
                    "message": f"Invalid experience value for skill '{skill_name}'"
                }), 400

            col = db.cast(Skill.skill_experience, db.Float)
            operators = {
                "<": col < exp_value,
                "<=": col <= exp_value,
                "==": col == exp_value,
                ">=": col >= exp_value,
                ">": col > exp_value
            }

            if op not in operators:
                return jsonify({
                    "status": "error",
                    "message": f"Invalid operator '{op}' for skill '{skill_name}'"
                }), 400

            query = query.filter(
                Candidate.skills.any(
                    db.and_(
                        db.func.lower(Skill.skill_name).ilike(f"%{skill_name}%"),
                        operators[op]
                    )
                )
            )

         # ---------------- Current Organization ----------------
        if current_org:
            query = query.filter(
                Candidate.work_history.any(
                    db.and_(
                        WorkHistory.organization.ilike(f"%{current_org}%"),
                        db.or_(
                            WorkHistory.org_end_year == None,      # NULL
                            WorkHistory.org_end_year == "present"  # string value
                        )
                    )
                )
            )


        # ---------------- Previous Organization ----------------
        if previous_org:
            query = query.filter(
                Candidate.work_history.any(
                    db.and_(
                        WorkHistory.organization.ilike(f"%{previous_org}%"),
                        db.and_(
                            WorkHistory.org_end_year != None,
                            WorkHistory.org_end_year != "present"
                        )
                    )
                )
            )


        # ---------------- PAGINATION ----------------
        total = query.count()
        total_pages = (total + limit - 1) // limit
        candidates = query.offset((page - 1) * limit).limit(limit).all()

        data = [
            {
                "cand_id": c.cand_id,
                "name": c.name,
                "email": c.email,
                "phone": c.phone,
                "status": c.status,
                "skills": [s.skill_name for s in c.skills],
                "total_experience": c.total_experience,
                "domain": c.domain,
                "immediate_joiner": c.immediate_joiner
            }
            for c in candidates
        ]

        return jsonify({
            "status": "success",
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
            "data": data
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@candidates_info_bp.route("/candidate/details", methods=["GET"])
@jwt_required
def get_candidate_details():
    current_user = get_current_user()
    try:
        org_id = current_user["org_id"]
        query_param = request.args.get("query", "").strip()

        if not query_param:
            return jsonify({"status": "error", "message": "query are required"}), 400

        like = f"%{query_param}%"

        query = get_visible_candidates_query(
            current_user,
            org_id
        )

        candidate = query.filter(
            db.or_(
                Candidate.name.ilike(like),
                Candidate.email.ilike(like),
                Candidate.phone.ilike(like),
                Candidate.cand_id.ilike(like),
            )
        ).first()


        if not candidate:
            if current_user:
                create_log(
                    current_user["user_id"],
                    action="get_candidate_failed",
                    entity_type="Candidate",
                    data={"query": query_param, "org_id": org_id}
                )
            return jsonify({"status": "error", "message": f"No candidate found matching '{query_param}'"}), 404

        # ---------------- PREPARE CANDIDATE DATA ----------------
        data = candidate.to_dict()
        data["status"] = candidate.status or "N/A"
        

        # Fetch job mappings and journey info
        job_mappings = JobCandidate.query.filter_by(cand_id=candidate.cand_id).all()
        jobs_info = []
        for mapping in job_mappings:
            journey = JobCandidateJourney.query.filter_by(
                cand_id=candidate.cand_id, job_id=mapping.job_id
            ).order_by(JobCandidateJourney.created_at.desc()).first()

            jobs_info.append({
                "job_id": mapping.job_id,
                "mapping_status": mapping.status,
                "journey_id": journey.journey_id if journey else None,
                "journey_status": journey.status if journey else None
            })

        data["jobs"] = jobs_info

        # ✅ LOGGING
        if current_user:
            create_log(
                current_user["user_id"],
                action="get_candidate_details",
                entity_type="Candidate",
                entity_id=candidate.cand_id,
                data={"query": query_param, "org_id": org_id, "job_count": len(jobs_info)}
            )

        return jsonify({"status": "success", "data": data}), 200

    except Exception as e:
        if current_user:
            create_log(
                current_user["user_id"],
                action="get_candidate_details_failed",
                entity_type="Candidate",
                data={"error": str(e)}
            )
        return jsonify({"status": "error", "message": str(e)}), 500
    
    

@candidates_info_bp.route("/candidate/update", methods=["PUT"])
@jwt_required
def update_candidate():

    current_user = get_current_user()
    if not current_user:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    try:
        data = request.get_json(force=True)
        if isinstance(data, str):
            data = json.loads(data)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Invalid JSON: {str(e)}"
        }), 400

    # ---------------- REQUIRED ----------------
    cand_id = data.get("cand_id")
    org_id = current_user["org_id"]

    if not cand_id:
        return jsonify({
            "status": "error",
            "message": "cand_id and org_id are required"
        }), 400

    # ---------------- FETCH CANDIDATE ----------------
    candidate = Candidate.query.filter_by(
        cand_id=cand_id,
        org_id=org_id
    ).first()

    if not candidate:
        return jsonify({
            "status": "error",
            "message": "Candidate not found"
        }), 404
    
    old_data = {
        "name": candidate.name,
        "email": candidate.email,
        "phone": candidate.phone,
        "current_full_address": candidate.current_full_address,
        "current_pincode": candidate.current_pincode,
        "linkedin": candidate.linkedin,
        "portfolio": candidate.portfolio,
        "github_url": candidate.github_url,
        "total_experience": candidate.total_experience,
        "domain": candidate.domain,
        "expected_package": candidate.expected_package,
        "notice_period": candidate.notice_period,
        "availability": candidate.availability,
        "immediate_joiner": candidate.immediate_joiner
    }
    # ---------------- UPDATE SCALAR FIELDS ----------------
    scalar_fields = [
        "name",
        "email", "email_2", "email_3",
        "phone", "phone_2", "phone_3",
        "current_full_address",  "current_pincode",
        "permanent_full_address",  "permanent_pincode",
        "linkedin", "portfolio", "github_url",
        "total_experience",
        "domain",
        "expected_package",
        "notice_period",
        "key_skills",
        "availability"
    ]



    for field in scalar_fields:
        if field in data:
            setattr(candidate, field, data.get(field))

    # ---------------- LOCATION (NORMALIZED) ----------------
    if "current_location" in data:
        candidate.current_location = normalize_location(
            data.get("current_location")
        )

    if "permanent_location" in data:
        candidate.permanent_location = normalize_location(
            data.get("permanent_location")
        )


    # ---------------- BOOLEAN FIELDS ----------------
    candidate.same_as_current = data.get(
        "same_as_current", candidate.same_as_current
    )
    candidate.authorized_to_work = data.get(
        "authorized_to_work", candidate.authorized_to_work
    )
    candidate.relocation = data.get(
        "relocation", candidate.relocation
    )
    candidate.declaration_consent = data.get(
        "declaration_consent", candidate.declaration_consent
    )
    candidate.immediate_joiner = data.get(
        "immediate_joiner", candidate.immediate_joiner
    )
    # ---------------- NEW FIELDS ----------------

    # Preferred Locations
    if "preferred_locations" in data:
        candidate.preferred_locations = data.get("preferred_locations") or []

    # Offer Status + Offers (NEW LOGIC)

    # Offer Status + Offers (FINAL OPTIONAL LOGIC)

    if "offer_status" in data:
        offer_status = data.get("offer_status", "no_offer")
        offers = data.get("offers") or []

        offers = offers[:3]

        offers = [
            o for o in offers
            if isinstance(o, dict)
        ]

        candidate.offer_status = offer_status
        candidate.offers = offers

    # Notes
    if "notes" in data:
        candidate.notes = data.get("notes") or ""

    # ---------------- SAME AS CURRENT LOGIC ----------------
    if candidate.same_as_current:
        candidate.permanent_full_address = candidate.current_full_address
        candidate.permanent_location = candidate.current_location
        candidate.permanent_pincode = candidate.current_pincode

    # ---------------- CLEAR CHILD TABLES ----------------
    Skill.query.filter_by(cand_id=cand_id).delete()
    Degree.query.filter_by(cand_id=cand_id).delete()
    WorkHistory.query.filter_by(cand_id=cand_id).delete()
    Certification.query.filter_by(cand_id=cand_id).delete()

    # ---------------- SKILLS ----------------
    skills_list = data.get("skills", [])
    for sk in skills_list:
        if sk.get("skill_name"):
            db.session.add(Skill(
                cand_id=cand_id,
                skill_name=sk.get("skill_name"),
                skill_experience=sk.get("skill_experience")
            ))

    # ---------------- EDUCATION (FIX: education OR degrees) ----------------
    education_list = data.get("education") or data.get("degrees") or []
    for edu in education_list:
        if edu.get("degree_name"):
            db.session.add(Degree(
                cand_id=cand_id,
                degree_name=edu.get("degree_name"),
                major=edu.get("major"),
                minor=edu.get("minor"),
                score=edu.get("score"),
                start_year=edu.get("start_year"),
                start_month=edu.get("start_month"),
                end_year=edu.get("end_year"),
                end_month=edu.get("end_month")
            ))

    # ---------------- WORK HISTORY ----------------
    work_list = data.get("work_history", [])
    for wh in work_list:
        if wh.get("organization"):
            db.session.add(WorkHistory(
                cand_id=cand_id,
                organization=wh.get("organization"),
                org_start_year=wh.get("org_start_year"),
                org_start_month=wh.get("org_start_month"),
                org_end_year=wh.get("org_end_year"),
                org_end_month=wh.get("org_end_month"),
                designations=wh.get("designations", [])
            ))

    # ---------------- CERTIFICATIONS ----------------
    cert_list = data.get("certifications", [])
    for cert in cert_list:
        if cert.get("certificate"):
            db.session.add(Certification(
                cand_id=cand_id,
                certificate=cert.get("certificate"),
                completion_year=cert.get("completion_year"),
                valid_upto=cert.get("valid_upto")
            ))

    # ---------------- RESUME (APPEND ONLY) ----------------
    # ---------------- RESUME (APPEND ONLY - NEW SYSTEM) ----------------
    resume_id = data.get("resume_id")

    # ---------------- RESUME ----------------
    resume_id = data.get("resume_id")

    print("resume_id from frontend:", resume_id)

    if resume_id:
        try:

            asset = DocumentAsset.query.filter_by(
                docu_id=resume_id
            ).first()

            print("asset found:", asset)

            if not asset:
                return jsonify({
                    "status": "error",
                    "message": f"Resume asset not found for {resume_id}"
                }), 400

            print("file_key:", asset.file_key)

            new_resume = Resume(
                cand_id=cand_id,
                org_id=org_id,
                resume_file=asset.file_key,
                original_filename=asset.original_filename,
                mime_type=asset.mime_type,
                file_size=asset.file_size,
                uploaded_at=datetime.utcnow(),
                source="upload_resume"
            )

            db.session.add(new_resume)
            db.session.flush()

            print("new_resume.id:", new_resume.id)

            candidate.primary_resume_id = new_resume.id

        except Exception as e:
            db.session.rollback()

            print("========== RESUME ERROR ==========")
            print(str(e))

            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500


    # ---------------- COVER LETTER ----------------
    cover_letter_id = data.get("cover_letter_id")

    print("cover_letter_id:", cover_letter_id)

    if cover_letter_id:

        try:

            asset = DocumentAsset.query.filter_by(
                docu_id=cover_letter_id
            ).first()

            print("cover asset:", asset)

            if not asset:
                return jsonify({
                    "status": "error",
                    "message": "Invalid cover_letter_id"
                }), 400

            resume = None

            if candidate.primary_resume_id:
                resume = Resume.query.filter_by(
                    id=candidate.primary_resume_id,
                    cand_id=cand_id
                ).first()

            if not resume:
                resume = Resume(
                    cand_id=cand_id,
                    org_id=org_id,
                    uploaded_at=datetime.utcnow(),
                    source="upload_resume"
                )

                db.session.add(resume)
                db.session.flush()

                candidate.primary_resume_id = resume.id

            resume.cover_letter_file = asset.file_key
            resume.cover_letter_filename = asset.original_filename
            resume.cover_letter_mime_type = asset.mime_type
            resume.cover_letter_size = asset.file_size
            asset.cand_id = cand_id
            asset.is_linked = True

            print("cover letter attached")

        except Exception as e:

            db.session.rollback()

            print("========== COVER LETTER ERROR ==========")
            print(str(e))

            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500



    # ---------------- FINAL METADATA ----------------
    candidate.added_by = current_user["user_id"]
    candidate.status = "Updated"

    # ✅ STEP 3: DETECT CHANGES
    changed_fields = {}

    for field, old_value in old_data.items():
        new_value = getattr(candidate, field)
        if old_value != new_value:
            changed_fields[field] = {
                "old": old_value,
                "new": new_value
            }

    # Child table summary flags
    if "skills" in data:
        changed_fields["skills"] = "updated"

    if "education" in data or "degrees" in data:
        changed_fields["education"] = "updated"

    if "work_history" in data:
        changed_fields["work_history"] = "updated"

    if "certifications" in data:
        changed_fields["certifications"] = "updated"


    db.session.commit()

    # ---------------- LOG ----------------
    create_log(
        current_user["user_id"],
        action="edit_candidate_profile",
        entity_type="Candidate",
        entity_id=candidate.cand_id,
        data={
            "org_id": org_id,
            "changes": changed_fields
        }
    )
    
    return jsonify({
        "status": "success",
        "message": "Candidate profile updated successfully",
        "cand_id": candidate.cand_id
    }), 200

@candidates_info_bp.route("/candidate/resume/download", methods=["GET","OPTIONS"])
@jwt_required
def download_candidate_resume():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    current_user = get_current_user()
    if not current_user:
        return jsonify({
            "status": "error",
            "message": "Unauthorized"
        }), 401

    cand_id = request.args.get("cand_id")
    org_id = current_user["org_id"]
    file_type = request.args.get("type", "resume")  # resume | cover_letter

    if not cand_id:
        return jsonify({
            "status": "error",
            "message": "cand_id are required"
        }), 400

    # if file_type not in ["resume", "cover_letter"]:
    #     return jsonify({
    #         "status": "error",
    #         "message": "Invalid type. Allowed: resume, cover_letter"
    #     }), 400
    
    #NEW document request
    allowed_types = [

        "resume",
        "cover_letter",

        "aadhar",
        "pan",
        "passport",
        "driving_license",

        "salary_slip",
        "experience_letter",
        "offer_letter",

        "marksheet",
        "certificate",

        "bank_statement",

        "id_proof",
        "address_proof",

        "portfolio",
        "other"
    ]

    if file_type not in allowed_types:

        return jsonify({
            "status": "error",
            "message": "Invalid document type"
        }), 400

    # 🔐 Visibility check
    query = get_visible_candidates_query(
        current_user,
        org_id
    )
    candidate = query.filter(Candidate.cand_id == cand_id).first()

    if not candidate:
        return jsonify({
            "status": "error",
            "message": "Candidate not accessible"
        }), 403

    # 📄 Resolve resume row (primary first)
    resume = None

    if candidate.primary_resume_id:
        resume = Resume.query.filter_by(
            id=candidate.primary_resume_id,
            cand_id=cand_id
        ).first()

    if not resume:
        resume = (
            Resume.query
            .filter_by(cand_id=cand_id)
            .order_by(Resume.uploaded_at.desc())
            .first()
        )

    # if not resume:
    #     return jsonify({
    #         "status": "error",
    #         "message": "Resume record not found"
    #     }), 404

    # # 📎 Pick correct file
    # if file_type == "cover_letter":
    #     file_key = resume.cover_letter_file
    #     action = "download_cover_letter"
    # else:
    #     file_key = resume.resume_file
    #     action = "download_resume"

    # if not file_key:
    #     return jsonify({
    #         "status": "error",
    #         "message": f"{file_type.replace('_', ' ').title()} not found"
    #     }), 404
    
    
    #New document request
    
    file_key = None
   
    # -------------------------------------------------
    # OLD RESUME / COVER LETTER FLOW
    # -------------------------------------------------
    

    if file_type in ["resume", "cover_letter"]:

        

        if resume:

            if file_type == "cover_letter":

                file_key = resume.cover_letter_file

                action = "download_cover_letter"

            else:

                file_key = resume.resume_file

                action = "download_resume"

        if not file_key:

            # FALLBACK TO document_assets
            latest_document = (
                DocumentAsset.query
                .filter_by(
                    cand_id=cand_id,
                    org_id=org_id,
                    document_type=file_type,
                    is_linked=True
                )
                .order_by(
                    DocumentAsset.uploaded_at.desc()
                )
                .first()
            )

            if latest_document:

                file_key = latest_document.file_key

                if file_type == "cover_letter":

                    action = "download_cover_letter"

                else:

                    action = "download_resume"

            else:

                return jsonify({
                    "status": "error",
                    "message": f"{file_type} not found"
                }), 404

        # Generate URL
        download_url = generate_presigned_url(
            file_key,
            expiry=300
        )

        # Audit Log
        create_log(
            current_user["user_id"],
            action=action,
            entity_type="Candidate",
            entity_id=cand_id,
            data={
                "org_id": org_id,
                "file_type": file_type
            }
        )

        # RETURN OLD FORMAT
        return jsonify({

            "status": "success",

            "file_type": file_type,

            "download_url": download_url,

            "expires_in": 300

        }), 200

    # -------------------------------------------------
    # NEW DOCUMENT REQUEST FLOW
    # -------------------------------------------------

    # if not file_key:

    #     document_asset = DocumentAsset.query.filter_by(
    #         cand_id=cand_id,
    #         org_id=org_id,
    #         document_type=file_type,
    #         is_linked=True
    #     ).order_by(
    #         DocumentAsset.uploaded_at.desc()
    #     ).first()

    #     if document_asset:

    #         file_key = document_asset.file_key

    #         action = f"download_{file_type}"
    
    
    if not file_key:

        document_assets = (
            DocumentAsset.query
            .filter_by(
                cand_id=cand_id,
                org_id=org_id,
                document_type=file_type,
                is_linked=True
            )
            .order_by(
                DocumentAsset.document_count.asc()
            )
            .all()
        )

        if document_assets:

            documents_response = []

            for document_asset in document_assets:

                download_url = generate_presigned_url(
                    document_asset.file_key,
                    expiry=300
                )

                documents_response.append({

                    "docu_id":
                        document_asset.docu_id,

                    "document_count":
                        document_asset.document_count,

                    "file_name":
                        document_asset.original_filename,

                    "download_url":
                        download_url,

                    "uploaded_at":
                        document_asset.uploaded_at

                })

            create_log(
                current_user["user_id"],
                action=f"download_{file_type}",
                entity_type="Candidate",
                entity_id=cand_id,
                data={
                    "org_id": org_id,
                    "file_type": file_type
                }
            )

            return jsonify({

                "status": "success",

                "file_type": file_type,

                "documents": documents_response,

                "total_documents":
                    len(documents_response)

            }), 200

    # -------------------------------------------------
    # FINAL NOT FOUND
    # -------------------------------------------------

    return jsonify({
        "status": "error",
        "message": f"{file_type} not found"
    }), 404




@candidates_info_bp.route("/candidates/export", methods=["POST"])
@jwt_required
def export_candidates():
    current_user = get_current_user()

    if not current_user:
        return jsonify({
            "status": "error",
            "message": "Unauthorized"
        }), 401

    try:
        data = request.get_json(force=True)

        candidate_ids = data.get("candidate_ids", [])
        fields = data.get("fields", [])
        template_id = data.get("template_id")   # ✅ NEW

        # ---------------- TEMPLATE SUPPORT ----------------
        if template_id:
            template = ExportTemplate.query.filter_by(
                id=template_id,
                org_id=current_user["org_id"]
            ).first()

            if not template:
                return jsonify({
                    "status": "error",
                    "message": "Template not found"
                }), 404

            # ✅ override fields from template
            fields = template.fields

        # ---------------- VALIDATIONS ----------------
        if not candidate_ids:
            return jsonify({
                "status": "error",
                "message": "No candidates selected"
            }), 400

        if not fields:
            return jsonify({
                "status": "error",
                "message": "No fields selected"
            }), 400

        # Optional safety limit
        if len(candidate_ids) > 500:
            return jsonify({
                "status": "error",
                "message": "Too many candidates selected (max 500)"
            }), 400

        org_id = current_user["org_id"]

        # ---------------- FETCH CANDIDATES ----------------
        candidates = Candidate.query.filter(
            Candidate.cand_id.in_(candidate_ids),
            Candidate.org_id == org_id
        ).all()

        if not candidates:
            return jsonify({
                "status": "error",
                "message": "No candidates found"
            }), 404

        export_data = []

        # ---------------- PROCESS DATA ----------------
        for candidate in candidates:
            c_dict = candidate.to_dict()
            row = {}

            for field in fields:
                value = c_dict.get(field)

                # ---------------- 🔥 FLATTEN COMPLEX FIELDS ----------------

                # ✅ Skills
                if field == "skills":
                    value = ", ".join([
                        f"{s.get('skill_name','')} ({s.get('skill_experience','')})"
                        for s in c_dict.get("skills", [])
                    ])

                # ✅ Education
                elif field == "degrees":
                    value = ", ".join([
                        f"{d.get('degree_name','')} "
                        f"({d.get('start_year','')} - {d.get('end_year','')}) "
                        f"{d.get('major','')}"
                        for d in c_dict.get("degrees", [])
                    ])

                # ✅ Work History
                elif field == "work_history":
                    value = ", ".join([
                        f"{w.get('organization','')} "
                        f"({w.get('org_start_year','')} - {w.get('org_end_year','')}) "
                        f"{', '.join([d.get('designation','') for d in (w.get('designations') or [])])}"
                        for w in c_dict.get("work_history", [])
                    ])

                # ✅ Certifications
                elif field == "certifications":
                    value = ", ".join([
                        f"{c.get('certificate','')} ({c.get('completion_year','')})"
                        for c in c_dict.get("certifications", [])
                    ])

                # ✅ Expected Package
                elif field == "expected_package":
                    pkg = c_dict.get("expected_package", {})
                    value = f"{pkg.get('min', '')} - {pkg.get('max', '')}"

                # ✅ Notice Period
                elif field == "notice_period":
                    np = c_dict.get("notice_period", {})
                    value = (
                        np.get("expected")
                        or np.get("official")
                        or ""
                    )

                # ✅ Preferred Locations
                elif field == "preferred_locations":
                    value = ", ".join([
                        str(loc) for loc in c_dict.get("preferred_locations", [])
                    ])

                # ✅ Availability
                elif field == "availability":
                    value = ", ".join([
                        str(v) for v in c_dict.get("availability", [])
                    ])

                # ✅ Date fix
                elif field in ["created_at", "updated_at"]:
                    value = str(value) if value else ""

                # ✅ Boolean fix
                elif isinstance(value, bool):
                    value = "Yes" if value else "No"

                # ✅ Dict fallback
                elif isinstance(value, dict):
                    value = str(value)

                # ✅ List fallback
                elif isinstance(value, list):
                    value = ", ".join([str(v) for v in value])

                # ✅ None fix
                if value is None:
                    value = ""

                row[field] = value

            export_data.append(row)

        # ---------------- CREATE DATAFRAME ----------------
        df = pd.DataFrame(export_data)

        # ---------------- COLUMN LABELS ----------------
        COLUMN_LABELS = {
            "cand_id": "Candidate ID",
            "name": "Full Name",
            "email": "Email",
            "phone": "Phone",
            "total_experience": "Experience",
            "domain": "Domain",
            "key_skills": "Key Skills",
            "skills": "Skills",
            "degrees": "Education",
            "work_history": "Work History",
            "certifications": "Certifications",
            "expected_package": "Expected Package",
            "notice_period": "Notice Period",
            "immediate_joiner": "Immediate Joiner",
            "current_full_address": "Address",
            "current_pincode": "Pincode",
            "preferred_locations": "Preferred Locations",
            "created_at": "Created At"
        }

        df.rename(columns=COLUMN_LABELS, inplace=True)

        # ---------------- CREATE FILE ----------------
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        df.to_excel(temp_file.name, index=False)

        # ---------------- RETURN FILE ----------------
        response = send_file(
            temp_file.name,
            as_attachment=True,
            download_name="candidates_export.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # ✅ Optional success headers
        response.headers["X-Message"] = "Candidates exported successfully"
        response.headers["X-Status"] = "success"

        return response

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    


@candidates_info_bp.route("/candidates/export/template", methods=["POST"])
@jwt_required
def create_export_template():
    current_user = get_current_user()

    if not current_user:
        return jsonify({
            "status": "error",
            "message": "Unauthorized"
        }), 401

    try:
        data = request.get_json(force=True)

        name = data.get("name")
        fields = data.get("fields", [])

        # ---------------- VALIDATIONS ----------------
        if not name:
            return jsonify({
                "status": "error",
                "message": "Template name is required"
            }), 400

        if not fields:
            return jsonify({
                "status": "error",
                "message": "Fields are required"
            }), 400

        # Optional: prevent duplicate names per org
        existing = ExportTemplate.query.filter_by(
            name=name,
            org_id=current_user["org_id"]
        ).first()

        if existing:
            return jsonify({
                "status": "error",
                "message": "Template with this name already exists"
            }), 400

        # ---------------- CREATE TEMPLATE ----------------
        template = ExportTemplate(
            name=name,
            fields=fields,
            org_id=current_user["org_id"],
            created_by=current_user["user_id"]
        )

        db.session.add(template)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Template created successfully",
            "data": {
                "id": template.id,
                "name": template.name,
                "fields": template.fields
            }
        }), 201

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    


@candidates_info_bp.route("/candidates/export/templates", methods=["GET"])
@jwt_required
def get_export_templates():
    current_user = get_current_user()

    if not current_user:
        return jsonify({
            "status": "error",
            "message": "Unauthorized"
        }), 401

    try:
        templates = ExportTemplate.query.filter_by(
            org_id=current_user["org_id"]
        ).order_by(ExportTemplate.created_at.desc()).all()

        return jsonify({
            "status": "success",
            "data": [
                {
                    "id": t.id,
                    "name": t.name,
                    "fields": t.fields,
                    "created_at": t.created_at
                }
                for t in templates
            ]
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    



# ===================================================
# BLACKLIST CANDIDATE
# ===================================================
@candidates_info_bp.route("/<string:cand_id>/blacklist", methods=["PUT"])
@jwt_required
def blacklist_candidate(cand_id):

    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    # ---------------------------------------------------
    # Find Candidate
    # ---------------------------------------------------
    candidate = Candidate.query.filter_by(
        cand_id=cand_id
    ).first()

    if not candidate:
        return jsonify({"error": "Candidate not found"}), 404

    # ---------------------------------------------------
    # Request Data
    # ---------------------------------------------------
    data = request.get_json() or {}

    # ---------------------------------------------------
    # Prevent duplicate blacklist
    # ---------------------------------------------------
    if candidate.is_blacklisted:
        return jsonify({
            "error": "Candidate already blacklisted"
        }), 400

    # ---------------------------------------------------
    # Update Candidate
    # ---------------------------------------------------
    candidate.is_blacklisted = True
    candidate.blacklisted_at = datetime.utcnow()
    candidate.blacklisted_by = current_user["user_id"]
    candidate.blacklist_reason = data.get("reason")

    db.session.commit()

    # ---------------------------------------------------
    # Audit Log
    # ---------------------------------------------------
    create_log(
        current_user["user_id"],
        action="BLACKLIST_CANDIDATE",
        entity_type="Candidate",
        entity_id=cand_id,
        data={
            "reason": candidate.blacklist_reason
        }
    )

    # ---------------------------------------------------
    # Response
    # ---------------------------------------------------
    return jsonify({
        "message": "Candidate blacklisted successfully",
        "data": {
            "cand_id": candidate.cand_id,
            "is_blacklisted": candidate.is_blacklisted,
            "blacklist_reason": candidate.blacklist_reason,
            "blacklisted_by": candidate.blacklisted_by,
            "blacklisted_at": candidate.blacklisted_at
        }
    }), 200



# ===================================================
# UNBLACKLIST CANDIDATE
# ===================================================
@candidates_info_bp.route("/<string:cand_id>/unblacklist", methods=["PUT"])
@jwt_required
def unblacklist_candidate(cand_id):

    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    # ---------------------------------------------------
    # Find Candidate
    # ---------------------------------------------------
    candidate = Candidate.query.filter_by(
        cand_id=cand_id
    ).first()

    if not candidate:
        return jsonify({"error": "Candidate not found"}), 404

    # ---------------------------------------------------
    # Check Status
    # ---------------------------------------------------
    if not candidate.is_blacklisted:
        return jsonify({
            "error": "Candidate is not blacklisted"
        }), 400

    # ---------------------------------------------------
    # Remove Blacklist
    # ---------------------------------------------------
    candidate.is_blacklisted = False
    candidate.blacklisted_at = None
    candidate.blacklisted_by = None
    candidate.blacklist_reason = None

    db.session.commit()

    # ---------------------------------------------------
    # Audit Log
    # ---------------------------------------------------
    create_log(
        current_user["user_id"],
        action="UNBLACKLIST_CANDIDATE",
        entity_type="Candidate",
        entity_id=cand_id,
        data={}
    )

    # ---------------------------------------------------
    # Response
    # ---------------------------------------------------
    return jsonify({
        "message": "Candidate removed from blacklist",
        "data": {
            "cand_id": candidate.cand_id,
            "is_blacklisted": candidate.is_blacklisted
        }
    }), 200



# ===================================================
# GET BLACKLISTED CANDIDATES
# ===================================================
@candidates_info_bp.route("/blacklisted", methods=["GET"])
@jwt_required
def get_blacklisted_candidates():

    current_user = get_current_user()

    if not current_user:
        return jsonify({
            "status": "error",
            "message": "Unauthorized"
        }), 401

    try:

        org_id = current_user["org_id"]

        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 10))
        search = request.args.get("search", "").strip()

        # ---------------------------------------------------
        # Base Query
        # ---------------------------------------------------
        query = Candidate.query.filter(
            Candidate.org_id == org_id,
            Candidate.is_blacklisted == True
        )

        # ---------------------------------------------------
        # Search Support
        # ---------------------------------------------------
        if search:

            like = f"%{search}%"

            query = query.filter(
                db.or_(
                    Candidate.name.ilike(like),
                    Candidate.email.ilike(like),
                    Candidate.phone.ilike(like),
                    Candidate.cand_id.ilike(like)
                )
            )

        # ---------------------------------------------------
        # Pagination
        # ---------------------------------------------------
        total = query.count()

        total_pages = (
            (total + limit - 1) // limit
        )

        candidates = (
            query
            .order_by(Candidate.blacklisted_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )

        # ---------------------------------------------------
        # Response Data
        # ---------------------------------------------------
        data = []

        for candidate in candidates:

            data.append({
                "cand_id": candidate.cand_id,
                "name": candidate.name,
                "email": candidate.email,
                "phone": candidate.phone,
                "status": candidate.status,
                "domain": candidate.domain,
                "total_experience": candidate.total_experience,
                "blacklist_reason": candidate.blacklist_reason,
                "blacklisted_by": candidate.blacklisted_by,
                "blacklisted_at": candidate.blacklisted_at
            })

        return jsonify({
            "status": "success",
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
            "data": data
        }), 200

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500




# ===================================================
# GET BLACKLISTED CANDIDATE DETAILS
# ===================================================
@candidates_info_bp.route(
    "/blacklisted/<string:cand_id>",
    methods=["GET"]
)
@jwt_required
def get_blacklisted_candidate_details(cand_id):

    current_user = get_current_user()

    if not current_user:
        return jsonify({
            "status": "error",
            "message": "Unauthorized"
        }), 401

    try:

        org_id = current_user["org_id"]

        # ---------------------------------------------------
        # Fetch blacklisted candidate
        # ---------------------------------------------------
        candidate = Candidate.query.filter(
            Candidate.org_id == org_id,
            Candidate.cand_id == cand_id,
            Candidate.is_blacklisted == True
        ).first()

        if not candidate:
            return jsonify({
                "status": "error",
                "message": "Blacklisted candidate not found"
            }), 404

        # ---------------------------------------------------
        # Candidate Full Data
        # ---------------------------------------------------
        data = candidate.to_dict()

        # blacklist info
        data["blacklist_info"] = {
            "reason": candidate.blacklist_reason,
            "blacklisted_by": candidate.blacklisted_by,
            "blacklisted_at": candidate.blacklisted_at
        }

        return jsonify({
            "status": "success",
            "data": data
        }), 200

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500