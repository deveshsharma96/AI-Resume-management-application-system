
"""
Auto-import all SQLAlchemy models so Flask-Migrate can detect them.
DO NOT manually list models here.
"""

import pkgutil
import importlib
import sys

from extensions import db

# New candidate request documents
from recruiter.models.document_request_model import *

# New Default setting for share candidates
from GlobalRecruiter.models.recruiter_default_share_target import (
    RecruiterDefaultShareTarget
)

# List all top-level packages that may contain models
MODEL_PACKAGES = [
    "Organization",
    "recruiter",
    "Candidates",
    "jobs",
    "Logs",
    "auth",
    "dashboard",
    "common",
    "support",
    "GlobalRecruiter",
    "email_integration",
    "Notifications"
]


def import_submodules(package_name):
    """
    Recursively import all submodules of a package
    """
    try:
        package = importlib.import_module(package_name)
    except ModuleNotFoundError:
        return

    if not hasattr(package, "__path__"):
        return

    for _, module_name, _ in pkgutil.walk_packages(
        package.__path__,
        package.__name__ + "."
    ):
        try:
            importlib.import_module(module_name)
        except Exception as e:
            print(f"[MODEL IMPORT ERROR] {module_name}: {e}")
            raise


# Import everything
for pkg in MODEL_PACKAGES:
    import_submodules(pkg)

