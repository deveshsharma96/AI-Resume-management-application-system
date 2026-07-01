from extensions import db


class JobVisibilityTarget(db.Model):
    __tablename__ = "job_visibility_target"

    id = db.Column(db.Integer, primary_key=True)

    visibility_id = db.Column(
        db.Integer,
        db.ForeignKey("job_visibility.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # user / team
    target_type = db.Column(db.String(20), nullable=False)

    # email (for user) or team_id
    target_id = db.Column(db.String(100), nullable=False)

    created_at = db.Column(db.DateTime, server_default=db.func.now())
