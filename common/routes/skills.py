"""
from flask import Blueprint, jsonify, request
from common.models.Predefined_skills import PredefinedSkill
from sqlalchemy import case
from extensions import db
skill_bp = Blueprint("skills", __name__)

@skill_bp.route("/skills/predefined", methods=["GET"])
def get_predefined_skills():
    skills = PredefinedSkill.query.filter_by(is_active=True)\
        .order_by(PredefinedSkill.name.asc()).all()

    return jsonify([
        {
            "id": skill.id,
            "name": skill.name
        }
        for skill in skills
    ])


# ----------------------------------------------------
# SEARCH SKILLS (Autocomplete)
# ----------------------------------------------------
@skill_bp.route("/skills/search", methods=["GET"])
def search_skills():
    query = request.args.get("q", "").strip()

    # ✅ If empty → return top 10 skills
    if not query:
        skills = PredefinedSkill.query.filter_by(is_active=True)\
            .order_by(PredefinedSkill.name.asc())\
            .limit(10).all()

        return jsonify([
            {
                "id": skill.id,
                "name": skill.name
            }
            for skill in skills
        ]), 200

    try:
        q_lower = query.lower()

        skills = PredefinedSkill.query.filter(
            PredefinedSkill.is_active == True,
            PredefinedSkill.name.ilike(f"%{q_lower}%")
        ).order_by(
            # ✅ Prioritize starts-with matches
            case(
                (PredefinedSkill.name.ilike(f"{q_lower}%"), 0),
                else_=1
            ),
            PredefinedSkill.name.asc()
        ).limit(10).all()

        return jsonify([
            {
                "id": skill.id,
                "name": skill.name
            }
            for skill in skills
        ]), 200

    except Exception as e:
        return jsonify({
            "error": "Failed to search skills",
            "details": str(e)
        }), 500
    




# ----------------------------------------------------
# CREATE OR GET SKILL
# ----------------------------------------------------

@skill_bp.route("/skills/create-or-get", methods=["POST"])
def create_or_get_skill():

    try:

        data = request.get_json(force=True)

        if not isinstance(data, dict):

            return jsonify({
                "error": "Invalid JSON payload"
            }), 400

        skill_name = data.get("name", "").strip()


        # ------------------------------------------------
        # Validation
        # ------------------------------------------------

        if not skill_name:

            return jsonify({
                "error": "Skill name is required"
            }), 400

        if len(skill_name) < 2:

            return jsonify({
                "error": "Skill name too short"
            }), 400

        # ------------------------------------------------
        # Normalize
        # ------------------------------------------------

        normalized_name = skill_name.lower()

        # ------------------------------------------------
        # Check existing
        # ------------------------------------------------

        existing_skill = PredefinedSkill.query.filter_by(
            normalized_name=normalized_name
        ).first()

        if existing_skill:

            return jsonify({
                "id": existing_skill.id,
                "name": existing_skill.name,
                "created": False
            }), 200

        # ------------------------------------------------
        # Create new skill
        # ------------------------------------------------

        new_skill = PredefinedSkill(
            name=skill_name,
            normalized_name=normalized_name,
            is_active=True,
            created_by_user=True
        )

        db.session.add(new_skill)

        db.session.commit()

        return jsonify({
            "id": new_skill.id,
            "name": new_skill.name,
            "created": True
        }), 201

    except Exception as e:

        db.session.rollback()

        return jsonify({
            "error": "Failed to create skill",
            "details": str(e)
        }), 500



"""



from flask import Blueprint, jsonify, request
from common.models.Predefined_skills import PredefinedSkill
from sqlalchemy import case, or_
from extensions import db

skill_bp = Blueprint("skills", __name__)


# ----------------------------------------------------
# GET ALL PREDEFINED SKILLS
# ----------------------------------------------------

@skill_bp.route("/skills/predefined", methods=["GET"])
def get_predefined_skills():

    current_org_id = request.headers.get("X-Org-Id")

    skills = PredefinedSkill.query.filter(

        PredefinedSkill.is_active == True,

        or_(
            PredefinedSkill.org_id == current_org_id,
            PredefinedSkill.org_id.is_(None)
        )

    ).order_by(
        PredefinedSkill.name.asc()
    ).all()

    return jsonify([
        {
            "id": skill.id,
            "name": skill.name
        }
        for skill in skills
    ])


# ----------------------------------------------------
# SEARCH SKILLS (Autocomplete)
# ----------------------------------------------------

@skill_bp.route("/skills/search", methods=["GET"])
def search_skills():

    current_org_id = request.headers.get("X-Org-Id")

    query = request.args.get("q", "").strip()

    # ------------------------------------------------
    # If empty -> return top 10 skills
    # ------------------------------------------------

    if not query:

        skills = PredefinedSkill.query.filter(

            PredefinedSkill.is_active == True,

            or_(
                PredefinedSkill.org_id == current_org_id,
                PredefinedSkill.org_id.is_(None)
            )

        ).order_by(
            PredefinedSkill.name.asc()
        ).limit(10).all()

        return jsonify([
            {
                "id": skill.id,
                "name": skill.name
            }
            for skill in skills
        ]), 200

    try:

        q_lower = query.lower()

        skills = PredefinedSkill.query.filter(

            PredefinedSkill.is_active == True,

            or_(
                PredefinedSkill.org_id == current_org_id,
                PredefinedSkill.org_id.is_(None)
            ),

            PredefinedSkill.normalized_name.ilike(
                f"%{q_lower}%"
            )

        ).order_by(

            # Prioritize starts-with matches
            case(
                (
                    PredefinedSkill.normalized_name.ilike(
                        f"{q_lower}%"
                    ),
                    0
                ),
                else_=1
            ),

            PredefinedSkill.normalized_name.asc()

        ).limit(10).all()

        return jsonify([
            {
                "id": skill.id,
                "name": skill.name
            }
            for skill in skills
        ]), 200

    except Exception as e:

        return jsonify({
            "error": "Failed to search skills",
            "details": str(e)
        }), 500


# ----------------------------------------------------
# CREATE OR GET SKILL
# ----------------------------------------------------

@skill_bp.route("/skills/create-or-get", methods=["POST"])
def create_or_get_skill():

    try:

        current_org_id = request.headers.get("X-Org-Id")

        data = request.get_json(force=True)

        # ------------------------------------------------
        # Handle double encoded JSON
        # ------------------------------------------------

        if isinstance(data, str):

            import json

            data = json.loads(data)

        if not isinstance(data, dict):

            return jsonify({
                "error": "Invalid JSON payload"
            }), 400

        skill_name = data.get("name", "").strip()

        # ------------------------------------------------
        # Validation
        # ------------------------------------------------

        if not skill_name:

            return jsonify({
                "error": "Skill name is required"
            }), 400

        if len(skill_name) < 2:

            return jsonify({
                "error": "Skill name too short"
            }), 400

        # ------------------------------------------------
        # Normalize
        # ------------------------------------------------

        normalized_name = skill_name.lower()

        # ------------------------------------------------
        # Check existing in SAME ORG ONLY
        # ------------------------------------------------

        existing_skill = PredefinedSkill.query.filter_by(
            normalized_name=normalized_name,
            org_id=current_org_id
        ).first()

        if existing_skill:

            return jsonify({
                "id": existing_skill.id,
                "name": existing_skill.name,
                "created": False
            }), 200

        # ------------------------------------------------
        # Create new org skill
        # ------------------------------------------------

        new_skill = PredefinedSkill(
            name=skill_name,
            normalized_name=normalized_name,
            org_id=current_org_id,
            is_active=True,
            created_by_user=True
        )

        db.session.add(new_skill)

        db.session.commit()

        return jsonify({
            "id": new_skill.id,
            "name": new_skill.name,
            "created": True
        }), 201

    except Exception as e:

        db.session.rollback()

        return jsonify({
            "error": "Failed to create skill",
            "details": str(e)
        }), 500