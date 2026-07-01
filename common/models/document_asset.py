from extensions import db
from datetime import datetime
import uuid


class DocumentAsset(db.Model):
    __tablename__ = "document_assets"

    docu_id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Object storage
    file_key = db.Column(db.String(512), nullable=False)

    # Metadata
    original_filename = db.Column(db.String(255))
    mime_type = db.Column(db.String(50))
    file_size = db.Column(db.Integer)

    # Document classification
    # document_type = db.Column(
    #     db.Enum(
    #         "resume",
    #         "cover_letter",
    #         "id_proof",
    #         "address_proof",
    #         "portfolio",
    #         "other"
    #     ),
    #     nullable=False
    # )
    
    #New Document classification
    document_type = db.Column(
        db.Enum(
            "resume",
            "cover_letter",
            "aadhar",
            "pan",
            "passport",
            "driving_license",
            "marksheet",
            "certificate",
            "salary_slip",
            "bank_statement",
            "experience_letter",
            "offer_letter",
            "id_proof",
            "address_proof",
            "portfolio",
            "other"
        ),
        nullable=False
    )
    
    

    # Ownership (linked later)
    cand_id = db.Column(
        db.String(50),
        db.ForeignKey("candidates.cand_id"),
        nullable=True,
        index=True
    )
    
    #New
    document_count = db.Column(
        db.Integer,
        nullable=False,
        default=1
    )

    # Audit
    uploaded_by = db.Column(db.String(255))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    org_id = db.Column(db.String(50), nullable=False)

    is_linked = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "docu_id": self.docu_id,
            "file_key": self.file_key,
            "original_filename": self.original_filename,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "document_type": self.document_type,
            "cand_id": self.cand_id,
            "uploaded_by": self.uploaded_by,
            "uploaded_at": self.uploaded_at.isoformat(),
            "is_linked": self.is_linked,
        }
