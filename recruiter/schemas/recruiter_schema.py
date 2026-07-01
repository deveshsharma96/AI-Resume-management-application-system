# recruiter_schema.py

recruiter_registration_fields = {
    "name": {"type": "string", "required": True},
    "email": {"type": "string", "required": True},
    "phone": {"type": "string", "required": True},
    "type": {"type": "string", "required": True},  # organization or freelancer
    "org_id": {"type": "string", "required": False},  # only for organization
    "designation": {"type": "string", "required": False},
    "password": {"type": "string", "required": True},
    "confirm_password": {"type": "string", "required": True},
}
