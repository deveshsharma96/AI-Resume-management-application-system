from flask import Blueprint, redirect, request, jsonify
from urllib.parse import urlencode
import requests
from datetime import datetime, timedelta
import jwt

from config import Config
from extensions import db
from email_integration.model import EmailIntegration

email_bp = Blueprint("email_bp", __name__)


# ---------------- GOOGLE CONNECT ----------------
@email_bp.route("/email/google/connect", methods=["GET"])
def connect_google():

    base_url = "https://accounts.google.com/o/oauth2/v2/auth"

    token = request.args.get("token")

    if not token:
        return jsonify({"error": "Authorization token missing"}), 401

    # 🔐 decode JWT from frontend
    from auth.utils.auth_utils import decode_token  # adjust if needed

    user = decode_token(token)

    if not user:
        return jsonify({"error": "Invalid token"}), 401

    # 🔐 create secure state
    state_payload = {
        "user_id": user["user_id"],
        "org_id": user.get("org_id"),
        "exp": datetime.utcnow() + timedelta(minutes=10)
    }

    state_token = jwt.encode(state_payload, Config.SECRET_KEY, algorithm="HS256")

    params = {
        "client_id": Config.GOOGLE_CLIENT_ID,
        "redirect_uri": Config.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "https://mail.google.com/",
        "access_type": "offline",
        "prompt": "consent",
        "state": state_token
    }

    url = f"{base_url}?{urlencode(params)}"
    return redirect(url)


# ---------------- GOOGLE CALLBACK ----------------
@email_bp.route("/auth/google/callback", methods=["GET"])
def google_callback():

    code = request.args.get("code")
    state_token = request.args.get("state")

    if not code:
        return jsonify({"error": "No code received"}), 400

    if not state_token:
        return jsonify({"error": "Missing state"}), 400

    # 🔐 decode state safely
    try:
        decoded = jwt.decode(state_token, Config.SECRET_KEY, algorithms=["HS256"])
        user_id = decoded["user_id"]
        org_id = decoded.get("org_id")
    except Exception:
        return jsonify({"error": "Invalid or expired state"}), 400

    # 🔥 Exchange code for token
    try:
        token_res = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": Config.GOOGLE_CLIENT_ID,
                "client_secret": Config.GOOGLE_CLIENT_SECRET,
                "redirect_uri": Config.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code"
            }
        )

        token_data = token_res.json()

    except Exception as e:
        return jsonify({"error": f"Token exchange failed: {str(e)}"}), 500

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")

    if not access_token:
        return jsonify({"error": "Failed to get access token"}), 400

    # 🔥 Get user email from Google
    try:
        user_info = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        ).json()

        email = user_info.get("email")

    except Exception as e:
        return jsonify({"error": f"Failed to fetch user info: {str(e)}"}), 500

    if not email:
        return jsonify({"error": "Email not found"}), 400

    # 🔥 Save / Update DB
    record = EmailIntegration.query.filter_by(
        user_id=user_id,
        email=email
    ).first()

    if not record:
        record = EmailIntegration(
            user_id=user_id,
            org_id=org_id,
            email=email,
            sync_interval=10,
            is_active=True
        )

    record.access_token = access_token

    if refresh_token:
        record.refresh_token = refresh_token

    record.expires_at = datetime.utcnow() + timedelta(seconds=3600)

    # reset sync pointer on reconnect
    record.last_synced_at = None

    db.session.add(record)
    db.session.commit()

    return redirect(f"http://127.0.0.1:8080/email-connected?email={email}")


# ---------------- UPDATE SYNC SETTINGS ----------------
@email_bp.route("/email/sync-settings", methods=["POST"])
def update_sync_settings():

    from flask import g

    actor = getattr(g, "current_user", None)
    if not actor:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()

    sync_interval = data.get("sync_interval")
    is_active = data.get("is_active")

    record = EmailIntegration.query.filter_by(
        user_id=actor["user_id"]
    ).first()

    if not record:
        return jsonify({"error": "No email connected"}), 400

    if sync_interval:
        record.sync_interval = int(sync_interval)

    if is_active is not None:
        record.is_active = bool(is_active)

    db.session.commit()

    return jsonify({
        "status": "success",
        "sync_interval": record.sync_interval,
        "is_active": record.is_active
    })