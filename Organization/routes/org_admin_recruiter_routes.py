# NOTE:
# Phone verification is temporarily disabled across Org Admin & Org Recruiter flows.
# Phone numbers are stored but not OTP-verified.

# routes/org_admin_recruiter_routes.py
from flask import Blueprint, request, jsonify, current_app
from extensions import db
from recruiter.models.org_recruiter_model import OrgRecruiter
from recruiter.models.admin_model import Admin
from recruiter.models.education_recruiter_admin_model import EducationRecruiterAdmin
from recruiter.models.work_history_employee_model import WorkHistoryEmployee
from recruiter.models.documents_model import Documents
from Organization.utils.email_utils import send_invitation_email
from werkzeug.security import generate_password_hash
from common.utils.password_utils import validate_password
import jwt
from config import Config
from Logs.log_helper import create_log
import json
from Organization.models.otp import OTP
# from recruiter.routes.recruiter_routes import send_phone_otp, verify_phone_otp
from recruiter.routes.recruiter_routes import send_email_otp, verify_email_otp
from common.utils.storage_service import upload_file
from datetime import datetime, timedelta
import os, uuid
from werkzeug.utils import secure_filename
from auth.utils.jwt_required import jwt_required
from flask import g
from GlobalRecruiter.models.recruiters import GlobalRecruiter
from GlobalRecruiter.models.organization_recruiter import OrganizationRecruiter
from Organization.models.team import Team


SECRET_KEY = Config.SECRET_KEY
org_admin_recruiter_bp = Blueprint("org_admin_recruiter_bp", __name__)

# ----------------------------------------
# Lightweight actor user for logs
# ----------------------------------------
class ActorUser:
    def __init__(self, email, name, role):
        self.email = email
        self.name = name
        self.role = role

# ----------------------------------------
# Helper: safely parse JSON strings
# ----------------------------------------
def safe_json_load(value):
    """
    Converts JSON-string fields to Python objects.
    If already list/dict → returns as-is.
    """
    if value is None:
        return []
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return []
    return []


def save_to_object_storage(file_obj, folder):
    temp_dir = "uploads/tmp"
    os.makedirs(temp_dir, exist_ok=True)

    filename = f"{uuid.uuid4()}_{secure_filename(file_obj.filename)}"
    file_path = os.path.join(temp_dir, filename)

    try:
        file_obj.save(file_path)

        file_key = upload_file(
            file_path,
            folder=folder
        )

        file_size = os.path.getsize(file_path)

        return {
            "file_key": file_key,
            "original_filename": file_obj.filename,
            "mime_type": file_obj.content_type,
            "file_size": file_size
        }

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

def save_document(user, role, file_obj, document_name):
    meta = save_to_object_storage(
        file_obj,
        folder=f"documents/{role}/{user.recruiter_id if role == 'org_recruiter' else user.admin_id}"
    )

    db.session.add(Documents(
        user_type=role,
        admin_id=user.admin_id if role == "admin" else None,
        recruiter_id=user.recruiter_id if role == "org_recruiter" else None,
        document_name=document_name,
        file_key=meta["file_key"],
        original_filename=meta["original_filename"],
        mime_type=meta["mime_type"],
        file_size=meta["file_size"],
        uploaded_at=datetime.utcnow()
    ))

# ----------------------------------------
# SEND INVITE   
# ----------------------------------------

@org_admin_recruiter_bp.route("/superadmin/invite", methods=["POST"])
@jwt_required
def send_invite():
    try:
        # -----------------------------
        # Parse Request
        # -----------------------------
        try:
            data = request.get_json(force=True)
        except Exception:
            try:
                data = json.loads(request.data.decode("utf-8") or "{}")
            except Exception:
                data = {}

        name = data.get("name")
        email = data.get("email")
        phone = data.get("phone")
        role = data.get("role")
        org_id = data.get("org_id")
        team_id = data.get("team_id")
        recruiter_type = data.get("recruiter_type")

        if role == "org_recruiter" and recruiter_type not in ["INTERNAL", "EXTERNAL"]:
            return jsonify({
                "error": "recruiter_type is required and must be INTERNAL or EXTERNAL"
            }), 400

        if not all([name, email, phone, role, org_id]):
            return jsonify({"error": "Missing required fields"}), 400

        if role not in ("admin", "org_recruiter"):
            return jsonify({"error": "Invalid role"}), 400
        
            
        if role == "org_recruiter" and recruiter_type not in ["INTERNAL", "EXTERNAL"]:
            return jsonify({
                "error": "recruiter_type must be INTERNAL or EXTERNAL"
            }), 400
        
        if role == "org_recruiter" and team_id:
            team = Team.query.filter_by(team_id=team_id).first()

            if not team:
                return jsonify({"error": "Invalid team_id"}), 400

            if team.team_type == "external" and recruiter_type != "EXTERNAL":
                return jsonify({
                    "error": "External team must have EXTERNAL recruiter"
                }), 400

            if team.team_type == "internal" and recruiter_type != "INTERNAL":
                return jsonify({
                    "error": "Internal team must have INTERNAL recruiter"
                }), 400

        email_2 = data.get("email_2")
        email_3 = data.get("email_3")
        phone_2 = data.get("phone_2")
        phone_3 = data.get("phone_3")

        # -----------------------------
        # DUPLICATE CHECK
        # -----------------------------
        if role == "org_recruiter":
            existing_email = OrgRecruiter.query.filter_by(
                email=email, org_id=org_id
            ).first()

            existing_phone = OrgRecruiter.query.filter_by(
                phone=phone, org_id=org_id
            ).first()

        else:
            existing_email = Admin.query.filter_by(
                email=email, org_id=org_id
            ).first()

            existing_phone = Admin.query.filter_by(
                phone=phone, org_id=org_id
            ).first()

        # -----------------------------
        # RESEND INVITE / DUPLICATE CHECK
        # -----------------------------

        if existing_email:

            # ACTIVE recruiter
            if existing_email.invite_status == "ACTIVE":
                return jsonify({
                    "error": f"{role} already active."
                }), 400

            # deleted invite → allow fresh invite
            if existing_email.invite_status == "DELETED":

                existing_email.name = name
                existing_email.phone = phone

                existing_email.invite_status = "PENDING"

                existing_email.invite_sent_at = None
                existing_email.invite_expiry_at = None
                existing_email.invite_attempts = 0

                db.session.commit()

            else:

                return jsonify({
                    "error": "Invite already exists",
                    "invite_status": existing_email.invite_status,
                    "user_id": (
                        existing_email.recruiter_id
                        if role == "org_recruiter"
                        else existing_email.admin_id
                    )
                }), 409


        if existing_phone and existing_phone != existing_email:

            if existing_phone.is_onboarding_completed:
                return jsonify({
                    "error": "Phone number already exists for an active account."
                }), 400


        # ---------------------------------------------------
        # ADMIN CREATION FLOW
        # ---------------------------------------------------
        if role == "admin":

            user = Admin(
                name=name,
                email=email,
                email_2=email_2,
                email_3=email_3,
                phone=phone,
                phone_2=phone_2,
                phone_3=phone_3,
                org_id=org_id,

                dob=data.get("dob"),
                gender=data.get("gender"),
                total_experience=data.get("total_experience"),

                current_full_address=data.get("current_full_address"),
                current_location=data.get("current_location"),
                current_pincode=data.get("current_pincode"),
                same_as_current=bool(data.get("same_as_current")),

                permanent_full_address=data.get("permanent_full_address"),
                permanent_location=(
                    data.get("current_location")
                    if data.get("same_as_current")
                    else data.get("permanent_location")
                ),
                permanent_pincode=data.get("permanent_pincode"),

                email_verified=False,
                email_2_verified=False,
                email_3_verified=False,
                phone_verified=False,
                phone_2_verified=False,
                phone_3_verified=False
            )

            db.session.add(user)
            db.session.flush()

        # ---------------------------------------------------
        # GLOBAL RECRUITER FLOW
        # ---------------------------------------------------
        else:

            # 1️⃣ Check Global Recruiter
            global_rec = GlobalRecruiter.query.filter_by(email=email).first()

            if not global_rec:
                global_rec = GlobalRecruiter(
                    name=name,
                    email=email,
                    phone=phone
                )
                db.session.add(global_rec)
                db.session.flush()   # ensures recruiter_id exists
            

            # Prevent external recruiter from joining multiple orgs
            if recruiter_type == "EXTERNAL":
                existing_any_org = OrganizationRecruiter.query.filter_by(
                    recruiter_id=global_rec.recruiter_id
                ).first()

                if existing_any_org:
                    return jsonify({
                        "error": "External recruiter can only belong to one organization"
                    }), 400

            # 2️⃣ Check existing organization mapping
            existing_mapping = OrganizationRecruiter.query.filter_by(
                recruiter_id=global_rec.recruiter_id,
                org_id=org_id
            ).first()

            if existing_mapping and existing_mapping.status == "ACTIVE":
                return jsonify({
                    "error": "Recruiter already belongs to this organization."
                }), 400

            # 3️⃣ Create organization mapping
            if not existing_mapping:

                mapping = OrganizationRecruiter(
                    recruiter_id=global_rec.recruiter_id,
                    org_id=org_id,
                    recruiter_type=recruiter_type,
                    status="INVITED"
                )

                db.session.add(mapping)

            
            

            # 4️⃣ Create OrgRecruiter profile
            user = OrgRecruiter(
                global_recruiter_id=global_rec.recruiter_id,
                name=name,
                email=email,
                email_2=email_2,
                email_3=email_3,
                phone=phone,
                phone_2=phone_2,
                phone_3=phone_3,
                team_id=team_id,
                org_id=org_id,

                dob=data.get("dob"),
                gender=data.get("gender"),
                total_experience=data.get("total_experience"),

                current_full_address=data.get("current_full_address"),
                current_location=data.get("current_location"),
                current_pincode=data.get("current_pincode"),
                same_as_current=bool(data.get("same_as_current")),

                permanent_full_address=data.get("permanent_full_address"),
                permanent_location=(
                    data.get("current_location")
                    if data.get("same_as_current")
                    else data.get("permanent_location")
                ),
                permanent_pincode=data.get("permanent_pincode"),

                email_verified=False,
                email_2_verified=False,
                email_3_verified=False,
                phone_verified=False,
                phone_2_verified=False,
                phone_3_verified=False
            )

            db.session.add(user)
            db.session.flush()


        # ---------------------------------------------------
        # SAVE EDUCATION
        # ---------------------------------------------------
        education_input = data.get("education") or []
        if isinstance(education_input, dict):
            education_input = [education_input]

        for edu in education_input:
            if not isinstance(edu, dict) or not any(edu.values()):
                continue

            db.session.add(EducationRecruiterAdmin(
                user_type=role,
                admin_id=user.admin_id if role == "admin" else None,
                recruiter_id=user.recruiter_id if role == "org_recruiter" else None,
                degree=edu.get("degree") or edu.get("degree_name"),
                score=edu.get("score"),
                major=edu.get("major"),
                minor=edu.get("minor"),
                start_year=edu.get("start_year"),
                end_year=edu.get("end_year"),
                start_month=edu.get("start_month"),
                end_month=edu.get("end_month")
            ))


        # ---------------------------------------------------
        # SAVE WORK HISTORY
        # ---------------------------------------------------
        work_input = data.get("work_history") or []
        if isinstance(work_input, dict):
            work_input = [work_input]

        for job in work_input:
            if not isinstance(job, dict) or not any(job.values()):
                continue

            designations = job.get("designations") if isinstance(job.get("designations"), list) else []

            db.session.add(WorkHistoryEmployee(
                user_type=role,
                admin_id=user.admin_id if role == "admin" else None,
                recruiter_id=user.recruiter_id if role == "org_recruiter" else None,
                organization=job.get("organization"),
                designations=designations,
                org_start_year=job.get("org_start_year"),
                org_end_year=job.get("org_end_year"),
                org_start_month=job.get("org_start_month"),
                org_end_month=job.get("org_end_month")
            ))


        # ---------------------------------------------------
        # DOCUMENT STORAGE
        # ---------------------------------------------------
        id_proof_file = request.files.get("id_proof_file")
        if id_proof_file:
            save_document(user, role, id_proof_file, "id_proof")

        address_proof_file = request.files.get("address_proof_file")
        if address_proof_file:
            save_document(user, role, address_proof_file, "address_proof")


        # ---------------------------------------------------
        # COMMIT EVERYTHING
        # ---------------------------------------------------
        db.session.commit()


        # ---------------------------------------------------
        # INVITE TOKEN
        # ---------------------------------------------------
        expiry_time = datetime.utcnow() + timedelta(hours=24)

        payload = {
            "name": name,
            "email": email,
            "role": role,
            "org_id": org_id,
            "type": "invite",
            "exp": expiry_time
        }

        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        user.invite_status = "PENDING"
        user.invite_sent_at = datetime.utcnow()
        user.invite_expiry_at = expiry_time
        user.invite_attempts = 1

        db.session.commit()

        if isinstance(token, bytes):
            token = token.decode()

        try:
            send_invitation_email(email, token, role)
        except Exception as e:
            current_app.logger.warning(f"Invitation email failed: {e}")


        actor_email = g.current_user["user_id"]
        actor_role = g.current_user["role"]

        if actor_role != "superadmin":
            return jsonify({"error": "Unauthorized"}), 403

        actor_user = ActorUser(actor_email, actor_email, actor_role)

        create_log(
            user=actor_user,
            action="send_invite",
            entity_type=role,
            entity_id=(user.admin_id if role == "admin" else user.recruiter_id),
            data={"email": email, "org_id": org_id}
        )

        return jsonify({
            "message": "Invite sent successfully",
            "token": token
        }), 200


    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error in send_invite")
        return jsonify({"error": str(e)}), 500

# ----------------------------------------
# VALIDATE TOKEN
# ----------------------------------------

@org_admin_recruiter_bp.route("/onboarding/validate-token", methods=["GET"])
def validate_token():
    token = request.args.get("token")
    if not token:
        return jsonify({"error": "Token missing"}), 400

    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        email = decoded.get("email")
        role = decoded.get("role")
        org_id = decoded.get("org_id")

        if not email or not role:
            return jsonify({"valid": False, "error": "Invalid token payload"}), 400

        user = None
        if role == "admin":
            if org_id:
                user = Admin.query.filter_by(email=email, org_id=org_id).first()
            else:
                user = Admin.query.filter_by(email=email).first()
        else:
            if org_id:
                user = OrgRecruiter.query.filter_by(email=email, org_id=org_id).first()
            else:
                user = OrgRecruiter.query.filter_by(email=email).first()

        if not user:
            return jsonify({"valid": True, "data": decoded, "prefill": None}), 200
        
        recruiter_type = None

        if role == "org_recruiter":
            mapping = OrganizationRecruiter.query.filter_by(
                recruiter_id=user.global_recruiter_id,
                org_id=user.org_id
            ).first()

            if mapping:
                recruiter_type = mapping.recruiter_type
                

        # Build prefill
        education = []
        for e in getattr(user, "education", []) or []:
            education.append({
                "degree": e.degree,
                "score": e.score,
                "major": e.major,
                "minor": e.minor,
                "start_year": e.start_year,
                "end_year": e.end_year,
                "start_month": e.start_month,
                "end_month": e.end_month
            })

        work_history = []
        for w in getattr(user, "work_history", []) or []:
            work_history.append({
                "organization": w.organization,
                "org_start_year": w.org_start_year,
                "org_end_year": w.org_end_year,
                "org_start_month": w.org_start_month,
                "org_end_month": w.org_end_month,
                "designations": w.designations or []
            })

        docs = []
        for d in getattr(user, "documents", []) or []:
            docs.append({
                "doc_id": d.doc_id,
                "document_name": d.document_name,
                "original_filename": d.original_filename
            })


        prefill = {
            "name": user.name,
            "email": user.email,
            "email_2": user.email_2 or "",
            "email_2_verified": bool(user.email_2_verified),
            "email_3": user.email_3 or "",
            "email_3_verified": bool(user.email_3_verified),
            "phone": user.phone,
            "phone_2": user.phone_2 or "",
            "phone_2_verified": bool(user.phone_2_verified),
            "phone_3": user.phone_3 or "",
            "phone_3_verified": bool(user.phone_3_verified),
            "email_verified": bool(user.email_verified),
            "phone_verified": bool(user.phone_verified),
            "dob": user.dob,
            "gender": user.gender,
            "total_experience": str(user.total_experience) if user.total_experience is not None else "",
            "current_full_address": user.current_full_address or "",
            "current_location": user.current_location or {},
            "current_pincode": user.current_pincode or "",
            "same_as_current": bool(user.same_as_current),
            "permanent_full_address": user.permanent_full_address or "",
            "permanent_location": user.permanent_location or {},
            "permanent_pincode": user.permanent_pincode or "",
            "education": education,
            "work_history": work_history,
            "documents": docs,
            "org_id": user.org_id,
            "role": role,
            "recruiter_type": recruiter_type,
            "team_id": user.team_id if role == "org_recruiter" else None,
            "team_name": user.team_name if role == "org_recruiter" else None
        }

        return jsonify({"valid": True, "data": decoded, "prefill": prefill}), 200

    except jwt.ExpiredSignatureError:

        decoded = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=["HS256"],
            options={"verify_exp": False}
        )

        email = decoded.get("email")
        role = decoded.get("role")
        org_id = decoded.get("org_id")

        if role == "org_recruiter":
            user = OrgRecruiter.query.filter_by(
                email=email,
                org_id=org_id
            ).first()
        else:
            user = Admin.query.filter_by(
                email=email,
                org_id=org_id
            ).first()

        if user and not user.is_onboarding_completed:
            user.invite_status = "EXPIRED"
            db.session.commit()

        return jsonify({
            "valid": False,
            "expired": True,
            "error": "Token expired"
        }), 400

    except jwt.InvalidTokenError:
        return jsonify({"valid": False, "error": "Invalid token"}), 400
    except Exception as e:
        current_app.logger.exception("[validate-token] unexpected")
        return jsonify({"error": str(e)}), 500

# ----------------------------------------
# COMPLETE REGISTRATION
# ----------------------------------------
@org_admin_recruiter_bp.route("/onboarding/complete", methods=["POST"])
def complete_registration():
    try:
        # robust JSON parsing
        try:
            if request.content_type.startswith("multipart/form-data"):
                data = request.form.to_dict()
            else:
                data = request.get_json(force=True) 

        except Exception:
            try:
                data = json.loads(request.data.decode("utf-8") or "{}")
            except Exception:
                data = {}

        token = data.get("token")
        if not token:
            return jsonify({"error": "Token missing"}), 400

        try:
            decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 400
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 400

        role = decoded.get("role")
        email = decoded.get("email")
        org_id = decoded.get("org_id")

        if role == "org_recruiter":
            user = OrgRecruiter.query.filter_by(email=email, org_id=org_id).first()
        else:
            user = Admin.query.filter_by(email=email, org_id=org_id).first()

        if not user:
            return jsonify({"error": "User not found"}), 404

        password = data.get("password")
        confirm_password = data.get("confirm_password")

        if not password or password != confirm_password:
            return jsonify({"error": "Passwords do not match or missing"}), 400
        
        is_valid, password_error = validate_password(password)
        if not is_valid:
            return jsonify({"error": password_error}), 400

        user.password_hash = generate_password_hash(password)

        user.dob = data.get("dob")
        user.gender = data.get("gender")
        te = data.get("total_experience")
        try:
            user.total_experience = float(te) if te not in (None, "") else None
        except Exception:
            user.total_experience = None

        user.current_full_address = data.get("current_full_address")
        user.current_location = data.get("current_location")
        user.current_pincode = data.get("current_pincode")

        user.same_as_current = bool(data.get("same_as_current"))

        if user.same_as_current:
            user.permanent_full_address = data.get("current_full_address")
            user.permanent_location = data.get("current_location")
            user.permanent_pincode = data.get("current_pincode")
        else:
            user.permanent_full_address = data.get("permanent_full_address")
            user.permanent_location = data.get("permanent_location")
            user.permanent_pincode = data.get("permanent_pincode")

        # optional secondary/tertiary emails & phones
        user.email_2 = data.get("email_2")
        user.email_3 = data.get("email_3")
        user.phone_2 = data.get("phone_2")
        user.phone_3 = data.get("phone_3")

        user.email_verified = data.get("email_verified", user.email_verified)
        user.email_2_verified = data.get("email_2_verified", user.email_2_verified)
        user.email_3_verified = data.get("email_3_verified", user.email_3_verified)
        """
        user.phone_verified = data.get("phone_verified", user.phone_verified)
        user.phone_2_verified = data.get("phone_2_verified", user.phone_2_verified)
        user.phone_3_verified = data.get("phone_3_verified", user.phone_3_verified)
        """

        # Phone verification temporarily disabled
        # if not user.phone_verified:
        #     return jsonify({"error": "Primary phone must be verified"}), 400

        if not user.email_verified:
            return jsonify({"error": "Primary email must be verified"}), 400
        
        user.is_onboarding_completed = True
        user.invite_status = "ACTIVE"
        
        mapping=None
        if role == "org_recruiter" and user.global_recruiter_id:
            mapping = OrganizationRecruiter.query.filter_by(
                recruiter_id=user.global_recruiter_id,
                org_id=user.org_id
            ).first()
            if mapping:
                mapping.status = "ACTIVE"   # 🔥 THIS IS MISSING
            

            if mapping and user.team_id:
                team = Team.query.filter_by(team_id=user.team_id).first()

                if not team:
                    return jsonify({"error": "Invalid team"}), 400

                if mapping.recruiter_type == "EXTERNAL" and team.team_type != "external":
                    return jsonify({
                        "error": "External recruiters must belong to an external team"
                    }), 400

                if mapping.recruiter_type == "INTERNAL" and team.team_type != "internal":
                    return jsonify({
                        "error": "Internal recruiters must belong to an internal team"
                    }), 400


        db.session.commit()
                

        # ---- EDUCATION ----
        EducationRecruiterAdmin.query.filter_by(
            recruiter_id=user.recruiter_id if role == "org_recruiter" else None,
            admin_id=user.admin_id if role == "admin" else None
        ).delete()
        db.session.flush()

        edu_input = data.get("education") or []
        if isinstance(edu_input, dict):
            edu_input = [edu_input]
        if not isinstance(edu_input, list):
            edu_input = []

        for edu in edu_input:
            if not isinstance(edu, dict):
                continue
            if not any(edu.values()):
                continue
            db.session.add(EducationRecruiterAdmin(
                user_type=role,
                admin_id=user.admin_id if role == "admin" else None,
                recruiter_id=user.recruiter_id if role == "org_recruiter" else None,
                degree=edu.get("degree") or edu.get("degree_name"),
                score=edu.get("score"),
                major=edu.get("major"),
                minor=edu.get("minor"),
                start_year=edu.get("start_year"),
                end_year=edu.get("end_year"),
                start_month=edu.get("start_month"),
                end_month=edu.get("end_month")      
            ))

        # ---- WORK HISTORY ----
        WorkHistoryEmployee.query.filter_by(
            recruiter_id=user.recruiter_id if role == "org_recruiter" else None,
            admin_id=user.admin_id if role == "admin" else None
        ).delete()
        
        db.session.flush()

        work_input = data.get("work_history") or []
        if isinstance(work_input, dict):
            work_input = [work_input]
        if not isinstance(work_input, list):
            work_input = []

        for job in work_input:
            if not isinstance(job, dict):
                continue
            if not any(job.values()):
                continue
            designations = job.get("designations") if isinstance(job.get("designations"), list) else []
            db.session.add(WorkHistoryEmployee(
                user_type=role,
                admin_id=user.admin_id if role == "admin" else None,
                recruiter_id=user.recruiter_id if role == "org_recruiter" else None,
                organization=job.get("organization"),
                designations=designations,
                org_start_year=job.get("org_start_year"),
                org_end_year=job.get("org_end_year"),
                org_start_month=job.get("org_start_month"),
                org_end_month=job.get("org_end_month")
            ))
            
        if role == "org_recruiter":
            Documents.query.filter_by(recruiter_id=user.recruiter_id).delete()
        else:
            Documents.query.filter_by(admin_id=user.admin_id).delete()

        db.session.flush()


        

        # ---- ID PROOF ----
        id_proof_file = request.files.get("id_proof_file")
        if id_proof_file:
            save_document(user, role, id_proof_file, "id_proof")

        # ---- ADDRESS PROOF ----
        address_proof_file = request.files.get("address_proof_file")
        if address_proof_file:
            save_document(user, role, address_proof_file, "address_proof")

        # ---- OTHER DOCUMENTS ----
        other_docs = request.files.getlist("other_documents")
        for file_obj in other_docs:
            if file_obj and file_obj.filename:
                save_document(user, role, file_obj, "other_document")

        db.session.commit()



        # ---- ADD TO TEAM MEMBERS ----
        if role == "org_recruiter" and user.team_id:
            from Organization.models.team_member import TeamMember
            from datetime import datetime

            existing_member = TeamMember.query.filter_by(
                team_id=user.team_id,
                user_email=user.email
            ).first()
            
            if not existing_member:
                db.session.add(TeamMember(
                    team_id=user.team_id,
                    user_email=user.email,
                    user_name=user.name,
                    user_role="org_recruiter",
                    added_at=datetime.utcnow()
                ))
                db.session.commit()

        return jsonify({"message": "Registration completed successfully"}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error in complete_registration")
        return jsonify({"error": str(e)}), 500






@org_admin_recruiter_bp.route(
    "/superadmin/invite/resend",
    methods=["POST"]
)
@jwt_required
def resend_invite():

    try:

        data = request.get_json()

        user_id = data.get("user_id")
        role = data.get("role")

        if role == "org_recruiter":
            user = OrgRecruiter.query.filter_by(
                recruiter_id=user_id
            ).first()
        else:
            user = Admin.query.filter_by(
                admin_id=user_id
            ).first()

        if not user:
            return jsonify({
                "error": "User not found"
            }), 404

        if user.is_onboarding_completed:
            return jsonify({
                "error": "User already active"
            }), 400

        expiry_time = datetime.utcnow() + timedelta(hours=24)

        payload = {
            "name": user.name,
            "email": user.email,
            "role": role,
            "org_id": user.org_id,
            "type": "invite",
            "exp": expiry_time
        }

        token = jwt.encode(
            payload,
            SECRET_KEY,
            algorithm="HS256"
        )

        if isinstance(token, bytes):
            token = token.decode()

        user.invite_status = "PENDING"
        user.invite_sent_at = datetime.utcnow()
        user.invite_expiry_at = expiry_time
        user.invite_attempts  = (user.invite_attempts or 0) + 1

        db.session.commit()

        send_invitation_email(
            user.email,
            token,
            role
        )

        return jsonify({
            "message": "Invite resent successfully"
        }), 200

    except Exception as e:
        db.session.rollback()

        return jsonify({
            "error": str(e)
        }), 500