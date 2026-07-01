from extensions import db
from datetime import datetime


class Resume(db.Model):
    __tablename__ = "resumes"

    id = db.Column(db.Integer, primary_key=True)

    cand_id = db.Column(
        db.String(50),
        db.ForeignKey("candidates.cand_id", ondelete="CASCADE"),
        nullable=False
    )


    candidate = db.relationship(
        "Candidate",
        foreign_keys=[cand_id],
        back_populates="resumes"
    )
    org_id = db.Column(db.String(50), nullable=False, index=True)

    # -------------------------------------------------
    # Resume / Cover Letter Files
    # -------------------------------------------------
    # NOTE: must be nullable because resume row is created
    # before file_key is assigned
    resume_file = db.Column(db.String(512), nullable=True)
    cover_letter_file = db.Column(db.String(512), nullable=True)

    resume_hash = db.Column(db.String(64), index=True, nullable=True)

    # -------------------------------------------------
    # Metadata
    # -------------------------------------------------
    original_filename = db.Column(db.String(255))
    cover_letter_filename = db.Column(db.String(255))

    mime_type = db.Column(db.String(50))
    cover_letter_mime_type = db.Column(db.String(50))

    file_size = db.Column(db.Integer)
    cover_letter_size = db.Column(db.Integer)

    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    # -------------------------------------------------
    # Source
    # -------------------------------------------------
    source = db.Column(
        db.Enum(
            "candidate_form",
            "full_form",
            "upload_resume",
            "email_integration",
            "public_form"
        ),
        default="upload_resume",
        nullable=False
    )
    __table_args__ = (
        db.UniqueConstraint("resume_hash", "org_id", name="uq_resume_hash_org"),
    )


    def to_dict(self):
        return {
            "id": self.id,
            "cand_id": self.cand_id,
            "resume_key": self.resume_file,
            "cover_letter_key": self.cover_letter_file,
            "original_filename": self.original_filename,
            "cover_letter_filename": self.cover_letter_filename,
            "mime_type": self.mime_type,
            "cover_letter_mime_type": self.cover_letter_mime_type,
            "file_size": self.file_size,
            "cover_letter_size": self.cover_letter_size,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "source": self.source,
        }
