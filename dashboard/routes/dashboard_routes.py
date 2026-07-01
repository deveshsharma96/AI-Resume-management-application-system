#NOTE:
# Phone verification is disabled.
# Phone numbers are stored only, not verified.
import Candidates
from flask import Blueprint, request, jsonify, current_app
from extensions import db
from Candidates.models.candidate import Candidate, Skill, Degree, WorkHistory, Certification, generate_cand_id
from Candidates.models.resume import Resume
# from Candidates.utils.resume_parser import parse_resume
#New for ai parser
from Candidates.utils.ai_parser import parse_resume_ai
from Candidates.utils.resume_parser import parse_resume

from Candidates.utils.parser_settings import get_parser_type, set_parser_type


from Candidates.utils.email_fetcher import fetch_resumes_from_email
from Candidates.utils.file_hash import generate_file_hash
from Organization.models.team import Team
import jwt
from datetime import datetime, timedelta
from Organization.utils.email_utils import send_candidate_form_link_email
import os
import json
from Candidates.models.parsed_candidate_temp import ParsedCandidateTemp
import uuid
from werkzeug.utils import secure_filename 
# Audit logging
from Logs.log_helper import create_log
# user models to resolve current user from header
from recruiter.models.recruiter_model import Recruiter
from Organization.models.super_admin import SuperAdmin
from recruiter.models.org_recruiter_model import OrgRecruiter
from recruiter.models.admin_model import Admin
import re
from common.utils.storage_service import upload_file
from common.models.document_asset import DocumentAsset
from auth.utils.jwt_required import jwt_required
from flask import g

from email_integration.model import EmailIntegration
from email_integration.service import connect_imap, refresh_access_token






#New default setting for candidate share 
from GlobalRecruiter.models.recruiter_default_share_target import (
    RecruiterDefaultShareTarget
)
from Candidates.services.candidate_share_service import (
    share_candidate_service
)





dashboard_bp = Blueprint("dashboard_bp", __name__)

# ------------------ Helper: JWT Token ------------------
def generate_jwt_token(email):
    payload = {
        "email": email,
        "exp": datetime.utcnow() + timedelta(days=2),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")


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


# ------------------ Helper: Resolve current user from header ------------------
def get_current_user():
    """
    Returns the authenticated user info populated by jwt_required middleware.
    """

    if not hasattr(g, "current_user"):
        return None

    return g.current_user


# ------------------ PREFILLED: Candidate opens link (token) ------------------
@dashboard_bp.route("/candidate/get-prefilled", methods=["GET"])

def get_prefilled():
    token = request.args.get("token")
    if not token:
        return jsonify({"status": "error", "message": "token is required"}), 400

    try:
        decoded = jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
        email = decoded.get("email")
        if not email:
            return jsonify({"status": "error", "message": "Email not in token"}), 400

        candidate = Candidate.query.filter_by(email=email).first()
        if not candidate:
            return jsonify({"status": "error", "message": "Candidate not found"}), 404

        actor = get_current_user()

        create_log(
            actor["user_id"] if actor else "candidate",
            action="view_candidate_prefilled",
            entity_type="Candidate",
            entity_id=candidate.cand_id,
            data={"via_token": True}
        )

        prefilled = {

            "cand_id": candidate.cand_id,
            "name": candidate.name,
            "email": candidate.email,
            "email_2": candidate.email_2,
            "email_3": candidate.email_3,
            "phone": candidate.phone,
            "phone_2": candidate.phone_2,
            "phone_3": candidate.phone_3,
            "email_verified": candidate.email_verified,
            "email2_verified": candidate.email2_verified,
            "email3_verified": candidate.email3_verified,
            """
            "phone_verified": candidate.phone_verified,
            "phone2_verified": candidate.phone2_verified,
            "phone3_verified": candidate.phone3_verified,

            """
            "current_full_address": candidate.current_full_address,
            "current_location": candidate.current_location,
            "current_pincode": candidate.current_pincode,
            "same_as_current": candidate.same_as_current,
            "permanent_full_address": candidate.permanent_full_address,
            "permanent_location": candidate.permanent_location,
            "permanent_pincode": candidate.permanent_pincode,
            "linkedin": candidate.linkedin,
            "portfolio": candidate.portfolio,
            "github_url": candidate.github_url,
            "expected_package": candidate.expected_package,
            "domain": candidate.domain,
            "notice_period": candidate.notice_period,
            "immediate_joiner": candidate.immediate_joiner,
            "key_skills": candidate.key_skills,
            "availability": candidate.availability or [],
            "authorized_to_work": candidate.authorized_to_work,
            "relocation": candidate.relocation,
            "declaration_consent": candidate.declaration_consent,
            "preferred_locations": candidate.preferred_locations or [],
            "offer_status": candidate.offer_status or "no_offer",
            "offers": candidate.offers or [],
            "notes": candidate.notes or "",
            "total_experience": candidate.total_experience
        }

        return jsonify({"status": "success", "prefilled": prefilled}), 200

    except jwt.ExpiredSignatureError:
        return jsonify({"status": "error", "message": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"status": "error", "message": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ------------------ 1️⃣ Basic Form (Send Email Link, No OTP) ------------------
@dashboard_bp.route("/add-candidate/basic-form", methods=["POST"])
@jwt_required
def add_basic():

    try:
        data = get_request_data()
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Invalid JSON: {str(e)}"
        }), 400

    # -------------------------------------------------
    # CURRENT USER (JWT)
    # -------------------------------------------------
    actor = get_current_user()

    if not actor:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    actor_email = actor["user_id"]
    org_id = actor["org_id"]

    # -------------------------------------------------
    # REQUIRED FIELD
    # -------------------------------------------------
    email = data.get("email")
    if not email:
        return jsonify({
            "status": "error",
            "message": "email is required"
        }), 400

    cand_id = generate_cand_id()
    token = generate_jwt_token(email)
    offer_status = data.get("offer_status", "no_offer")
    offers = data.get("offers") or []

    # keep max 3 offers (safety)
    offers = offers[:3]

    # basic cleanup (no strict validation)
    offers = [
        o for o in offers
        if isinstance(o, dict)
    ]

    # -------------------------------------------------
    # CREATE CANDIDATE
    # -------------------------------------------------
    candidate = Candidate(
        cand_id=cand_id,
        name=data.get("name"),
        email=email,
        email_2=data.get("email_2"),
        email_3=data.get("email_3"),

        phone=data.get("phone"),
        phone_2=data.get("phone_2"),
        phone_3=data.get("phone_3"),

        org_id=org_id,
        added_by=actor_email,

        token=token,
        status="completed",

        current_full_address=data.get("current_full_address"),
        current_location=data.get("current_location"),
        current_pincode=data.get("current_pincode"),
        same_as_current=data.get("same_as_current"),

        permanent_full_address=data.get("permanent_full_address"),
        permanent_location=data.get("permanent_location"),
        permanent_pincode=data.get("permanent_pincode"),

        authorized_to_work=data.get("authorized_to_work", False),
        relocation=data.get("relocation", ""),
        declaration_consent=data.get("declaration_consent", False),

        linkedin=data.get("linkedin"),
        portfolio=data.get("portfolio"),
        github_url=data.get("github_url"),

        key_skills=data.get("key_skills"),
        availability=data.get("availability", []),
        # preferred_locations=data.get("preferred_locations", []),
        # offer_status=offer_status,
        # offers=offers,
        notes=data.get("notes", ""),

        expected_package=data.get("expected_package"),
        domain=data.get("domain"),
        notice_period=data.get("notice_period"),
        immediate_joiner=data.get("immediate_joiner", False),
        total_experience=data.get("total_experience", "")
    )

    db.session.add(candidate)
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
            is_linked=False
        ).first()

        if not resume_asset:
            db.session.rollback()
            return jsonify({
                "status": "error",
                "message": "Invalid or already linked resume document"
            }), 400

    if cover_letter_id:
        cover_asset = DocumentAsset.query.filter_by(
            docu_id=cover_letter_id,
            document_type="cover_letter",
            is_linked=False
        ).first()

        if not cover_asset:
            db.session.rollback()
            return jsonify({
                "status": "error",
                "message": "Invalid or already linked cover letter document"
            }), 400

    # -------------------------------------------------
    # CREATE RESUME ROW IF ANY DOCUMENT EXISTS
    # -------------------------------------------------
    if resume_asset or cover_asset:
        resume_row = Resume(
            cand_id=cand_id,
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
            source="candidate_form"
        )

        db.session.add(resume_row)
        db.session.flush()

        candidate.primary_resume_id = resume_row.id

        if resume_asset:
            resume_asset.cand_id = cand_id
            resume_asset.is_linked = True
            db.session.add(resume_asset)

        if cover_asset:
            cover_asset.cand_id = cand_id
            cover_asset.is_linked = True
            db.session.add(cover_asset)

    # -------------------------------------------------
    # VISIBILITY
    # -------------------------------------------------
    from Candidates.utils.candidate_visibility_helper import (
        create_default_candidate_visibility
    )

    create_default_candidate_visibility(cand_id, actor)
    
    recruiter = OrgRecruiter.query.filter_by(
        email=actor_email,
        org_id=org_id
    ).first()


     

    # -------------------------------------------------
    # EDUCATION
    # -------------------------------------------------
    for edu in data.get("education", []):
        if edu.get("degree"):
            db.session.add(Degree(
                cand_id=cand_id,
                degree_name=edu.get("degree"),
                start_year=edu.get("start_year"),
                start_month=edu.get("start_month"),
                end_year=edu.get("end_year"),
                end_month=edu.get("end_month"),
                major=edu.get("major"),
                minor=edu.get("minor"),
                score=edu.get("score")
            ))

    # -------------------------------------------------
    # CERTIFICATIONS
    # -------------------------------------------------
    for cert in data.get("certifications", []):
        if cert.get("certificate"):
            db.session.add(Certification(
                cand_id=cand_id,
                certificate=cert.get("certificate"),
                completion_year=cert.get("completion_year"),
                valid_upto=cert.get("valid_upto")
            ))

    # -------------------------------------------------
    # SKILLS
    # -------------------------------------------------
    for sk in data.get("skills", []):
        if sk.get("skill_name"):
            db.session.add(Skill(
                cand_id=cand_id,
                skill_name=sk.get("skill_name"),
                skill_experience=sk.get("skill_experience")
            ))

    # -------------------------------------------------
    # WORK HISTORY
    # -------------------------------------------------
    for wh in data.get("work_history", []):
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

    db.session.commit()
    
    
    
    # ==========================================
    # New DEFAULT setting for candidate share AUTO 
    # ==========================================

    if recruiter:

        saved_targets = RecruiterDefaultShareTarget.query.filter_by(
            recruiter_email=recruiter.email
        ).all()

        targets = []

        for row in saved_targets:

            targets.append({
                "type": row.target_type,
                "value": row.target_value
            })

        if targets:

            fake_current_user = {
                "user_id": recruiter.email,
                "org_id": recruiter.org_id,
                "name": recruiter.name,
                "role": "org_recruiter"
            }

            share_candidate_service(
                current_user=fake_current_user,
                cand_ids=[candidate.cand_id],
                targets=targets,
                notify=False
            )

    # -------------------------------------------------
    # EMAIL
    # -------------------------------------------------
    send_candidate_form_link_email(
        candidate.email,
        candidate.name,
        token
    )

    # -------------------------------------------------
    # LOGGING
    # -------------------------------------------------
    create_log(
        actor_email,
        action="create_candidate",
        entity_type="Candidate",
        entity_id=cand_id,
        data={"added_by": "basic_form", "org_id": org_id}
    )

    return jsonify({
        "status": "success",
        "cand_id": cand_id,
        "token": token
    }), 201

@dashboard_bp.route("/add-candidate/full-form", methods=["POST"])
@jwt_required
def add_full():

    try:
        data = get_request_data()
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Invalid request data: {str(e)}"
        }), 400

    # ---------------- CURRENT USER (JWT) ----------------
    actor = get_current_user()

    if not actor:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    actor_email = actor["user_id"]
    org_id = actor["org_id"]

    # ---------------- VALIDATION ----------------
    required_fields = ["name", "email", "phone"]
    missing = [f for f in required_fields if not data.get(f)]

    if missing:
        return jsonify({
            "status": "error",
            "message": f"Missing required fields: {', '.join(missing)}"
        }), 400

    cand_id = generate_cand_id()
    # ---------------- VALIDATION ----------------

    offer_status = data.get("offer_status", "no_offer")
    offers = data.get("offers") or []
    offers = offers[:3]

    offers = [
        o for o in offers
        if isinstance(o, dict)
    ]

    # ---------------- CREATE CANDIDATE ----------------
    candidate = Candidate(
        cand_id=cand_id,
        name=data.get("name"),

        email=data.get("email"),
        email_2=data.get("email_2"),
        email_3=data.get("email_3"),

        phone=data.get("phone"),
        phone_2=data.get("phone_2"),
        phone_3=data.get("phone_3"),

        org_id=org_id,

        current_full_address=data.get("current_full_address"),
        current_location=data.get("current_location"),
        current_pincode=data.get("current_pincode"),

        same_as_current=data.get("same_as_current", False),
        permanent_full_address=data.get("permanent_full_address"),
        permanent_location=data.get("permanent_location"),
        permanent_pincode=data.get("permanent_pincode"),

        linkedin=data.get("linkedin"),
        portfolio=data.get("portfolio"),
        github_url=data.get("github_url"),

        total_experience=data.get("total_experience"),
        authorized_to_work=data.get("authorized_to_work"),
        relocation=data.get("relocation"),
        declaration_consent=data.get("declaration_consent"),
        expected_package=data.get("expected_package"),

        domain=data.get("domain"),
        notice_period=data.get("notice_period"),
        immediate_joiner=data.get("immediate_joiner", False),
        key_skills=data.get("key_skills"),
        availability=data.get("availability", []),
        # preferred_locations=data.get("preferred_locations", []),
        # offer_status=offer_status,
        # offers=offers,
        notes=data.get("notes", ""),

        added_by=actor_email,
        status="Uploaded"
    )

    db.session.add(candidate)
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
            is_linked=False
        ).first()

        if not resume_asset:
            db.session.rollback()
            return jsonify({
                "status": "error",
                "message": "Invalid or already linked resume document"
            }), 400

    if cover_letter_id:
        cover_asset = DocumentAsset.query.filter_by(
            docu_id=cover_letter_id,
            document_type="cover_letter",
            is_linked=False
        ).first()

        if not cover_asset:
            db.session.rollback()
            return jsonify({
                "status": "error",
                "message": "Invalid or already linked cover letter document"
            }), 400

    # ---------------- CREATE RESUME ROW ----------------
    if resume_asset or cover_asset:
        resume_row = Resume(
            cand_id=cand_id,
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
            source="full_form"
        )

        db.session.add(resume_row)
        db.session.flush()

        candidate.primary_resume_id = resume_row.id

        if resume_asset:
            resume_asset.cand_id = cand_id
            resume_asset.is_linked = True
            db.session.add(resume_asset)

        if cover_asset:
            cover_asset.cand_id = cand_id
            cover_asset.is_linked = True
            db.session.add(cover_asset)

    # ---------------- VISIBILITY ----------------
    from Candidates.utils.candidate_visibility_helper import (
        create_default_candidate_visibility
    )

    create_default_candidate_visibility(cand_id, actor)
    
    recruiter = OrgRecruiter.query.filter_by(
        email=actor_email,
        org_id=org_id
    ).first()

    

    # ---------------- SKILLS ----------------
    for sk in data.get("skills", []):
        if sk.get("skill_name"):
            db.session.add(Skill(
                cand_id=cand_id,
                skill_name=sk.get("skill_name"),
                skill_experience=sk.get("skill_experience")
            ))

    # ---------------- EDUCATION ----------------
    for ed in data.get("education", []):
        if ed.get("degree_name"):
            db.session.add(Degree(
                cand_id=cand_id,
                degree_name=ed.get("degree_name"),
                score=ed.get("score"),
                major=ed.get("major"),
                minor=ed.get("minor"),
                start_year=ed.get("start_year"),
                start_month=ed.get("start_month"),
                end_year=ed.get("end_year"),
                end_month=ed.get("end_month")
            ))

    # ---------------- CERTIFICATIONS ----------------
    for cert in data.get("certifications", []):
        if cert.get("certificate"):
            db.session.add(Certification(
                cand_id=cand_id,
                certificate=cert.get("certificate"),
                completion_year=cert.get("completion_year"),
                valid_upto=cert.get("valid_upto")
            ))

    # ---------------- WORK HISTORY ----------------
    for wh in data.get("work_history", []):
        if wh.get("organization"):

            designations = wh.get("designations")
            if not isinstance(designations, list):
                designations = []

            db.session.add(WorkHistory(
                cand_id=cand_id,
                organization=wh.get("organization"),
                org_start_year=wh.get("org_start_year"),
                org_start_month=wh.get("org_start_month"),
                org_end_year=wh.get("org_end_year"),
                org_end_month=wh.get("org_end_month"),
                designations=designations
            ))

    db.session.commit()
    
    
    # ==========================================
    #  New DEFAULT setting for candidate share AUTO 
    # ==========================================

    if recruiter:

        saved_targets = RecruiterDefaultShareTarget.query.filter_by(
            recruiter_email=recruiter.email
        ).all()

        targets = []

        for row in saved_targets:

            targets.append({
                "type": row.target_type,
                "value": row.target_value
            })

        if targets:

            fake_current_user = {
                "user_id": recruiter.email,
                "org_id": recruiter.org_id,
                "name": recruiter.name,
                "role": "org_recruiter"
            }

            share_candidate_service(
                current_user=fake_current_user,
                cand_ids=[candidate.cand_id],
                targets=targets,
                notify=False
            )

    # ---------------- LOG ----------------
    create_log(
        actor_email,
        action="create_candidate",
        entity_type="Candidate",
        entity_id=cand_id,
        data={"added_by": "full_form", "org_id": org_id}
    )

    return jsonify({
        "status": "success",
        "cand_id": cand_id
    }), 201


@dashboard_bp.route("/add-candidate/upload-resume", methods=["POST"])
@jwt_required
def upload_resume():

    actor = get_current_user()
    if not actor:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    actor_email = actor["user_id"]
    org_id = actor["org_id"]

    files = request.files.getlist("files")
    
    if not files:
        single = request.files.get("file")
        if single:
            files = [single]

    if not files:
        return jsonify({"status": "error", "message": "No files uploaded"}), 400

    temp_dir = "uploads/resumes"
    os.makedirs(temp_dir, exist_ok=True)

    results = []

    try:
        for resume_file in files:
            if not resume_file or resume_file.filename == "":
                continue

            ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
            ext = os.path.splitext(resume_file.filename)[1].lower()

            if ext not in ALLOWED_EXTENSIONS:
                results.append({
                    "file": resume_file.filename,
                    "status": "failed",
                    "message": "Unsupported file type"
                })
                continue

            from datetime import datetime

            original_name = secure_filename(resume_file.filename)

            # Split name and extension
            name, ext = os.path.splitext(original_name)

            #from datetime import datetime
            import pytz

            ist = pytz.timezone("Asia/Kolkata")
            timestamp = datetime.now(ist).strftime("%Y-%m-%d_%H-%M-%S")

            new_filename = f"{name}_{timestamp}{ext}"
            safe_filename = f"{uuid.uuid4()}_{original_name}"
            file_path = os.path.join(temp_dir, safe_filename)

            try:

                resume_file.save(file_path)

                file_size = os.path.getsize(file_path)
                size_mb = file_size / (1024 * 1024)

                if size_mb > 5:
                    results.append({
                        "file": original_name,
                        "status": "failed",
                        "message": "File too large (max 5MB)"
                    })
                    continue

                resume_hash = generate_file_hash(file_path)

                existing_resume = Resume.query.filter_by(
                    resume_hash=resume_hash,
                    org_id=org_id
                ).first()

                existing_temp = ParsedCandidateTemp.query.filter_by(
                    resume_hash=resume_hash,
                    org_id=org_id,
                    status="draft"
                ).first()

                if existing_resume:
                    results.append({
                        "file": original_name,
                        "status": "already_saved"
                    })
                    continue

                if existing_temp:
                    results.append({
                        "file": original_name,
                        "status": "resume_draft_exists",
                        "temp_id": existing_temp.temp_id
                    })
                    continue

                resume_key = upload_file(
                    file_path,
                    folder="resumes/bulk"
                )

                asset = DocumentAsset(
                    docu_id=str(uuid.uuid4()),
                    file_key=resume_key,
                    original_filename=new_filename,
                    mime_type=resume_file.mimetype,
                    file_size=file_size,
                    document_type="resume",
                    uploaded_by=actor_email,
                    org_id=org_id,
                    is_linked=False
                )
                db.session.add(asset)

                # parsed_data = parse_resume(file_path)
                #New
                parser_type = get_parser_type()

                if parser_type == "resume":
                    parsed_data = parse_resume(file_path)
                else:
                    parsed_data = parse_resume_ai(file_path)

                if not isinstance(parsed_data, dict):
                    results.append({
                        "file": original_name,
                        "status": "failed",
                        "message": "Invalid parse output"
                    })
                    continue

                if "error" in parsed_data:
                    results.append({
                        "file": original_name,
                        "status": "failed",
                        "message": parsed_data["error"]
                    })
                    continue

                parsed_data.setdefault("skills", [])
                parsed_data.setdefault("education", [])
                parsed_data.setdefault("work_history", [])
                parsed_data.setdefault("certifications", [])

                parsed_data["_parser_version"] = "v1.0"

                if not parsed_data.get("email"):
                    parsed_data.setdefault("_warnings", []).append("email_not_found")

                parse_metrics = {
                    "parse_confidence": parsed_data.get("parse_confidence"),
                    "has_email": bool(parsed_data.get("email")),
                    "has_phone": bool(parsed_data.get("phone")),
                    "skills_count": len(parsed_data["skills"]),
                    "education_count": len(parsed_data["education"]),
                    "work_history_count": len(parsed_data["work_history"]),
                }

                temp_id = str(uuid.uuid4())

                db.session.add(
                    ParsedCandidateTemp(
                        temp_id=temp_id,
                        org_id=org_id,
                        uploaded_by=actor_email,
                        source="upload_resume",
                        resume_file=resume_key,
                        resume_hash=resume_hash,
                        parsed_json=parsed_data,
                        raw_parsed_json=parsed_data.copy(),
                        parse_metrics=parse_metrics
                    )
                )
                db.session.commit()

                results.append({
                    "file": original_name,
                    "status": "parsed",
                    "temp_id": temp_id
                })

            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

        return jsonify({
            "status": "success",
            "upload_type": "single" if len(results) == 1 else "multiple",
            "results": results
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
        
#New
@dashboard_bp.route("/settings/parser", methods=["POST"])
@jwt_required
def set_parser():

    data = request.get_json()
    parser_type = data.get("parser")

    if parser_type not in ["ai", "resume"]:
        return jsonify({
            "status": "error",
            "message": "Invalid parser type"
        }), 400

    set_parser_type(parser_type)

    return jsonify({
        "status": "success",
        "parser": parser_type
    })
#New
@dashboard_bp.route("/settings/parser", methods=["GET"])
@jwt_required
def get_parser():

    return jsonify({
        "status": "success",
        "parser": get_parser_type()
    })
    
    
    
    

@dashboard_bp.route("/add-candidate/email-integration", methods=["POST"])
@jwt_required
def add_candidate_email_fetch():

    # ---------------- REQUEST PARSING ----------------
    if request.is_json:
        try:
            data = request.get_json(force=True)
            if isinstance(data, str):
                data = json.loads(data)
        except Exception as e:
            return jsonify({"status": "error", "message": f"Invalid JSON: {str(e)}"}), 400
    else:
        data = request.form.to_dict()

    # ---------------- AUTH ----------------
    actor = get_current_user()
    if not actor:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    actor_email = actor["user_id"]
    org_id = actor["org_id"]

    # ---------------- INPUT VALIDATION ----------------
    user_email = data.get("email")
    app_password = data.get("app_password")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    mail_filter = data.get("mail_filter", "unread")

    if not all([user_email, app_password, start_date, end_date]):
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    # ---------------- FETCH EMAIL ATTACHMENTS ----------------
    try:
        resume_files = fetch_resumes_from_email(
            user_email,
            app_password,
            start_date,
            end_date,
            mail_filter=mail_filter
        )
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Email fetch failed: {str(e)}"
        }), 500

    if not resume_files:
        return jsonify({
            "status": "success",
            "results": [],
            "message": "No resumes found (check filters)"
        }), 200

    results = []

    # ---------------- PROCESS FILES ----------------
    for file_path in resume_files:

        from datetime import datetime

        original_name = secure_filename(os.path.basename(file_path))

        name, ext = os.path.splitext(original_name)
        from datetime import datetime
        import pytz

        ist = pytz.timezone("Asia/Kolkata")
        timestamp = datetime.now(ist).strftime("%Y-%m-%d_%H-%M-%S")

        new_filename = f"{name}_{timestamp}{ext}"

        try:
            # ---------------- FILE VALIDATION ----------------
            if not os.path.exists(file_path):
                results.append({
                    "file": original_name,
                    "status": "failed",
                    "message": "Downloaded file missing"
                })
                continue

            file_size = os.path.getsize(file_path)

            if file_size > 5 * 1024 * 1024:
                results.append({
                    "file": original_name,
                    "status": "failed",
                    "message": "File too large (max 5MB)"
                })
                continue

            ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
            ext = os.path.splitext(original_name)[1].lower()

            if ext not in ALLOWED_EXTENSIONS:
                results.append({
                    "file": original_name,
                    "status": "failed",
                    "message": "Unsupported file type"
                })
                continue

            # ---------------- DUPLICATE CHECK ----------------
            resume_hash = generate_file_hash(file_path)

            if (
                Resume.query.filter_by(resume_hash=resume_hash, org_id=org_id).first()
                or ParsedCandidateTemp.query.filter_by(
                    resume_hash=resume_hash,
                    org_id=org_id,
                    status="draft"
                ).first()
            ):
                results.append({
                    "file": original_name,
                    "status": "already_exists"
                })
                continue

            # ---------------- PARSE RESUME ----------------
            # parsed_data = parse_resume(file_path)
            #New
            parser_type = get_parser_type()

            if parser_type == "resume":
                parsed_data = parse_resume(file_path)
                parsed_data["education"] = parsed_data.pop("degrees", [])
            else:
                parsed_data = parse_resume_ai(file_path)
            # ---------------- ADD EMAIL SOURCE NOTE ----------------
            

            if not parsed_data or not isinstance(parsed_data, dict):
                results.append({
                    "file": original_name,
                    "status": "failed",
                    "message": "Parser returned invalid output"
                })
                continue

            if "error" in parsed_data:
                results.append({
                    "file": original_name,
                    "status": "failed",
                    "message": parsed_data["error"]
                })
                continue

            from datetime import datetime
            from zoneinfo import ZoneInfo

            timestamp = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")

            source_note = f"Imported from email: {user_email} at {timestamp}"

            # 🔥 FORCE notes field safely
            parsed_data["notes"] = (
                f"{parsed_data.get('notes')} | {source_note}"
                if parsed_data.get("notes")
                else source_note
            )       

            # ---------------- CHECK EMAIL ----------------
            if not parsed_data.get("email"):
                parsed_data.setdefault("_warnings", []).append("email_not_found")   

            # ---------------- UPLOAD FILE ----------------
            resume_key = upload_file(
                file_path,
                folder="resumes/email"
            )

            # ---------------- CREATE DOCUMENT ASSET ----------------
            asset = DocumentAsset(
                docu_id=str(uuid.uuid4()),
                file_key=resume_key,
                original_filename=new_filename,
                mime_type="application/pdf",
                file_size=file_size,
                document_type="resume",
                uploaded_by=actor_email,
                org_id=org_id,
                is_linked=False
            )
            db.session.add(asset)

            # ---------------- SAVE TEMP ----------------
            temp_id = str(uuid.uuid4())

            db.session.add(
                ParsedCandidateTemp(
                    temp_id=temp_id,
                    org_id=org_id,
                    uploaded_by=actor_email,
                    source="email_integration",
                    resume_file=resume_key,
                    resume_hash=resume_hash,
                    parsed_json=parsed_data,
                    status="draft"
                )
            )

            db.session.commit()

            # ---------------- RESPONSE ----------------
            results.append({
                "file": original_name,
                "status": "parsed",
                "temp_id": temp_id
            })

        except Exception as e:
            db.session.rollback()

            results.append({
                "file": original_name,
                "status": "failed",
                "message": str(e)
            })

    # ---------------- FINAL RESPONSE ----------------
    return jsonify({
        "status": "success",
        "mail_filter": mail_filter,
        "results": results
    }), 200

    
def normalize_int(value):
    if value in ("", None):
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def safe_add(instance):
    try:
        db.session.add(instance)
        db.session.flush()
        return True
    except Exception as e:
        print("DB INSERT FAILED:", e)
        return False

@dashboard_bp.route("/candidates/confirm-save/bulk", methods=["POST"])
@jwt_required
def bulk_confirm_save_candidates():

    actor = get_current_user()
    if not actor:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    actor_email = actor["user_id"]

    try:
        data = request.get_json(force=True)
        if isinstance(data, str):
            data = json.loads(data)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Invalid JSON: {str(e)}"}), 400
    mode = data.get("mode", "strict")  


    temp_ids = data.get("temp_ids")
    if not temp_ids or not isinstance(temp_ids, list):
        return jsonify({"status": "error", "message": "temp_ids must be a non-empty list"}), 400

    results = []

    for temp_id in temp_ids:
        try:

            # =====================================================
            # 1️⃣ FETCH TEMP
            # =====================================================
            temp = ParsedCandidateTemp.query.filter_by(
                temp_id=temp_id,
                status="draft",
                uploaded_by=actor_email
            ).first()

            if not temp:
                results.append({
                    "temp_id": temp_id,
                    "status": "skipped",
                    "message": "Temp record not found or already saved"
                })
                continue

            parsed = temp.parsed_json or {}

            email = parsed.get("email")


            offer_status = parsed.get("offer_status") or "no_offer"
            offers = parsed.get("offers") or []

            offers = offers[:3]

            offers = [
                o for o in offers
                if isinstance(o, dict)
            ]

            # ================================
            # 🚀 MODE HANDLING
            # ================================
            if mode == "strict":
                if not email:
                    results.append({
                        "temp_id": temp_id,
                        "status": "failed",
                        "message": "Primary email missing"
                    })
                    continue

            elif mode == "direct":
                if not email:
                    email = f"noemail_{uuid.uuid4()}@temp.com"

            if mode == "direct":
                final_status = "Uploaded"
            else:
                final_status = "Screened"

            # =====================================================
            # 2️⃣ CREATE / FETCH CANDIDATE
            # =====================================================
            candidate = Candidate.query.filter_by(
                email=email,
                org_id=temp.org_id
            ).first()

            created = False

            if not candidate:
                cand_id = generate_cand_id()

                # ✅ STEP 1: allowed DB columns
                allowed_fields = {c.name for c in Candidate.__table__.columns}

                # ✅ STEP 2: prepare base data
                candidate_data = {
                    "cand_id": cand_id,
                    "name": parsed.get("name") or "Unknown Candidate",
                    "email": email,
                    "phone": parsed.get("phone"),

                    "email_2": parsed.get("email_2"),
                    "email_3": parsed.get("email_3"),
                    "phone_2": parsed.get("phone_2"),
                    "phone_3": parsed.get("phone_3"),

                    "current_full_address": parsed.get("current_full_address"),
                    "current_location": parsed.get("current_location"),
                    "current_pincode": parsed.get("current_pincode"),

                    "same_as_current": parsed.get("same_as_current"),

                    "permanent_full_address": parsed.get("permanent_full_address"),
                    "permanent_location": parsed.get("permanent_location"),
                    "permanent_pincode": parsed.get("permanent_pincode"),

                    "linkedin": parsed.get("linkedin"),
                    "portfolio": parsed.get("portfolio"),
                    "github_url": parsed.get("github_url"),

                    "total_experience": parsed.get("total_experience"),
                    "domain": parsed.get("domain"),
                    "key_skills": parsed.get("key_skills"),

                    "expected_package": parsed.get("expected_package"),
                    "notice_period": parsed.get("notice_period"),
                    "availability": parsed.get("availability"),

                    "relocation": parsed.get("relocation"),
                    "authorized_to_work": parsed.get("authorized_to_work"),
                    "immediate_joiner": parsed.get("immediate_joiner"),

                    # ❌ DO NOT include unsupported fields like notes, offer_status, offers

                    "org_id": temp.org_id,
                    "added_by": actor_email,
                    "status": final_status
                }

                #New auto-filter invalid keys
                candidate_data = {
                    k: v for k, v in candidate_data.items()
                    if k in allowed_fields
                }

                # ✅ STEP 4: create safely
                candidate = Candidate(**candidate_data)

                db.session.add(candidate)
                db.session.flush()
                created = True

            else:
                cand_id = candidate.cand_id

            candidate.status = final_status

            # =====================================================
            # 3️⃣ VISIBILITY
            # =====================================================
            if created:
                from Candidates.utils.candidate_visibility_helper import (
                    create_default_candidate_visibility
                )
                create_default_candidate_visibility(cand_id, actor)
                
                recruiter = OrgRecruiter.query.filter_by(
                    email=actor_email,
                    org_id=temp.org_id
                ).first()
                
                
                
                # ==========================================
                #  New DEFAULT setting for candidate share AUTO 
                # ==========================================

                if recruiter:

                    saved_targets = RecruiterDefaultShareTarget.query.filter_by(
                        recruiter_email=recruiter.email
                    ).all()

                    targets = []

                    for row in saved_targets:

                        targets.append({
                            "type": row.target_type,
                            "value": row.target_value
                        })

                    if targets:

                        fake_current_user = {
                            "user_id": recruiter.email,
                            "org_id": recruiter.org_id,
                            "name": recruiter.name,
                            "role": "org_recruiter"
                        }

                        share_candidate_service(
                            current_user=fake_current_user,
                            cand_ids=[candidate.cand_id],
                            targets=targets,
                            notify=False
                        )

                

            if parsed.get("skills"):
                Skill.query.filter_by(cand_id=cand_id).delete()

            if parsed.get("education"):
                Degree.query.filter_by(cand_id=cand_id).delete()

            if parsed.get("work_history"):
                WorkHistory.query.filter_by(cand_id=cand_id).delete()

            if parsed.get("certifications"):
                Certification.query.filter_by(cand_id=cand_id).delete()

            # =====================================================
            # 4️⃣ RESUME CREATION
            # =====================================================
            resume_exists = Resume.query.filter_by(
                resume_hash=temp.resume_hash,
                cand_id=cand_id
            ).first()

            if not resume_exists:

                # 🔍 get original asset
                existing_asset = DocumentAsset.query.filter_by(
                    file_key=temp.resume_file,
                    org_id=temp.org_id
                ).first()

                asset = DocumentAsset(
                    docu_id=str(uuid.uuid4()),
                    org_id=temp.org_id,
                    cand_id=cand_id,
                    document_type="resume",
                    file_key=temp.resume_file,
                    original_filename=existing_asset.original_filename if existing_asset else "Unknown",
                    mime_type=existing_asset.mime_type if existing_asset else "application/pdf",
                    file_size=existing_asset.file_size if existing_asset else None,
                    uploaded_by=actor_email,
                    is_linked=True
                )

                db.session.add(asset)
                db.session.flush()

                resume_row = Resume(
                    org_id=temp.org_id,
                    cand_id=cand_id,
                    resume_file=asset.file_key,
                    original_filename=asset.original_filename,
                    mime_type=asset.mime_type,
                    resume_hash=temp.resume_hash,
                    uploaded_at=datetime.utcnow(),
                    source=temp.source
                )

                db.session.add(resume_row)
                db.session.flush()

                candidate.primary_resume_id = resume_row.id

            # =====================================================
            # 5️⃣ SKILLS
            # =====================================================
            for sk in parsed.get("skills", []):
                if sk.get("skill_name"):
                    db.session.add(Skill(
                        cand_id=cand_id,
                        skill_name=sk.get("skill_name"),
                        skill_experience=sk.get("skill_experience")
                    ))

            # =====================================================
            # 6️⃣ EDUCATION
            # =====================================================
            for edu in parsed.get("education", []):
                degree_name = edu.get("degree_name") or edu.get("degree")
                if not degree_name:
                    continue

                db.session.add(Degree(
                    cand_id=cand_id,
                    degree_name=degree_name,
                    major=edu.get("major"),
                    minor=edu.get("minor"),
                    score=edu.get("score"),
                    start_year=str(edu.get("start_year")) if edu.get("start_year") else None,
                    end_year=str(edu.get("end_year")) if edu.get("end_year") else None,
                    start_month=edu.get("start_month"),
                    end_month=edu.get("end_month")
                ))

            # =====================================================
            # 7️⃣ CERTIFICATIONS
            # =====================================================
            for cert in parsed.get("certifications", []):
                name = (
                    cert.get("certificate")
                    or cert.get("certificate_name")
                    or cert.get("name")
                )

                if name:
                    db.session.add(Certification(
                        cand_id=cand_id,
                        certificate=name,
                        completion_year=normalize_int(cert.get("completion_year")),
                        valid_upto=normalize_int(cert.get("valid_upto"))
                    ))

            # =====================================================
            # 8️⃣ WORK HISTORY (FIXED + ROBUST)
            # =====================================================
            for wh in parsed.get("work_history", []):

                org = (
                    wh.get("organization")
                    or wh.get("company")
                    or wh.get("company_name")
                )

                if not org:
                    continue

                # ✅ IMPORTANT: use designations directly
                designations = wh.get("designations")

                # fallback if parser gives flat structure
                if not designations and wh.get("designation"):
                    designations = [{
                        "designation": wh.get("designation"),
                        "start_year": wh.get("start_year"),
                        "start_month": wh.get("start_month"),
                        "end_year": wh.get("end_year"),
                        "end_month": wh.get("end_month"),
                        "responsibilities": wh.get("responsibilities")
                    }]

                if not isinstance(designations, list):
                    designations = []

                db.session.add(WorkHistory(
                    cand_id=cand_id,
                    organization=org,
                    org_start_year=wh.get("org_start_year") or wh.get("start_year"),
                    org_end_year=wh.get("org_end_year") or wh.get("end_year"),
                    org_start_month=wh.get("org_start_month") or wh.get("start_month"),
                    org_end_month=wh.get("org_end_month") or wh.get("end_month"),
                    designations=designations
                ))
            # =====================================================
            # 9️⃣ FINALIZE
            # =====================================================
            db.session.delete(temp)
            db.session.commit()
            
            
            
            
    
    
    

            results.append({
                "temp_id": temp_id,
                "status": "saved",
                "cand_id": cand_id,
                "created": created
            })

        except Exception as e:
            db.session.rollback()
            results.append({
                "temp_id": temp_id,
                "status": "failed",
                "message": str(e)
            })

    return jsonify({
        "status": "success",
        "results": results
    }), 200

@dashboard_bp.route("/candidates/auto-save", methods=["POST"])
@jwt_required
def auto_save_candidate():

    actor = get_current_user()
    if not actor:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    actor_email = actor["user_id"]

    try:
        data = request.get_json(force=True)
        if isinstance(data, str):
            data = json.loads(data)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Invalid JSON: {str(e)}"
        }), 400

    temp_id = data.get("temp_id")
    edited_data = data.get("edited_data")

    if not temp_id or not isinstance(edited_data, dict):
        return jsonify({
            "status": "error",
            "message": "temp_id and edited_data (object) are required"
        }), 400

    temp = ParsedCandidateTemp.query.filter_by(
        temp_id=temp_id,
        uploaded_by=actor_email
    ).first()

    if not temp:
        return jsonify({
            "status": "error",
            "message": "Temp record not found"
        }), 404

    if temp.status != "draft":
        return jsonify({
            "status": "error",
            "message": "Candidate already saved, auto-save disabled"
        }), 409

    current_data = temp.parsed_json or {}

    PROTECTED_KEYS = {"education", "certifications"}

    for key, value in edited_data.items():

        if key in PROTECTED_KEYS and not value:
            continue

        if value is None:
            continue

        current_data[key] = value

    current_data["_meta"] = {
        "last_auto_saved_by": actor_email,
        "last_auto_saved_at": datetime.utcnow().isoformat()
    }

    temp.parsed_json = current_data
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Auto-saved successfully",
        "temp_id": temp_id
    }), 200


@dashboard_bp.route("/candidates/temp/<temp_id>", methods=["GET"])
@jwt_required
def get_temp_candidate(temp_id):

    actor = get_current_user()
    if not actor:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    actor_email = actor["user_id"]

    temp = ParsedCandidateTemp.query.filter_by(
        temp_id=temp_id,
        uploaded_by=actor_email
    ).first()

    if not temp:
        return jsonify({
            "status": "error",  
            "message": "Temp record not found"
        }), 404

    return jsonify({
        "status": "success",
        "temp_id": temp.temp_id,
        "parsed_data": temp.parsed_json,
        "temp_status": temp.status
    }), 200

@dashboard_bp.route("/candidates/my-temp-resumes", methods=["GET"])
@jwt_required
def get_my_temp_resumes():

    from common.models.document_asset import DocumentAsset

    actor = get_current_user()
    if not actor:
        return jsonify({
            "status": "error",
            "message": "Unauthorized"
        }), 401

    actor_email = actor["user_id"]
    org_id = actor["org_id"]
    
    # drafts = ParsedCandidateTemp.query.filter_by(
    #     org_id=org_id,
    #     status="draft",
    #     uploaded_by=actor_email
        
    # ).order_by(
    #     ParsedCandidateTemp.created_at.desc()
    # ).all()

    #New
    drafts = ParsedCandidateTemp.query.filter(
        ParsedCandidateTemp.org_id == org_id,
        ParsedCandidateTemp.status == "draft",
        ParsedCandidateTemp.uploaded_by == actor_email
    ).order_by(
        ParsedCandidateTemp.created_at.desc()
    ).all()

    results = []









    for draft in drafts:
        parsed = draft.parsed_json or {}

        # Fetch original filename
        asset = DocumentAsset.query.filter_by(
            file_key=draft.resume_file,
            org_id=org_id
        ).first()

        results.append({
            "temp_id": draft.temp_id,

            "status": "parsed",
            
            # ✅ MAIN FIX HERE
            "file": (
                asset.original_filename
                if asset and asset.original_filename
                else parsed.get("name") or "Unknown"
            ),

            "email": parsed.get("email"),
            "phone": parsed.get("phone"),

            #New
            "warnings": parsed.get("_warnings", []),

            "uploaded_at": (
                draft.created_at.isoformat()
                if draft.created_at else None
            ),

            "source": draft.source
        })

    return jsonify({
        "status": "success",
        "count": len(results),
        "drafts": results
    }), 200



@dashboard_bp.route("/add-candidate/email-integration-oauth", methods=["POST"])
@jwt_required
def add_candidate_email_fetch_oauth():

    actor = get_current_user()
    if not actor:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    actor_email = actor["user_id"]
    org_id = actor["org_id"]

    data = request.get_json(force=True)

    start_date = data.get("start_date")
    end_date = data.get("end_date")
    mail_filter = data.get("mail_filter", "unread")

    from email_integration.model import EmailIntegration
    from email_integration.service import refresh_access_token
    from Candidates.utils.email_fetcher import fetch_resumes_from_email_oauth
    from datetime import datetime, timedelta

    # ---------------- GET OAUTH RECORD ----------------
    record = EmailIntegration.query.filter_by(
        user_id=actor_email,
        is_active=True
    ).first()

    if not record:
        return jsonify({
            "status": "error",
            "message": "No Gmail connected via OAuth"
        }), 400

    # ---------------- REFRESH TOKEN ----------------
    if record.is_expired():
        token_data = refresh_access_token(record.refresh_token)

        record.access_token = token_data["access_token"]
        record.expires_at = datetime.utcnow() + timedelta(seconds=3600)

        db.session.commit()

    # ---------------- FETCH EMAILS ----------------
    try:
        resume_files = fetch_resumes_from_email_oauth(
            record.email,
            record.access_token,
            start_date,
            end_date,
            mail_filter=mail_filter
        )
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Email fetch failed: {str(e)}"
        }), 500

    if not resume_files:
        return jsonify({
            "status": "success",
            "results": [],
            "message": "No resumes found"
        }), 200

    # ---------------- PROCESS FILES ----------------
    results = []

    for file_path in resume_files:
        try:
            # 👉 CALL YOUR EXISTING LOGIC HERE
            # (copy from manual API OR better call shared function)

            from Candidates.utils.email_processing import process_email_resumes  # adjust import

            processed = process_email_resumes(
                record.email,
                org_id,
                actor_email,
                [file_path]
            )

            results.extend(processed)

        except Exception as e:
            results.append({
                "file": file_path,
                "status": "failed",
                "message": str(e)
            })

    return jsonify({
        "status": "success",
        "message": "OAuth IMAP connected successfully",
        "results": results
    }), 200

