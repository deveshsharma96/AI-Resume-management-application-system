from functools import wraps
from flask import request, jsonify, g
import jwt
from config import Config
from Organization.models.organization import Organization



def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        # ✅ ✅ FIX: Allow preflight requests
        if request.method == "OPTIONS":
            return "", 200

        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return jsonify({"error": "Authorization token missing"}), 401

        try:
            token = auth_header.split(" ")[1]

            payload = jwt.decode(
                token,
                Config.SECRET_KEY,
                algorithms=["HS256"]
            )

            # Ensure access token only
            if payload.get("type") != "access":
                return jsonify({"error": "Invalid token type"}), 401

            g.current_user = {
                "user_id": payload.get("user_id"),
                "org_id": payload.get("org_id"),
                "role": payload.get("role")
            }
            # ----------------------------------------
            # 🚫 BLOCK DELETED ORGANIZATION (GLOBAL PROTECTION)
            # ----------------------------------------
            org_id = g.current_user.get("org_id")

            if org_id:
                org = Organization.query.filter_by(org_id=org_id).first()

                if org and org.is_deleted:
                    return jsonify({
                        "error": "Organization is deactivated"
                    }), 403

        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Access token expired"}), 401
        except Exception:
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)

    return decorated


def jwt_optional(f):

    @wraps(f)
    def decorated(*args, **kwargs):

        auth_header = request.headers.get("Authorization")

        if not auth_header:
            # allow request without JWT
            g.current_user = None
            return f(*args, **kwargs)

        try:

            token = auth_header.split(" ")[1]

            payload = jwt.decode(
                token,
                Config.SECRET_KEY,
                algorithms=["HS256"]
            )

            if payload.get("type") != "access":
                g.current_user = None
            else:
                g.current_user = {
                    "user_id": payload.get("user_id"),
                    "org_id": payload.get("org_id"),
                    "role": payload.get("role")
                }

        except Exception:
            g.current_user = None

        return f(*args, **kwargs)

    return decorated