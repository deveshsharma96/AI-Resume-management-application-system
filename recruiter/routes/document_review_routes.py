
from flask import Blueprint, request, jsonify, g

from extensions import db

from recruiter.models.candidate_request_document_model import (
    CandidateRequestDocument
)

from common.models.document_asset import (
    DocumentAsset
)

from datetime import datetime

from auth.utils.jwt_required import jwt_required
from recruiter.models.document_request_model import DocumentRequest

from recruiter.models.org_recruiter_model import OrgRecruiter

document_review_bp = Blueprint(
    "document_review_bp",
    __name__
)


# ---------------------------------------------------------
# GET SUBMITTED DOCUMENTS
# ---------------------------------------------------------

@document_review_bp.route(
    "/submitted/<int:request_id>",
    methods=["GET"]
)
@jwt_required
def get_submitted_documents(request_id):
    
    current_user = g.current_user

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

    try:

        submitted_documents = CandidateRequestDocument.query.filter_by(
            request_id=request_id,
            is_latest=True
        ).all()

        response = []

        for submitted_doc in submitted_documents:
            
            
            approved_recruiter = None

            if submitted_doc.approved_by:

                approved_recruiter = OrgRecruiter.query.filter_by(
                    email=submitted_doc.approved_by
                ).first() 

            asset = DocumentAsset.query.filter_by(
                docu_id=submitted_doc.docu_id
            ).first()

            response.append({

                "request_document_id":
                    submitted_doc.id,

                "request_id":
                    submitted_doc.request_id,

                "document_name":
                    submitted_doc.document_name,

                "docu_id":
                    submitted_doc.docu_id,

                "status":
                    submitted_doc.status,

                "rejection_reason":
                    submitted_doc.rejection_reason,

                "approved_by": {

                    "email":
                        submitted_doc.approved_by,

                    "recruiter_id":
                        approved_recruiter.recruiter_id
                        if approved_recruiter else None,

                    "name":
                        approved_recruiter.name
                        if approved_recruiter else None

                } if submitted_doc.approved_by else None,

                "approved_at":
                    submitted_doc.approved_at,

                "submitted_at":
                    submitted_doc.submitted_at,

                "is_latest":
                    submitted_doc.is_latest,

                "file_name":
                    asset.original_filename
                    if asset else None,

                "mime_type":
                    asset.mime_type
                    if asset else None,

                "file_size":
                    asset.file_size
                    if asset else None,

                "file_key":
                    asset.file_key
                    if asset else None
            })

        return jsonify({

            "success": True,

            "request_id": request_id,

            "documents": response

        }), 200

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ---------------------------------------------------------
# REVIEW DOCUMENT
# ---------------------------------------------------------

@document_review_bp.route(
    "/review",
    methods=["PUT"]
)
@jwt_required
def review_document():

    try:

        current_user = g.current_user

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

        data = request.json

        docu_id = data.get("docu_id")

        status = data.get("status")

        rejection_reason = data.get(
            "rejection_reason"
        )

        approved_by = current_user["user_id"]

        # -------------------------------------------------
        # FIND DOCUMENT
        # -------------------------------------------------

        document = CandidateRequestDocument.query.filter_by(
            docu_id=docu_id,
            is_latest=True
        ).first()

        if not document:

            return jsonify({
                "success": False,
                "message": "Document not found"
            }), 404

        # -------------------------------------------------
        # SECURITY CHECK
        # -------------------------------------------------

        document_request = DocumentRequest.query.filter_by(
            id=document.request_id,
            org_id=current_user["org_id"]
        ).first()

        if not document_request:

            return jsonify({
                "success": False,
                "message": "Unauthorized access"
            }), 403

        # -------------------------------------------------
        # UPDATE STATUS
        # -------------------------------------------------

        document.status = status

        # -------------------------------------------------
        # APPROVED
        # -------------------------------------------------

        if status == "approved":

            document.approved_by = approved_by

            document.approved_at = datetime.utcnow()

            document.rejection_reason = None

        # -------------------------------------------------
        # REJECTED
        # -------------------------------------------------

        elif status == "rejected":

            document.rejection_reason = (
                rejection_reason
            )

            document.approved_by = approved_by

            document.approved_at = datetime.utcnow()

        db.session.commit()

        return jsonify({

            "success": True,

            "message":
                "Document reviewed successfully",

            "docu_id":
                document.docu_id,

            "status":
                document.status

        }), 200

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500