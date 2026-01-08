"""
Pi-Car - Rotas de Veiculo (OBD-II)

Endpoints da API para dados do veiculo via OBD-II.
"""

from flask import Blueprint, jsonify
from backend.services.obd_service import obd_data

vehicle_bp = Blueprint('vehicle', __name__)


@vehicle_bp.route('/status')
def vehicle_status():
    """Retorna dados atuais do OBD-II"""
    return jsonify(obd_data)
