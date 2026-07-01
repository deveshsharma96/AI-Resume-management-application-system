# utils/token_utils.py

import jwt
from datetime import datetime, timedelta
from config import Config

def generate_token(email):
    """
    Generate JWT token with 24-hour expiration (or as defined in config)
    """
    payload = {
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=Config.TOKEN_EXPIRATION_HOURS)
    }
    token = jwt.encode(payload, Config.SECRET_KEY, algorithm="HS256")
    return token

def verify_token(token):
    """
    Verify JWT token and return email if valid
    """
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
        return payload["email"]
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
