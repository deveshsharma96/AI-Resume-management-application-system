# Organization/models/team_member.py

from extensions import db
from datetime import datetime

class TeamMember(db.Model):
    __tablename__ = "team_members"

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.String(50), db.ForeignKey("teams.team_id"), nullable=False)
    recruiter_id = db.Column(db.String(50), nullable=True)

    user_email = db.Column(db.String(255), nullable=False)
    user_name = db.Column(db.String(255), nullable=False)
    user_role = db.Column(db.String(50), nullable=False)  

    recruiter_type = db.Column(
        db.Enum("INTERNAL", "EXTERNAL", name="team_member_recruiter_type_enum"),
        nullable=True
    )


    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "team_id": self.team_id,
            "user_email": self.user_email,
            "user_role": self.user_role,
            "user_name": self.user_name, 
            "added_at": self.added_at.isoformat()
        }
