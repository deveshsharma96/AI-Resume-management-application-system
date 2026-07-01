#document_request_model.py
from extensions import db
from datetime import datetime


class DocumentRequest(db.Model):

    __tablename__ = "document_requests"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    org_id = db.Column(
        db.String(255),
        nullable=False
    )

    candidate_id = db.Column(
        db.String(255),
        nullable=False
    )

    template_name = db.Column(
        db.String(255)
    )

    documents = db.Column(
        db.JSON,
        nullable=False
    )

    upload_token = db.Column(
        db.String(500)
    )

    # -----------------------------------------
    # REQUEST STATUS
    # -----------------------------------------

    status = db.Column(
        db.Enum(
            "pending",
            "uploaded",
            "approved",
            "rejected",
            "withdrawn",
            name="document_request_status_enum"
        ),
        default="pending"
    )

    # pending
    # partially_submitted
    # submitted
    # approved
    # rejected
    # completed

    # -----------------------------------------
    # ACTIVE REQUEST CONTROL
    # -----------------------------------------

    is_active = db.Column(
        db.Boolean,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
    
    requested_by = db.Column(
        db.String(255),
        nullable=True
    )

    requested_by_role = db.Column(
        db.String(50),
        nullable=True
    )

    approved_by = db.Column(
        db.String(255),
        nullable=True
    )

    rejected_by = db.Column(
        db.String(255),
        nullable=True
    )

    withdrawn_by = db.Column(
        db.String(255),
        nullable=True
    )

    withdrawn_at = db.Column(
        db.DateTime,
        nullable=True
    )