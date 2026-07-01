from extensions import db

from datetime import datetime


class CandidateRequestDocument(db.Model):

    __tablename__ = "candidate_request_documents"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    request_id = db.Column(
        db.Integer,
        db.ForeignKey("document_requests.id"),
        nullable=False
    )

    document_name = db.Column(
        db.String(255),
        nullable=False
    )

    # -------------------------------------------------
    # LINKED S3 DOCUMENT
    # -------------------------------------------------

    docu_id = db.Column(
        db.String(36),
        db.ForeignKey("document_assets.docu_id"),
        nullable=False
    )

    # -------------------------------------------------
    # REVIEW FLOW
    # -------------------------------------------------

    status = db.Column(
        db.String(50),
        default="submitted"
    )
    # submitted
    # approved
    # rejected
    # resubmission_requested

    rejection_reason = db.Column(
        db.Text,
        nullable=True
    )

    approved_by = db.Column(
        db.String(255),
        nullable=True
    )

    approved_at = db.Column(
        db.DateTime,
        nullable=True
    )

    # -------------------------------------------------
    # VERSION CONTROL
    # -------------------------------------------------

    is_latest = db.Column(
        db.Boolean,
        default=True
    )

    # -------------------------------------------------
    # TIMESTAMPS
    # -------------------------------------------------

    submitted_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
    
    
    org_id = db.Column(
        db.String(255),
        nullable=False
    )
    
    
    cand_id = db.Column(
        db.String(255),
        nullable=False
    )


