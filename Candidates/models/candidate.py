from extensions import db
from datetime import datetime
import random
import string

from Candidates.models.candidate_visibility import CandidateVisibility
from common.models.document_asset import DocumentAsset



def generate_cand_id():
    """Generate an alphanumeric candidate ID like CAND12345"""
    return "CAND" + "".join(random.choices(string.digits, k=5))

# ----------------------------------------------------------------------
# ✅ Candidate Model
# ----------------------------------------------------------------------


class Candidate(db.Model):
    __tablename__ = "candidates"
    cand_id = db.Column(db.String(10), primary_key=True, default=generate_cand_id)
    primary_resume_id = db.Column(
        db.Integer,
        db.ForeignKey("resumes.id", ondelete="SET NULL"),
        nullable=True
    )



    # ---------------- Personal Details ----------------
    name = db.Column(db.String(255), nullable=False)

    # ---- Emails ----
    email = db.Column(db.String(255), nullable=False)       # Primary (Must verify)
    email_2 = db.Column(db.String(255), nullable=True)      # Optional
    email_3 = db.Column(db.String(255), nullable=True)      # Optional

    # ---- Phones ----
    phone = db.Column(db.String(20), nullable=False)        # Primary (stored, not verified)
    phone_2 = db.Column(db.String(20), nullable=True)       
    phone_3 = db.Column(db.String(20), nullable=True)       
    # ---------------- Verification Fields ----------------
    email_verified = db.Column(db.Boolean, default=False)    # MUST verify
    email2_verified = db.Column(db.Boolean, default=False)   # Optional
    email3_verified = db.Column(db.Boolean, default=False)   # Optional

    phone_verified = db.Column(db.Boolean, default=False)    # verification disabled
    phone2_verified = db.Column(db.Boolean, default=False)   # verification disabled
    phone3_verified = db.Column(db.Boolean, default=False)   # verification disabled

    """
    email_verified_at = db.Column(db.DateTime, nullable=True)
    email2_verified_at = db.Column(db.DateTime, nullable=True)
    email3_verified_at = db.Column(db.DateTime, nullable=True)

    phone_verified_at = db.Column(db.DateTime, nullable=True)
    phone2_verified_at = db.Column(db.DateTime, nullable=True)
    phone3_verified_at = db.Column(db.DateTime, nullable=True)
    """

    # ---- Address Fields ----
    current_full_address = db.Column(db.String(500), nullable=True)
    current_location = db.Column(db.JSON, nullable=True)
    current_pincode = db.Column(db.String(20), nullable=True)
    same_as_current = db.Column(db.Boolean, default=False)
    permanent_full_address = db.Column(db.String(500), nullable=True)
    permanent_location = db.Column(db.JSON, nullable=True)
    permanent_pincode = db.Column(db.String(20), nullable=True)

    linkedin = db.Column(db.String(255), nullable=True)
    portfolio = db.Column(db.String(255), nullable=True)
    github_url = db.Column(db.String(255), nullable=True)
    # ---------------- Key Skills (Form-only) ----------------
    key_skills = db.Column(db.String(255), nullable=True)
    # ---------------- Availability ----------------
    availability = db.Column(db.JSON, nullable=True)



    # ---------------- Meta Info ----------------
    org_id = db.Column(db.String(50), db.ForeignKey("organizations.org_id"), nullable=True)
    added_by = db.Column(db.String(50), nullable=False)
    added_by_team_id = db.Column(db.String(50), nullable=True)
    token = db.Column(db.String(512), nullable=True)
    status = db.Column(db.String(50), default="new")
    interview_round = db.Column(db.Integer, default=0)
    interview_sub_round = db.Column(db.Integer, default=0)
    interview_result = db.Column(db.String(50), nullable=True)

    # ---------------- Work / Resume Info ----------------
    total_experience = db.Column(db.String(50), nullable=True)
    resume_file = db.Column(db.JSON, nullable=True)
    cover_letter_file = db.Column(db.JSON, nullable=True)
    authorized_to_work = db.Column(db.Boolean, nullable=True)
    relocation = db.Column(db.String(50), nullable=True)
    declaration_consent = db.Column(db.Boolean, default=False)

    # ---------------- New Fields ----------------
    expected_package = db.Column(db.JSON, nullable=True)
    domain = db.Column(db.String(255), nullable=True)
    notice_period = db.Column(db.JSON, nullable=True)
    immediate_joiner = db.Column(db.Boolean, default=False)
    # ---------------- New Fields (NEW ADDITIONS) ----------------

    # Preferred Location (multi input / dropdown + custom typing)
    preferred_locations = db.Column(db.JSON, nullable=True)
    offer_status = db.Column(db.String(50), nullable=True)

    # Offers (max 3 offers now, used only if offer_status = has_offers)
    offers = db.Column(db.JSON, nullable=True)
    """
    Structure:
    [
    {
        "ctc": "10 LPA",
        "company": "TCS",
        "location": "Noida"
    }
    ]
    """

    notes = db.Column(db.Text, nullable=True)

    # ---------------- Blacklist ----------------
    is_blacklisted = db.Column(
        db.Boolean,
        default=False
    )

    blacklisted_at = db.Column(
        db.DateTime,
        nullable=True
    )

    blacklisted_by = db.Column(
        db.String(255),
        nullable=True
    )

    blacklist_reason = db.Column(
        db.Text,
        nullable=True
    )


    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ---------------- Relationships ----------------
    degrees = db.relationship("Degree", backref="candidate", lazy=True, cascade="all, delete-orphan")
    skills = db.relationship("Skill", backref="candidate", lazy=True, cascade="all, delete-orphan")
    work_history = db.relationship("WorkHistory", backref="candidate", lazy=True, cascade="all, delete-orphan")
    certifications = db.relationship("Certification", backref="candidate", lazy=True, cascade="all, delete-orphan")
    resumes = db.relationship(
        "Resume",
        foreign_keys="Resume.cand_id",
        back_populates="candidate",
        lazy=True,
        cascade="all, delete-orphan"
    )
    primary_resume = db.relationship(
        "Resume",
        foreign_keys=[primary_resume_id],
        uselist=False
    )


    # ---------------- Visibility ----------------
    visibility = db.relationship(
        "CandidateVisibility",
        backref="candidate",
        uselist=False,
        cascade="all, delete-orphan"
    )


    def to_dict(self):
        resume_id = None
        cover_letter_id = None

        assets = DocumentAsset.query.filter_by(
            cand_id=self.cand_id,
            is_linked=True
        ).all()

        for asset in assets:
            if asset.document_type == "resume":
                resume_id = asset.docu_id
            elif asset.document_type == "cover_letter":
                cover_letter_id = asset.docu_id
        return {
            "cand_id": self.cand_id,
            "name": self.name,

            # ---- Emails ----
            "email": self.email,
            "email_2": self.email_2 or "",
            "email_3": self.email_3 or "",
            "email_verified": self.email_verified,
            "email2_verified": self.email2_verified,
            "email3_verified": self.email3_verified,

            # ---- Phones ----
            "phone": self.phone,
            "phone_2": self.phone_2 or "",
            "phone_3": self.phone_3 or "",
            "phone_verified": self.phone_verified,
            "phone2_verified": self.phone2_verified,
            "phone3_verified": self.phone3_verified,

            # --- Address (Safe Defaults) ---
            "current_full_address": self.current_full_address or "",
            "current_location": self.current_location or {"value": "", "label": ""},
            "current_pincode": self.current_pincode or "",
            "same_as_current": self.same_as_current,
            "permanent_full_address": self.permanent_full_address or "",
            "permanent_location": self.permanent_location or {"value": "", "label": ""},
            "permanent_pincode": self.permanent_pincode or "",

            # --- Links ---
            "linkedin": self.linkedin or "",
            "portfolio": self.portfolio or "",
            "github_url": self.github_url or "",
            "resume_id": resume_id,
            "cover_letter_id": cover_letter_id,
            "preferred_locations": self.preferred_locations or [],
            "offers": self.offers or [],
            "offer_status": self.offer_status or "no_offer",
            "notes": self.notes or "",

            # --- Meta ---
            "org_id": self.org_id,
            "added_by": self.added_by,
            "added_by_team_id": self.added_by_team_id,
            "total_experience": self.total_experience or "",
            "authorized_to_work": self.authorized_to_work or False,
            "relocation": self.relocation or "",
            "declaration_consent": self.declaration_consent,

            "expected_package": self.expected_package or {"min": "", "max": ""},
            "domain": self.domain or "",
            "notice_period": self.notice_period or {
                "official": "",
                "expected": "",
                "last_working_day": ""
            },
            "immediate_joiner": self.immediate_joiner or False,
            "key_skills": self.key_skills or "",
            "availability": self.availability or [],
            "is_blacklisted": self.is_blacklisted,
            "blacklisted_at": self.blacklisted_at,
            "blacklisted_by": self.blacklisted_by,
            "blacklist_reason": self.blacklist_reason,


            "degrees": [d.to_dict() for d in self.degrees],
            "skills": [s.to_dict() for s in self.skills],
            "work_history": [w.to_dict() for w in self.work_history],
            "certifications": [c.to_dict() for c in self.certifications],
            

            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    def update_status(self, new_state):
        from Candidates.state_machine.candidate_state_machine import CandidateStateMachine
        if not CandidateStateMachine.can_transition(self.status, new_state):
            raise ValueError(f"Invalid status transition: {self.status} → {new_state}")
        self.status = new_state

# ----------------------------------------------------------------------
# ✅ Degree Model (Education) with Months
# ----------------------------------------------------------------------
class Degree(db.Model):
    __tablename__ = "degrees"
    id = db.Column(db.Integer, primary_key=True)
    cand_id = db.Column(db.String(10), db.ForeignKey("candidates.cand_id"), nullable=False)

    degree_name = db.Column(db.String(255), nullable=False)
    start_year = db.Column(db.String(10), nullable=True)
    start_month = db.Column(db.String(10), nullable=True)   # NEW
    end_year = db.Column(db.String(10), nullable=True)
    end_month = db.Column(db.String(10), nullable=True)     # NEW
    major = db.Column(db.String(255), nullable=True)
    minor = db.Column(db.String(255), nullable=True)
    score = db.Column(db.String(50), nullable=True)

    def to_dict(self):
        return {
            "degree_name": self.degree_name,
            "start_year": self.start_year,
            "start_month": self.start_month,
            "end_year": self.end_year,
            "end_month": self.end_month,
            "major": self.major,
            "minor": self.minor,
            "score": self.score
        }

# ----------------------------------------------------------------------
# ✅ WorkHistory Model with Designations and Months
# ----------------------------------------------------------------------
class WorkHistory(db.Model):
    __tablename__ = "work_history"
    id = db.Column(db.Integer, primary_key=True)
    cand_id = db.Column(db.String(10), db.ForeignKey("candidates.cand_id"), nullable=False)
    organization = db.Column(db.String(255), nullable=False)
    org_start_year = db.Column(db.String(10), nullable=True)
    org_start_month = db.Column(db.String(10), nullable=True)  # NEW
    org_end_year = db.Column(db.String(10), nullable=True)
    org_end_month = db.Column(db.String(10), nullable=True)    # NEW

    designations = db.Column(db.JSON, nullable=True)  # List of dicts with months
    # Example designations:
    # [
    #   {
    #      "designation": "Software Engineer",
    #      "start_year": "2020",
    #      "start_month": "06",
    #      "end_year": "2022",
    #      "end_month": "03",
    #      "responsibilities": "Developed APIs"
    #   }
    # ]

    def to_dict(self):
        return {
            "organization": self.organization,
            "org_start_year": self.org_start_year,
            "org_start_month": self.org_start_month,
            "org_end_year": self.org_end_year,
            "org_end_month": self.org_end_month,
            "designations": self.designations
        }


# ----------------------------------------------------------------------
# ✅ Skill Model
# ----------------------------------------------------------------------
class Skill(db.Model):
    __tablename__ = "skills"
    id = db.Column(db.Integer, primary_key=True)
    cand_id = db.Column(db.String(10), db.ForeignKey("candidates.cand_id"), nullable=True)
    skill_name = db.Column(db.String(255), nullable=True)
    skill_experience = db.Column(db.String(50), nullable=True)

    def to_dict(self):
        return {
            "skill_name": self.skill_name,
            "skill_experience": self.skill_experience
        }


# ----------------------------------------------------------------------
# ✅ Certification Model
# ----------------------------------------------------------------------
class Certification(db.Model):
    __tablename__ = "certifications"
    id = db.Column(db.Integer, primary_key=True)
    cand_id = db.Column(db.String(10), db.ForeignKey("candidates.cand_id"), nullable=False)
    certificate = db.Column(db.String(255), nullable=False)
    completion_year = db.Column(db.Integer, nullable=True)
    valid_upto = db.Column(db.Integer, nullable=True)

    def to_dict(self):
        return {
            "certificate": self.certificate,
            "completion_year": self.completion_year,
            "valid_upto": self.valid_upto
        }
