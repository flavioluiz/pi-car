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


@music_bp.route('/search')
def music_search():
    """Busca musicas por titulo, artista ou album"""
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    result = mpd_service.search(query)
    if isinstance(result, dict) and 'error' in result:
        return jsonify(result), 500
    return jsonify(result)


@music_bp.route('/artists')
def music_artists():
    """Lista todos os artistas"""
    result = mpd_service.list_artists()
    if isinstance(result, dict) and 'error' in result:
        return jsonify(result), 500
    return jsonify(result)


@music_bp.route('/artist/<path:name>')
def music_by_artist(name):
    """Lista musicas de um artista"""
    result = mpd_service.list_by_artist(name)
    if isinstance(result, dict) and 'error' in result:
        return jsonify(result), 500
    return jsonify(result)


@music_bp.route('/playlists')
def music_playlists():
    """Lista playlists salvas"""
    result = mpd_service.list_playlists()
    if isinstance(result, dict) and 'error' in result:
        return jsonify(result), 500
    return jsonify(result)


@music_bp.route('/playlists/<path:name>/load', methods=['POST'])
def music_load_playlist(name):
    """Carrega uma playlist salva"""
    result = mpd_service.load_playlist(name)
    if 'error' in result:
        return jsonify(result), 500
    return jsonify(result)


@music_bp.route('/playlists/<path:name>/save', methods=['POST'])
def music_save_playlist(name):
    """Salva a fila atual como playlist"""
    result = mpd_service.save_playlist(name)
    if 'error' in result:
        return jsonify(result), 500
    return jsonify(result)


@music_bp.route('/shuffle', methods=['POST'])
def music_shuffle():
    """Toggle modo shuffle"""
    result = mpd_service.toggle_random()
    if 'error' in result:
        return jsonify(result), 500
    return jsonify(result)


@music_bp.route('/repeat', methods=['POST'])
def music_repeat():
    """Toggle modo repeat"""
    result = mpd_service.toggle_repeat()
    if 'error' in result:
        return jsonify(result), 500
    return jsonify(result)


@music_bp.route('/play/<int:pos>', methods=['POST'])
def music_play_pos(pos):
    """Toca musica na posicao especifica da fila"""
    result = mpd_service.play_pos(pos)
    if 'error' in result:
        return jsonify(result), 500
    return jsonify(result)


@music_bp.route('/clear', methods=['POST'])
def music_clear():
    """Limpa a fila atual"""
    result = mpd_service.clear_queue()
    if 'error' in result:
        return jsonify(result), 500
    return jsonify(result)


@music_bp.route('/remove/<int:pos>', methods=['POST'])
def music_remove(pos):
    """Remove musica da fila pela posicao"""
    result = mpd_service.remove_from_queue(pos)
    if 'error' in result:
        return jsonify(result), 500
    return jsonify(result)


@music_bp.route('/playlists/<path:name>/add', methods=['POST'])
def music_add_playlist(name):
    """Adiciona playlist a fila atual"""
    result = mpd_service.add_playlist_to_queue(name)
    if 'error' in result:
        return jsonify(result), 500
    return jsonify(result)


@music_bp.route('/playlists/<path:name>/play', methods=['POST'])
def music_play_playlist(name):
    """Toca playlist (substitui fila)"""
    result = mpd_service.play_playlist(name)
    if 'error' in result:
        return jsonify(result), 500
    return jsonify(result)


@music_bp.route('/play-uri', methods=['POST'])
def music_play_uri():
    """Toca musica (substitui fila)"""
    data = request.json
    uri = data.get('uri') if data else None
    if not uri:
        return jsonify({'error': 'URI nao fornecido'}), 400
    result = mpd_service.play_uri(uri)
    if 'error' in result:
        return jsonify(result), 500
    return jsonify(result)


@music_bp.route('/all')
def music_all():
    """Lista todas as musicas"""
    result = mpd_service.list_all_songs()
    if isinstance(result, dict) and 'error' in result:
        return jsonify(result), 500
    return jsonify(result)


@music_bp.route('/seek', methods=['POST'])
def music_seek():
    """Vai para posicao especifica da musica"""
    data = request.json
    position = data.get('position') if data else None
    if position is None:
        return jsonify({'error': 'Posicao nao fornecida'}), 400
    result = mpd_service.seek(position)
    if 'error' in result:
        return jsonify(result), 500
    return jsonify(result)


@music_bp.route('/restart', methods=['POST'])
def music_restart():
    """Reinicia a musica atual"""
    result = mpd_service.restart_song()
    if 'error' in result:
        return jsonify(result), 500
    return jsonify(result)
