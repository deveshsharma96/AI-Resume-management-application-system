from extensions import db
from GlobalRecruiter.models.organization_recruiter import OrganizationRecruiter


class RecruiterRoleService:

    @staticmethod
    def has_internal_anywhere(recruiter_id):
        return OrganizationRecruiter.query.filter_by(
            recruiter_id=recruiter_id,
            recruiter_type="INTERNAL"   # ✅ FIX
        ).first() is not None

    @staticmethod
    def can_assign_internal(recruiter_id):
        existing = OrganizationRecruiter.query.filter_by(
            recruiter_id=recruiter_id,
            recruiter_type="INTERNAL"   # ✅ FIX
        ).first()
        return existing is None

    @staticmethod
    def is_internal_in_org(recruiter_id, org_id):
        mapping = OrganizationRecruiter.query.filter_by(
            recruiter_id=recruiter_id,
            org_id=org_id,
            recruiter_type="INTERNAL",   # ✅ FIX
            status="ACTIVE"
        ).first()

        return mapping is not None

    @staticmethod
    def get_active_mapping(recruiter_id, org_id):
        return OrganizationRecruiter.query.filter_by(
            recruiter_id=recruiter_id,
            org_id=org_id,
            status="ACTIVE"
        ).first()

    @staticmethod
    def create_mapping(recruiter_id, org_id, recruiter_type, status="ACTIVE"):

        existing = OrganizationRecruiter.query.filter_by(
            recruiter_id=recruiter_id,
            org_id=org_id
        ).first()

        if existing:
            # 🔥 CASE 1: Already active → block
            if existing.status == "ACTIVE":
                raise Exception("Recruiter already shared with this organization")

            # 🔥 CASE 2: Previously removed → reactivate
            if existing.status in ["DISABLED", "INVITED"]:
                existing.status = "ACTIVE"
                existing.recruiter_type = recruiter_type
                db.session.commit()
                return existing

        # 🔥 INTERNAL constraint (same as before)
        if recruiter_type == "INTERNAL":
            if not RecruiterRoleService.can_assign_internal(recruiter_id):
                raise Exception("Recruiter already has INTERNAL role elsewhere")

        mapping = OrganizationRecruiter(
            recruiter_id=recruiter_id,
            org_id=org_id,
            recruiter_type=recruiter_type,
            status=status
        )

        db.session.add(mapping)
        db.session.commit()

        return mapping