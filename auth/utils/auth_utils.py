from flask import request
import jwt
from auth.routes.auth_routes import find_user
from config import Config
from datetime import datetime, timedelta

SECRET_KEY = Config.SECRET_KEY


def generate_token(payload: dict, expires_in_hours: int = 24) -> str:
    """
    Generate a JWT token.
    Payload MUST include:
      - role
      - email (recommended)
      - user_id (for candidates)
    """
    token_payload = payload.copy()
    token_payload["iat"] = datetime.utcnow()
    token_payload["exp"] = datetime.utcnow() + timedelta(hours=expires_in_hours)

    return jwt.encode(token_payload, SECRET_KEY, algorithm="HS256")



def get_current_user():
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    try:
        token = auth_header.split(" ")[1]  # "Bearer <token>"
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        email = payload.get("email")
        return find_user(email)
    except Exception:
        return None


def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except Exception:
        return None