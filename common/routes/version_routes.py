from flask import Blueprint, jsonify
from common.utils.version import APP_VERSION, BUILD_VERSION

version_bp = Blueprint("version_bp", __name__)

@version_bp.route("/version", methods=["GET"])
def get_version():
    return jsonify({
        "app_version": APP_VERSION,
        "build_version": BUILD_VERSION
    }), 200



