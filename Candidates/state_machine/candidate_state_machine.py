# Candidates/state_machine/candidate_state_machine.py

class CandidateStateMachine:

    allowed_transitions = {
        "new": ["completed"],
        "completed": ["screened"],
    }

    @classmethod
    def can_transition(cls, old_state, new_state):
        return new_state in cls.allowed_transitions.get(old_state, [])

    @classmethod
    def transition(cls, candidate, new_state):

        current_state = candidate.status

        # ------------------------------------------------------
        # Validate transition
        # ------------------------------------------------------
        if not cls.can_transition(current_state, new_state):
            return {
                "success": False,
                "error": f"Invalid transition: {current_state} → {new_state}"
            }

        # ------------------------------------------------------
        # Apply transition
        # ------------------------------------------------------
        candidate.status = new_state

        return {"success": True}