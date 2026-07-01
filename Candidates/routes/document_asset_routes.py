#Candidates/routes/document_asset_routes.py
import os
import uuid

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from extensions import db

from common.utils.storage_service import (
    upload_file,
    upload_file_object
)

from common.models.document_asset import (
    DocumentAsset
)

from recruiter.models.document_request_model import (
    DocumentRequest
)

document_asset_bp = Blueprint(
    "document_asset_bp",
    __name__
)



# UPLOAD_FOLDER = "uploads/temp"

# os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@document_asset_bp.route(
    "/upload",
    methods=["POST"]
)
def upload_candidate_file():

    try:

        file = request.files.get("file")

        upload_token = request.form.get(
            "upload_token"
        )

        document_type = request.form.get(
            "document_name",
            "other"
        )

        if not upload_token:

            return jsonify({
                "success": False,
                "message": "upload_token required"
            }), 400


        document_request = DocumentRequest.query.filter_by(
            upload_token=upload_token,
            is_active=True
        ).first()

        if not document_request:

            return jsonify({
                "success": False,
                "message": "Invalid upload token"
            }), 404


        if document_request.status == "withdrawn":

            return jsonify({
                "success": False,
                "message": "Request withdrawn"
            }), 400
            
        # -------------------------------------------------
        # VALIDATE REQUESTED DOCUMENT
        # -------------------------------------------------

        requested_document_names = {

            doc["name"].lower().strip()

            for doc in document_request.documents
        }

        if document_type.lower().strip() not in requested_document_names:

            return jsonify({
                "success": False,
                "message": "Document not requested"
            }), 400


        cand_id = document_request.candidate_id

        org_id = document_request.org_id
        
        document_count = int(
            request.form.get("document_count", 1)
        )
        
        
        existing_document = DocumentAsset.query.filter_by(

                cand_id=cand_id,

                org_id=org_id,

                document_type=document_type,

                document_count=document_count

            ).first()

        if not file:
             

            return jsonify({
                "success": False,
                "message": "File required"
            }), 400

        filename = secure_filename(file.filename)

        folder = f"candidate_documents/{document_type}"

        # -------------------------------------------------
        # REPLACE EXISTING SLOT
        # -------------------------------------------------

        if existing_document:

            file_key = upload_file_object(
                file,
                filename,
                folder
            )

            existing_document.file_key = file_key

            existing_document.original_filename = filename

            existing_document.mime_type = file.mimetype

            existing_document.file_size = (
                file.content_length or 0
            )

            db.session.commit()

            return jsonify({

                "success": True,

                "message":
                    "Document replaced successfully",

                "docu_id":
                    existing_document.docu_id,

                "document_count":
                    document_count,

                "replaced": True

            }), 200


        # -------------------------------------------------
        # CREATE NEW SLOT
        # -------------------------------------------------

        file_key = upload_file_object(
            file,
            filename,
            folder
        )

        document_asset = DocumentAsset(

            docu_id=str(uuid.uuid4()),

            cand_id=cand_id,

            org_id=org_id,

            document_type=document_type,

            document_count=document_count,

            file_key=file_key,

            original_filename=filename,

            mime_type=file.mimetype,

            file_size=file.content_length or 0,

            uploaded_by="candidate",

            is_linked=False
        )

        db.session.add(document_asset)

        db.session.commit()

        # if os.path.exists(temp_path):

        #     os.remove(temp_path)

        return jsonify({

            "success": True,

            "docu_id": document_asset.docu_id,

            "file_key": file_key

        }), 201

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500