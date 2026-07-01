from extensions import db

class OrganizationCollaboration(db.Model):
    __tablename__ = "organization_collaborations"

    id = db.Column(db.Integer, primary_key=True)

    source_org_id = db.Column(
        db.String(255),
        db.ForeignKey("organizations.org_id"),
        nullable=False
    )

    target_org_id = db.Column(
        db.String(255),
        db.ForeignKey("organizations.org_id"),
        nullable=False
    )

    status = db.Column(
        db.Enum("PENDING", "ACCEPTED", "REJECTED","CANCELLED", name="collab_status_enum"),
        nullable=False,
        default="PENDING"
    )

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    __table_args__ = (
        db.UniqueConstraint(
            "source_org_id",
            "target_org_id",
            name="uq_org_collaboration"
        ),
    )

    def __repr__(self):
        return f"<Collaboration {self.source_org_id} -> {self.target_org_id}>"