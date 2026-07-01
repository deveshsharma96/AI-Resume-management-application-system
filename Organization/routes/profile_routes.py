


from recruiter.utils.email_utils import send_verification_code as send_recruiter_otp
from Organization.utils.email_utils import send_verification_code as send_superadmin_otp
from recruiter.utils.otp_utils import send_sms_otp, generate_otp, verify_otp
from Logs.log_helper import create_log

from flask import Blueprint, request, jsonify, g
from auth.utils.jwt_required import jwt_required

from Organization.models.super_admin import SuperAdmin
from Organization.models.team_member import TeamMember
from Organization.models.team import Team

from recruiter.models.recruiter_model import Recruiter
from recruiter.models.admin_model import Admin
from recruiter.models.org_recruiter_model import OrgRecruiter

from extensions import db
from Organization.models.otp import OTP

from recruiter.models.education_recruiter_admin_model import EducationRecruiterAdmin
from recruiter.models.work_history_employee_model import WorkHistoryEmployee
from recruiter.models.documents_model import Documents

from GlobalRecruiter.models.recruiters import GlobalRecruiter
from GlobalRecruiter.models.organization_recruiter import OrganizationRecruiter


profile_bp = Blueprint("profile_bp", __name__)


# --------------------------------------------------------
# JWT current user helper
# --------------------------------------------------------
def get_current_user():
    if not hasattr(g, "current_user"):
        return None
    return g.current_user


# --------------------------------------------------------
# Helper: find user by email
# --------------------------------------------------------
def find_user_by_email(identifier, org_id=None):

    if not identifier:
        return None

    identifier = identifier.strip().lower()

    # ---------------- SUPER ADMIN ----------------
    super_admin = SuperAdmin.query.filter_by(email=identifier).first()
    if super_admin:
        return super_admin

    # ---------------- ADMIN ----------------
    admin = Admin.query.filter_by(email=identifier).first()
    if admin:
        return admin
    
    # ---------------- ORG RECRUITER ----------------
    org_rec = OrgRecruiter.query.filter_by(email=identifier).first()

    if org_rec:
        return org_rec

    # ---------------- GLOBAL RECRUITER ----------------
    global_rec = GlobalRecruiter.query.filter_by(email=identifier).first()

    if global_rec:

        if org_id:
            mapping = OrganizationRecruiter.query.filter_by(
                recruiter_id=global_rec.recruiter_id,
                org_id=org_id,
                status="ACTIVE"
            ).first()

            if not mapping:
                return None

            global_rec._dynamic_role = mapping.role.lower()
        else:
            global_rec._dynamic_role = "recruiter"

        return global_rec

    # ---------------- FREELANCER RECRUITER ----------------
    # Try email first
    freelancer = Recruiter.query.filter_by(email=identifier).first()

    if freelancer:
        return freelancer

    # Try rec_id (THIS IS YOUR FIX 🔥)
    freelancer = Recruiter.query.filter_by(rec_id=identifier).first()

    if freelancer:
        return freelancer

    return None

# --------------------------------------------------------
# Normalizers
# --------------------------------------------------------
def normalize_year(value):
    if value in ("", None):
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def normalize_month(value):
    if value in ("", None):
        return None
    return value


def normalize_designations(designations):

    if not designations:
        return []

    normalized = []

    for d in designations:
        normalized.append({
            "designation": d.get("designation"),
            "responsibilities": d.get("responsibilities"),
            "start_year": normalize_year(d.get("start_year")),
            "end_year": normalize_year(d.get("end_year")),
            "start_month": normalize_month(d.get("start_month")),
            "end_month": normalize_month(d.get("end_month")),
        })

    return normalized


# --------------------------------------------------------
# GET USER PROFILE
# --------------------------------------------------------
@profile_bp.route("/user/<string:email>", methods=["GET"])
@jwt_required
def get_user_profile(email):

    org_id = request.args.get("org_id")

    user = find_user_by_email(email, org_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    role = getattr(user, "role", "unknown")

    team_info = None
    team_members = []

    membership = TeamMember.query.filter_by(user_email=user.email).first()

    if membership:

        team = Team.query.filter_by(team_id=membership.team_id).first()

        if team:

            team_info = {
                "team_id": team.team_id,
                "team_name": team.team_name
            }

            members = TeamMember.query.filter_by(team_id=team.team_id).all()

            team_members = [{
                "id": m.id,
                "email": m.user_email,
                "name": m.user_name,
                "role": m.user_role,
                "added_at": m.added_at.isoformat()
            } for m in members]

    education = [{
        "degree": e.degree,
        "degree_name": e.degree,
        "score": e.score,
        "major": e.major,
        "minor": e.minor,
        "start_year": e.start_year,
        "end_year": e.end_year,
        "start_month": e.start_month,
        "end_month": e.end_month
    } for e in getattr(user, "education", [])]

    work_history = [{
        "organization": w.organization,
        "org_start_year": w.org_start_year,
        "org_end_year": w.org_end_year,
        "designations": w.designations,
        "org_start_month": w.org_start_month,
        "org_end_month": w.org_end_month
    } for w in getattr(user, "work_history", [])]

    documents = [{
        "document_name": d.document_name,
        "file_path": d.file_path
    } for d in getattr(user, "documents", [])]

    return jsonify({
        "profile": {
            "name": getattr(user, "name", None),
            "email": user.email,
            "designation": getattr(user, "designation", None),
            "phone": getattr(user, "phone", None),
            "role": role,
            "org_id": org_id,

            "dob": getattr(user, "dob", None),
            "gender": getattr(user, "gender", None),

            "email_verified": getattr(user, "email_verified", False),
            "phone_verified": getattr(user, "phone_verified", False),

            "email_2": getattr(user, "email_2", None),
            "email_3": getattr(user, "email_3", None),
            "phone_2": getattr(user, "phone_2", None),
            "phone_3": getattr(user, "phone_3", None),

            "email_2_verified": getattr(user, "email_2_verified", False),
            "email_3_verified": getattr(user, "email_3_verified", False),
            "phone_2_verified": getattr(user, "phone_2_verified", False),
            "phone_3_verified": getattr(user, "phone_3_verified", False),

            "team_info": team_info,
            "degrees": education,
            "work_history": work_history,
            "documents": documents
        }
    }), 200

@profile_bp.route("/update-profile", methods=["PUT"])
@jwt_required
def update_profile():

    data = request.get_json(silent=True)

    if isinstance(data, str):
        import json
        data = json.loads(data)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON payload"}), 400

    # ---------------- JWT USER ----------------
    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    current_email = current_user["user_id"]

    role = data.get("role")
    org_id = data.get("org_id")

    # 🔥 Important change for GlobalRecruiter architecture
    user = find_user_by_email(current_email, org_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    try:
        audit_changes = {}

        # ---------------- BASIC FIELDS ----------------
        simple_fields = [
            "name", "dob", "gender", "designation",
            "current_full_address", "current_pincode",
            "permanent_full_address", "permanent_pincode",
            "same_as_current", "total_experience",
            "email_2", "email_3",
            "phone_2", "phone_3",
            "email_2_verified", "email_3_verified",
            "phone_2_verified", "phone_3_verified"
        ]

        for field in simple_fields:
            if field in data and hasattr(user, field):

                old_value = getattr(user, field)
                new_value = data[field]

                if old_value != new_value:

                    audit_changes[field] = {
                        "old": old_value,
                        "new": new_value
                    }

                    setattr(user, field, new_value)

        # ---------------- LOCATIONS ----------------
        curr = data.get("current_location") or {}
        perm = data.get("permanent_location") or {}

        user.current_country = curr.get("country")
        user.current_state = curr.get("state")
        user.current_city = curr.get("city")

        user.permanent_country = perm.get("country")
        user.permanent_state = perm.get("state")
        user.permanent_city = perm.get("city")

        # ---------------- EMAIL CHANGE ----------------
        new_email = data.get("email")

        if new_email:

            new_email = new_email.strip().lower()

            if new_email != user.email:

                otp_verified = OTP.query.filter_by(
                    email=new_email,
                    otp_type="email_change",
                    verified=True
                ).first()

                if not otp_verified:
                    raise ValueError("Email is not verified")

                audit_changes["email"] = {
                    "old": user.email,
                    "new": new_email
                }

                user.email = new_email
                user.email_verified = True

        # ---------------- PHONE CHANGE ----------------
        if data.get("phone"):

            new_phone = data["phone"].strip()

            if new_phone != user.phone:

                audit_changes["phone"] = {
                    "old": user.phone,
                    "new": new_phone
                }

                user.phone = new_phone
                user.phone_verified = False

        # ==========================================================
        # EDUCATION / WORK / DOCUMENTS
        # ==========================================================
        if role in ["admin", "org_recruiter"]:

            if role == "admin":

                EducationRecruiterAdmin.query.filter_by(
                    user_type="admin",
                    admin_id=user.admin_id
                ).delete()

            elif role == "org_recruiter":

                EducationRecruiterAdmin.query.filter_by(
                    user_type="org_recruiter",
                    recruiter_id=user.recruiter_id
                ).delete()

            for edu in (data.get("degrees") or []):

                if not any(edu.values()):
                    continue

                degree_value = edu.get("degree") or edu.get("degree_name")

                db.session.add(
                    EducationRecruiterAdmin(
                        user_type=role,
                        admin_id=user.admin_id if role == "admin" else None,
                        recruiter_id=user.recruiter_id if role == "org_recruiter" else None,
                        degree=degree_value,
                        score=edu.get("score"),
                        major=edu.get("major"),
                        minor=edu.get("minor"),
                        start_year=normalize_year(edu.get("start_year")),
                        end_year=normalize_year(edu.get("end_year")),
                        start_month=normalize_month(edu.get("start_month")),
                        end_month=normalize_month(edu.get("end_month"))
                    )
                )

            # ---------------- WORK HISTORY ----------------
            if role == "admin":

                WorkHistoryEmployee.query.filter_by(
                    user_type="admin",
                    admin_id=user.admin_id
                ).delete()

            elif role == "org_recruiter":

                WorkHistoryEmployee.query.filter_by(
                    user_type="org_recruiter",
                    recruiter_id=user.recruiter_id
                ).delete()

            for job in (data.get("work_history") or []):

                if not any(job.values()):
                    continue

                db.session.add(
                    WorkHistoryEmployee(
                        user_type=role,
                        admin_id=user.admin_id if role == "admin" else None,
                        recruiter_id=user.recruiter_id if role == "org_recruiter" else None,
                        organization=job.get("organization"),
                        designations=normalize_designations(job.get("designations")),
                        org_start_year=normalize_year(job.get("org_start_year")),
                        org_end_year=normalize_year(job.get("org_end_year")),
                        org_start_month=normalize_month(job.get("org_start_month")),
                        org_end_month=normalize_month(job.get("org_end_month")),
                    )
                )

            # ---------------- DOCUMENTS ----------------
            if role == "admin":

                Documents.query.filter_by(
                    user_type="admin",
                    admin_id=user.admin_id
                ).delete()

            elif role == "org_recruiter":

                Documents.query.filter_by(
                    user_type="org_recruiter",
                    recruiter_id=user.recruiter_id
                ).delete()

            for doc in (data.get("documents") or []):

                if not any(doc.values()):
                    continue

                db.session.add(
                    Documents(
                        user_type=role,
                        admin_id=user.admin_id if role == "admin" else None,
                        recruiter_id=user.recruiter_id if role == "org_recruiter" else None,
                        document_name=doc.get("document_name"),
                        file_path=doc.get("file_path"),
                        base64_content=doc.get("bytes")
                    )
                )

        # ---------------- ENTITY ID ----------------
        entity_id = None

        if role == "admin":
            entity_id = user.admin_id

        elif role == "org_recruiter":
            entity_id = user.recruiter_id

        elif role == "superadmin":
            entity_id = user.admin_id

        create_log(
            user=user,
            action="update_profile",
            entity_type=role,
            entity_id=entity_id,
            data=audit_changes
        )

        db.session.commit()

        return jsonify({"message": "Profile updated successfully"}), 200

    except ValueError as ve:

        db.session.rollback()

        return jsonify({"error": str(ve)}), 400

    except Exception as e:

        db.session.rollback()

        return jsonify({
            "error": "Profile update failed",
            "details": str(e)
        }), 500