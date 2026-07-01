"""
from extensions import db
from sqlalchemy import or_, and_
from GlobalRecruiter.models.recruiters import GlobalRecruiter
from GlobalRecruiter.models.organization_recruiter import OrganizationRecruiter
from GlobalRecruiter.models.organization_collaboration import OrganizationCollaboration
from GlobalRecruiter.services.recruiter_role_service import RecruiterRoleService


class RecruiterSharingService:

    # --------------------------------------------------
    # 1️⃣ CREATE COLLABORATION
    # --------------------------------------------------
    @staticmethod
    def create_collaboration(source_org, target_org):

        existing = OrganizationCollaboration.query.filter(
            or_(
                and_(
                    OrganizationCollaboration.source_org_id == source_org,
                    OrganizationCollaboration.target_org_id == target_org
                ),
                and_(
                    OrganizationCollaboration.source_org_id == target_org,
                    OrganizationCollaboration.target_org_id == source_org
                )
            )
        ).first()

        if existing:
            raise Exception("Collaboration already exists")

        collab = OrganizationCollaboration(
            source_org_id=source_org,
            target_org_id=target_org,
            status="PENDING"
        )

        db.session.add(collab)
        db.session.commit()

        return collab


    # --------------------------------------------------
    # 2️⃣ ACCEPT
    # --------------------------------------------------
    @staticmethod
    def accept_collaboration(source_org, target_org):

        collab = OrganizationCollaboration.query.filter_by(
            source_org_id=source_org,
            target_org_id=target_org
        ).first()

        if not collab:
            raise Exception("Collaboration not found")

        collab.status = "ACCEPTED"
        db.session.commit()

        return collab


    # --------------------------------------------------
    # 3️⃣ REJECT
    # --------------------------------------------------
    @staticmethod
    def reject_collaboration(source_org, target_org):

        collab = OrganizationCollaboration.query.filter_by(
            source_org_id=source_org,
            target_org_id=target_org,
            status="PENDING"
        ).first()

        if not collab:
            raise Exception("No pending collaboration found")

        collab.status = "REJECTED"
        db.session.commit()

        return collab


    # --------------------------------------------------
    # 4️⃣ CANCEL
    # --------------------------------------------------
    @staticmethod
    def cancel_collaboration(source_org, target_org):

        collab = OrganizationCollaboration.query.filter_by(
            source_org_id=source_org,
            target_org_id=target_org,
            status="PENDING"
        ).first()

        if not collab:
            raise Exception("No pending request found to cancel")

        collab.status = "CANCELLED"
        db.session.commit()

        return collab


    # --------------------------------------------------
    # 5️⃣ SHARE RECRUITER
    # --------------------------------------------------
    @staticmethod
    def share_internal_recruiter(recruiter_id, source_org, target_org):

        if source_org == target_org:
            raise Exception("Cannot share recruiter within same organization")

        recruiter = GlobalRecruiter.query.get(recruiter_id)
        if not recruiter:
            raise Exception("Recruiter not found")

        if not RecruiterRoleService.is_internal_in_org(recruiter_id, source_org):
            raise Exception("Recruiter is not INTERNAL in source organization")

        collab = OrganizationCollaboration.query.filter_by(
            source_org_id=source_org,
            target_org_id=target_org,
            status="ACCEPTED"
        ).first()

        if not collab:
            raise Exception("No accepted collaboration found")

        existing = OrganizationRecruiter.query.filter_by(
            recruiter_id=recruiter_id,
            org_id=target_org
        ).first()

        if existing:
            raise Exception("Recruiter already mapped to target organization")

        return RecruiterRoleService.create_mapping(
            recruiter_id=recruiter_id,
            org_id=target_org,
            role="EXTERNAL",
            status="ACTIVE"
        )


    # --------------------------------------------------
    # 6️⃣ INCOMING REQUESTS
    # --------------------------------------------------
    @staticmethod
    def get_incoming(org_id):

        records = OrganizationCollaboration.query.filter_by(
            target_org_id=org_id,
            status="PENDING"
        ).all()

        return [
            {
                "source_org": r.source_org_id,
                "status": r.status,
                "created_at": str(r.created_at)
            }
            for r in records
        ]


    # --------------------------------------------------
    # 7️⃣ OUTGOING REQUESTS
    # --------------------------------------------------
    @staticmethod
    def get_outgoing(org_id):

        records = OrganizationCollaboration.query.filter_by(
            source_org_id=org_id
        ).all()

        return [
            {
                "target_org": r.target_org_id,
                "status": r.status,
                "created_at": str(r.created_at)
            }
            for r in records
        ]


    # --------------------------------------------------
    # 8️⃣ ACTIVE COLLABORATIONS
    # --------------------------------------------------
    @staticmethod
    def get_active(org_id):

        records = OrganizationCollaboration.query.filter(
            or_(
                OrganizationCollaboration.source_org_id == org_id,
                OrganizationCollaboration.target_org_id == org_id
            ),
            OrganizationCollaboration.status == "ACCEPTED"
        ).all()

        result = []

        for r in records:
            other_org = r.target_org_id if r.source_org_id == org_id else r.source_org_id

            result.append({
                "org_id": other_org,
                "status": "ACTIVE",
                "created_at": str(r.created_at)
            })

        return result


    # --------------------------------------------------
    # 9️⃣ SHARED RECRUITERS
    # --------------------------------------------------
    @staticmethod
    def get_shared_recruiters(org_id):

        mappings = OrganizationRecruiter.query.filter_by(
            org_id=org_id,
            role="EXTERNAL",
            status="ACTIVE"
        ).all()

        result = []

        for m in mappings:
            recruiter = GlobalRecruiter.query.get(m.recruiter_id)

            result.append({
                "recruiter_id": recruiter.recruiter_id,
                "name": recruiter.name,
                "email": recruiter.email
            })

        return result
        """

from extensions import db
from sqlalchemy import or_, and_
from GlobalRecruiter.models.recruiters import GlobalRecruiter
from GlobalRecruiter.models.organization_recruiter import OrganizationRecruiter
from GlobalRecruiter.models.organization_collaboration import OrganizationCollaboration
from GlobalRecruiter.services.recruiter_role_service import RecruiterRoleService
from Organization.models.organization import Organization


class RecruiterSharingService:

    @staticmethod
    def create_collaboration(source_org, target_org):

        existing = OrganizationCollaboration.query.filter(
            or_(
                and_(
                    OrganizationCollaboration.source_org_id == source_org,
                    OrganizationCollaboration.target_org_id == target_org
                ),
                and_(
                    OrganizationCollaboration.source_org_id == target_org,
                    OrganizationCollaboration.target_org_id == source_org
                )
            )
        ).first()

        # ✅ If exists, handle based on status
        if existing:

            # ❌ Block if active
            if existing.status in ["PENDING", "ACCEPTED"]:
                raise Exception("Collaboration already exists")

            # ✅ If rejected or cancelled → delete old record
            if existing.status in ["REJECTED", "CANCELLED"]:
                db.session.delete(existing)
                db.session.commit()

        # ✅ Create fresh collaboration
        collab = OrganizationCollaboration(
            source_org_id=source_org,
            target_org_id=target_org,
            status="PENDING"
        )

        db.session.add(collab)
        db.session.commit()

        return collab

    # --------------------------------------------------
    # ACCEPT BY ORG (FIX)
    # --------------------------------------------------
    @staticmethod
    def accept_collaboration_by_org(source_org, target_org):

        collab = OrganizationCollaboration.query.filter_by(
            source_org_id=source_org,
            target_org_id=target_org
        ).first()

        if not collab:
            raise Exception("Collaboration not found")

        collab.status = "ACCEPTED"
        db.session.commit()

        return collab


    # --------------------------------------------------
    # REJECT BY ORG (FIX)
    # --------------------------------------------------
    from sqlalchemy import or_, and_

    @staticmethod
    def reject_collaboration_by_org(source_org, target_org):

        collab = OrganizationCollaboration.query.filter(
            or_(
                and_(
                    OrganizationCollaboration.source_org_id == source_org,
                    OrganizationCollaboration.target_org_id == target_org
                ),
                and_(
                    OrganizationCollaboration.source_org_id == target_org,
                    OrganizationCollaboration.target_org_id == source_org
                )
            )
        ).first()

        if not collab:
            raise Exception("Collaboration not found")

        if collab.status != "PENDING":
            raise Exception(f"Cannot reject collaboration with status {collab.status}")

        collab.status = "REJECTED"
        db.session.commit()

        return collab
    
    # --------------------------------------------------
    # CANCEL BY ORG (FIX)
    # --------------------------------------------------
    @staticmethod
    def cancel_collaboration_by_org(source_org, target_org):

        collab = OrganizationCollaboration.query.filter(
            or_(
                and_(
                    OrganizationCollaboration.source_org_id == source_org,
                    OrganizationCollaboration.target_org_id == target_org
                ),
                and_(
                    OrganizationCollaboration.source_org_id == target_org,
                    OrganizationCollaboration.target_org_id == source_org
                )
            )
        ).first()

        if not collab:
            raise Exception("Collaboration not found")

        if collab.status == "PENDING":
            collab.status = "CANCELLED"
            db.session.commit()
            return collab

        elif collab.status == "ACCEPTED":
            db.session.delete(collab)
            db.session.commit()
            return {"message": "Collaboration deleted"}

        else:
            raise Exception(f"Cannot cancel collaboration with status {collab.status}")

    @staticmethod
    def share_internal_recruiter(recruiter_id, source_org, target_org):

        if source_org == target_org:
            raise Exception("Cannot share recruiter within same organization")

        recruiter = GlobalRecruiter.query.get(recruiter_id)
        if not recruiter:
            raise Exception("Recruiter not found")

        # ✅ Check INTERNAL in target org (correct)
        if not RecruiterRoleService.is_internal_in_org(recruiter_id, target_org):
            raise Exception("Recruiter is not INTERNAL in target organization")

        collab = OrganizationCollaboration.query.filter(
            or_(
                and_(
                    OrganizationCollaboration.source_org_id == source_org,
                    OrganizationCollaboration.target_org_id == target_org
                ),
                and_(
                    OrganizationCollaboration.source_org_id == target_org,
                    OrganizationCollaboration.target_org_id == source_org
                )
            ),
            OrganizationCollaboration.status == "ACCEPTED"
        ).first()

        if not collab:
            raise Exception("No accepted collaboration found")

        # ✅ FIX 1: check in source_org (NOT target_org)
        existing = OrganizationRecruiter.query.filter_by(
            recruiter_id=recruiter_id,
            org_id=source_org
        ).first()

        if existing:
            # 🔥 already active → block
            if existing.status == "ACTIVE":
                raise Exception("Recruiter already shared with this organization")

            # 🔥 previously removed → reactivate
            if existing.status in ["DISABLED", "INVITED"]:
                existing.status = "ACTIVE"
                existing.recruiter_type = "EXTERNAL"
                db.session.commit()
                return existing

        # ✅ FIX 2: create mapping in source_org (NOT target_org)
        return RecruiterRoleService.create_mapping(
            recruiter_id=recruiter_id,
            org_id=source_org,
            recruiter_type="EXTERNAL",
            status="ACTIVE"
        )

    # --------------------------------------------------
    # 6️⃣ INCOMING REQUESTS (UPDATED)
    # --------------------------------------------------
    @staticmethod
    def get_incoming(org_id):

        records = OrganizationCollaboration.query.filter_by(
            target_org_id=org_id,
            status="PENDING"
        ).all()

        result = []

        for r in records:
            source_org = Organization.query.get(r.source_org_id)

            result.append({
                "collaboration_id": r.id,
                "source_org_id": r.source_org_id,
                "source_org_name": source_org.org_name if source_org else None,
                "status": r.status,
                "created_at": str(r.created_at)
            })

        return result


    # --------------------------------------------------
    # 7️⃣ OUTGOING REQUESTS (UPDATED)
    # --------------------------------------------------
    @staticmethod
    def get_outgoing(org_id):

        records = OrganizationCollaboration.query.filter_by(
            source_org_id=org_id
        ).all()

        result = []

        for r in records:
            target_org = Organization.query.get(r.target_org_id)

            result.append({
                "collaboration_id": r.id,
                "target_org_id": r.target_org_id,
                "target_org_name": target_org.org_name if target_org else None,
                "status": r.status,
                "created_at": str(r.created_at)
            })

        return result


    # --------------------------------------------------
    # 8️⃣ ACTIVE COLLABORATIONS (UPDATED)
    # --------------------------------------------------
    @staticmethod
    def get_active(org_id):

        records = OrganizationCollaboration.query.filter(
            or_(
                OrganizationCollaboration.source_org_id == org_id,
                OrganizationCollaboration.target_org_id == org_id
            ),
            OrganizationCollaboration.status == "ACCEPTED"
        ).all()

        result = []

        for r in records:
            other_org = r.target_org_id if r.source_org_id == org_id else r.source_org_id

            result.append({
                "collaboration_id": r.id,   # ✅ added
                "org_id": other_org,
                "status": "ACTIVE",
                "created_at": str(r.created_at)
            })

        return result


    # --------------------------------------------------
    # 9️⃣ SHARED RECRUITERS (NO CHANGE)
    # --------------------------------------------------
    @staticmethod
    def get_shared_recruiters(org_id):

        mappings = OrganizationRecruiter.query.filter_by(
            org_id=org_id,
            recruiter_type="EXTERNAL",
            status="ACTIVE"
        ).all()

        result = []

        for m in mappings:

            # 🔥 Check if this recruiter is INTERNAL in some OTHER org
            internal_mapping = OrganizationRecruiter.query.filter(
                OrganizationRecruiter.recruiter_id == m.recruiter_id,
                OrganizationRecruiter.org_id != org_id,
                OrganizationRecruiter.recruiter_type == "INTERNAL",
                OrganizationRecruiter.status == "ACTIVE"
            ).first()

            # ❌ Skip local external recruiters (form-created)
            if not internal_mapping:
                continue

            recruiter = GlobalRecruiter.query.get(m.recruiter_id)

            if not recruiter:
                continue

            result.append({
                "recruiter_id": recruiter.recruiter_id,
                "name": recruiter.name,
                "email": recruiter.email
            })

        return result
    


    # --------------------------------------------------
    # 🔟 ALL COLLABORATIONS (NEW)
    # --------------------------------------------------
    @staticmethod
    def get_collaborations(org_id):

        records = OrganizationCollaboration.query.filter(
            or_(
                OrganizationCollaboration.source_org_id == org_id,
                OrganizationCollaboration.target_org_id == org_id
            )
        ).all()

        result = []

        for r in records:

            source_org = Organization.query.get(r.source_org_id)
            target_org = Organization.query.get(r.target_org_id)

            result.append({
                "collaboration_id": r.id,
                "source_org_id": r.source_org_id,
                "source_org_name": source_org.org_name if source_org else None,
                "target_org_id": r.target_org_id,
                "target_org_name": target_org.org_name if target_org else None,
                "status": r.status,
                "created_at": str(r.created_at)
            })

        return result