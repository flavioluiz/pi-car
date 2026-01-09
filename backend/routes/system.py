"""
Pi-Car - Rotas de Sistema

Endpoints da API para status geral e lancamento de apps.
"""

import subprocess
from flask import Blueprint, jsonify
from backend.services.mpd_service import MPDService, music_data
from backend.services.gps_service import gps_data
from backend.services.obd_service import obd_data
from backend.services.rtlsdr_service import radio_data

system_bp = Blueprint('system', __name__)
mpd_service = MPDService()  # Usado para status e rotas de compatibilidade


@system_bp.route('/status')
def api_status():
    """Retorna todos os dados do veiculo"""
    # Atualiza dados de musica (GPS e OBD sao atualizados por threads)
    mpd_service.get_status()

    return jsonify({
        'gps': gps_data,
        'obd': obd_data,
        'music': music_data,
        'radio': radio_data
    })


@system_bp.route('/launch/<app_name>')
def launch_app(app_name):
    """Lanca aplicativos externos"""
    apps = {
        'navit': 'navit',
        'gqrx': 'gqrx',
        'terminal': 'lxterminal'
    }

    if app_name in apps:
        try:
            subprocess.Popen(
                [apps[app_name]],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'App nao encontrado'}), 404


@system_bp.route('/playlist')
def api_playlist():
    """Retorna playlist atual (compatibilidade com API original)"""
    result = mpd_service.get_playlist()
    if isinstance(result, dict) and 'error' in result:
        return jsonify(result), 500
    return jsonify(result)


@system_bp.route('/library')
def api_library():
    """Retorna biblioteca de musicas (compatibilidade com API original)"""
    result = mpd_service.get_library()
    if isinstance(result, dict) and 'error' in result:
        return jsonify(result), 500
    return jsonify(result)
