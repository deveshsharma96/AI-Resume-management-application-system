# Candidates/routes/job_candidate_journey_routes.py

from flask import Blueprint, request, jsonify, g
from extensions import db

from Candidates.models.job_candidate_journey import JobCandidateJourney
from Candidates.state_machine.JobCandidateJourneyStateMachine import JobCandidateJourneyStateMachine
from Candidates.models.interview import Interview
from Candidates.models.candidate import Candidate
from Candidates.utils.visibility_query import get_visible_candidates_query
from Candidates.models.journey_note import JourneyNote
from jobs.models.job_model import Job
from datetime import datetime
import pytz
from flask import g
from auth.utils.jwt_required import jwt_required
from Logs.log_helper import create_log
import json


job_candidate_journey_bp = Blueprint(
    "job_candidate_journey_bp",
    __name__
)


# ---------------------------------------------------
# Helper: get current user from JWT
# ---------------------------------------------------
def get_current_user():
    if not hasattr(g, "current_user"):
        return None
    return g.current_user


# ---------------------------------------------------
# Helper: convert UTC → IST safely
# ---------------------------------------------------
def to_ist(dt):
    if not dt:
        return None

    ist = pytz.timezone("Asia/Kolkata")

    # If datetime is naive (no timezone info)
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)

    return dt.astimezone(ist).strftime("%a, %d %b %Y %H:%M:%S %Z")


# ===================================================
# UPDATE JOURNEY STATUS
# ===================================================
@job_candidate_journey_bp.route("/<string:journey_id>/status", methods=["PUT"])
@jwt_required
def update_journey_status(journey_id):

    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}

    if isinstance(data, str):
        data = json.loads(data)

    new_state = data.get("status")
    reschedule = data.get("reschedule", False)

    if not new_state:
        return jsonify({"error": "Status is required"}), 400

    journey = JobCandidateJourney.query.filter_by(
        journey_id=journey_id
    ).first()

    if not journey:
        return jsonify({"error": "Journey not found"}), 404


    # ---------------------------------------------------
    # Prevent direct final selection/rejection
    # ---------------------------------------------------
    if (
        journey.status == "interview_scheduled"
        and new_state in ["selected", "rejected"]
    ):
        return jsonify({
            "error": (
                "Use interview result API to finalize "
                "candidate after interview scheduling"
            )
        }), 400

    # ---------------------------------------------------
    # 🔐 Candidate visibility check
    # ---------------------------------------------------
    org_id = current_user["org_id"]

    visible_query = get_visible_candidates_query(
        current_user,
        org_id
    )

    candidate = visible_query.filter(
        Candidate.cand_id == journey.cand_id
    ).first()

    if not candidate:
        return jsonify({"error": "No permission"}), 403

    # ---------------------------------------------------
    # State machine transition (FIXED)
    # ---------------------------------------------------
    response = JobCandidateJourneyStateMachine.transition(
        journey=journey,
        new_state=new_state,
        reschedule=reschedule
    )

    if not response.get("success"):
        return jsonify({
            "error": response.get("error")
        }), 400
    
    db.session.add(JourneyNote(
        journey_id=journey.journey_id,
        note=f"Status changed to {new_state}",
        stage="status_change",
        created_by=current_user["user_id"]
    ))

    db.session.commit()

    # ---------------------------------------------------
    # Audit log
    # ---------------------------------------------------
    create_log(
        current_user["user_id"],
        action="update_journey_status",
        entity_type="JobCandidateJourney",
        entity_id=journey_id,
        data={
            "new_status": journey.status,
            "candidate_id": journey.cand_id,
            "job_id": journey.job_id
        }
    )

    return jsonify({
        "message": "Journey status updated",
        "data": {
            "status": journey.status,
            "interview_round": getattr(journey, "interview_round", 0),
            "interview_sub_round": getattr(journey, "interview_sub_round", 0),
            "result": getattr(journey, "interview_result", None),
            "job_id": journey.job_id,
            "candidate_id": journey.cand_id
        }
    }), 200

# ===================================================
# GET JOURNEY DETAILS (WITH NOTES)
# ===================================================
@job_candidate_journey_bp.route("/<string:journey_id>", methods=["GET"])
@jwt_required
def get_journey(journey_id):

    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    journey = JobCandidateJourney.query.filter_by(
        journey_id=journey_id
    ).first()

    if not journey:
        return jsonify({"error": "Journey not found"}), 404

    # ---------------------------------------------------
    # 🔐 Candidate visibility check
    # ---------------------------------------------------
    org_id = current_user["org_id"]

    candidate = Candidate.query.filter_by(
        cand_id=journey.cand_id,
        org_id=current_user["org_id"]
    ).first()

    if not candidate:
        return jsonify({"error": "No permission"}), 403

    # ---------------------------------------------------
    # Job details
    # ---------------------------------------------------
    job = Job.query.filter_by(
        job_id=journey.job_id
    ).first()

    job_data = None

    if job:
        job_data = {
            "job_id": job.job_id,
            "title": job.title,
            "description": job.description,
            "job_status": job.Job_status
        }

    created_at_ist = to_ist(journey.created_at)
    updated_at_ist = to_ist(journey.updated_at)

    # ---------------------------------------------------
    # Interviews
    # ---------------------------------------------------
    interviews = Interview.query.filter_by(
        journey_id=journey.journey_id
    ).all()

    interview_data = []

    for iv in interviews:
        interview_data.append({
            "interview_id": iv.interview_id,
            "interview_round": iv.interview_round,
            "interview_sub_round": iv.interview_sub_round,
            "interview_result": iv.result,
            "scheduled_at_utc": iv.scheduled_at,
            "scheduled_at_ist": to_ist(iv.scheduled_at),
            "duration_minutes": iv.duration_minutes,
            "interviewer": iv.interviewer,
            "location": iv.location,
            "platform": iv.platform,
            "meeting_link": iv.meeting_link,
            "status": iv.status
        })

    # ---------------------------------------------------
    # 🆕 NOTES (TIMELINE)
    # ---------------------------------------------------
    notes = JourneyNote.query.filter_by(
        journey_id=journey.journey_id
    ).order_by(JourneyNote.created_at.desc()).all()

    notes_data = []

    for n in notes:
        notes_data.append({
            "note_id": n.note_id,
            "note": n.note,
            "stage": n.stage,
            "interview_id": n.interview_id,
            "created_by": n.created_by,
            "visible_to_candidate": n.visible_to_candidate,
            "created_at": to_ist(n.created_at)
        })

    # ---------------------------------------------------
    # FINAL RESPONSE
    # ---------------------------------------------------
    return jsonify({
        "status": "success",
        "data": {
            "journey_id": journey.journey_id,
            "cand_id": journey.cand_id,
            "job_id": journey.job_id,
            "status": journey.status,
            "interview_round": journey.interview_round,
            "interview_sub_round": journey.interview_sub_round,
            "interview_result": journey.interview_result,
            "added_by": journey.added_by,
            "visible_to_recruiter": journey.visible_to_recruiter,
            "visible_to_candidate": journey.visible_to_candidate,
            "created_at": created_at_ist,
            "updated_at": updated_at_ist,
            "job_details": job_data,
            "interviews": interview_data,
            "notes": notes_data   # ✅ ADDED
        }
    }), 200



# ===================================================
# 🆕 SHARE CANDIDATE TO JOB (NEW API)
# ===================================================
@job_candidate_journey_bp.route("/jobs/<string:job_id>/share-candidate", methods=["POST"])
@jwt_required
def share_candidate_to_job(job_id):

    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
    cand_id = data.get("cand_id")

    if not cand_id:
        return jsonify({"error": "cand_id is required"}), 400

    # ---------------------------------------------------
    # 1️⃣ Check Candidate
    # ---------------------------------------------------
    candidate = Candidate.query.filter_by(cand_id=cand_id).first()
    if not candidate:
        return jsonify({"error": "Candidate not found"}), 404

    # ---------------------------------------------------
    # 2️⃣ Check Job
    # ---------------------------------------------------
    job = Job.query.filter_by(job_id=job_id).first()
    if not job:
        return jsonify({"error": "Job not found"}), 404

    # ---------------------------------------------------
    # 3️⃣ Prevent duplicate sharing
    # ---------------------------------------------------
    existing = JobCandidateJourney.query.filter_by(
        job_id=job_id,
        cand_id=cand_id
    ).first()

    if existing:
        return jsonify({
            "message": "Candidate already shared to this job",
            "journey_id": existing.journey_id
        }), 200

    # ---------------------------------------------------
    # 4️⃣ Create Journey
    # ---------------------------------------------------
    journey = JobCandidateJourney(
        job_id=job_id,
        cand_id=cand_id,
        status="shared",
        interview_round=0,
        interview_sub_round=0,
        added_by=current_user["user_id"],
        visible_to_recruiter=True,
        visible_to_candidate=False
    )
    db.session.add(journey)
    db.session.flush() 

    db.session.add(JourneyNote(
        journey_id=journey.journey_id,
        note="Candidate shared to job",
        stage="shared",
        created_by=current_user["user_id"]
    ))

    
    db.session.commit()

    # ---------------------------------------------------
    # Audit log
    # ---------------------------------------------------
    create_log(
        current_user["user_id"],
        action="share_candidate_to_job",
        entity_type="JobCandidateJourney",
        entity_id=journey.journey_id,
        data={
            "candidate_id": cand_id,
            "job_id": job_id
        }
    )

    return jsonify({
        "message": "Candidate shared to job successfully",
        "data": {
            "journey_id": journey.journey_id,
            "status": journey.status,
            "job_id": job_id,
            "cand_id": cand_id
        }
    }), 201




@job_candidate_journey_bp.route("/jobs/<string:job_id>/pipeline", methods=["GET"])
@jwt_required
def get_pipeline(job_id):

    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    # ---------------------------------------------------
    # Check job exists
    # ---------------------------------------------------
    job = Job.query.filter_by(job_id=job_id).first()
    if not job:
        return jsonify({"error": "Job not found"}), 404

    # ---------------------------------------------------
    # Fetch all journeys for this job
    # ---------------------------------------------------
    journeys = JobCandidateJourney.query.filter_by(job_id=job_id).all()

    # ---------------------------------------------------
    # Group by status
    # ---------------------------------------------------
    pipeline = {
        "shared": [],
        "shortlisted": [],
        "interview_scheduled": [],
        "cleared": [],
        "selected": [],
        "rejected": [],
        "need_more_info": []
    }

    for j in journeys:

        candidate = Candidate.query.filter_by(cand_id=j.cand_id).first()

        candidate_data = {
            "journey_id": j.journey_id,
            "cand_id": j.cand_id,
            "name": candidate.name if candidate else None,
            "email": candidate.email if candidate else None,
            "status": j.status,
            "interview_round": j.interview_round,
            "interview_sub_round": j.interview_sub_round,
            "interview_result": j.interview_result,
            "created_at": to_ist(j.created_at)
        }

        # fallback safety
        if j.status not in pipeline:
            pipeline.setdefault(j.status, [])

        pipeline[j.status].append(candidate_data)

    return jsonify({
        "status": "success",
        "job_id": job_id,
        "pipeline": pipeline
    }), 200



@job_candidate_journey_bp.route("/candidate/<string:cand_id>", methods=["GET"])
@jwt_required
def get_candidate_journeys(cand_id):

    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    # ---------------------------------------------------
    # Validate candidate belongs to same org
    # ---------------------------------------------------
    candidate = Candidate.query.filter_by(
        cand_id=cand_id,
        org_id=current_user["org_id"]
    ).first()

    if not candidate:
        return jsonify({"error": "No permission or candidate not found"}), 403

    # ---------------------------------------------------
    # Fetch all journeys
    # ---------------------------------------------------
    journeys = JobCandidateJourney.query.filter_by(
        cand_id=cand_id
    ).order_by(JobCandidateJourney.created_at.desc()).all()

    result = []

    for j in journeys:

        job = Job.query.filter_by(job_id=j.job_id).first()

        result.append({
            "journey_id": j.journey_id,
            "job_id": j.job_id,
            "job_title": job.title if job else None,
            "status": j.status,
            "interview_round": j.interview_round,
            "interview_sub_round": j.interview_sub_round,
            "interview_result": j.interview_result,
            "created_at": j.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    return jsonify({
        "message": "Candidate journeys fetched successfully",
        "cand_id": cand_id,
        "total_journeys": len(result),
        "data": result
    }), 200