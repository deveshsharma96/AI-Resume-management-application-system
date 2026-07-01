
from flask import Blueprint, request, jsonify,current_app
from extensions import db
from auth.utils.jwt_required import jwt_required
from flask import g

import json
from jobs.models.job_model import Job,generate_job_id
from jobs.models.job_skill_requirement import JobSkillRequirement
from jobs.models.job_experience_requirement import JobExperienceRequirement
from jobs.models.job_education_requirement import JobEducationRequirement
from jobs.models.job_salary_requirement import JobSalaryRange

from datetime import datetime, timezone, timedelta
from Organization.models.organization_form_link import OrganizationFormLink
from auth.permissions import permission_required
from Logs.log_helper import create_log
from jobs.models.job_visibility import JobVisibility
from jobs.models.job_visibility_target import JobVisibilityTarget
from Organization.models.team_member import TeamMember


# User models for logging
from recruiter.models.recruiter_model import Recruiter
from Organization.models.super_admin import SuperAdmin
from recruiter.models.org_recruiter_model import OrgRecruiter
from recruiter.models.admin_model import Admin
from sqlalchemy import or_, and_
from Organization.utils.email_utils import send_job_shared_email
from common.models.Predefined_skills import PredefinedSkill
from recruiter.models.hiring_manager_model import HiringManager
from jobs.models.job_hiring_manager import JobHiringManager

job_bp = Blueprint("job_bp", __name__)

# ---------------- Helper: Convert UTC to IST ----------------
def to_ist(dt):
    if not dt:
        return None
    ist = dt.replace(tzinfo=timezone.utc) + timedelta(hours=5, minutes=30)
    return ist.strftime("%Y-%m-%d %H:%M:%S")

# Allowed Job Statuses
ALLOWED_JOB_STATUS = ["draft", "published", "closed"]

# ---------------- Helper: Get current user from header ----------------
def get_current_user():
    """
    Returns the authenticated user populated by jwt_required middleware.
    """
    if not hasattr(g, "current_user"):
        return None

    return g.current_user


def get_user_identity(user):
    if not user:
        return None, None

    return (
        user.get("role"),
        str(user.get("user_id"))
    )


def is_owner(job, user):
    user_type, user_id = get_user_identity(user)
    return (
        job.created_by_type == user_type and
        job.created_by_id == user_id
    )



def parse_work_mode(value):
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else [parsed]
    except Exception:
        return [value]
    

def validate_and_prepare_skills(selected_skills, other_skill=None):
    valid_skills = {s.name.lower() for s in PredefinedSkill.query.all()}
    cleaned = []

    for skill in selected_skills:
        if skill.lower() in valid_skills:
            cleaned.append(skill.lower())

    if other_skill:
        cleaned.append(other_skill.strip().lower())

    return cleaned



@job_bp.route("/create", methods=["POST"])
@jwt_required
def create_job():
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(force=True, silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON format. Send application/json"}), 400

    if "Job_status" in data and data["Job_status"] not in ALLOWED_JOB_STATUS:
        return jsonify({"error": "Invalid Job_status"}), 400

    try:
        # ---------------- Get Owner Identity ----------------
        user_type, user_id = get_user_identity(current_user)

        if not user_type or not user_id:
            return jsonify({"error": "Invalid user identity"}), 400

        # ---------------- Job Type Validation ----------------
        job_type = data.get("job_type")
        contract_duration = data.get("contract_duration")

        if job_type == "Contract" and not contract_duration:
            return jsonify({
                "error": "contract_duration is required when job_type is Contract"
            }), 400

        # ---------------- Normalize Work Mode ----------------
        work_mode_raw = data.get("work_mode")

        if isinstance(work_mode_raw, str):
            work_mode_raw = [work_mode_raw]
        elif work_mode_raw is None:
            work_mode_raw = []

        if not isinstance(work_mode_raw, list):
            return jsonify({
                "error": "work_mode must be a string or list of strings"
            }), 400
        


        # ---------------- Hiring Manager ----------------

        # -------------------------------------------------
        hiring_manager_ids = data.get(
            "hiring_manager_ids",
            []
        )

        # -----------------------------------------
        # Validation
        # -----------------------------------------

        if not isinstance(hiring_manager_ids, list):

            return jsonify({
                "error": "hiring_manager_ids must be a list"
            }), 400

        # ---------------- Create Job ----------------
        job = Job(
            job_id=generate_job_id(),
            org_id=current_user["org_id"],
            title=data["title"],
            description=data["description"],
            Job_status=data.get("Job_status", "draft"),

            # ✅ OWNER FIELDS (FIXED)
            created_by_type=user_type,
            created_by_id=user_id,
            is_private=True,

            min_notice_period=data.get("min_notice_period"),
            max_notice_period=data.get("max_notice_period"),
            location=data.get("location"),
            work_mode=json.dumps(work_mode_raw),
            job_type=job_type,
            
            contract_duration=contract_duration if job_type == "Contract" else None
        )

        db.session.add(job)
        # IMPORTANT
        db.session.flush()

        # -------------------------------------------------
        # Assign Hiring Managers
        # -------------------------------------------------

        for hm_id in hiring_manager_ids:

            hiring_manager = HiringManager.query.filter_by(
                manager_id=hm_id,
                org_id=current_user["org_id"]
            ).first()

            if not hiring_manager:

                db.session.rollback()

                return jsonify({
                    "error": f"Invalid hiring manager: {hm_id}"
                }), 400

            db.session.add(
                JobHiringManager(
                    job_id=job.job_id,
                    manager_id=hm_id
                )
            )

        # ---------------- Add Skill Requirements ----------------
        mandatory_skills = data.get("mandatory_skills", [])
        optional_skills = data.get("optional_skills", [])

        other_mandatory = data.get("other_mandatory_skill")
        other_optional = data.get("other_optional_skill")

        clean_mandatory = validate_and_prepare_skills(
            mandatory_skills,
            other_mandatory
        )

        clean_optional = validate_and_prepare_skills(
            optional_skills,
            other_optional
        )

        db.session.add(
            JobSkillRequirement(
                job_id=job.job_id,
                mandatory_skills=",".join(clean_mandatory),
                optional_skills=",".join(clean_optional)
            )
        )

        # ---------------- Add Experience ----------------
        exp = data.get("experience")
        if exp and isinstance(exp, dict):
            db.session.add(
                JobExperienceRequirement(
                    job_id=job.job_id,
                    min_years=exp.get("min_years", 0),
                    max_years=exp.get("max_years", 0)
                )
            )

        # ---------------- Add Education ----------------
        for edu in data.get("education_requirements", []):
            db.session.add(
                JobEducationRequirement(
                    job_id=job.job_id,
                    education_level=edu
                )
            )

        # ---------------- Add Salary Range ----------------
        salary = data.get("salary_range")
        if salary and isinstance(salary, dict):
            db.session.add(
                JobSalaryRange(
                    job_id=job.job_id,
                    min_salary=salary.get("min"),
                    max_salary=salary.get("max"),
                    currency=salary.get("currency", "INR"),
                    salary_type=salary.get("salary_type", "annual")
                )
            )

        # ---------------- Commit ----------------
        db.session.commit()

        # ---------------- Logging ----------------
        create_log(
            current_user["user_id"],
            action="create_job",
            entity_type="Job",
            entity_id=job.job_id,
            data={
                "title": job.title,
                "Job_status": job.Job_status,
                "created_by_type": user_type,
                "created_by_id": user_id
            }
        )

        return jsonify({
            "message": "Job created successfully",
            "job_id": job.job_id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400



# ---------------- Edit Job ----------------
@job_bp.route("/<string:job_id>", methods=["PUT"])
@jwt_required
def edit_job(job_id):

    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    # ---------------- Get Job ----------------
    job = Job.query.filter_by(job_id=job_id).first()

    if not job:
        return jsonify({"error": "Job not found"}), 404

    # ---------------- Ownership Check ----------------
    if job.is_private and not is_owner(job, current_user):
        return jsonify({
            "error": "You are not allowed to edit this job"
        }), 403

    data = request.get_json(force=True, silent=True)

    print("DATA:", data)
    print("TYPE:", type(data))

    if not data:
        return jsonify({
            "error": "Invalid JSON payload"
        }), 400

    # ---------------- Validate Job Status ----------------
    if (
        "Job_status" in data and
        data["Job_status"] not in ALLOWED_JOB_STATUS
    ):
        return jsonify({
            "error": "Invalid Job_status"
        }), 400

    try:

        # =====================================================
        # BASIC FIELDS
        # =====================================================

        job.title = data.get("title", job.title)

        job.description = data.get(
            "description",
            job.description
        )

        job.Job_status = data.get(
            "Job_status",
            job.Job_status
        )

        job.updated_at = datetime.utcnow()

        # =====================================================
        # SKILLS
        # =====================================================

        if "mandatory_skills" in data or "optional_skills" in data:

            skills = JobSkillRequirement.query.filter_by(
                job_id=job_id
            ).first()

            if not skills:
                skills = JobSkillRequirement(job_id=job_id)
                db.session.add(skills)

            # ---------------- Mandatory Skills ----------------

            if "mandatory_skills" in data:

                mandatory_skills = data.get(
                    "mandatory_skills",
                    []
                )

                if not isinstance(mandatory_skills, list):
                    return jsonify({
                        "error": "mandatory_skills must be a list"
                    }), 400

                clean_mandatory = validate_and_prepare_skills(
                    mandatory_skills,
                    data.get("other_mandatory_skill")
                )

                skills.mandatory_skills = ",".join(
                    clean_mandatory
                )

            # ---------------- Optional Skills ----------------

            if "optional_skills" in data:

                optional_skills = data.get(
                    "optional_skills",
                    []
                )

                if not isinstance(optional_skills, list):
                    return jsonify({
                        "error": "optional_skills must be a list"
                    }), 400

                clean_optional = validate_and_prepare_skills(
                    optional_skills,
                    data.get("other_optional_skill")
                )

                skills.optional_skills = ",".join(
                    clean_optional
                )

        # =====================================================
        # EXPERIENCE
        # =====================================================

        if "experience" in data:

            exp = data.get("experience")

            # ✅ Prevent crash if frontend sends string
            if exp is not None and not isinstance(exp, dict):
                return jsonify({
                    "error": "experience must be an object"
                }), 400

            if exp:

                if job.experience:

                    job.experience.min_years = exp.get(
                        "min_years",
                        job.experience.min_years
                    )

                    job.experience.max_years = exp.get(
                        "max_years",
                        job.experience.max_years
                    )

                else:

                    db.session.add(
                        JobExperienceRequirement(
                            job_id=job_id,
                            min_years=exp.get("min_years", 0),
                            max_years=exp.get("max_years", 0),
                        )
                    )

        # =====================================================
        # EDUCATION
        # =====================================================

        if "education_requirements" in data:

            education_requirements = data.get(
                "education_requirements",
                []
            )

            if not isinstance(education_requirements, list):
                return jsonify({
                    "error": "education_requirements must be a list"
                }), 400

            # Delete old education entries
            JobEducationRequirement.query.filter_by(
                job_id=job_id
            ).delete()

            # Add new entries
            for edu in education_requirements:

                db.session.add(
                    JobEducationRequirement(
                        job_id=job_id,
                        education_level=edu
                    )
                )

        # =====================================================
        # SALARY
        # =====================================================

        if "salary_range" in data:

            salary = data["salary_range"]

            # ✅ Prevent crash if frontend sends string
            if salary is not None and not isinstance(salary, dict):
                return jsonify({
                    "error": "salary_range must be an object"
                }), 400

            # Delete salary if null
            if salary is None:

                JobSalaryRange.query.filter_by(
                    job_id=job_id
                ).delete()

            else:

                existing_salary = JobSalaryRange.query.filter_by(
                    job_id=job_id
                ).first()

                # ---------------- Update Existing ----------------

                if existing_salary:

                    existing_salary.min_salary = salary.get(
                        "min",
                        existing_salary.min_salary
                    )

                    existing_salary.max_salary = salary.get(
                        "max",
                        existing_salary.max_salary
                    )

                    existing_salary.currency = salary.get(
                        "currency",
                        existing_salary.currency
                    )

                    existing_salary.salary_type = salary.get(
                        "salary_type",
                        existing_salary.salary_type
                    )

                # ---------------- Create New ----------------

                else:

                    db.session.add(
                        JobSalaryRange(
                            job_id=job_id,
                            min_salary=salary.get("min"),
                            max_salary=salary.get("max"),
                            currency=salary.get(
                                "currency",
                                "INR"
                            ),
                            salary_type=salary.get(
                                "salary_type",
                                "annual"
                            ),
                        )
                    )

        # =====================================================
        # LOCATION
        # =====================================================

        if "location" in data:
            job.location = data["location"]

        # =====================================================
        # NOTICE PERIOD
        # =====================================================

        if "min_notice_period" in data:
            job.min_notice_period = data[
                "min_notice_period"
            ]

        if "max_notice_period" in data:
            job.max_notice_period = data[
                "max_notice_period"
            ]

        # =====================================================
        # WORK MODE
        # =====================================================

        if "work_mode" in data:

            work_mode_raw = data.get("work_mode")

            if isinstance(work_mode_raw, str):
                work_mode_raw = [work_mode_raw]

            elif work_mode_raw is None:
                work_mode_raw = []

            if not isinstance(work_mode_raw, list):
                return jsonify({
                    "error": (
                        "work_mode must be a string "
                        "or list of strings"
                    )
                }), 400

            job.work_mode = json.dumps(work_mode_raw)

        # =====================================================
        # JOB TYPE
        # =====================================================

        if "job_type" in data:

            job.job_type = data["job_type"]

            if job.job_type == "Contract":

                if not data.get("contract_duration"):

                    return jsonify({
                        "error": (
                            "contract_duration is required "
                            "when job_type is Contract"
                        )
                    }), 400

                job.contract_duration = data[
                    "contract_duration"
                ]

            else:
                job.contract_duration = None

        # =====================================================
        # CONTRACT DURATION
        # =====================================================

        if (
            "contract_duration" in data and
            job.job_type == "Contract"
        ):

            job.contract_duration = data[
                "contract_duration"
            ]

        # =====================================================
        # SAVE CHANGES
        # =====================================================

        db.session.commit()

        # =====================================================
        # LOGGING
        # =====================================================

        create_log(
            current_user["user_id"],
            action="edit_job",
            entity_type="Job",
            entity_id=job.job_id,
            data={
                "title": job.title,
                "Job_status": job.Job_status
            }
        )

        return jsonify({
            "message": "Job updated successfully"
        }), 200

    except Exception as e:

        db.session.rollback()

        return jsonify({
            "error": str(e)
        }), 400




@job_bp.route("/<string:job_id>", methods=["DELETE"])
@jwt_required
def delete_job(job_id):
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    job = Job.query.filter_by(job_id=job_id).first()
    if not job:
        return jsonify({"error": "Job not found"}), 404

    # ✅ Proper Ownership Check
    if not is_owner(job, current_user):
        return jsonify({"error": "You are not allowed to delete this job"}), 403

    try:
        from jobs.models.job_candidate_model import JobCandidate

        JobCandidate.query.filter_by(job_id=job_id).delete()
        JobSkillRequirement.query.filter_by(job_id=job_id).delete()
        JobEducationRequirement.query.filter_by(job_id=job_id).delete()
        JobSalaryRange.query.filter_by(job_id=job_id).delete()

        if job.experience:
            db.session.delete(job.experience)

        db.session.delete(job)
        db.session.commit()

        create_log(
            current_user["user_id"],
            action="delete_job",
            entity_type="Job",
            entity_id=job.job_id,
            data={"title": job.title, "Job_status": job.Job_status}
        )

        return jsonify({"message": "Job deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400



# ---------------- Publish Job ----------------


@job_bp.route("/<string:job_id>/publish", methods=["PATCH"])
@jwt_required
def publish_job(job_id):
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    job = Job.query.filter_by(job_id=job_id).first()
    if not job:
        return jsonify({"error": "Job not found"}), 404

    # ✅ Ownership Check
    if not is_owner(job, current_user):
        return jsonify({"error": "You are not allowed to publish this job"}), 403

    try:
        job.Job_status = "published"
        job.is_private = False   # ✅ IMPORTANT: make visible after publish

        if not job.job_public_link:
            org_link = OrganizationFormLink.query.filter_by(org_id=job.org_id).first()
            if not org_link:
                return jsonify({"error": "No public form found for this organization"}), 400

            frontend_base = current_app.config.get("FRONTEND_BASE_URL")
            if not frontend_base:
                return jsonify({"error": "FRONTEND_BASE_URL not configured"}), 500

            job.job_public_link = (
                f"{frontend_base}/#/candidateform"
                f"?token={org_link.token}&job_id={job.job_id}"
            )

        job.updated_at = datetime.utcnow()
        db.session.commit()

        create_log(
            current_user["user_id"],
            action="publish_job",
            entity_type="Job",
            entity_id=job.job_id,
            data={"title": job.title, "Job_status": job.Job_status}
        )

        return jsonify({
            "message": "Job published successfully",
            "job_id": job.job_id,
            "job_link": job.job_public_link
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    

# ---------------- Close Job ----------------
@job_bp.route("/<string:job_id>/close", methods=["PATCH"])
@jwt_required
def close_job(job_id):
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    job = Job.query.filter_by(job_id=job_id).first()
    if not job:
        return jsonify({"error": "Job not found"}), 404

    # ✅ Ownership Check
    if not is_owner(job, current_user):
        return jsonify({"error": "You are not allowed to close this job"}), 403

    if job.Job_status == "closed":
        return jsonify({"message": "Job is already closed"}), 200

    try:
        job.Job_status = "closed"
        job.updated_at = datetime.utcnow()
        db.session.commit()

        create_log(
            current_user["user_id"],
            action="close_job",
            entity_type="Job",
            entity_id=job.job_id,
            data={"title": job.title, "Job_status": job.Job_status}
        )

        return jsonify({
            "message": "Job closed successfully",
            "job_id": job.job_id,
            "link": job.job_public_link
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


from sqlalchemy.sql import exists

@job_bp.route("/", methods=["GET"])
@jwt_required
def list_jobs():
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    org_id = request.args.get("org_id")
    Job_status = request.args.get("Job_status")

    if not org_id:
        return jsonify({"error": "org_id is required"}), 400

    user_type, user_id = get_user_identity(current_user)

    # ------------------------------------------
    # Get user's team ids (if recruiter)
    # ------------------------------------------
    team_ids = []
    memberships = TeamMember.query.filter_by(
        user_email=current_user["user_id"]
    ).all()

    for m in memberships:
        team_ids.append(str(m.team_id))

    # ------------------------------------------
    # Shared visibility check
    # ------------------------------------------
    shared_subquery = db.session.query(JobVisibilityTarget.id).join(
        JobVisibility,
        JobVisibility.id == JobVisibilityTarget.visibility_id
    ).filter(
        JobVisibility.job_id == Job.job_id,
        or_(
            # Shared to user
            and_(
                JobVisibilityTarget.target_type == "user",
                JobVisibilityTarget.target_id == user_id
            ),
            # Shared to team
            and_(
                JobVisibilityTarget.target_type == "team",
                JobVisibilityTarget.target_id.in_(team_ids)
            ),
            # Shared to organization
            and_(
                JobVisibilityTarget.target_type == "organization",
                JobVisibilityTarget.target_id == str(org_id)
            )
        )
    ).exists()


    # ------------------------------------------
    # Hiring Manager Assigned Jobs
    # ------------------------------------------

    assigned_hm_subquery = db.session.query(
        JobHiringManager.id
    ).filter(
        JobHiringManager.job_id == Job.job_id,
        JobHiringManager.manager_id == str(user_id)
    ).exists()

    # -------------------------------------------------
    # Hiring Manager → only assigned jobs
    # -------------------------------------------------

    if current_user["role"] == "hiring_manager":

        query = Job.query.filter(
            Job.org_id == org_id,
            assigned_hm_subquery
        )

    # -------------------------------------------------
    # Recruiters / Admins
    # -------------------------------------------------

    else:

        query = Job.query.filter(
            Job.org_id == org_id,
            or_(

                # Public jobs
                Job.is_private == False,

                # Owner jobs
                and_(
                    Job.created_by_type == user_type,
                    Job.created_by_id == user_id
                ),

                # Shared jobs
                shared_subquery
            )
        )

    if Job_status:
        query = query.filter_by(Job_status=Job_status)

    jobs = query.all()

    result = []
    for job in jobs:
        result.append({
            "job_id": job.job_id,
            "title": job.title,
            "Job_status": job.Job_status,
            "is_private": job.is_private,
            "created_by_type": job.created_by_type,
            "created_by_id": job.created_by_id,
            "created_at": to_ist(job.created_at),
            "updated_at": to_ist(job.updated_at)
        })

    return jsonify(result), 200

# ---------------- Get Job Details ----------------
@job_bp.route("/<string:job_id>", methods=["GET"])
@jwt_required
def get_job(job_id):
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    job = Job.query.filter_by(job_id=job_id).first()
    if not job:
        return jsonify({"error": "Job not found"}), 404

    user_type, user_id = get_user_identity(current_user)

    # ------------------------------------------
    # Get user's team ids (if recruiter)
    # ------------------------------------------
    team_ids = []

    try:

        memberships = TeamMember.query.filter_by(
            user_email=current_user["user_id"]
        ).all()

        for m in memberships:
            team_ids.append(str(m.team_id))

    except Exception:
        pass

    # ------------------------------------------
    # Shared visibility check
    # ------------------------------------------
    shared = db.session.query(JobVisibilityTarget.id).join(
        JobVisibility,
        JobVisibility.id == JobVisibilityTarget.visibility_id
    ).filter(
        JobVisibility.job_id == job.job_id,
        or_(
            # Shared to user
            and_(
                JobVisibilityTarget.target_type == "user",
                JobVisibilityTarget.target_id == user_id
            ),
            # Shared to team
            and_(
                JobVisibilityTarget.target_type == "team",
                JobVisibilityTarget.target_id.in_(team_ids)
            ),
            # Shared to organization
            and_(
                JobVisibilityTarget.target_type == "organization",
                JobVisibilityTarget.target_id == str(job.org_id)
            )
        )
    ).first()

    # ------------------------------------------
    # Assigned Hiring Manager Check
    # ------------------------------------------

    assigned_hm = JobHiringManager.query.filter_by(
        job_id=job.job_id,
        manager_id=str(user_id)
    ).first()
    # ------------------------------------------
    # Final Access Check
    # ------------------------------------------
    if (
        job.is_private
        and not is_owner(job, current_user)
        and not shared
        and not assigned_hm
    ):
        return jsonify({
            "error": "You are not allowed to view this job"
        }), 403

    # ---------------- Skills ----------------
    skill_req = JobSkillRequirement.query.filter_by(job_id=job.job_id).first()

    mandatory_skills = (
        skill_req.mandatory_skills.split(",")
        if skill_req and skill_req.mandatory_skills
        else []
    )

    optional_skills = (
        skill_req.optional_skills.split(",")
        if skill_req and skill_req.optional_skills
        else []
    )

    # ---------------- Experience ----------------
    experience = {
        "min_years": job.experience.min_years if job.experience else None,
        "max_years": job.experience.max_years if job.experience else None
    }

    # ---------------- Salary ----------------
    salary_range = None
    if job.salary:
        salary_range = {
            "min": job.salary.min_salary,
            "max": job.salary.max_salary,
            "currency": job.salary.currency,
            "salary_type": job.salary.salary_type
        }


        
    hiring_managers = []

    job_hms = JobHiringManager.query.filter_by(
        job_id=job.job_id
    ).all()

    for mapping in job_hms:

        hm = HiringManager.query.filter_by(
            manager_id=mapping.manager_id
        ).first()

        if hm:

            hiring_managers.append({
                "manager_id": hm.manager_id,
                "name": hm.name,
                "email": hm.email,
                "phone": hm.phone,
                "email_verified": hm.email_verified,
                "is_onboarding_completed":
                    hm.is_onboarding_completed
            })

    result = {
        "job_id": job.job_id,
        "org_id": job.org_id,
        "title": job.title,
        "description": job.description,
        "Job_status": job.Job_status,
        "job_public_link": job.job_public_link,
        "can_apply": (job.Job_status == "published"),
        "is_private": job.is_private,
        "created_by_type": job.created_by_type,
        "created_by_id": job.created_by_id,
        "min_notice_period": job.min_notice_period,
        "max_notice_period": job.max_notice_period,
        "mandatory_skills": mandatory_skills,
        "hiring_managers": hiring_managers,
        "optional_skills": optional_skills,
        "location": job.location,
        "work_mode": parse_work_mode(job.work_mode),
        "job_type": job.job_type,
        "contract_duration": job.contract_duration,
        "experience": experience,
        "salary_range": salary_range,
        "created_at": to_ist(job.created_at),
        "updated_at": to_ist(job.updated_at)
    }

    try:
        create_log(
            current_user["user_id"],
            action="get_job_details",
            entity_type="Job",
            entity_id=job.job_id,
            data={
                "title": job.title,
                "Job_status": job.Job_status,
                "is_private": job.is_private
            }
        )
    except Exception as e:
        print(f"[AuditLog Error] Failed to log get_job: {e}")

    return jsonify(result), 200






@job_bp.route("/<string:job_id>/share", methods=["POST"])
@jwt_required
def share_job(job_id):
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    job = Job.query.filter_by(job_id=job_id).first()
    if not job:
        return jsonify({"error": "Job not found"}), 404

    # ✅ Only owner can share
    if not is_owner(job, current_user):
        return jsonify({"error": "You are not allowed to share this job"}), 403

    data = request.get_json() or {}
    targets = data.get("targets", [])
    notify = data.get("notify", False)

    if not targets or not isinstance(targets, list):
        return jsonify({"error": "targets must be a non-empty list"}), 400

    user_type, user_id = get_user_identity(current_user)

    # -----------------------------------
    # Get or Create Visibility Record
    # -----------------------------------
    visibility = JobVisibility.query.filter_by(
        job_id=job_id
    ).first()

    if not visibility:
        visibility = JobVisibility(
            job_id=job_id,
            org_id=job.org_id,
            owner_type=user_type,
            owner_id=user_id,
            shared_by_type=user_type,
            shared_by_id=user_id
        )
        db.session.add(visibility)
        db.session.flush()

    added_targets = []

    for target in targets:
        t_type = target.get("type")
        t_value = target.get("value")

        if not t_type or not t_value:
            continue

        # -----------------------------------
        # ✅ Validate Target Type
        # -----------------------------------
        if t_type not in ["user", "team", "organization"]:
            return jsonify({
                "error": f"Invalid target type: {t_type}"
            }), 400

        # -----------------------------------
        # ✅ Organization Validation
        # -----------------------------------
        if t_type == "organization":
            if str(t_value) != str(job.org_id):
                return jsonify({
                    "error": "You can only share to the same organization"
                }), 400

        # -----------------------------------
        # Prevent duplicate sharing
        # -----------------------------------
        exists = JobVisibilityTarget.query.filter_by(
            visibility_id=visibility.id,
            target_type=t_type,
            target_id=str(t_value)
        ).first()

        if exists:
            continue

        db.session.add(
            JobVisibilityTarget(
                visibility_id=visibility.id,
                target_type=t_type,
                target_id=str(t_value)
            )
        )

        added_targets.append({
            "type": t_type,
            "id": t_value
        })

    if not added_targets:
        return jsonify({"message": "Job already shared"}), 200

    db.session.commit()

    if notify:
        for target in targets:

            # 🔥 Only send email to direct users
            if target.get("type") != "user":
                continue

            target_email = target.get("value")

            target_user = (
                SuperAdmin.find_by_email(target_email)
                or Admin.find_by_email(target_email)
                or OrgRecruiter.find_by_email(target_email)
            )

            if not target_user:
                continue

            try:
                send_job_shared_email(
                    to_email=target_user.email,
                    to_name=getattr(target_user, "name", "Recruiter"),
                    job_title=job.title,
                    job_id=job.job_id,
                    shared_by_name=current_user.get("name", current_user["user_id"]),
                    shared_by_email=current_user["user_id"]
                )
            except Exception as e:
                print(f"[WARN] Failed to send job share email to {target_email}: {e}")

    # -----------------------------------
    # Logging
    # -----------------------------------
    create_log(
        current_user["user_id"],
        action="share_job",
        entity_type="Job",
        entity_id=job_id,
        data={
            "shared_with": added_targets,
            "notify": notify
        }
    )

    return jsonify({
        "message": "Job shared successfully",
        "job_id": job_id,
        "shared_with": added_targets,
        "notify": notify
    }), 200



# ---------------------------------------------------------
# ASSIGN / UPDATE HIRING MANAGER
# ---------------------------------------------------------
@job_bp.route(
    "/<string:job_id>/assign-hiring-manager",
    methods=["PATCH"]
)
@jwt_required
def assign_hiring_manager(job_id):

    current_user = get_current_user()

    if not current_user:
        return jsonify({
            "error": "Unauthorized"
        }), 401

    # -------------------------------------------------
    # Get Job
    # -------------------------------------------------
    job = Job.query.filter_by(
        job_id=job_id
    ).first()

    if not job:
        return jsonify({
            "error": "Job not found"
        }), 404

    # -------------------------------------------------
    # Ownership Check
    # -------------------------------------------------
    if not is_owner(job, current_user):

        return jsonify({
            "error": (
                "You are not allowed to assign "
                "hiring manager to this job"
            )
        }), 403

    # -------------------------------------------------
    # Parse Request
    # -------------------------------------------------
    data = request.get_json(
        force=True,
        silent=True
    ) or {}

    hiring_manager_ids = data.get(
        "hiring_manager_ids",
        []
    )

    # -------------------------------------------------
    # Validation
    # -------------------------------------------------
    if not isinstance(hiring_manager_ids, list):

        return jsonify({
            "error":
                "hiring_manager_ids must be a list"
        }), 400

    try:

        # -------------------------------------------------
        # Remove Existing Hiring Managers
        # -------------------------------------------------
        JobHiringManager.query.filter_by(
            job_id=job.job_id
        ).delete()

        assigned_hms = []

        # -------------------------------------------------
        # Assign New Hiring Managers
        # -------------------------------------------------
        for hm_id in hiring_manager_ids:

            hiring_manager = HiringManager.query.filter_by(
                manager_id=hm_id,
                org_id=current_user["org_id"]
            ).first()

            if not hiring_manager:

                db.session.rollback()

                return jsonify({
                    "error":
                        f"Invalid hiring manager: {hm_id}"
                }), 400

            db.session.add(
                JobHiringManager(
                    job_id=job.job_id,
                    manager_id=hm_id
                )
            )

            assigned_hms.append({
                "manager_id":
                    hiring_manager.manager_id,

                "name":
                    hiring_manager.name
            })

        # -------------------------------------------------
        # Update Timestamp
        # -------------------------------------------------
        job.updated_at = datetime.utcnow()

        db.session.commit()

        # -------------------------------------------------
        # Logging
        # -------------------------------------------------
        create_log(
            current_user["user_id"],
            action="assign_hiring_manager",
            entity_type="Job",
            entity_id=job.job_id,
            data={
                "job_title": job.title,
                "assigned_hiring_managers":
                    assigned_hms
            }
        )

        # -------------------------------------------------
        # Response
        # -------------------------------------------------
        return jsonify({
            "message":
                "Hiring managers updated successfully",

            "job_id":
                job.job_id,

            "hiring_managers":
                assigned_hms
        }), 200

    except Exception as e:

        db.session.rollback()

        return jsonify({
            "error": str(e)
        }), 400