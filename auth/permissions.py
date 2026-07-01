from functools import wraps
from flask import request, jsonify

# Import models directly (NO circular import!)
from Organization.models.super_admin import SuperAdmin
from recruiter.models.recruiter_model import Recruiter
from recruiter.models.org_recruiter_model import OrgRecruiter
from recruiter.models.admin_model import Admin


# ------------------------------
# 🔍 LOCAL USER FINDER (safe)
# ------------------------------
def find_user(email):
    """Find user from ANY model."""
    for model in [SuperAdmin, Recruiter, OrgRecruiter, Admin]:
        user = model.query.filter_by(email=email).first()
        if user:
            return user
    return None


# ------------------------------
# 🔐 ROLE → PERMISSIONS MAPPING
# ------------------------------
PERMISSIONS = {
    "superadmin": {
        "manage_org": True,
        "delete_job": True, 
        "manage_jobs": True,
        "manage_candidates": True,
        "view_analytics": True,
    },
    "admin": {
        "manage_org": False,
        "manage_jobs": True,
        "delete_job": False,
        "manage_candidates": True,
        "view_analytics": True,
    },
    "org_recruiter": {
        "manage_org": False,
        "manage_jobs": False,
        "delete_job": False,
        "manage_candidates": True,
        "view_analytics": False,
    },
    "recruiter": {
        "manage_org": True,
        "manage_jobs": True,
        "delete_job": False,
        "manage_candidates": True,
        "view_analytics": False,
    }
}
# ------------------------------
# 🔐 DECORATOR: CHECK PERMISSION
# ------------------------------
def permission_required(permission_name):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):

            # 1️⃣ Get email from frontend header
            email = request.headers.get("X-User-Email")

            if not email:
                return jsonify({"error": "Missing X-User-Email header"}), 401

            # 2️⃣ Find the user
            user = find_user(email)
            if not user:
                return jsonify({"error": "Invalid user"}), 401

            role = user.role

            # 3️⃣ Permission check
            allowed = PERMISSIONS.get(role, {}).get(permission_name, False)

            if not allowed:
                return jsonify({
                    "error": "Permission denied",
                    "role": role,
                    "missing_permission": permission_name
                }), 403

            return f(*args, **kwargs)

        return wrapper
    return decorator