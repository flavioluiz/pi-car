"""
Pi-Car - Rotas de GPS

Endpoints da API para dados de GPS.
"""

from flask import Blueprint, jsonify
from backend.services.gps_service import gps_data

gps_bp = Blueprint('gps', __name__)


@gps_bp.route('/status')
def gps_status():
    """Retorna dados atuais do GPS"""
    return jsonify(gps_data)
