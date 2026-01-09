"""
Pi-Car - Rotas de Radio SDR

Endpoints da API para controle do RTL-SDR.
"""

import os
import json
from flask import Blueprint, jsonify, request
from backend.services.rtlsdr_service import (
    radio_data,
    get_rtlsdr_service,
    AIRPORT_PRESETS,
    FM_PRESETS
)

radio_bp = Blueprint('radio', __name__)

# Favorites file path
FAVORITES_FILE = os.path.expanduser('~/.pi-car/radio_favorites.json')


def _load_favorites():
    """Load favorites from file."""
    try:
        if os.path.exists(FAVORITES_FILE):
            with open(FAVORITES_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {'favorites': []}


def _save_favorites(data):
    """Save favorites to file."""
    try:
        os.makedirs(os.path.dirname(FAVORITES_FILE), exist_ok=True)
        with open(FAVORITES_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


@radio_bp.route('/status')
def radio_status():
    """Retorna status atual do radio."""
    return jsonify(radio_data)


@radio_bp.route('/tune', methods=['POST'])
def radio_tune():
    """Sintoniza uma frequencia.

    Body JSON:
        frequency: frequencia em MHz (ex: 99.5)
        mode: opcional, 'FM' ou 'AM'
    """
    data = request.get_json() or {}
    frequency = data.get('frequency')
    mode = data.get('mode')

    if frequency is None:
        return jsonify({'error': 'frequency required'}), 400

    try:
        frequency = float(frequency)
    except (TypeError, ValueError):
        return jsonify({'error': 'invalid frequency'}), 400

    service = get_rtlsdr_service()

    # Set mode if provided
    if mode:
        mode_result = service.set_mode(mode)
        if 'error' in mode_result:
            return jsonify(mode_result), 400

    # Tune to frequency
    result = service.tune(frequency)

    if 'error' in result:
        return jsonify(result), 500

    return jsonify(result)


@radio_bp.route('/mode', methods=['POST'])
def radio_mode():
    """Define o modo de demodulacao (FM/AM).

    Body JSON:
        mode: 'FM' ou 'AM'
    """
    data = request.get_json() or {}
    mode = data.get('mode')

    if not mode:
        return jsonify({'error': 'mode required'}), 400

    service = get_rtlsdr_service()
    result = service.set_mode(mode)

    if 'error' in result:
        return jsonify(result), 400

    return jsonify(result)


@radio_bp.route('/gain', methods=['POST'])
def radio_gain():
    """Define o ganho do receptor.

    Body JSON:
        gain: 'auto' ou valor em dB
    """
    data = request.get_json() or {}
    gain = data.get('gain')

    if gain is None:
        return jsonify({'error': 'gain required'}), 400

    service = get_rtlsdr_service()
    result = service.set_gain(gain)

    if 'error' in result:
        return jsonify(result), 500

    return jsonify(result)


@radio_bp.route('/gains')
def radio_gains():
    """Retorna lista de ganhos validos para o dispositivo."""
    service = get_rtlsdr_service()
    gains = service.get_valid_gains()
    return jsonify({'gains': gains})


@radio_bp.route('/fft')
def radio_fft():
    """Retorna dados FFT para espectrograma."""
    service = get_rtlsdr_service()
    result = service.get_fft()

    if 'error' in result:
        return jsonify(result), 500

    return jsonify(result)


@radio_bp.route('/presets')
def radio_presets():
    """Retorna presets de frequencias (FM e aeroportos)."""
    return jsonify({
        'fm': FM_PRESETS,
        'airports': AIRPORT_PRESETS
    })


@radio_bp.route('/presets/airport/<icao>')
def radio_airport_preset(icao):
    """Retorna frequencias de um aeroporto especifico."""
    icao = icao.upper()
    if icao not in AIRPORT_PRESETS:
        return jsonify({'error': f'Airport {icao} not found'}), 404
    return jsonify(AIRPORT_PRESETS[icao])


@radio_bp.route('/favorites')
def radio_favorites_list():
    """Lista todos os favoritos."""
    data = _load_favorites()
    return jsonify(data)


@radio_bp.route('/favorites', methods=['POST'])
def radio_favorites_add():
    """Adiciona uma frequencia aos favoritos.

    Body JSON:
        freq: frequencia em MHz
        mode: 'FM' ou 'AM'
        name: nome/label do favorito
    """
    req_data = request.get_json() or {}

    freq = req_data.get('freq')
    mode = req_data.get('mode', 'FM')
    name = req_data.get('name', '')

    if freq is None:
        return jsonify({'error': 'freq required'}), 400

    try:
        freq = float(freq)
    except (TypeError, ValueError):
        return jsonify({'error': 'invalid freq'}), 400

    # Load current favorites
    data = _load_favorites()

    # Check if already exists
    for fav in data['favorites']:
        if abs(fav['freq'] - freq) < 0.01:  # Within 10 kHz
            return jsonify({'error': 'frequency already in favorites'}), 400

    # Add new favorite
    data['favorites'].append({
        'freq': freq,
        'mode': mode.upper(),
        'name': name
    })

    if _save_favorites(data):
        return jsonify({'success': True, 'favorites': data['favorites']})
    else:
        return jsonify({'error': 'failed to save favorites'}), 500


@radio_bp.route('/favorites/<int:index>', methods=['DELETE'])
def radio_favorites_remove(index):
    """Remove um favorito pelo indice."""
    data = _load_favorites()

    if index < 0 or index >= len(data['favorites']):
        return jsonify({'error': 'invalid index'}), 404

    removed = data['favorites'].pop(index)

    if _save_favorites(data):
        return jsonify({'success': True, 'removed': removed})
    else:
        return jsonify({'error': 'failed to save favorites'}), 500


@radio_bp.route('/favorites/clear', methods=['POST'])
def radio_favorites_clear():
    """Remove todos os favoritos."""
    data = {'favorites': []}

    if _save_favorites(data):
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'failed to save favorites'}), 500
