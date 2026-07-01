# # Candidates/routes/candidate_document_routes.py

# import os

# from common.utils.storage_service import upload_file
# from flask import Blueprint, request, jsonify
# from werkzeug.utils import secure_filename

# from recruiter.models.document_request_model import (
#     DocumentRequest
# )

# # from recruiter.models.candidate_uploaded_document_model import (
# #     CandidateUploadedDocument
# # )

# from extensions import db

# import uuid

# from common.models.document_asset import (
#     DocumentAsset
# )

# from Candidates.models.candidate import (
#     Candidate
# )


# from datetime import datetime

# from Candidates.models.resume import Resume


# candidate_document_bp = Blueprint(
#     "candidate_document_bp",
#     __name__
# )

# UPLOAD_FOLDER = "uploads/candidate_documents"

# os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# @candidate_document_bp.route(
#     "/pending/<string:candidate_id>",
#     methods=["GET"]
# )
# def pending_documents(candidate_id):

#     try:

#         requests = DocumentRequest.query.filter_by(
#             candidate_id=candidate_id
#         ).all()

#         response = []

#         for req in requests:

#             response.append({
#                 "request_id": req.id,
#                 "documents": req.documents,
#                 "status": req.status
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


# @candidate_document_bp.route("/upload", methods=["POST"])
# def upload_document():

#     try:

#         request_id = request.form.get("request_id")

#         document_name = request.form.get("document_name")
        
#         replace_document_id = request.form.get(
#             "replace_document_id"
#         )
        
#         note = request.form.get("note")
    
#         mandatory = request.form.get(
#             "mandatory",
#             "false"
#         ).lower() == "true"

#         file = request.files.get("file")

#         if not file:

#             return jsonify({
#                 "success": False,
#                 "message": "File is required"
#             }), 400

#         filename = secure_filename(file.filename)

#         temp_path = os.path.join(
#             UPLOAD_FOLDER,
#             filename
#         )

#         file.save(temp_path)

#         # Upload to PureStore S3
#         # ------------------------------------------
#         # DOCUMENT TYPE MAPPING
#         # ------------------------------------------

#         DOCUMENT_CONFIG = {

#             "resume": {
#                 "folder": "resumes/bulk",
#                 "type": "resume"
#             },

#             "cover letter": {
#                 "folder": "cover_letters",
#                 "type": "cover_letter"
#             },

#             "aadhar": {
#                 "folder": "candidate_documents/aadhar",
#                 "type": "aadhar"
#             },

#             "pan": {
#                 "folder": "candidate_documents/pan",
#                 "type": "pan"
#             },

#             "passport": {
#                 "folder": "candidate_documents/passport",
#                 "type": "passport"
#             },

#             "driving license": {
#                 "folder": "candidate_documents/driving_license",
#                 "type": "driving_license"
#             },

#             "marksheet": {
#                 "folder": "candidate_documents/marksheet",
#                 "type": "marksheet"
#             },

#             "certificate": {
#                 "folder": "candidate_documents/certificate",
#                 "type": "certificate"
#             },

#             "salary slip": {
#                 "folder": "candidate_documents/salary_slip",
#                 "type": "salary_slip"
#             },

#             "bank statement": {
#                 "folder": "candidate_documents/bank_statement",
#                 "type": "bank_statement"
#             },

#             "experience letter": {
#                 "folder": "candidate_documents/experience_letter",
#                 "type": "experience_letter"
#             },

#             "offer letter": {
#                 "folder": "candidate_documents/offer_letter",
#                 "type": "offer_letter"
#             }
#         }


#         config = DOCUMENT_CONFIG.get(
#             document_name.lower(),
#             {
#                 "folder": "candidate_documents/other",
#                 "type": "other"
#             }
#         )

#         folder = config["folder"]

#         document_type = config["type"]
        
#         SINGLE_FILE_DOCUMENTS = [

#             "aadhar",
#             "pan",
#             "passport",
#             "driving_license"
#         ]
        
#         if document_type in SINGLE_FILE_DOCUMENTS:

#             existing_document = CandidateUploadedDocument.query.filter_by(
#                 request_id=request_id,
#                 document_type=document_type,
#                 is_latest=True
#             ).first()

#             if existing_document and not replace_document_id:

#                 return jsonify({
#                     "success": False,
#                     "message": f"{document_name} already uploaded. Replace existing file."
#                 }), 400

#         file_key = upload_file(temp_path, folder)
        
        
        
            
#         if replace_document_id:

#             old_document = CandidateUploadedDocument.query.get(
#                 replace_document_id
#             )

#             if old_document:

#                 old_document.is_latest = False
                
#                 db.session.flush()

#         uploaded_document = CandidateUploadedDocument(

#             request_id=request_id,

#             document_name=document_name,

#             mandatory=mandatory,
            
#             note=note,

#             file_key=file_key,

#             original_filename=filename,

#             mime_type=file.mimetype,

#             file_size=os.path.getsize(temp_path),

#             document_type=document_type,

#             is_latest=True,

#             replaced_document_id=replace_document_id,

#             status="uploaded"
#         )

#         db.session.add(uploaded_document)
        
#         db.session.flush()
        
#         # ------------------------------------------
#         # Update Resume / Cover Letter
#         # ------------------------------------------

#         all_uploaded = False
        
#         document_request = DocumentRequest.query.get(
#             request_id
#         )

#         candidate = Candidate.query.filter_by(
#             cand_id=document_request.candidate_id
#         ).first()
        
#         if not candidate:

#             return jsonify({
#                 "success": False,
#                 "message": "Candidate not found"
#             }), 404

#         normalized_document_type = document_type

#         if normalized_document_type:

#             document_asset = DocumentAsset(

#                 docu_id=str(uuid.uuid4()),

#                 cand_id=candidate.cand_id,

#                 org_id=candidate.org_id,

#                 document_type=normalized_document_type,

#                 file_key=file_key,

#                 original_filename=filename,

#                 mime_type=file.mimetype,

#                 file_size=os.path.getsize(temp_path),

#                 uploaded_by="candidate",

#                 is_linked=True
#             )

#             db.session.add(document_asset)

#             db.session.flush()
            
#             # ------------------------------------------
#             # ONLY RESUME / COVER LETTER UPDATE RESUME TABLE
#             # ------------------------------------------

#             if normalized_document_type in ["resume", "cover_letter"]:

#             # ------------------------------------------
#             # CREATE / UPDATE RESUME TABLE
#             # ------------------------------------------

#                 resume = None

#                 # Existing primary resume
#                 if candidate.primary_resume_id:

#                     resume = Resume.query.filter_by(
#                         id=candidate.primary_resume_id,
#                         cand_id=candidate.cand_id
#                     ).first()

#                 # Create new resume row if missing
#                 if not resume:

#                     resume = Resume(
#                         cand_id=candidate.cand_id,
#                         org_id=candidate.org_id,
#                         uploaded_at=datetime.utcnow(),
#                         source="upload_resume"
#                     )

#                     db.session.add(resume)
#                     db.session.flush()

#                     candidate.primary_resume_id = resume.id


#                 # Resume upload
#                 if normalized_document_type == "resume":

#                     resume.resume_file = file_key
#                     resume.original_filename = filename
#                     resume.mime_type = file.mimetype
#                     resume.file_size = os.path.getsize(temp_path)

#                 # Cover letter upload
#                 elif normalized_document_type == "cover_letter":

#                     resume.cover_letter_file = file_key
#                     resume.cover_letter_filename = filename
#                     resume.cover_letter_mime_type = file.mimetype
#                     resume.cover_letter_size = os.path.getsize(temp_path)
                            

#             # ------------------------------------------
#             # Check if all mandatory docs uploaded
#             # ------------------------------------------

#             document_request = DocumentRequest.query.get(
#                 request_id
#             )

#             required_documents = document_request.documents

#             uploaded_documents = CandidateUploadedDocument.query.filter_by(
#                 request_id=request_id,
#                 is_latest=True
#             ).all()

#             all_uploaded = True

#             for required_doc in required_documents:

#                 if required_doc.get("mandatory"):

#                     uploaded_count = CandidateUploadedDocument.query.filter_by(
#                         request_id=request_id,
#                         document_name=required_doc.get("name"),
#                         is_latest=True
#                     ).count()

#                     if uploaded_count == 0:

#                         all_uploaded = False
#                         break
#         # ------------------------------------------
#         # Update request status
#         # ------------------------------------------

#         if all_uploaded:

#             document_request.status = "completed"

#         else:

#             document_request.status = "pending"

#         if os.path.exists(temp_path):
#             os.remove(temp_path)
        
#         db.session.commit()

#         return jsonify({
#             "success": True,
#             "message": "Document uploaded successfully",
#             "file_key": file_key
#         }), 201

#     except Exception as e:

#         return jsonify({
#             "success": False,
#             "message": str(e)
#         }), 500
        
  
        
# @candidate_document_bp.route(
#     "/request/<string:token>",
#     methods=["GET"]
# )
# def get_request_by_token(token):

#     try:

#         document_request = DocumentRequest.query.filter_by(
#             upload_token=token
#         ).first()

#         if not document_request:

#             return jsonify({
#                 "success": False,
#                 "message": "Invalid upload link"
#             }), 404

#         uploaded_documents = CandidateUploadedDocument.query.filter_by(
#             request_id=document_request.id
#         ).all()

        


#         documents_with_status = []

#         for doc in document_request.documents:

#             doc_name = doc.get("name", "")

#             uploaded_docs = CandidateUploadedDocument.query.filter_by(
#                 request_id=document_request.id,
#                 document_name=doc_name,
#                 is_latest=True
#             ).all()

#             files = []

#             for uploaded_doc in uploaded_docs:

#                 files.append({

#                     "document_id": uploaded_doc.id,

#                     "file_key": uploaded_doc.file_key,

#                     "original_filename": uploaded_doc.original_filename,

#                     "mime_type": uploaded_doc.mime_type,

#                     "file_size": uploaded_doc.file_size,

#                     "uploaded_at": uploaded_doc.uploaded_at,

#                     "status": uploaded_doc.status,

#                     "note": uploaded_doc.note
#                 })

#             documents_with_status.append({

#                 "name": doc_name,

#                 "mandatory": doc.get(
#                     "mandatory",
#                     False
#                 ),

#                 "allow_multiple": doc.get(
#                     "allow_multiple",
#                     False
#                 ),

#                 "note": doc.get("note"),

#                 "status": (
#                     "submitted"
#                     if len(files) > 0
#                     else "pending"
#                 ),

#                 "total_files_uploaded": len(files),

#                 "files": files
#             })

            
#             # ------------------------------------------
#             # DOCUMENT WITH MULTIPLE SLOTS
#             # ------------------------------------------

            

#         return jsonify({

#             "success": True,

#             "request_id": document_request.id,

#             "candidate_id": document_request.candidate_id,

#             "documents": documents_with_status,

#             "overall_status": document_request.status

#         }), 200

#     except Exception as e:

#         return jsonify({
#             "success": False,
#             "message": str(e)
#         }), 500



#Candidate_document_routes.py

from flask import Blueprint, request, jsonify

from extensions import db

from recruiter.models.document_request_model import (
    DocumentRequest
)

from recruiter.models.candidate_request_document_model import (
    CandidateRequestDocument
)

from common.models.document_asset import (
    DocumentAsset
)


candidate_document_bp = Blueprint(
    "candidate_document_bp",
    __name__
)


@candidate_document_bp.route(
    "/request/<string:token>",
    methods=["GET"]
)

def get_request_by_token(token):

    try:

        document_request = DocumentRequest.query.filter_by(
            upload_token=token
        ).first()

        if not document_request:

            return jsonify({
                "success": False,
                "message": "Invalid request"
            }), 404

        if document_request.status == "withdrawn":

            return jsonify({
                "success": False,
                "message": "Document request withdrawn"
            }), 400

        if not document_request.is_active:

            return jsonify({
                "success": False,
                "message": "Request expired"
            }), 400

            

        response_documents = []

        for requested_doc in document_request.documents:

            latest_submission = CandidateRequestDocument.query.filter_by(

                request_id=document_request.id,

                document_name=requested_doc["name"],

                is_latest=True

            ).first()

            document_response = {

                "name":
                    requested_doc.get("name"),

                "mandatory":
                    requested_doc.get("mandatory"),

                "allow_multiple":
                    requested_doc.get("allow_multiple"),

                "note":
                    requested_doc.get("note"),

                "status":
                    "pending",

                "submitted":
                    False,

                "docu_id":
                    None,

                "file_name":
                    None,

                "rejection_reason":
                    None
            }

            if latest_submission:

                asset = DocumentAsset.query.filter_by(
                    docu_id=latest_submission.docu_id
                ).first()

                document_response["status"] = (
                    latest_submission.status
                )

                document_response["submitted"] = True

                document_response["docu_id"] = (
                    latest_submission.docu_id
                )

                document_response["rejection_reason"] = (
                    latest_submission.rejection_reason
                )

                if asset:

                    document_response["file_name"] = (
                        asset.original_filename
                    )

            response_documents.append(
                document_response
            )

        return jsonify({

            "success": True,

            "request_id":
                document_request.id,

            "candidate_id":
                document_request.candidate_id,

            "request_status":
                document_request.status,

            "documents":
                response_documents

        }), 200

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500



@candidate_document_bp.route(
    "/submit",
    methods=["POST"]
)
def submit_documents():

    try:

        data = request.json

        request_id = data.get("request_id")

        cand_id = data.get("candidate_id")

        org_id = data.get("org_id")

        documents = data.get("documents", [])

        document_request = DocumentRequest.query.get(
            request_id
        )

        if not document_request:

            return jsonify({
                "success": False,
                "message": "Invalid request"
            }), 404
            
        cand_id = document_request.candidate_id

        org_id = document_request.org_id

        if not document_request.is_active:

            return jsonify({
                "success": False,
                "message": "Request expired"
            }), 400

        for document in documents:

            document_name = document.get("name")

            docu_ids = document.get(
                "docu_ids",
                []
            )
            
            approved_document = CandidateRequestDocument.query.filter_by(

                request_id=request_id,

                cand_id=cand_id,

                org_id=org_id,

                document_name=document_name,

                status="approved",

                is_latest=True

            ).first()


            if approved_document:

                return jsonify({

                    "success": False,

                    "message":
                        f"{document_name} already approved. "
                        f"Resubmission not allowed."

                }), 400

            for docu_id in docu_ids:

                # -----------------------------
                # VALIDATE DOCU_ID
                # -----------------------------

                asset = DocumentAsset.query.filter_by(
                    docu_id=docu_id
                ).first()

                if not asset:
                    continue

                # -----------------------------
                # MARK OLD AS NOT LATEST
                # -----------------------------

                CandidateRequestDocument.query.filter_by(
                    request_id=request_id,
                    document_name=document_name,
                    is_latest=True
                ).update({
                    "is_latest": False
                })

                # -----------------------------
                # CREATE NEW REQUEST DOCUMENT
                # -----------------------------

                request_document = CandidateRequestDocument(

                    request_id=request_id,

                    cand_id=cand_id,

                    org_id=org_id,

                    document_name=document_name,

                    docu_id=docu_id,

                    status="submitted",

                    is_latest=True
                )

                db.session.add(request_document)

                # -----------------------------
                # MARK FILE LINKED
                # -----------------------------

                asset.is_linked = True

        # ---------------------------------
        # UPDATE REQUEST STATUS
        # ---------------------------------

        document_request.status = "uploaded"
        
        

        db.session.commit()

        return jsonify({

            "success": True,

            "message":
                "Documents submitted successfully"

        }), 200
        
        

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
        
    

