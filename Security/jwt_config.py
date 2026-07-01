# security/jwt_config.py
from flask_jwt_extended import JWTManager

def init_jwt(app):
    app.config["JWT_SECRET_KEY"] = "your-secret-key"
    jwt = JWTManager(app)
    return jwt




# ---------------- New Candidate Custom JWT ----------------
# Custom JWT implementation for candidate authentication.
# Added to create role-specific tokens with controlled payload structure.
# Helps differentiate candidate tokens from admin/recruiter tokens.

import jwt
from datetime import datetime, timedelta
from flask import current_app


def generate_candidate_token(user_id, email):
    payload = {
        "candidate_user_id": user_id,
        "email": email,
        "role": "candidate",
        "exp": datetime.utcnow() + timedelta(days=7),
        "iat": datetime.utcnow()
    }

    return jwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm="HS256"
    )
    
# Used for API authentication (Flask-JWT-Extended)
from flask_jwt_extended import create_access_token


def generate_candidate_access_token(user_id, email):
    additional_claims = {
        "email": email,
        "role": "candidate"
    }

    return create_access_token(
        identity=user_id,  # THIS creates "sub"
        additional_claims=additional_claims
    )