# Candidates/routes/journey_interview_routes.py
"""
from flask import Blueprint, request, jsonify
from extensions import db
from datetime import datetime
from Candidates.models.job_candidate_journey import JobCandidateJourney
from Candidates.models.interview import Interview
from Candidates.models.journey_note import JourneyNote
from Candidates.state_machine.JobCandidateJourneyStateMachine import JobCandidateJourneyStateMachine
from Candidates.utils.meeting_link_generator import generate_meeting_link
from Organization.utils.email_utils import _send_email
from Candidates.models.candidate import Candidate
from flask import g
from auth.utils.jwt_required import jwt_required
from Logs.log_helper import create_log

journey_bp = Blueprint("journey_bp", __name__)


# ---------------------------------------------------
# Helper: convert UTC → IST
# ---------------------------------------------------
def to_ist(dt):
    if not dt:
        return None
    from datetime import timezone, timedelta
    ist = dt.replace(tzinfo=timezone.utc) + timedelta(hours=5, minutes=30)
    return ist.strftime("%Y-%m-%d %H:%M:%S")


def get_current_user():
    if not hasattr(g, "current_user"):
        return None
    return g.current_user

# ===================================================
# CREATE / SCHEDULE INTERVIEW
# ===================================================
@journey_bp.route("/<int:journey_id>/interviews", methods=["POST"])
@jwt_required
def create_interview(journey_id):

    data = request.get_json() or {}

    journey = JobCandidateJourney.query.filter_by(journey_id=journey_id).first()
    if not journey:
        return jsonify({"error": "Journey not found"}), 404

    scheduled_at = data.get("scheduled_at")
    duration_minutes = data.get("duration_minutes")
    interviewer = data.get("interviewer")
    location = data.get("location")
    platform = data.get("platform")
    created_by = data.get("created_by", "system")
    reschedule = data.get("reschedule", False)

    # ---------------------------------------------------
    # 1️⃣ Update journey state
    # ---------------------------------------------------
    sm_resp = JobCandidateJourneyStateMachine.transition(
        journey=journey,
        new_state="interview_scheduled",
        reschedule=reschedule
    )

    if not sm_resp.get("success"):
        return jsonify({"error": sm_resp.get("error")}), 400

    # ---------------------------------------------------
    # 2️⃣ Generate meeting link
    # ---------------------------------------------------
    meeting_link = None
    if platform in ("google_meet", "microsoft_teams"):
        meeting_link = generate_meeting_link(
            platform=platform,
            journey_id=journey.journey_id,
            interview_round=journey.interview_round
        )

    # ---------------------------------------------------
    # 3️⃣ Create Interview
    # ---------------------------------------------------
    iv = Interview(
        journey_id=journey.journey_id,
        interview_round=journey.interview_round or 0,
        interview_sub_round=journey.interview_sub_round or 0,
        scheduled_at=datetime.fromisoformat(scheduled_at) if scheduled_at else None,
        duration_minutes=duration_minutes,
        interviewer=interviewer,
        location=location,
        platform=platform,
        meeting_link=meeting_link,
        status="scheduled",
        result=None,
        created_by=created_by
    )

    db.session.add(iv)
    db.session.commit()

    # ---------------------------------------------------
    # 4️⃣ Send Email
    # ---------------------------------------------------
    candidate = Candidate.query.filter_by(cand_id=journey.cand_id).first()

    if candidate:
        interview_time_ist = to_ist(iv.scheduled_at)

        email_subject = "Your Interview Has Been Scheduled - HireNest"
        email_body = f
Hi {candidate.name},

Your interview has been scheduled.

Date & Time (IST): {interview_time_ist}
Duration: {iv.duration_minutes} minutes
Interviewer: {iv.interviewer}

Platform: {iv.platform}
Meeting Link: {iv.meeting_link}

Please join on time.

Regards,
HireNest Team

        _send_email(candidate.email, email_subject, email_body)

    return jsonify({
        "message": "Interview scheduled",
        "data": {
            "interview_id": iv.interview_id,
            "journey_id": iv.journey_id,
            "interview_round": iv.interview_round,
            "interview_sub_round": iv.interview_sub_round,
            "scheduled_at_utc": iv.scheduled_at,
            "scheduled_at_ist": to_ist(iv.scheduled_at),
            "interviewer": iv.interviewer,
            "duration_minutes": iv.duration_minutes,
            "platform": iv.platform,
            "meeting_link": iv.meeting_link,
            "status": iv.status
        }
    }), 201


# ===================================================
# RESCHEDULE INTERVIEW
# ===================================================
@journey_bp.route("/<int:journey_id>/interviews/<int:interview_id>/reschedule", methods=["PUT"])
@jwt_required
def reschedule_interview(journey_id, interview_id):

    data = request.get_json() or {}

    journey = JobCandidateJourney.query.filter_by(journey_id=journey_id).first()
    if not journey:
        return jsonify({"error": "Journey not found"}), 404

    interview = Interview.query.filter_by(
        interview_id=interview_id,
        journey_id=journey_id
    ).first()

    if not interview:
        return jsonify({"error": "Interview not found"}), 404

    new_scheduled_at = data.get("scheduled_at")

    # ---------------------------------------------------
    # Update journey state (reschedule)
    # ---------------------------------------------------
    sm_resp = JobCandidateJourneyStateMachine.transition(
        journey=journey,
        new_state="interview_scheduled",
        reschedule=True
    )

    if not sm_resp.get("success"):
        return jsonify({"error": sm_resp.get("error")}), 400

    # ---------------------------------------------------
    # Generate new meeting link
    # ---------------------------------------------------
    meeting_link = generate_meeting_link(
        platform=data.get("platform", interview.platform),
        journey_id=journey.journey_id,
        interview_round=journey.interview_round
    )

    # ---------------------------------------------------
    # Update Interview
    # ---------------------------------------------------
    interview.scheduled_at = datetime.fromisoformat(new_scheduled_at)
    interview.meeting_link = meeting_link
    interview.status = "rescheduled"

    db.session.commit()

    # ---------------------------------------------------
    # Send Email
    # ---------------------------------------------------
    candidate = Candidate.query.filter_by(cand_id=journey.cand_id).first()

    if candidate:
        interview_time_ist = to_ist(interview.scheduled_at)

        email_subject = "Your Interview Has Been Rescheduled - HireNest"
        email_body = f
Hi {candidate.name},

Your interview has been rescheduled.

New Date & Time (IST): {interview_time_ist}

Platform: {interview.platform}
Meeting Link: {interview.meeting_link}

Regards,
HireNest Team

        _send_email(candidate.email, email_subject, email_body)

    return jsonify({"message": "Interview rescheduled"}), 200


# ===================================================
# 🆕 UPDATE INTERVIEW RESULT (IMPORTANT)
# ===================================================
@journey_bp.route("/interviews/<int:interview_id>/result", methods=["PUT"])
@jwt_required
def update_interview_result(interview_id):

    data = request.get_json() or {}
    result = data.get("result")

    if not result:
        return jsonify({"error": "Result is required"}), 400

    interview = Interview.query.filter_by(interview_id=interview_id).first()
    if not interview:
        return jsonify({"error": "Interview not found"}), 404

    journey = JobCandidateJourney.query.filter_by(
        journey_id=interview.journey_id
    ).first()

    if not journey:
        return jsonify({"error": "Journey not found"}), 404

    # Save result
    interview.result = result
    interview.status = "completed"

    # Trigger state transition
    if result == "cleared":
        sm_resp = JobCandidateJourneyStateMachine.transition(journey, "cleared")

    elif result == "rejected_by_us":
        sm_resp = JobCandidateJourneyStateMachine.transition(journey, "rejected_by_us")

    elif result == "rejected_by_candidate":
        sm_resp = JobCandidateJourneyStateMachine.transition(journey, "rejected_by_candidate")

    elif result == "selected":
        sm_resp = JobCandidateJourneyStateMachine.transition(journey, "selected")

    else:
        return jsonify({"error": "Invalid result"}), 400

    if not sm_resp.get("success"):
        return jsonify({"error": sm_resp.get("error")}), 400

    db.session.commit()

    return jsonify({
        "message": "Interview result updated",
        "data": {
            "interview_id": interview.interview_id,
            "result": interview.result,
            "journey_status": journey.status
        }
    }), 200


# ===================================================
# NOTES (UNCHANGED)
# ===================================================
@journey_bp.route("/<int:journey_id>/notes", methods=["POST"])
@jwt_required
def add_note(journey_id):

    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}

    note = JourneyNote(
        journey_id=journey_id,
        note=data.get("note"),
        stage=data.get("stage"),
        interview_id=data.get("interview_id"),
        visible_to_candidate=data.get("visible_to_candidate", False),
        visible_to_recruiter=True,
        created_by=current_user["user_id"]   # ✅ IMPORTANT
    )

    db.session.add(note)
    db.session.commit()

    return jsonify({"message": "Note added"}), 201



"""


# Candidates/routes/journey_interview_routes.py

from flask import Blueprint, request, jsonify, g
from extensions import db
from datetime import datetime
from Candidates.models.job_candidate_journey import JobCandidateJourney
from Candidates.models.interview import Interview
from Candidates.models.journey_note import JourneyNote
from Candidates.state_machine.JobCandidateJourneyStateMachine import JobCandidateJourneyStateMachine
from Candidates.utils.meeting_link_generator import generate_meeting_link
from Organization.utils.email_utils import _send_email
from Candidates.models.candidate import Candidate

from auth.utils.jwt_required import jwt_required
from Logs.log_helper import create_log
import json


journey_bp = Blueprint("journey_bp", __name__)


# ---------------------------------------------------
# Helper: get current user from JWT
# ---------------------------------------------------
def get_current_user():
    if not hasattr(g, "current_user"):
        return None
    return g.current_user


# ---------------------------------------------------
# Helper: convert UTC → IST
# ---------------------------------------------------
def to_ist(dt):
    if not dt:
        return None
    from datetime import timezone, timedelta
    ist = dt.replace(tzinfo=timezone.utc) + timedelta(hours=5, minutes=30)
    return ist.strftime("%Y-%m-%d %H:%M:%S")


# ===================================================
# CREATE / SCHEDULE INTERVIEW
# ===================================================
@journey_bp.route("/<int:journey_id>/interviews", methods=["POST"])
@jwt_required
def create_interview(journey_id):

    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    import json

    data = request.get_json() or {}

    if isinstance(data, str):
        data = json.loads(data)

    journey = JobCandidateJourney.query.filter_by(journey_id=journey_id).first()
    if not journey:
        return jsonify({"error": "Journey not found"}), 404

    scheduled_at = data.get("scheduled_at")
    duration_minutes = data.get("duration_minutes")
    interviewer = data.get("interviewer")
    location = data.get("location")
    platform = data.get("platform")
    reschedule = data.get("reschedule", False)

    created_by = current_user["user_id"]

    # ---------------------------------------------------
    # 1️⃣ Update journey state
    # ---------------------------------------------------
    sm_resp = JobCandidateJourneyStateMachine.transition(
        journey=journey,
        new_state="interview_scheduled",
        reschedule=reschedule
    )

    if not sm_resp.get("success"):
        return jsonify({"error": sm_resp.get("error")}), 400

    # ---------------------------------------------------
    # 2️⃣ Generate meeting link
    # ---------------------------------------------------
    meeting_link = None
    if platform in ("google_meet", "microsoft_teams"):
        meeting_link = generate_meeting_link(
            platform=platform,
            journey_id=journey.journey_id,
            interview_round=journey.interview_round
        )

    # ---------------------------------------------------
    # 3️⃣ Create Interview
    # ---------------------------------------------------
    iv = Interview(
        journey_id=journey.journey_id,
        interview_round=journey.interview_round or 0,
        interview_sub_round=journey.interview_sub_round or 0,
        scheduled_at=datetime.fromisoformat(scheduled_at) if scheduled_at else None,
        duration_minutes=duration_minutes,
        interviewer=interviewer,
        location=location,
        platform=platform,
        meeting_link=meeting_link,
        status="scheduled",
        result=None,
        created_by=created_by
    )

    db.session.add(iv)
    db.session.flush()  # ✅ important

    # ---------------------------------------------------
    # 4️⃣ Activity Note
    # ---------------------------------------------------
    db.session.add(JourneyNote(
        journey_id=journey.journey_id,
        interview_id=iv.interview_id,
        note=f"Interview scheduled (Round {iv.interview_round})",
        stage="interview_scheduled",
        created_by=created_by
    ))

    db.session.commit()

    # ---------------------------------------------------
    # 5️⃣ Audit Log
    # ---------------------------------------------------
    create_log(
        created_by,
        action="schedule_interview",
        entity_type="Interview",
        entity_id=iv.interview_id,
        data={"journey_id": journey.journey_id}
    )

    # ---------------------------------------------------
    # 6️⃣ Send Email
    # ---------------------------------------------------
    candidate = Candidate.query.filter_by(cand_id=journey.cand_id).first()

    if candidate:
        interview_time_ist = to_ist(iv.scheduled_at)

        _send_email(
            candidate.email,
            "Your Interview Has Been Scheduled - HireNest",
            f"""
Hi {candidate.name},

Your interview has been scheduled.

Date & Time (IST): {interview_time_ist}
Interviewer: {iv.interviewer}

Platform: {iv.platform}
Meeting Link: {iv.meeting_link}

Regards,
CandiIQ Team
"""
        )

    return jsonify({
        "message": "Interview scheduled",
        "data": {
            "interview_id": iv.interview_id,
            "journey_id": iv.journey_id,
            "interview_round": iv.interview_round,
            "interview_sub_round": iv.interview_sub_round,
            "scheduled_at_utc": iv.scheduled_at,
            "scheduled_at_ist": to_ist(iv.scheduled_at),
            "interviewer": iv.interviewer,
            "duration_minutes": iv.duration_minutes,
            "platform": iv.platform,
            "meeting_link": iv.meeting_link,
            "status": iv.status
        }
    }), 201


# ===================================================
# RESCHEDULE INTERVIEW
# ===================================================
@journey_bp.route("/<int:journey_id>/interviews/<int:interview_id>/reschedule", methods=["PUT"])
@jwt_required
def reschedule_interview(journey_id, interview_id):

    current_user = get_current_user()

    data = request.get_json() or {}

    if isinstance(data, str):
        data = json.loads(data)

    journey = JobCandidateJourney.query.filter_by(journey_id=journey_id).first()
    interview = Interview.query.filter_by(interview_id=interview_id, journey_id=journey_id).first()

    if not journey or not interview:
        return jsonify({"error": "Not found"}), 404

    sm_resp = JobCandidateJourneyStateMachine.transition(
        journey=journey,
        new_state="interview_scheduled",
        reschedule=True
    )

    if not sm_resp.get("success"):
        return jsonify({"error": sm_resp.get("error")}), 400

    interview.scheduled_at = datetime.fromisoformat(data.get("scheduled_at"))
    interview.status = "rescheduled"

    db.session.add(JourneyNote(
        journey_id=journey.journey_id,
        interview_id=interview.interview_id,
        note=f"Interview rescheduled (Round {journey.interview_round}.{journey.interview_sub_round})",
        stage="interview_rescheduled",
        created_by=current_user["user_id"]
    ))

    db.session.commit()

    create_log(
        current_user["user_id"],
        action="reschedule_interview",
        entity_type="Interview",
        entity_id=interview_id,
        data={"journey_id": journey_id}
    )

    return jsonify({
        "message": "Interview rescheduled",
        "data": {
            "interview_id": interview.interview_id,
            "journey_id": interview.journey_id,
            "interview_round": journey.interview_round,
            "interview_sub_round": journey.interview_sub_round,
            "scheduled_at_utc": interview.scheduled_at,
            "scheduled_at_ist": to_ist(interview.scheduled_at),
            "platform": interview.platform,
            "meeting_link": interview.meeting_link,
            "status": interview.status
        }
    }), 200

"""
# ===================================================
# UPDATE INTERVIEW RESULT
# ===================================================
@journey_bp.route("/interviews/<int:interview_id>/result", methods=["PUT"])
@jwt_required
def update_interview_result(interview_id):

    current_user = get_current_user()

    data = request.get_json() or {}

    if isinstance(data, str):
        data = json.loads(data)
    result = data.get("result")

    interview = Interview.query.get(interview_id)
    journey = JobCandidateJourney.query.get(interview.journey_id)

    interview.result = result
    interview.status = "completed"

    sm_resp = JobCandidateJourneyStateMachine.transition(journey, result)

    if not sm_resp.get("success"):
        return jsonify({"error": sm_resp.get("error")}), 400

    db.session.add(JourneyNote(
        journey_id=journey.journey_id,
        interview_id=interview_id,
        note=f"Interview result: {result}",
        stage="interview_result",
        created_by=current_user["user_id"]
    ))

    db.session.commit()

    create_log(
        current_user["user_id"],
        action="update_interview_result",
        entity_type="Interview",
        entity_id=interview_id,
        data={"result": result}
    )

    return jsonify({
        "message": "Interview result updated",
        "data": {
            "interview_id": interview.interview_id,
            "result": interview.result,
            "journey_status": journey.status
        }
    }), 200
"""


# ===================================================
# UPDATE INTERVIEW RESULT
# ===================================================
@journey_bp.route("/interviews/<int:interview_id>/result", methods=["PUT"])
@jwt_required
def update_interview_result(interview_id):

    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}

    # Safety for stringified JSON
    if isinstance(data, str):
        data = json.loads(data)

    result = data.get("result")

    if not result:
        return jsonify({"error": "Result is required"}), 400

    # ---------------------------------------------------
    # Fetch Interview
    # ---------------------------------------------------
    interview = Interview.query.get(interview_id)

    if not interview:
        return jsonify({"error": "Interview not found"}), 404

    # ---------------------------------------------------
    # Fetch Journey
    # ---------------------------------------------------
    journey = JobCandidateJourney.query.get(
        interview.journey_id
    )

    if not journey:
        return jsonify({"error": "Journey not found"}), 404

    # ---------------------------------------------------
    # Prevent duplicate result update
    # ---------------------------------------------------
    if interview.result is not None:
        return jsonify({
            "error": "Result already set for this interview"
        }), 400

    # ---------------------------------------------------
    # Save Interview Result
    # ---------------------------------------------------
    interview.result = result
    interview.status = "completed"

    # ---------------------------------------------------
    # Allowed Interview Results
    # ---------------------------------------------------
    allowed_results = [
        "cleared",
        "selected",
        "rejected_by_us",
        "rejected_by_candidate"
    ]

    if result not in allowed_results:
        return jsonify({
            "error": "Invalid result"
        }), 400

    # ---------------------------------------------------
    # State Machine Transition
    # ---------------------------------------------------
    sm_resp = JobCandidateJourneyStateMachine.transition(
        journey,
        result
    )

    if not sm_resp.get("success"):
        return jsonify({
            "error": sm_resp.get("error")
        }), 400

    # ---------------------------------------------------
    # Timeline Note
    # ---------------------------------------------------
    db.session.add(
        JourneyNote(
            journey_id=journey.journey_id,
            interview_id=interview_id,
            note=f"Interview result: {result}",
            stage="interview_result",
            created_by=current_user["user_id"]
        )
    )

    # ---------------------------------------------------
    # Commit DB
    # ---------------------------------------------------
    db.session.commit()

    # ---------------------------------------------------
    # Audit Log
    # ---------------------------------------------------
    create_log(
        current_user["user_id"],
        action="update_interview_result",
        entity_type="Interview",
        entity_id=interview_id,
        data={
            "result": result,
            "journey_status": journey.status
        }
    )

    # ---------------------------------------------------
    # Response
    # ---------------------------------------------------
    return jsonify({
        "message": "Interview result updated",
        "data": {
            "interview_id": interview.interview_id,
            "interview_result": interview.result,
            "journey_status": journey.status,
            "journey_result": journey.interview_result,
            "interview_round": interview.interview_round,
            "interview_sub_round": interview.interview_sub_round
        }
    }), 200

@journey_bp.route("/<int:journey_id>/notes", methods=["POST"])
@jwt_required
def add_note(journey_id):

    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}

    if isinstance(data, str):
        data = json.loads(data)

    note_text = data.get("note")

    if not note_text:
        return jsonify({"error": "Note is required"}), 400

    # check journey exists
    journey = JobCandidateJourney.query.filter_by(
        journey_id=journey_id
    ).first()

    if not journey:
        return jsonify({"error": "Journey not found"}), 404

    note = JourneyNote(
        journey_id=journey_id,
        interview_id=data.get("interview_id"),
        note=note_text,
        stage=data.get("stage", "manual"),
        visible_to_candidate=data.get("visible_to_candidate", False),
        visible_to_recruiter=True,
        created_by=current_user["user_id"]
    )

    db.session.add(note)
    db.session.commit()

    # audit log
    create_log(
        current_user["user_id"],
        action="add_note",
        entity_type="JourneyNote",
        entity_id=note.note_id,
        data={
            "journey_id": journey_id,
            "stage": note.stage
        }
    )

    return jsonify({
        "message": "Note added successfully",
        "data": {
            "note_id": note.note_id,
            "note": note.note,
            "stage": note.stage
        }
    }), 201


@journey_bp.route("/<int:journey_id>/notes", methods=["GET"])
@jwt_required
def get_notes(journey_id):

    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    journey = JobCandidateJourney.query.filter_by(
        journey_id=journey_id
    ).first()

    if not journey:
        return jsonify({"error": "Journey not found"}), 404

    notes = JourneyNote.query.filter_by(
        journey_id=journey_id
    ).order_by(JourneyNote.created_at.desc()).all()

    result = []

    for n in notes:
        result.append({
            "note_id": n.note_id,
            "note": n.note,
            "stage": n.stage,
            "interview_id": n.interview_id,
            "created_by": n.created_by,
            "visible_to_candidate": n.visible_to_candidate,
            "created_at": n.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    return jsonify({
        "message": "Notes fetched successfully",
        "count": len(result),
        "data": result
    }), 200