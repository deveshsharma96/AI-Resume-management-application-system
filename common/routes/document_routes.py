"""
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
import jwt

import uuid

from extensions import db
from common.utils.storage_service import upload_file

# ✅ NEW MODEL
from common.models.document_asset import DocumentAsset

# User resolution
from recruiter.models.recruiter_model import Recruiter
from Organization.models.super_admin import SuperAdmin
from recruiter.models.org_recruiter_model import OrgRecruiter
from recruiter.models.admin_model import Admin
from datetime import datetime
from Organization.models.organization_form_link import OrganizationFormLink
from Candidates.models.candidate import Candidate
from flask import current_app




documents_bp = Blueprint(
    "documents_bp",
    __name__,
    url_prefix="/documents"
)

# -------------------------------------------------
# Resolve current user from header
# -------------------------------------------------
def get_current_user():
    email = request.headers.get("X-User-Email")
    if not email:
        return None

    for model in [SuperAdmin, Recruiter, OrgRecruiter, Admin]:
        try:
            user = model.find_by_email(email)
        except Exception:
            user = None
        if user:
            return user
    return None


# -------------------------------------------------
# Upload Document (NO cand_id required)
# -------------------------------------------------
@documents_bp.route("/upload", methods=["POST"])
def upload_document():

    # ---------------- USER RESOLUTION ----------------
    actor = get_current_user()
    org_id = None
    uploaded_by = None

# ==================================================
    # 1️⃣ Logged-in User
    # ==================================================
    if actor:
        org_id = getattr(actor, "org_id", None)
        uploaded_by = actor.email

    else:

        candidate_token = request.form.get("candidate_token")
        invite_token = request.form.get("invite_token")
        form_token = request.form.get("form_token")

        # ==================================================
        # 2️⃣ Candidate Prefilled Token
        # ==================================================
        if candidate_token:
            try:
                decoded = jwt.decode(
                    candidate_token,
                    current_app.config["JWT_SECRET_KEY"],
                    algorithms=["HS256"]
                )

                email = decoded.get("email")
                if not email:
                    return jsonify({
                        "status": "error",
                        "message": "Invalid candidate token"
                    }), 400

                email = email.strip().lower()
                candidate = Candidate.query.filter_by(email=email).first()

                if not candidate:
                    return jsonify({
                        "status": "error",
                        "message": "Invalid candidate token"
                    }), 400

                org_id = candidate.org_id
                uploaded_by = email

            except jwt.ExpiredSignatureError:
                return jsonify({
                    "status": "error",
                    "message": "Candidate token expired"
                }), 400

            except jwt.InvalidTokenError:
                return jsonify({
                    "status": "error",
                    "message": "Invalid candidate token"
                }), 400

        # ==================================================
        # 3️⃣ Invite Token (Admin / Recruiter onboarding)
        # ==================================================
        elif invite_token:
            try:
                decoded = jwt.decode(
                    invite_token,
                    current_app.config["SECRET_KEY"],
                    algorithms=["HS256"]
                )

                org_id = decoded.get("org_id")
                uploaded_by = decoded.get("email")

            except jwt.ExpiredSignatureError:
                return jsonify({
                    "status": "error",
                    "message": "Invite token expired"
                }), 400

            except jwt.InvalidTokenError:
                return jsonify({
                    "status": "error",
                    "message": "Invalid invite token"
                }), 400

        # ==================================================
        # 4️⃣ Public Org Form Token (DB based)
        # ==================================================
        elif form_token:
            form_link = OrganizationFormLink.query.filter_by(token=form_token).first()

            if not form_link:
                return jsonify({
                    "status": "error",
                    "message": "Invalid form token"
                }), 400

            org_id = form_link.org_id
            uploaded_by = "public_candidate"

        else:
            return jsonify({
                "status": "error",
                "message": "Unauthorized - missing user or token"
            }), 401


    if not org_id:
        return jsonify({
            "status": "error",
            "message": "Organization not found"
        }), 400

    document_type = request.form.get("document_name")  # resume / cover_letter / other
    file = request.files.get("file")

    if not document_type or not file:
        return jsonify({
            "status": "error",
            "message": "document_name and file are required"
        }), 400

    # ---------------- FILE VALIDATION ----------------
    ALLOWED_EXTENSIONS = {".pdf", ".docx", ".png", ".jpg", ".jpeg"}
    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({
            "status": "error",
            "message": "Unsupported file type"
        }), 400

    temp_dir = "uploads/documents"
    os.makedirs(temp_dir, exist_ok=True)

    safe_name = secure_filename(file.filename)
    temp_path = os.path.join(
        temp_dir,
        f"{uuid.uuid4()}_{safe_name}"
    )

    try:
        # ---------------- SAVE TEMP FILE ----------------
        file.save(temp_path)
        file_size = os.path.getsize(temp_path)

        # ---------------- UPLOAD TO OBJECT STORAGE ----------------
        file_key = upload_file(
            temp_path,
            folder="documents/staging"
        )

        # ---------------- CREATE DOCUMENT ASSET ----------------
        asset = DocumentAsset(
            file_key=file_key,
            original_filename=file.filename,
            mime_type=file.content_type,
            file_size=file_size,
            document_type=document_type,
            uploaded_by=uploaded_by,
            uploaded_at=datetime.utcnow(),
            org_id=org_id,
        )

        db.session.add(asset)
        db.session.commit()

        return jsonify({
            "status": "success",
            "docu_id": asset.docu_id,
            "file_key": asset.file_key,
            "document_type": asset.document_type
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


            """




from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.utils import secure_filename
import os
import jwt
import uuid
from datetime import datetime

from extensions import db

from common.utils.storage_service import upload_file
from common.models.document_asset import DocumentAsset

from Organization.models.organization_form_link import OrganizationFormLink
from Candidates.models.candidate import Candidate

from auth.utils.jwt_required import jwt_optional


documents_bp = Blueprint(
    "documents_bp",
    __name__,
    url_prefix="/documents"
)


# -------------------------------------------------
# Helper: get user from JWT if available
# -------------------------------------------------
def get_current_user():
    if hasattr(g, "current_user"):
        return g.current_user
    return None


# -------------------------------------------------
# Upload Document (NO cand_id required)
# -------------------------------------------------
@documents_bp.route("/upload", methods=["POST"])
@jwt_optional
def upload_document():

    actor = get_current_user()

    org_id = None
    uploaded_by = None

    # ==================================================
    # 1️⃣ Logged-in User (JWT)
    # ==================================================
    if actor:
        org_id = actor["org_id"]
        uploaded_by = actor["user_id"]

    else:

        candidate_token = request.form.get("candidate_token")
        invite_token = request.form.get("invite_token")
        form_token = request.form.get("form_token")

        # ==================================================
        # 2️⃣ Candidate Prefilled Token
        # ==================================================
        if candidate_token:

            try:
                decoded = jwt.decode(
                    candidate_token,
                    current_app.config["JWT_SECRET_KEY"],
                    algorithms=["HS256"]
                )

                email = decoded.get("email")

                if not email:
                    return jsonify({
                        "status": "error",
                        "message": "Invalid candidate token"
                    }), 400

                email = email.strip().lower()

                candidate = Candidate.query.filter_by(email=email).first()

                if not candidate:
                    return jsonify({
                        "status": "error",
                        "message": "Invalid candidate token"
                    }), 400

                org_id = candidate.org_id
                uploaded_by = email

            except jwt.ExpiredSignatureError:
                return jsonify({
                    "status": "error",
                    "message": "Candidate token expired"
                }), 400

            except jwt.InvalidTokenError:
                return jsonify({
                    "status": "error",
                    "message": "Invalid candidate token"
                }), 400

        # ==================================================
        # 3️⃣ Invite Token (Admin / Recruiter onboarding)
        # ==================================================
        elif invite_token:

            try:
                decoded = jwt.decode(
                    invite_token,
                    current_app.config["SECRET_KEY"],
                    algorithms=["HS256"]
                )

                org_id = decoded.get("org_id")
                uploaded_by = decoded.get("email")

            except jwt.ExpiredSignatureError:
                return jsonify({
                    "status": "error",
                    "message": "Invite token expired"
                }), 400

            except jwt.InvalidTokenError:
                return jsonify({
                    "status": "error",
                    "message": "Invalid invite token"
                }), 400

        # ==================================================
        # 4️⃣ Public Org Form Token (DB based)
        # ==================================================
        elif form_token:

            form_link = OrganizationFormLink.query.filter_by(
                token=form_token
            ).first()

            if not form_link:
                return jsonify({
                    "status": "error",
                    "message": "Invalid form token"
                }), 400

            org_id = form_link.org_id
            uploaded_by = "public_candidate"

        else:
            return jsonify({
                "status": "error",
                "message": "Unauthorized - missing user or token"
            }), 401

    # -------------------------------------------------
    # Org check
    # -------------------------------------------------
    if not org_id:
        return jsonify({
            "status": "error",
            "message": "Organization not found"
        }), 400

    document_type = request.form.get("document_name")
    file = request.files.get("file")

    if not document_type or not file:
        return jsonify({
            "status": "error",
            "message": "document_name and file are required"
        }), 400

    # -------------------------------------------------
    # Document type validation
    # -------------------------------------------------
    ALLOWED_DOCUMENT_TYPES = {
        "resume",
        "cover_letter",
        "certificate",
        "id_proof",
        "other"
    }

    if document_type not in ALLOWED_DOCUMENT_TYPES:
        return jsonify({
            "status": "error",
            "message": "Invalid document type"
        }), 400

    # -------------------------------------------------
    # File validation
    # -------------------------------------------------
    ALLOWED_EXTENSIONS = {".pdf", ".docx", ".png", ".jpg", ".jpeg"}

    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({
            "status": "error",
            "message": "Unsupported file type"
        }), 400

    # -------------------------------------------------
    # Temp storage
    # -------------------------------------------------
    temp_dir = "uploads/documents"
    os.makedirs(temp_dir, exist_ok=True)

    safe_name = secure_filename(file.filename)

    temp_path = os.path.join(
        temp_dir,
        f"{uuid.uuid4()}_{safe_name}"
    )

    try:

        # Save temp
        file.save(temp_path)

        file_size = os.path.getsize(temp_path)

        # Upload to object storage
        file_key = upload_file(
            temp_path,
            folder="documents/staging"
        )

        # Create asset
        asset = DocumentAsset(
            file_key=file_key,
            original_filename=file.filename,
            mime_type=file.content_type,
            file_size=file_size,
            document_type=document_type,
            uploaded_by=uploaded_by,
            uploaded_at=datetime.utcnow(),
            org_id=org_id
        )

        db.session.add(asset)
        db.session.commit()

        return jsonify({
            "status": "success",
            "docu_id": asset.docu_id,
            "file_key": asset.file_key,
            "document_type": asset.document_type
        }), 201

    except Exception as e:

        db.session.rollback()

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

    finally:

        if os.path.exists(temp_path):
            os.remove(temp_path)