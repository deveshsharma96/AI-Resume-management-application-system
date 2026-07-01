# Organization/models/team.py

from extensions import db
import uuid
from datetime import datetime

class Team(db.Model):
    __tablename__ = "teams"

    team_id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = db.Column(db.String(50), nullable=False)

    team_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)

    team_type = db.Column(
        db.Enum("internal", "external", name="team_type_enum"),
        nullable=False,
        default="internal"
    )

    created_by = db.Column(db.String(255), nullable=False)   # email of admin/superadmin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship (not required right now, but helpful)
    members = db.relationship("TeamMember", backref="team", lazy=True)

    def to_dict(self):
        return {
            "team_id": self.team_id,
            "org_id": self.org_id,
            "team_name": self.team_name,
            "description": self.description,
            "team_type": self.team_type,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat()
        }
