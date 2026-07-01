# Candidates/utils/meeting_link_generator.py
import uuid

def generate_meeting_link(platform, journey_id, interview_round):
    unique = f"{journey_id}-{interview_round}-{uuid.uuid4()}"

    # Google Meet format
    if platform == "google_meet":
        # Google Meet requires a 10-character alphanumeric code
        code = unique.replace("-", "")[:10]
        return f"https://meet.google.com/{code}"

    # Microsoft Teams format
    if platform == "microsoft_teams":
        return f"https://teams.microsoft.com/l/meetup-join/{unique}"

    # Default: platform unsupported
    return None
