# Candidates/utils/journey_history_helper.py

from Candidates.models.job_candidate_journey_history import (
    JobCandidateJourneyHistory
)

def create_journey_history(
    journey,
    current_user_id
):
    history = JobCandidateJourneyHistory(
        journey_id=journey.journey_id,

        old_status=journey.status,
        old_interview_round=journey.interview_round,
        old_interview_sub_round=journey.interview_sub_round,
        old_interview_result=journey.interview_result,

        changed_by=current_user_id
    )

    return history