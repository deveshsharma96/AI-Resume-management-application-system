#New default setting for share candiate


from extensions import db


class RecruiterDefaultShareTarget(db.Model):

    __tablename__ = "recruiter_default_share_targets"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    recruiter_email = db.Column(
        db.String(255),
        nullable=False
    )

    target_type = db.Column(
        db.String(50),
        nullable=False
    )

    target_value = db.Column(
        db.String(255),
        nullable=False
    )

    share_mode = db.Column(
        db.String(50),
        nullable=False,
        default="FUTURE_CANDIDATES"
    )