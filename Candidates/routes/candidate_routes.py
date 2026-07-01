
from flask import Blueprint, request, jsonify, current_app,g
from extensions import db
from Candidates.models.candidate import Candidate, Degree, Skill, WorkHistory, Certification
from Candidates.models.resume import Resume
import jwt
from datetime import datetime
from Organization.models.organization_form_link import OrganizationFormLink
import json
from jobs.models.job_candidate_model import JobCandidate
from jobs.models.job_model import Job
from Candidates.routes.job_candidate_journey_routes import JobCandidateJourney
from common.models.document_asset import DocumentAsset
from auth.utils.jwt_required import jwt_required
from Logs.log_helper import create_log

#New for candidate Details show and update
from flask_jwt_extended import jwt_required, get_jwt_identity
from auth.candidate.models.candidate_user import CandidateUser
from werkzeug.security import check_password_hash, generate_password_hash

from sqlalchemy.orm.attributes import flag_modified



candidate_bp = Blueprint("candidate_bp", __name__, url_prefix="/api/candidate")


#New for candidate Details show
@candidate_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_candidate_profile():
    user_id = get_jwt_identity()

    user = CandidateUser.query.filter_by(user_id=user_id).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "user_id": user.user_id,
        "email": user.email,
        "phone": user.phone,
        "profile_data": user.profile_data or {}
    }), 200
    
    
#New for candidate Details  update


@candidate_bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_candidate_profile():

    user_id = get_jwt_identity()

    data = request.get_json() or {}

    user = CandidateUser.query.filter_by(
        user_id=user_id
    ).first()

    if not user:
        return jsonify({
            "error": "User not found"
        }), 404

    # =====================================================
    # PHONE UPDATE
    # =====================================================

    if "phone" in data:
        user.phone = data["phone"]

    # =====================================================
    # PASSWORD UPDATE
    # =====================================================

    current_password = data.get("current_password")
    new_password = data.get("new_password")

    if current_password and new_password:

        if not check_password_hash(
            user.password_hash,
            current_password
        ):
            return jsonify({
                "error": "Current password incorrect"
            }), 400

        user.password_hash = generate_password_hash(
            new_password
        )

    # =====================================================
    # PROFILE DATA UPDATE
    # =====================================================

    profile_updates = data.get("profile_data", {})

    if not user.profile_data:
        user.profile_data = {}

    # merge old + new
    updated_profile = {
        **user.profile_data,
        **profile_updates
    }

    user.profile_data = updated_profile

    # VERY IMPORTANT
    flag_modified(user, "profile_data")

    db.session.commit()

    return jsonify({
        "message": "Profile updated successfully",
        "profile_data": user.profile_data
    }), 200







# ------------------ Helper: Clean hidden characters ------------------
def clean_value(val):
    if isinstance(val, str):
        return val.strip().replace("\u202a", "").replace("\u202c", "")
    return val


# ------------------ Helper: Verify if emails/phones are verified ------------------
"""
def check_verification(candidate, data):
    # Only primary email and phone must be verified
    primary_fields = [
        ("email", "email_verified"),
        ("phone", "phone_verified"),
    ]

    for field, verified_field in primary_fields:
        value = clean_value(data.get(field))
        if value and not getattr(candidate, verified_field, False):
            return False, f"Primary {field} ({value}) is not verified."

    # Secondary & tertiary emails/phones do not require verification
    return True, None
"""

def get_request_data():
    """
    Supports:
    - application/json
    - multipart/form-data with `data` JSON field
    - plain form-data
    """
    if request.is_json:
        data = request.get_json(force=True)
        if isinstance(data, str):
            return json.loads(data)
        return data

    if request.form.get("data"):
        return json.loads(request.form.get("data"))

    return request.form.to_dict()



def get_current_user():
    if not hasattr(g, "current_user"):
        return None
    return g.current_user




def check_verification(candidate, data):
    # Only primary email must be verified
    value = clean_value(data.get("email"))
    if value and not getattr(candidate, "email_verified", False):
        return False, f"Primary email ({value}) is not verified."

    return True, None

# =====================================================================
#                        COMPLETE FORM ROUTE
# =====================================================================

@candidate_bp.route("/complete-form/<token>", methods=["GET", "POST"])
def complete_candidate_form(token):

    # ------------------ VALIDATE TOKEN ------------------
    try:
        decoded = jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
        email = decoded.get("email")
        if not email:
            return jsonify({"status": "error", "message": "Email missing from token"}), 400

    except jwt.ExpiredSignatureError:
        return jsonify({"status": "error", "message": "Link expired"}), 400
    except jwt.InvalidTokenError:
        return jsonify({"status": "error", "message": "Invalid or malformed link"}), 400

    # ------------------ FETCH CANDIDATE ------------------
    candidate = Candidate.query.filter_by(email=email).first()
    if not candidate:
        return jsonify({"status": "error", "message": "Candidate not found"}), 404

    # =====================================================================
    #                                GET
    # =====================================================================
    if request.method == "GET":
        try:
            data = candidate.to_dict()
            return jsonify({
                "status": "success",
                "message": "Valid token",
                **data,
                "form_url": f"{current_app.config['FRONTEND_BASE_URL']}/#/candidateform?token={token}"
            }), 200

        except Exception as e:
            current_app.logger.error(f"[Candidate GET Error] {e}")
            return jsonify({"status": "error", "message": "Failed to load form data"}), 500

    # =====================================================================
    #                                POST
    # =====================================================================
    # Load JSON safely
    try:
        data = get_request_data()
    except Exception as e:
        return jsonify({"status": "error", "message": f"Invalid JSON: {e}"}), 400

    try:
        # ------------------ UPDATE VERIFIED FIELDS FIRST ------------------
        verification_map = [
            ("email_verified", "email_verified"),
            ("email2_verified", "email2_verified"),
            ("email3_verified", "email3_verified"),
        ]
        """("phone_verified", "phone_verified"),
            ("phone2_verified", "phone2_verified"),
            ("phone3_verified", "phone3_verified"),   
        """

        for json_field, model_field in verification_map:
            if data.get(json_field) is True:
                setattr(candidate, model_field, True)

        # ------------------ Now check verification ------------------
        verified, message = check_verification(candidate, data)
        if not verified:
            return jsonify({"status": "error", "message": message}), 400

        # ------------------ UPDATE SCALAR FIELDS ------------------
        scalar_fields = [
            "name", "current_full_address", "current_location", "current_pincode",
            "permanent_full_address", "permanent_location", "permanent_pincode",
            "linkedin", "portfolio", "github_url",
            "expected_package", "domain", "notice_period","key_skills","availability",
            "total_experience",
            "email", "email_2", "email_3",
            "phone", "phone_2", "phone_3"
        ]

        for field in scalar_fields:
            val = clean_value(data.get(field))

            # Always update phone_2 and phone_3
            if field in ["phone_2", "phone_3"]:
                setattr(candidate, field, val or "")
            else:
                if val not in [None, ""]:
                    setattr(candidate, field, val)


        # ------------------ BOOLEAN FIELDS ------------------
        candidate.same_as_current = data.get("same_as_current", candidate.same_as_current)
        candidate.authorized_to_work = data.get("authorized_to_work", candidate.authorized_to_work)
        candidate.relocation = data.get("relocation", candidate.relocation)
        candidate.declaration_consent = data.get("declaration_consent", candidate.declaration_consent)
        candidate.immediate_joiner = data.get("immediate_joiner", candidate.immediate_joiner)
        # ------------------ KEY SKILLS & AVAILABILITY ------------------
        candidate.key_skills = data.get("key_skills", candidate.key_skills)
        candidate.availability = data.get("availability", candidate.availability or [])
        # ------------------ NEW FIELDS ------------------

        # Preferred Locations
        candidate.preferred_locations = data.get(
            "preferred_locations",
            candidate.preferred_locations or []
        )

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
        candidate.notes = data.get("notes", candidate.notes or "")

        # ------------------ SAME AS CURRENT LOGIC ------------------
        if candidate.same_as_current:
            candidate.permanent_full_address = candidate.current_full_address
            candidate.permanent_location = candidate.current_location
            candidate.permanent_pincode = candidate.current_pincode

        # ------------------ FINAL METADATA ------------------
        candidate.added_by = "candidate_form_completed"
        candidate.token = None
        candidate.status = "completed"

        # ------------------ PARSE ARRAY FIELDS ------------------
        def parse_array(field):
            val = data.get(field, [])
            if isinstance(val, str):
                try:
                    val = json.loads(val)
                except:
                    return []
            return val if isinstance(val, list) else []

        # ------------------ CLEAR OLD RELATED DATA ------------------
        
        Certification.query.filter_by(cand_id=candidate.cand_id).delete()
        Degree.query.filter_by(cand_id=candidate.cand_id).delete()
        Skill.query.filter_by(cand_id=candidate.cand_id).delete()
        WorkHistory.query.filter_by(cand_id=candidate.cand_id).delete()
        db.session.flush()

        # ------------------ CERTIFICATIONS ------------------
        for cert in parse_array("certifications"):
            if cert.get("certificate"):
                db.session.add(Certification(
                    cand_id=candidate.cand_id,
                    certificate=cert.get("certificate"),
                    completion_year=cert.get("completion_year"),
                    valid_upto=cert.get("valid_upto")
                ))

        # ------------------ SKILLS ------------------
        for sk in parse_array("skills"):
            name = sk.get("skill_name") or sk.get("skill")
            exp = sk.get("skill_experience") or sk.get("experience")
            if name:
                db.session.add(Skill(
                    cand_id=candidate.cand_id,
                    skill_name=name,
                    skill_experience=exp
                ))

        

        # ------------------ WORK HISTORY ------------------
        for wh in parse_array("work_history"):
            if wh.get("organization"):

                designations = wh.get("designations")
                if not isinstance(designations, list):
                    designations = []

                db.session.add(WorkHistory(
                    cand_id=candidate.cand_id,
                    organization=clean_value(wh.get("organization")),
                    org_start_year=wh.get("org_start_year"),
                    org_start_month=wh.get("org_start_month"),
                    org_end_year=wh.get("org_end_year"),
                    org_end_month=wh.get("org_end_month"),
                    designations=designations   # <-- store as list directly
                ))


        # ------------------ EDUCATION ------------------
        education_list = data.get("education", [])

    

        for edu in education_list:
            degree = Degree(
                cand_id=candidate.cand_id,
                degree_name=edu.get("degree_name"),
                major=edu.get("major"),
                minor=edu.get("minor"),
                score=edu.get("score"),
                start_year=edu.get("start_year"),
                end_year=edu.get("end_year"),
                start_month=edu.get("start_month"),
                end_month=edu.get("end_month")
            )
            db.session.add(degree)

        # =================================================
        # DOCUMENT ASSET LINKING (UPDATED)
        # =================================================
        resume_id = data.get("resume_id")
        cover_letter_id = data.get("cover_letter_id")

        resume_asset = None
        cover_asset = None

        if resume_id:
            resume_asset = DocumentAsset.query.filter_by(
                docu_id=resume_id,
                document_type="resume",
                org_id=candidate.org_id
                
            ).first()
            if not resume_asset:
                return jsonify({"status": "error", "message": "Invalid resume"}), 400

        if cover_letter_id:
            cover_asset = DocumentAsset.query.filter_by(
                docu_id=cover_letter_id,
                document_type="cover_letter",
                org_id=candidate.org_id
            ).first()
            if not cover_asset:
                return jsonify({"status": "error", "message": "Invalid cover letter"}), 400

        if resume_asset or cover_asset:
            resume_row = Resume(
                cand_id=candidate.cand_id,
                org_id=candidate.org_id, 
                resume_file=resume_asset.file_key if resume_asset else None,
                cover_letter_file=cover_asset.file_key if cover_asset else None,
                original_filename=resume_asset.original_filename if resume_asset else None,
                cover_letter_filename=cover_asset.original_filename if cover_asset else None,
                mime_type=resume_asset.mime_type if resume_asset else None,
                cover_letter_mime_type=cover_asset.mime_type if cover_asset else None,
                file_size=resume_asset.file_size if resume_asset else None,
                cover_letter_size=cover_asset.file_size if cover_asset else None,
                uploaded_at=datetime.utcnow(),
                source="candidate_form"
            )

            db.session.add(resume_row)
            db.session.flush()

            candidate.primary_resume_id = resume_row.id

            if resume_asset:
                resume_asset.cand_id = candidate.cand_id
                resume_asset.is_linked = True

            if cover_asset:
                cover_asset.cand_id = candidate.cand_id
                cover_asset.is_linked = True

        db.session.commit()


        return jsonify({
            "status": "success",
            "message": "Candidate form submitted successfully",
            "cand_id": candidate.cand_id,
            "org_id": candidate.org_id
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[Candidate Form POST Error] {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ------------------ Public Candidate Form (GET) ------------------
@candidate_bp.route("/org-form/<token>", methods=["GET"])
def get_org_form(token):
    form_link = OrganizationFormLink.query.filter_by(token=token).first()
    if not form_link:
        return jsonify({"error": "Invalid or expired form link"}), 404

    form_structure = {
        "personal_fields": [
            "name",
            "email", "email_2", "email_3",
            "email_verified", "email2_verified", "email3_verified",
            "phone", "phone_2", "phone_3",
            #phone_verified", "phone2_verified", "phone3_verified",
            "current_full_address", "current_location", "current_pincode",
            "same_as_current",
            "permanent_full_address", "permanent_location", "permanent_pincode",
            "linkedin", "portfolio", "github_url",
            "expected_package", "domain", "notice_period", "immediate_joiner",
            "preferred_locations",
            "offer_status",
            "offers",
            "notes",

            # ✅ ADD THESE
            "key_skills",
            "availability",
        ],
        "meta_fields": [
            "total_experience", "authorized_to_work",
            "relocation", "declaration_consent",
        ],
        "education_fields": [
            "degree", "start_year", "start_month",
            "end_year", "end_month", "major", "minor", "score"
        ],
        "certification_fields": ["certificate", "completion_year", "valid_upto"],
        "skill_fields": ["skill", "experience"],
        "work_history_fields": [
            "organization", "org_start_year", "org_start_month",
            "org_end_year", "org_end_month", "designations"
        ],
        "org_id": form_link.org_id
    }
    return jsonify(form_structure), 200


# ------------------ Public Candidate Form (POST) ------------------
@candidate_bp.route("/org-form/<token>", methods=["POST"])
def submit_org_form(token):
    form_link = OrganizationFormLink.query.filter_by(token=token).first()
    if not form_link:
        return jsonify({"error": "Invalid or expired form link"}), 404

    # Load JSON safely
    try:
        data = get_request_data()
    except Exception as e:
        return jsonify({"status": "error", "message": f"Invalid JSON: {str(e)}"}), 400

    org_id = form_link.org_id
    job_id = data.get("job_id")
    job_mapping_done = False

    # Validate job if provided
    if job_id:
        job = Job.query.filter_by(job_id=job_id).first()
        if not job:
            return jsonify({"error": "Invalid job_id"}), 404
        if job.Job_status == "closed":
            return jsonify({"error": "This job is closed."}), 403

    # ---------------- Emails & Phones ----------------
    email = data.get("email")
    phone = data.get("phone")

    # Check primary email/phone
    if not email:
        return jsonify({"error": "Primary email is required"}), 400
    
    if not phone:
        return jsonify({"error": "Primary phone is required"}), 400
    
    email_verified = data.get("email_verified", False)
    #phone_verified = data.get("phone_verified", False)

    if not email_verified:
        return jsonify({"error": "Primary email must be verified"}), 400
    """
    if not phone_verified:
        return jsonify({"error": "Primary phone must be verified"}), 400
    """
    # Optional secondary emails/phones
    email_2 = data.get("email_2")
    email_3 = data.get("email_3")
    phone_2 = data.get("phone_2")
    phone_3 = data.get("phone_3")

    email2_verified = data.get("email2_verified", False)
    email3_verified = data.get("email3_verified", False)
    #phone2_verified = data.get("phone2_verified", False)
    #phone3_verified = data.get("phone3_verified", False)
    
    
    offer_status = data.get("offer_status", "no_offer")
    offers = data.get("offers") or []

    offers = offers[:3]

    offers = [
        o for o in offers
        if isinstance(o, dict)
    ]

    # ---------------- Create candidate ----------------
    new_candidate = Candidate(
        name=data.get("name") or "N/A",
        email=email,
        email_2=email_2,
        email_3=email_3,
        phone=phone,
        phone_2=phone_2,
        phone_3=phone_3,
        email_verified=email_verified,
        email2_verified=email2_verified,
        email3_verified=email3_verified,
        #phone_verified=phone_verified,
        #phone2_verified=phone2_verified,
        #phone3_verified=phone3_verified,
        current_full_address=data.get("current_full_address") or "",
        current_location=data.get("current_location") or {"value": "", "label": ""},
        current_pincode=data.get("current_pincode") or "",
        same_as_current=data.get("same_as_current", False),
        permanent_full_address=data.get("permanent_full_address") or "",
        permanent_location=data.get("permanent_location") or {"value": "", "label": ""},
        permanent_pincode=data.get("permanent_pincode") or "",
        linkedin=data.get("linkedin") or "",
        portfolio=data.get("portfolio") or "",
        github_url=data.get("github_url") or "",
        total_experience=data.get("total_experience") or "",
        
        authorized_to_work=data.get("authorized_to_work") or False,
        relocation=data.get("relocation") or "",
        declaration_consent=data.get("declaration_consent", False),
        expected_package=data.get("expected_package") or {"min": "", "max": ""},
        domain=data.get("domain") or "",
        notice_period=data.get("notice_period") or {"official": "", "expected": "", "last_working_day": ""},
        immediate_joiner=data.get("immediate_joiner", False),
        key_skills=data.get("key_skills")or "",
        availability=data.get("availability", []),
        preferred_locations=data.get("preferred_locations", []),
        offer_status=offer_status,
        offers=offers,
        notes=data.get("notes", ""),
        org_id=org_id,
        status="completed",
        added_by="public_form"
    )

    
    if new_candidate.same_as_current:
        new_candidate.permanent_full_address = new_candidate.permanent_full_address or new_candidate.current_full_address
        new_candidate.permanent_location = new_candidate.permanent_location or new_candidate.current_location
        new_candidate.permanent_pincode = new_candidate.permanent_pincode or new_candidate.current_pincode

    db.session.add(new_candidate)
    db.session.flush()


    
    # =================================================
    # LINK DOCUMENT ASSETS (RESUME + COVER LETTER)
    # =================================================
    resume_id = data.get("resume_id")
    cover_letter_id = data.get("cover_letter_id")

    resume_asset = None
    cover_asset = None

    if resume_id:
        resume_asset = DocumentAsset.query.filter_by(
            docu_id=resume_id,
            document_type="resume",
            org_id=org_id
        ).first()

        if not resume_asset:
            return jsonify({
                "status": "error",
                "message": "Invalid or already linked resume"
            }), 400

    if cover_letter_id:
        cover_asset = DocumentAsset.query.filter_by(
            docu_id=cover_letter_id,
            document_type="cover_letter",
            org_id=org_id
        ).first()

        if not cover_asset:
            return jsonify({
                "status": "error",
                "message": "Invalid or already linked cover letter"
            }), 400

    # ---------------- CREATE RESUME ROW ----------------
    if resume_asset or cover_asset:
        resume_row = Resume(
            cand_id=new_candidate.cand_id,
            org_id=org_id,

            resume_file=resume_asset.file_key if resume_asset else None,
            cover_letter_file=cover_asset.file_key if cover_asset else None,

            original_filename=resume_asset.original_filename if resume_asset else None,
            cover_letter_filename=cover_asset.original_filename if cover_asset else None,

            mime_type=resume_asset.mime_type if resume_asset else None,
            cover_letter_mime_type=cover_asset.mime_type if cover_asset else None,

            file_size=resume_asset.file_size if resume_asset else None,
            cover_letter_size=cover_asset.file_size if cover_asset else None,

            uploaded_at=datetime.utcnow(),
            source="public_form"
        )

        db.session.add(resume_row)
        db.session.flush()

        # ✅ primary resume
        new_candidate.primary_resume_id = resume_row.id

        # ✅ link assets
        if resume_asset:
            resume_asset.cand_id = new_candidate.cand_id
            resume_asset.is_linked = True
            db.session.add(resume_asset)

        if cover_asset:
            cover_asset.cand_id = new_candidate.cand_id
            cover_asset.is_linked = True
            db.session.add(cover_asset)


    # ------------------ Default Candidate Visibility ------------------
    from Candidates.utils.candidate_visibility_helper import (
        create_default_candidate_visibility
    )

    # Public form → no logged-in recruiter
    # Visibility will be owned by SYSTEM / ORG
    create_default_candidate_visibility(
        cand_id=new_candidate.cand_id,
        creator_user=None,
        org_id=org_id,
        source="public_form"
    )
            

    # ---------------- Helper: parse array fields ----------------
    def parse_json_field(field_name):
        val = data.get(field_name, [])
        if isinstance(val, str):
            try:
                val = json.loads(val)
            except:
                val = []
        return val

    
    # ---------------- Education ----------------
    # ---------------- Education ----------------
    educations = parse_json_field("education")
    for edu in educations:
        if not isinstance(edu, dict):
            continue

        degree_name = (edu.get("degree_name") or "").strip()

        if degree_name:
            db.session.add(Degree(
                cand_id=new_candidate.cand_id,
                degree_name=degree_name,
                start_year=edu.get("start_year"),
                start_month=edu.get("start_month"),
                end_year=edu.get("end_year"),
                end_month=edu.get("end_month"),
                major=edu.get("major"),
                minor=edu.get("minor"),
                score=edu.get("score"),
            ))

    # ---------------- Skills ----------------
    # Skills
    skills_to_insert = []
    skills = parse_json_field("skills")
    for skill in skills:
        skill_name = skill.get("skill")
        if skill_name and skill_name.strip():
            skills_to_insert.append({"skill": skill_name.strip(), "experience": skill.get("experience")})
    i = 0
    while True:
        skill_name = data.get(f"skill_name_{i}")
        if not skill_name:
            break
        skill_experience = data.get(f"skill_experience_{i}")
        if skill_name.strip() and not any(s["skill"] == skill_name.strip() for s in skills_to_insert):
            skills_to_insert.append({"skill": skill_name.strip(), "experience": skill_experience})
        i += 1
    for skill in skills_to_insert:
        db.session.add(Skill(cand_id=new_candidate.cand_id, skill_name=skill["skill"], skill_experience=skill.get("experience")))

    # ---------------- Certifications ----------------
    for cert in parse_json_field("certifications"):
        if cert.get("certificate"):
            db.session.add(Certification(
                cand_id=new_candidate.cand_id,
                certificate=cert.get("certificate"),
                completion_year=cert.get("completion_year"),
                valid_upto=cert.get("valid_upto")
            ))

    # ---------------- Work History ----------------
    for wh in parse_json_field("work_history"):
        if wh.get("organization"):
            db.session.add(WorkHistory(
                cand_id=new_candidate.cand_id,
                organization=wh.get("organization"),
                org_start_year=wh.get("org_start_year"),
                org_start_month=wh.get("org_start_month"),
                org_end_year=wh.get("org_end_year"),
                org_end_month=wh.get("org_end_month"),
                designations=wh.get("designations")
            ))

    # ---------------- Job Mapping ----------------
    if job_id:
        mapping = JobCandidate.query.filter_by(job_id=job_id, cand_id=new_candidate.cand_id).first()
        if not mapping:
            db.session.add(JobCandidate(
                job_id=job_id,
                cand_id=new_candidate.cand_id,
                status="Uploaded"
            ))

        journey = JobCandidateJourney.query.filter_by(job_id=job_id, cand_id=new_candidate.cand_id).first()
        if not journey:
            db.session.add(JobCandidateJourney(
                job_id=job_id,
                cand_id=new_candidate.cand_id,
                added_by="public_form",
                status="shared",
                visible_to_recruiter=True,
                visible_to_candidate=False
            ))

        job_mapping_done = True

    db.session.commit()

    return jsonify({
        "data": {
            "cand_id": new_candidate.cand_id,
            "org_id": org_id,
            "job_id": job_id,
            "job_mapping": "done" if job_mapping_done else "skipped",
            "added_by": new_candidate.added_by
        },
        "status": "success"
    }), 201



@candidate_bp.route("/<string:cand_id>/screen", methods=["PUT"])
@jwt_required
def screen_candidate(cand_id):

    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    # ---------- Get Candidate ----------
    candidate = Candidate.query.filter_by(cand_id=cand_id).first()

    if not candidate:
        return jsonify({"error": "Candidate not found"}), 404

    # ---------- Normalize status ----------
    current_status = (candidate.status or "").strip().lower()

    # ---------- Validate State ----------
    if current_status != "completed":
        return jsonify({
            "error": f"Candidate must be in 'completed' state. Current: {candidate.status}"
        }), 400

    # ---------- Update ----------
    candidate.status = "screened"
    db.session.commit()

    # ---------- Log ----------
    create_log(
        current_user["user_id"],
        action="SCREEN_CANDIDATE",
        entity_type="Candidate",
        entity_id=cand_id,
        data={"status": "screened"}
    )

    return jsonify({
        "message": "Candidate screened successfully",
        "data": {
            "cand_id": cand_id,
            "status": candidate.status
        }
    }), 200