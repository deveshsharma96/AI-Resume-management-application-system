import re

PASSWORD_REGEX = re.compile(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$'
)



def validate_password(password: str):
    if not password:
        return False, "Password is required"

    if not PASSWORD_REGEX.match(password):
        return False, (
            "Password must be at least 8 characters long and include "
            "one uppercase letter, one lowercase letter, one number, "
            "and one special character."
        )

    return True, None


