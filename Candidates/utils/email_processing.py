import os
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from Candidates.utils.resume_parser import parse_resume
from Candidates.models.parsed_candidate_temp import ParsedCandidateTemp
from Candidates.models.resume import Resume
from common.models.document_asset import DocumentAsset
from Candidates.utils.file_hash import generate_file_hash
from common.utils.storage_service import upload_file

from extensions import db


def process_email_resumes(user_email, org_id, actor_email, resume_files):

    results = []

    for file_path in resume_files:

        original_name = os.path.basename(file_path)

        try:
            # ---------------- VALIDATION ----------------
            if not os.path.exists(file_path):
                results.append({
                    "file": original_name,
                    "status": "failed",
                    "message": "File not found"
                })
                continue

            file_size = os.path.getsize(file_path)

            if file_size > 5 * 1024 * 1024:
                results.append({
                    "file": original_name,
                    "status": "failed",
                    "message": "File too large"
                })
                continue

            ext = os.path.splitext(original_name)[1].lower()
            if ext not in {".pdf", ".docx", ".txt"}:
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

            # ---------------- PARSE ----------------
            parsed_data = parse_resume(file_path)

            if not parsed_data or not isinstance(parsed_data, dict):
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

            # ---------------- SOURCE NOTE ----------------
            timestamp = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")

            source_note = f"Imported from Gmail (OAuth): {user_email} at {timestamp}"

            parsed_data["notes"] = (
                f"{parsed_data.get('notes')} | {source_note}"
                if parsed_data.get("notes")
                else source_note
            )

            # ---------------- UPLOAD ----------------
            resume_key = upload_file(file_path, folder="resumes/email")

            asset = DocumentAsset(
                docu_id=str(uuid.uuid4()),
                file_key=resume_key,
                original_filename=original_name,
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
                    source="email_integration_oauth",
                    resume_file=resume_key,
                    resume_hash=resume_hash,
                    parsed_json=parsed_data,
                    status="draft"
                )
            )

            db.session.commit()

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

    return results