"""
Pi-Car - Vehicle Routes (OBD-II)

API endpoints for vehicle data via OBD-II.
"""

from flask import Blueprint, jsonify
from backend.services.obd_service import obd_data, get_obd_service

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
