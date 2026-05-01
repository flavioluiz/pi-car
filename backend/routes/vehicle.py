"""
Pi-Car - Vehicle Routes (OBD-II)

API endpoints for vehicle data via OBD-II.
"""

from flask import Blueprint, jsonify, request
from backend.services.obd_service import get_obd_service

vehicle_bp = Blueprint('vehicle', __name__)


@vehicle_bp.route('/status')
def vehicle_status():
    """Returns current OBD-II data including all available metrics."""
    service = get_obd_service()
    return jsonify(service.get_status())


@vehicle_bp.route('/supported')
def vehicle_supported():
    """Returns list of supported OBD-II commands for this vehicle."""
    service = get_obd_service()
    return jsonify({
        'supported_commands': service.get_supported_commands()
    })


@vehicle_bp.route('/settings', methods=['POST'])
def vehicle_settings():
    """Updates runtime OBD visualization settings."""
    service = get_obd_service()
    return jsonify(service.update_settings(request.get_json(silent=True) or {}))


@vehicle_bp.route('/trip/reset', methods=['POST'])
def vehicle_trip_reset():
    """Resets OBD trip fuel/distance accumulators."""
    service = get_obd_service()
    service.reset_trip()
    return jsonify(service.get_status())
