import imaplib
import base64
import requests
from datetime import datetime, timedelta
from config import Config


# ---------------- XOAUTH2 ----------------
def generate_xoauth2(email, access_token):
    auth_string = f"user={email}\1auth=Bearer {access_token}\1\1"
    return base64.b64encode(auth_string.encode()).decode()


# ---------------- REFRESH TOKEN ----------------
def refresh_access_token(refresh_token):
    url = "https://oauth2.googleapis.com/token"

    data = {
        "client_id": Config.GOOGLE_CLIENT_ID,
        "client_secret": Config.GOOGLE_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }

    response = requests.post(url, data=data)

    if response.status_code != 200:
        raise Exception(f"Token refresh failed: {response.text}")

    token_data = response.json()

    if "access_token" not in token_data:
        raise Exception(f"Invalid refresh response: {token_data}")

    return token_data


# ---------------- CONNECT IMAP ----------------
def connect_imap(email, access_token):
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)

        auth_string = generate_xoauth2(email, access_token)

        mail.authenticate("XOAUTH2", lambda x: auth_string)

        return mail

    except Exception as e:
        raise Exception(f"IMAP connection failed: {str(e)}")


# ---------------- SYNC LOGIC ----------------
def should_sync(record):
    """
    Decide whether this user's email should be synced now.
    """

    if not record.is_active:
        return False

    if not record.last_synced_at:
        return True

    next_run = record.last_synced_at + timedelta(minutes=record.sync_interval)

    return datetime.utcnow() >= next_run