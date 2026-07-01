from extensions import db


class OrganizationRecruiter(db.Model):
    __tablename__ = "organization_recruiter"

    id = db.Column(db.Integer, primary_key=True)

    recruiter_id = db.Column(
        db.Integer,
        db.ForeignKey("recruiter.recruiter_id"),
        nullable=False
    )
    org_id = db.Column(
        db.String(255),
        db.ForeignKey("organizations.org_id"),
        nullable=False
    )

    recruiter_type = db.Column(
        db.Enum("INTERNAL", "EXTERNAL", name="recruiter_type_enum"),
        nullable=False
    )

    status = db.Column(
        db.Enum("ACTIVE", "INVITED", "DISABLED", name="recruiter_status_enum"),
        nullable=False
    )

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())

    __table_args__ = (
        db.UniqueConstraint("recruiter_id", "org_id", name="uq_recruiter_org"),
    )

    def __repr__(self):
        return f"<OrgRecruiter recruiter={self.recruiter_id} org={self.org_id} role={self.role}>"