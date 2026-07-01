# Candidates/state_machine/job_candidate_journey_state_machine.py

class JobCandidateJourneyStateMachine:

    # ------------------------------------------------------
    # Allowed Transitions (UPDATED as per flowchart)
    # ------------------------------------------------------
    allowed_transitions = {
        "shared": ["interview_scheduled", "rejected", "need_more_info" ,"shortlisted"],
        "shortlisted": [
            "interview_scheduled",
            "rejected",
            "need_more_info",
        ],

        "interview_scheduled": [
            "interview_scheduled",   # loop (new round / reschedule)
            "cleared",
            "rejected_by_us",
            "rejected_by_candidate",
            "selected"
        ],

        "cleared": ["interview_scheduled", "selected"],

        "need_more_info": ["shared","interview_scheduled","rejected",],

        "rejected": [],
        "selected": []
    }

    # ------------------------------------------------------
    # Validate transition
    # ------------------------------------------------------
    @classmethod
    def can_transition(cls, old_state, new_state):
        return new_state in cls.allowed_transitions.get(old_state, [])

    # ------------------------------------------------------
    # Start new interview round
    # ------------------------------------------------------
    @classmethod
    def start_new_round(cls, journey):
        journey.interview_round = (journey.interview_round or 0) + 1
        journey.interview_sub_round = 0
        journey.interview_result = None

    # ------------------------------------------------------
    # Reschedule existing round
    # ------------------------------------------------------
    @classmethod
    def reschedule_round(cls, journey):
        if not journey.interview_round:
            journey.interview_round = 1
            journey.interview_sub_round = 1
        else:
            journey.interview_sub_round = (journey.interview_sub_round or 0) + 1

    # ------------------------------------------------------
    # Main Transition Logic
    # ------------------------------------------------------
    @classmethod
    def transition(
        cls,
        journey,
        new_state,
        interview_result=None,
        reschedule=False,
        finalize_on_result=False
    ):

        current_state = journey.status

        # --------------------------------------------------
        # 1️⃣ Validate Transition
        # --------------------------------------------------
        if not cls.can_transition(
            current_state,
            new_state
        ):
            return {
                "success": False,
                "error": (
                    f"Invalid transition: "
                    f"{current_state} → {new_state}"
                )
            }

        # --------------------------------------------------
        # 2️⃣ FINAL STATES
        # --------------------------------------------------
        if new_state in ["selected", "rejected"]:

            journey.status = new_state
            journey.interview_result = new_state

            return {"success": True}

        # --------------------------------------------------
        # 3️⃣ INTERVIEW SCHEDULED
        # --------------------------------------------------
        if new_state == "interview_scheduled":

            if reschedule:
                cls.reschedule_round(journey)

            else:
                cls.start_new_round(journey)

            journey.status = "interview_scheduled"

            return {"success": True}

        # --------------------------------------------------
        # 4️⃣ CLEARED
        # --------------------------------------------------
        if new_state == "cleared":

            journey.status = "cleared"
            journey.interview_result = "cleared"

            return {"success": True}

        # --------------------------------------------------
        # 5️⃣ REJECTION TYPES
        # --------------------------------------------------
        if new_state in [
            "rejected_by_us",
            "rejected_by_candidate"
        ]:

            journey.status = "rejected"
            journey.interview_result = new_state

            return {"success": True}

        # --------------------------------------------------
        # 6️⃣ SHORTLISTED
        # --------------------------------------------------
        if new_state == "shortlisted":

            journey.status = "shortlisted"

            return {"success": True}

        # --------------------------------------------------
        # 7️⃣ NEED MORE INFO
        # --------------------------------------------------
        if new_state == "need_more_info":

            journey.status = "need_more_info"

            return {"success": True}
        # --------------------------------------------------
        # 8️⃣ DEFAULT FALLBACK
        # --------------------------------------------------
        journey.status = new_state

        return {"success": True}