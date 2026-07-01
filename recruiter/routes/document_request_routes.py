# # recruiter/routes/document_request_routes.py

# from flask import Blueprint, request, jsonify
# from flask import request
# from recruiter.services.document_request_service import (
#     create_document_request
# )

# from recruiter.models.document_request_model import (
#     DocumentRequest
# )

# from recruiter.models.candidate_uploaded_document_model import (
#     CandidateUploadedDocument
# )

# from extensions import db


# document_request_bp = Blueprint(
#     "document_request_bp",
#     __name__
# )


# @document_request_bp.route("/create", methods=["POST"])

# def create_request():

#     try:
#         # ---------------- AUTHORIZATION CHECK ----------------

#         auth_header = request.headers.get("Authorization")

#         if not auth_header:

#             return jsonify({
#                 "success": False,
#                 "message": "Authorization token missing"
#             }), 401

#         # Optional: check Bearer format
#         if not auth_header.startswith("Bearer "):

#             return jsonify({
#                 "success": False,
#                 "message": "Invalid authorization format"
#             }), 401

#         token = auth_header.split(" ")[1]

#         print("=" * 50)
#         print("ORG TOKEN RECEIVED")
#         print(token)
#         print("=" * 50)

#         # -----------------------------------------------------

#         data = request.get_json()

#         result = create_document_request(data)

#         return jsonify({
#             "success": True,
#             "message": "Document request created successfully",
#             "request_id": result["document_request"].id,
#             "upload_link": result["upload_link"]
#         }), 201

#     except Exception as e:

#         return jsonify({
#             "success": False,
#             "message": str(e)
#         }), 500


# @document_request_bp.route(
#     "/candidate/<int:candidate_id>",
#     methods=["GET"]
# )
# def get_candidate_requests(candidate_id):

#     try:

#         requests = DocumentRequest.query.filter_by(
#             candidate_id=candidate_id
#         ).all()

#         response = []

#         for req in requests:

#             response.append({
#                 "request_id": req.id,
#                 "documents": req.documents,
#                 "status": req.status,
#                 "created_at": req.created_at
#             })

#         return jsonify({
#             "success": True,
#             "data": response
#         }), 200

#     except Exception as e:

#         return jsonify({
#             "success": False,
#             "message": str(e)
#         }), 500


# @document_request_bp.route("/review", methods=["PUT"])
# def review_document():

#     try:

#         data = request.get_json()

#         document = CandidateUploadedDocument.query.get(
#             data["document_id"]
#         )

#         if not document:

#             return jsonify({
#                 "success": False,
#                 "message": "Document not found"
#             }), 404

#         document.status = data["status"]

#         document.comments = data.get("comments")

#         db.session.commit()

#         return jsonify({
#             "success": True,
#             "message": "Document reviewed successfully"
#         }), 200

#     except Exception as e:

#         return jsonify({
#             "success": False,
#             "message": str(e)
#         }), 500



# recruiter/routes/document_request_routes.py

from flask import Blueprint, request, jsonify, g

from auth.utils.jwt_required import jwt_required


from extensions import db

from recruiter.models.document_request_model import (
    DocumentRequest
)

from recruiter.models.candidate_request_document_model import (
    CandidateRequestDocument
)

from Candidates.models.candidate import (
    Candidate
)

from common.models.document_asset import (
    DocumentAsset
)

from Organization.utils.email_utils import (
    send_document_request_email
)

import uuid

from datetime import datetime


document_request_bp = Blueprint(
    "document_request_bp",
    __name__
)

# ---------------------------------------------------------
# CURRENT USER
# ---------------------------------------------------------

def get_current_user():

    if not hasattr(g, "current_user"):
        return None

    return g.current_user



# ---------------------------------------------------------
# CREATE DOCUMENT REQUEST
# ---------------------------------------------------------

@document_request_bp.route(
    "/create",
    methods=["POST"]
)
@jwt_required
def create_request():

    try:

        current_user = get_current_user()

        if not current_user:

            return jsonify({
                "success": False,
                "message": "Unauthorized"
            }), 401
            
            
        allowed_roles = [

            "superadmin",

            "admin",

            "org_recruiter"
        ]

        if current_user["role"] not in allowed_roles:

            return jsonify({
                "success": False,
                "message": "Permission denied"
            }), 403

        data = request.get_json()

        org_id = current_user["org_id"]

        candidate_id = data.get("candidate_id")

        documents = data.get("documents", [])

        template_name = data.get(
            "template_name"
        )

        # -------------------------------------------------
        # DEACTIVATE OLD REQUESTS
        # -------------------------------------------------
   
        
        existing_request = DocumentRequest.query.filter_by(
            candidate_id=candidate_id,
            org_id=org_id,
            is_active=True
        ).first()

        # -------------------------------------------------
        # CREATE REQUEST
        # -------------------------------------------------

        # -------------------------------------------------
        # UPDATE EXISTING REQUEST
        # -------------------------------------------------

        if existing_request:

            old_documents = list(
                existing_request.documents or []
            )

            existing_document_names = {
                doc["name"].lower().strip()
                for doc in old_documents
            }

            updated_documents = old_documents.copy()

            for new_doc in documents:

                if new_doc["name"].lower().strip() not in existing_document_names:

                    updated_documents.append(new_doc)

            existing_request.documents = updated_documents

            existing_request.template_name = template_name

            existing_request.status = "pending"

            existing_request.requested_by = (
                current_user["user_id"]
            )

            existing_request.requested_by_role = (
                current_user["role"]
            )

            db.session.commit()

            document_request = existing_request

            upload_token = existing_request.upload_token
            
            message = "Document request updated successfully"

        # -------------------------------------------------
        # CREATE NEW REQUEST
        # -------------------------------------------------

        else:

            upload_token = str(uuid.uuid4())

            document_request = DocumentRequest(

                org_id=org_id,

                candidate_id=candidate_id,

                template_name=template_name,

                documents=documents,

                upload_token=upload_token,

                status="pending",

                requested_by=current_user["user_id"],

                requested_by_role=current_user["role"],

                is_active=True
            )

            db.session.add(document_request)

            db.session.commit()
            
            message = "Document request created successfully"

        # -------------------------------------------------
        # GET CANDIDATE EMAIL
        # -------------------------------------------------

        candidate = Candidate.query.filter_by(
            cand_id=candidate_id
        ).first()

        # -------------------------------------------------
        # SEND EMAIL
        # -------------------------------------------------

        if candidate and candidate.email:

            send_document_request_email(

                to_email=candidate.email,

                candidate_name=(
                    candidate.name
                    if candidate.name
                    else "Candidate"
                ),

                upload_token=upload_token,

                documents=document_request.documents
            )

        return jsonify({

            "success": True,

            "message": message,

            "request_id":
                document_request.id,

            "upload_token":
                upload_token

        }), 201

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ---------------------------------------------------------
# GET REQUESTS OF CANDIDATE
# ---------------------------------------------------------

@document_request_bp.route(
    "/candidate/<string:candidate_id>",
    methods=["GET"]
)
@jwt_required
def get_candidate_requests(candidate_id):

    try:

        requests = DocumentRequest.query.filter_by(
            candidate_id=candidate_id
        ).order_by(
            DocumentRequest.created_at.desc()
        ).all()

        response = []

        for req in requests:

            response.append({

                "request_id":
                    req.id,

                "template_name":
                    req.template_name,

                "documents":
                    req.documents,

                "request_status":
                    req.status,

                "is_active":
                    req.is_active,

                "created_at":
                    req.created_at

            })

        return jsonify({
            "success": True,
            "data": response
        }), 200

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ---------------------------------------------------------
# GET SUBMITTED DOCUMENTS
# ORGANIZATION SIDE
# ---------------------------------------------------------

@document_request_bp.route(
    "/submitted/<int:request_id>",
    methods=["GET"]
)
@jwt_required
def get_submitted_documents(request_id):

    try:
        
        current_user = get_current_user()

        if not current_user:

            return jsonify({
                "success": False,
                "message": "Unauthorized"
            }), 401


        allowed_roles = [

            "superadmin",

            "admin",

            "org_recruiter"
        ]

        if current_user["role"] not in allowed_roles:

            return jsonify({
                "success": False,
                "message": "Permission denied"
            }), 403
            
        document_request = DocumentRequest.query.filter_by(
            id=request_id,
            org_id=current_user["org_id"]
        ).first()

        if not document_request:

            return jsonify({
                "success": False,
                "message": "Request not found"
            }), 404

        submitted_documents = CandidateRequestDocument.query.filter_by(
            request_id=request_id,
            is_latest=True
        ).all()

        response = []

        for submitted_doc in submitted_documents:

            asset = DocumentAsset.query.filter_by(
                docu_id=submitted_doc.docu_id
            ).first()

            response.append({

                "request_document_id":
                    submitted_doc.id,

                "document_name":
                    submitted_doc.document_name,

                "docu_id":
                    submitted_doc.docu_id,

                "status":
                    submitted_doc.status,

                "rejection_reason":
                    submitted_doc.rejection_reason,

                "approved_by":
                    submitted_doc.approved_by,

                "approved_at":
                    submitted_doc.approved_at,

                "submitted_at":
                    submitted_doc.submitted_at,

                "file_name":
                    asset.original_filename
                    if asset else None,

                "mime_type":
                    asset.mime_type
                    if asset else None,

                "file_size":
                    asset.file_size
                    if asset else None
            })

        return jsonify({

            "success": True,

            "request_id":
                request_id,

            "documents":
                response

        }), 200

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ---------------------------------------------------------
# REVIEW DOCUMENT
# ---------------------------------------------------------

@document_request_bp.route(
    "/review",
    methods=["PUT"]
)
@jwt_required
def review_document():

    try:
        
        current_user = get_current_user()

        if not current_user:

            return jsonify({
                "success": False,
                "message": "Unauthorized"
            }), 401
            
        
        allowed_roles = [

            "superadmin",

            "admin",

            "org_recruiter"
        ]

        if current_user["role"] not in allowed_roles:

            return jsonify({
                "success": False,
                "message": "Permission denied"
            }), 403

        data = request.get_json()

        request_document_id = data.get(
            "request_document_id"
        )

        status = data.get("status")

        rejection_reason = data.get(
            "rejection_reason"
        )

        

        submitted_doc = CandidateRequestDocument.query.get(
            request_document_id
        )

        if not submitted_doc:

            return jsonify({
                "success": False,
                "message": "Document not found"
            }), 404
            
        # -----------------------------------------
        # VALIDATE SAME ORG ACCESS
        # -----------------------------------------

        if submitted_doc.org_id != current_user["org_id"]:

            return jsonify({
                "success": False,
                "message": "Unauthorized access"
            }), 403

        submitted_doc.status = status

        if status == "rejected":

            submitted_doc.rejection_reason = (
                rejection_reason
            )

            submitted_doc.approved_by = current_user["user_id"]

            submitted_doc.approved_at = datetime.utcnow()

        if status == "approved":

            submitted_doc.approved_by = current_user["user_id"]

            submitted_doc.approved_at = datetime.utcnow()

        db.session.commit()

        return jsonify({

            "success": True,

            "message":
                "Document reviewed successfully"

        }), 200

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
        

# ---------------------------------------------------------
# WITHDRAW DOCUMENT REQUEST
# ---------------------------------------------------------

@document_request_bp.route(
    "/withdraw/<int:request_id>",
    methods=["PUT"]
)
@jwt_required
def withdraw_document_request(request_id):

    try:

        current_user = get_current_user()

        if not current_user:

            return jsonify({
                "success": False,
                "message": "Unauthorized"
            }), 401

        allowed_roles = [

            "superadmin",

            "admin",

            "org_recruiter"
        ]

        if current_user["role"] not in allowed_roles:

            return jsonify({
                "success": False,
                "message": "Permission denied"
            }), 403

        document_request = DocumentRequest.query.filter_by(
            id=request_id,
            org_id=current_user["org_id"]
        ).first()

        if not document_request:

            return jsonify({
                "success": False,
                "message": "Request not found"
            }), 404

        document_request.status = "withdrawn"

        document_request.is_active = False

        document_request.withdrawn_by = (
            current_user["user_id"]
        )

        db.session.commit()

        return jsonify({

            "success": True,

            "message":
                "Request withdrawn successfully"

        }), 200

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500