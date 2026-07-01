from extensions import db
from datetime import datetime

class SupportTicket(db.Model):
    __tablename__ = "support_tickets"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)

    issue_type = db.Column(
        db.Enum("bug", "feedback", name="issue_type_enum"),
        nullable=False
    )

    description = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
