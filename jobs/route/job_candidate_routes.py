
from flask import Blueprint, request, jsonify, g
from auth.utils.jwt_required import jwt_required
from extensions import db
from Candidates.models.candidate import Candidate
from Candidates.models.job_candidate_journey import JobCandidateJourney
from jobs.models.job_candidate_model import JobCandidate
from jobs.models.job_model import Job
from Logs.log_helper import create_log
import json

job_candidate_bp = Blueprint("job_candidate_bp", __name__)


# ---------------- Helper: Get current user object ----------------
def get_current_user():
    if not hasattr(g, "current_user"):
        return None
    return g.current_user


@job_candidate_bp.route("/<string:job_id>/add_candidate", methods=["POST"])
@jwt_required
def add_candidate_to_job(job_id):

    # ---------- Parse JSON ----------
    data = request.get_json(silent=True)

    if isinstance(data, str):
        try:
            data = json.loads(data)
        except:
            return jsonify({"error": "Invalid JSON format"}), 400

    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400

    single_cand = data.get("cand_id")
    multiple_cands = data.get("cand_ids")

    candidates_to_add = []

    if single_cand:
        candidates_to_add.append(single_cand)
    elif multiple_cands and isinstance(multiple_cands, list):
        candidates_to_add.extend(multiple_cands)
    else:
        return jsonify({
            "error": "Provide cand_id or cand_ids (list)"
        }), 400

    if len(candidates_to_add) == 0:
        return jsonify({"error": "Candidate list is empty"}), 400

    # ---------- Current User ----------
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    added_by = current_user["user_id"]

    # ---------- Validate Job ----------
    job = Job.query.filter_by(job_id=job_id).first()
    if not job:
        return jsonify({"error": "Job not found"}), 404

    # ---------- Result Trackers ----------
    added_candidates = []
    failed_candidates = []
    already_exists = []

    # ---------- Process Candidates ----------
    for cand_id in candidates_to_add:

        candidate = Candidate.query.filter_by(cand_id=cand_id).first()
        if not candidate:
            failed_candidates.append({
                "cand_id": cand_id,
                "reason": "Candidate not found"
            })
            continue

        # -------- Check existing mapping --------
        mapping = JobCandidate.query.filter_by(
            job_id=job_id,
            cand_id=cand_id
        ).first()

        # -------- Check existing journey --------
        existing_journey = JobCandidateJourney.query.filter_by(
            job_id=job_id,
            cand_id=cand_id
        ).first()

        # -------- If both exist → skip --------
        if mapping and existing_journey:
            already_exists.append(cand_id)
            continue

        try:
            # -------- Create Mapping (if not exists) --------
            if not mapping:
                mapping = JobCandidate(
                    job_id=job_id,
                    cand_id=cand_id,
                    status="assigned"   # or "added"
                )
                db.session.add(mapping)

            # -------- Create Journey (if not exists) --------
            if not existing_journey:
                journey = JobCandidateJourney(
                    job_id=job_id,
                    cand_id=cand_id,
                    added_by=added_by,
                    status="shared",  # ✅ IMPORTANT
                    interview_round=0,
                    interview_sub_round=0,
                    visible_to_recruiter=True,
                    visible_to_candidate=False
                )
                db.session.add(journey)

            added_candidates.append(cand_id)

        except Exception as e:
            failed_candidates.append({
                "cand_id": cand_id,
                "reason": str(e)
            })

    # ---------- Commit ----------
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": "Database error",
            "details": str(e)
        }), 500

    # ---------- Logging ----------
    create_log(
        current_user["user_id"],
        action="ADD_MULTIPLE_CANDIDATES_TO_JOB",
        entity_type="JobCandidate",
        entity_id=job_id,
        data={
            "job_id": job_id,
            "added": added_candidates,
            "failed": failed_candidates,
            "already_exists": already_exists
        }
    )

    # ---------- Response ----------
    return jsonify({
        "message": "Candidate processing completed",
        "job_id": job_id,
        "summary": {
            "total_requested": len(candidates_to_add),
            "added": len(added_candidates),
            "failed": len(failed_candidates),
            "already_exists": len(already_exists)
        },
        "details": {
            "added_candidates": added_candidates,
            "failed_candidates": failed_candidates,
            "already_existing": already_exists
        }
    }), 200