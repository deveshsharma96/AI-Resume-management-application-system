from flask import request
import jwt
from config import Config

SECRET_KEY = Config.SECRET_KEY


def get_current_actor():
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return None

    try:
        token = auth_header.split(" ")[1]

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=["HS256"]
        )

        if payload.get("type") != "access":
            return None

        return {
            "user_id": payload.get("user_id"),
            "org_id": payload.get("org_id"),
            "role": payload.get("role")
        }

    except Exception:
        return None


# Candidate JWT remains same (already correct)
from auth.candidate.models.candidate_user import CandidateUser


def get_current_candidate():
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    try:
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

        if payload.get("role") != "candidate":
            return None

        user_id = payload.get("user_id")
        if not user_id:
            return None

        return CandidateUser.query.filter_by(user_id=user_id).first()

    except Exception:
        return None