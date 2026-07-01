# Candidates/models/candidate_visibility.py

from extensions import db
from datetime import datetime

class CandidateVisibility(db.Model):
    __tablename__ = "candidate_visibility"

    id = db.Column(db.Integer, primary_key=True)

    cand_id = db.Column(
        db.String(50),
        db.ForeignKey("candidates.cand_id", ondelete="CASCADE"),
        nullable=False
    )

    # Who added the candidate
    shared_by_email = db.Column(db.String(255), nullable=False)

    # Optional: the owner (creator) of this visibility row
    owner_id = db.Column(db.String(255), nullable=True)

    # Optional: org_id of the candidate
    org_id = db.Column(db.String(50), nullable=True)

    # Optional: team id and type
    owner_team_id = db.Column(db.String(50), nullable=True)
    owner_team_type = db.Column(db.Enum("internal", "external", name="team_type_enum"), nullable=True)

    # Visibility type
    visibility_type = db.Column(
        db.Enum(
            "private",
            "team",
            "organization",
            "teams",
            "users",
            name="candidate_visibility_type"
        ),
        nullable=False,
        default="private"
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    targets = db.relationship(
        "CandidateVisibilityTarget",
        backref="visibility",
        cascade="all, delete-orphan",
        lazy=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "cand_id": self.cand_id,
            "shared_by_email": self.shared_by_email,
            "owner_id": self.owner_id,
            "org_id": self.org_id,
            "owner_team_id": self.owner_team_id,
            "owner_team_type": self.owner_team_type,
            "visibility_type": self.visibility_type,
            "created_at": self.created_at.isoformat()
        }
