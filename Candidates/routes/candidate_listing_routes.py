"""

from flask import Blueprint, jsonify, request, g
from auth.utils.jwt_required import jwt_required
from Candidates.models.candidate import Candidate
from Candidates.utils.visibility_query import get_visible_candidates_query


candidate_listing_bp = Blueprint(
    "candidate_listing_bp",
    __name__,
    url_prefix="/api/candidates"
)


# ---------------- Helper: Get current user ----------------
def get_current_user():
    if not hasattr(g, "current_user"):
        return None
    return g.current_user


@candidate_listing_bp.route("", methods=["GET"])
@jwt_required
def list_candidates():

    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    # 🔐 org from JWT
    org_id = current_user["org_id"]

    # 🔐 Visibility-aware base query
    query = get_visible_candidates_query(current_user, org_id)

    # 🔍 Search
    search = request.args.get("search")
    if search:
        like = f"%{search}%"
        query = query.filter(
            (Candidate.name.ilike(like)) |
            (Candidate.email.ilike(like)) |
            (Candidate.phone.ilike(like)) |
            (Candidate.cand_id.ilike(like))
        )

    # 🎯 Filters
    status = request.args.get("status")
    if status:
        query = query.filter(Candidate.status == status)

    domain = request.args.get("domain")
    if domain:
        query = query.filter(Candidate.domain == domain)

    # 📄 Pagination
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 10))

    total = query.count()

    candidates = (
        query
        .order_by(Candidate.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return jsonify({
        "status": "success",
        "total": total,
        "page": page,
        "limit": limit,
        "data": [c.to_dict() for c in candidates]
    }), 200


    """

from flask import Blueprint, jsonify, request, g
from auth.utils.jwt_required import jwt_required
from Candidates.models.candidate import Candidate
from Candidates.utils.visibility_query import get_visible_candidates_query
from GlobalRecruiter.models.organization_recruiter import OrganizationRecruiter


candidate_listing_bp = Blueprint(
    "candidate_listing_bp",
    __name__,
    url_prefix="/api/candidates"
)


# ---------------- Helper: Get current user ----------------
def get_current_user():
    if not hasattr(g, "current_user"):
        return None
    return g.current_user


@candidate_listing_bp.route("", methods=["GET"])
@jwt_required
def list_candidates():

    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    source_org_id = current_user["org_id"]
    user_email = current_user["user_id"]

    # ---------------------------------------------------
    # ✅ STEP 1: GET ALL ACCESSIBLE ORGS
    # ---------------------------------------------------
    org_ids = [source_org_id]

    org_links = OrganizationRecruiter.query.filter_by(
        recruiter_email=user_email
    ).all()

    for link in org_links:
        if link.org_id not in org_ids:
            org_ids.append(link.org_id)

    # ---------------------------------------------------
    # ✅ STEP 2: BUILD COMBINED QUERY
    # ---------------------------------------------------
    queries = [
        get_visible_candidates_query(current_user, org_id)
        for org_id in org_ids
    ]

    # combine queries safely
    query = queries[0]
    for q in queries[1:]:
        query = query.union(q)

    # ---------------------------------------------------
    # 🔍 Search
    # ---------------------------------------------------
    search = request.args.get("search")
    if search:
        like = f"%{search}%"
        query = query.filter(
            (Candidate.name.ilike(like)) |
            (Candidate.email.ilike(like)) |
            (Candidate.phone.ilike(like)) |
            (Candidate.cand_id.ilike(like))
        )

    # ---------------------------------------------------
    # 🎯 Filters
    # ---------------------------------------------------
    status = request.args.get("status")
    if status:
        query = query.filter(Candidate.status == status)

    domain = request.args.get("domain")
    if domain:
        query = query.filter(Candidate.domain == domain)

    # ---------------------------------------------------
    # 📄 Pagination
    # ---------------------------------------------------
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 10))

    total = query.count()

    candidates = (
        query
        .order_by(Candidate.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return jsonify({
        "status": "success",
        "total": total,
        "page": page,
        "limit": limit,
        "data": [c.to_dict() for c in candidates]
    }), 200