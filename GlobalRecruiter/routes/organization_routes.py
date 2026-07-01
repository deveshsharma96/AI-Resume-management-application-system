from flask import Blueprint, request, jsonify
from Organization.models.organization import Organization
from sqlalchemy import func

# ✅ New Blueprint (important name change)
organization_v2_bp = Blueprint("organization_v2_bp", __name__)


# --------------------------------------------------
# 🔍 SEARCH ORGANIZATION (V2)
# --------------------------------------------------
@organization_v2_bp.route("/v2/org/search", methods=["GET", "OPTIONS"])
def search_organization():

    # ✅ Handle preflight (CORS)
    if request.method == "OPTIONS":
        return "", 200

    query = request.args.get("q", "").strip()

    if not query:
        return jsonify([]), 200

    try:
        orgs = Organization.query.filter(
            func.lower(Organization.org_name).like(f"%{query.lower()}%")
        ).limit(20).all()

        return jsonify([
            {
                "org_id": org.org_id,
                "org_name": org.org_name
            }
            for org in orgs
        ]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

