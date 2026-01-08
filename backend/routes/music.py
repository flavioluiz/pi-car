"""
Pi-Car - Rotas de Musica

Endpoints da API para controle de musica via MPD.
"""

from flask import Blueprint, jsonify, request
from backend.services.mpd_service import MPDService

music_bp = Blueprint('music', __name__)
mpd_service = MPDService()


@music_bp.route('/<action>')
def music_control(action):
    """Controle do player de musica"""
    result = mpd_service.control(action)
    if 'error' in result:
        return jsonify(result), 500
    return jsonify(result)


@music_bp.route('/add', methods=['POST'])
def music_add():
    """Adiciona musica a playlist"""
    data = request.json
    uri = data.get('uri') if data else None
    result = mpd_service.add_to_playlist(uri)
    if 'error' in result:
        return jsonify(result), 500
    return jsonify(result)


@music_bp.route('/playlist')
def music_playlist():
    """Retorna playlist atual"""
    result = mpd_service.get_playlist()
    if isinstance(result, dict) and 'error' in result:
        return jsonify(result), 500
    return jsonify(result)


@music_bp.route('/library')
def music_library():
    """Retorna biblioteca de musicas"""
    result = mpd_service.get_library()
    if isinstance(result, dict) and 'error' in result:
        return jsonify(result), 500
    return jsonify(result)
