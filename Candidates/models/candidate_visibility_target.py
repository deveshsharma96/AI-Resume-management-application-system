from extensions import db

class CandidateVisibilityTarget(db.Model):
    __tablename__ = "candidate_visibility_targets"

    id = db.Column(db.Integer, primary_key=True)

    visibility_id = db.Column(
        db.Integer,
        db.ForeignKey("candidate_visibility.id", ondelete="CASCADE"),
        nullable=False
    )

    # team / user
    target_type = db.Column(
        db.Enum("team", "user", name="visibility_target_type"),
        nullable=False
    )

    # team_id OR user_email
    target_id = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "visibility_id": self.visibility_id,
            "target_type": self.target_type,
            "target_id": self.target_id
        }
