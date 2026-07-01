from extensions import db
from datetime import datetime
import uuid
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy import JSON


class ParsedCandidateTemp(db.Model):
    __tablename__ = "parsed_candidates_temp"

    # ---------------- PRIMARY ----------------
    temp_id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # ---------------- CONTEXT ----------------
    org_id = db.Column(db.String(50), nullable=False)
    uploaded_by = db.Column(db.String(255), nullable=False)

    source = db.Column(
        db.Enum("upload_resume", "email_integration"),
        nullable=False
    )

    # ---------------- RESUME ----------------
    resume_file = db.Column(db.String(255), nullable=False)
    resume_hash = db.Column(db.String(64), nullable=False)

    # ---------------- PARSED DATA ----------------
    # Cleaned / normalized parsed data (used by UI & save flow)
    parsed_json = db.Column(
        MutableDict.as_mutable(db.JSON),
        nullable=False
    )

    # 🔴 NEW: RAW PARSED DATA (IMPORTANT)
    # Stores original parser output before any edits / normalization
    raw_parsed_json = db.Column(
        MutableDict.as_mutable(db.JSON),
        nullable=True
    )

    # ---------------- PARSE METRICS ----------------
    # confidence, counts, flags, etc.
    parse_metrics = db.Column(
        MutableDict.as_mutable(db.JSON),
        nullable=True
    )

    # ---------------- STATE ----------------
    status = db.Column(
        db.Enum("draft", "saved"),
        default="draft",
        nullable=False
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ---------------- HELPERS ----------------
    def to_dict(self):
        return {
            "temp_id": self.temp_id,
            "org_id": self.org_id,
            "uploaded_by": self.uploaded_by,
            "source": self.source,
            "resume_file": self.resume_file,
            "resume_hash": self.resume_hash,
            "parsed_json": self.parsed_json,
            "raw_parsed_json": self.raw_parsed_json,  # ✅ exposed
            "parse_metrics": self.parse_metrics,
            "status": self.status,
            "created_at": self.created_at.isoformat()
        }
