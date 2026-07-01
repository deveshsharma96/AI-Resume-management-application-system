from Logs.audit_log_model import AuditLog
from extensions import db
from datetime import datetime
import json


def create_log(user, action, entity_type=None, entity_id=None, data=None):
    """
    Create an audit log entry.
    Supports both:
    - user object (old system)
    - user email string (JWT system)
    """

    # ---------------- Resolve User Info ----------------
    if isinstance(user, str):
        # JWT system (user is email)
        user_id = user
        user_name = user
        user_role = "unknown"

    else:
        # Old system (user model object)
        user_id = getattr(user, "email", "unknown")
        user_name = getattr(user, "name", user_id)
        user_role = getattr(user, "role", "unknown")

    # ---------------- Safe JSON Data ----------------
    try:
        safe_data = json.loads(json.dumps(data or {}, default=str))
    except Exception:
        safe_data = {}

    # ---------------- Create Log Entry ----------------
    log = AuditLog(
        user_id=user_id,
        user_name=user_name,
        user_role=user_role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        data=safe_data,
        timestamp=datetime.utcnow()
    )

    # ---------------- Save to DB ----------------
    try:
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[AuditLog Error] Failed to save log: {e}")