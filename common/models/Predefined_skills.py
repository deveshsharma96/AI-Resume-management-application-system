from extensions import db
from datetime import datetime


class PredefinedSkill(db.Model):
    __tablename__ = "predefined_skills"

    id = db.Column(db.Integer, primary_key=True)

    # Display name
    name = db.Column(
        db.String(255),
        nullable=False
    )

    # Lowercase searchable name
    normalized_name = db.Column(
        db.String(255),
        nullable=False,
        index=True
    )

    # NULL = global seeded skill
    # value = org custom skill
    org_id = db.Column(
        db.String(50),
        nullable=True,
        index=True
    )

    is_active = db.Column(
        db.Boolean,
        default=True
    )

    created_by_user = db.Column(
        db.Boolean,
        default=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    # Composite uniqueness
    __table_args__ = (
        db.UniqueConstraint(
            'org_id',
            'normalized_name',
            name='uq_org_skill'
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name
        }