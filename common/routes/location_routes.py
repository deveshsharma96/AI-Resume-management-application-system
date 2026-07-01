from flask import Blueprint, jsonify
from common.utils.location_service import get_location_from_pincode

location_bp = Blueprint("location_bp", __name__)


@location_bp.route("/location/pincode/<country>/<pincode>", methods=["GET"])
def get_location(country, pincode):

    result = get_location_from_pincode(country, pincode)

    if not result:
        return jsonify({
            "status": "error",
            "message": "Invalid pincode or unsupported country"
        }), 400

    return jsonify({
        "status": "success",
        "data": result
    }), 200