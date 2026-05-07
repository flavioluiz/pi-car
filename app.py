#!/usr/bin/env python3
"""
Central Multimidia Veicular - Interface Web Unificada
Integra: MPD (musica), GPS (gpsd), OBD-II (diagnostico)

Autor: Flavio @ ITA
Uso: python3 app.py
Modo teste: python3 app.py --teste
Acesse: http://localhost:5000
"""

from __future__ import annotations

import argparse
import copy
import random
import sys
import threading
import time
import types
from datetime import datetime, timezone

from flask import Flask, render_template, request

import config


def _parse_args():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument('--teste', '--test', action='store_true', dest='test_mode')
    parser.add_argument('--port', type=int, default=None, help='Porta HTTP do servidor web')
    args, _ = parser.parse_known_args()
    return args


CLI_ARGS = _parse_args()
TEST_MODE = bool(CLI_ARGS.test_mode)
FLASK_PORT = CLI_ARGS.port if CLI_ARGS.port is not None else config.FLASK_PORT


def _update_test_telemetry(gps_data, obd_data, radio_data, wifi_data):
    gps_data.update({
        'lat': -23.200000 + random.uniform(-0.01, 0.01),
        'lon': -45.900000 + random.uniform(-0.01, 0.01),
        'speed': random.uniform(0, 88),
        'altitude': 560 + random.uniform(-15, 15),
        'satellites': random.randint(6, 14),
        'connected': True,
    })

    direct = obd_data['direct']
    inferred = obd_data['inferred']
    connection = obd_data['connection']
    metadata = obd_data['metadata']

    speed = random.uniform(0, 118)
    rpm = random.uniform(700, 3900)
    coolant = random.uniform(82, 96)
    battery = random.uniform(13.2, 14.4)
    instant = random.uniform(7.5, 15.5)
    sample_time = datetime.now(timezone.utc).isoformat()

    direct.update({
        'rpm': round(rpm, 0),
        'speed_kmh': round(speed, 0),
        'coolant_temp_c': round(coolant, 0),
        'intake_temp_c': round(26 + random.uniform(-3, 8), 0),
        'map_kpa': round(random.uniform(25, 75), 0),
        'engine_load_pct': round(random.uniform(18, 74), 0),
        'throttle_pct': round(random.uniform(6, 64), 0),
        'timing_advance_deg': round(random.uniform(2, 20), 1),
        'short_fuel_trim_b1_pct': round(random.uniform(-8, 8), 1),
        'long_fuel_trim_b1_pct': round(random.uniform(-6, 6), 1),
        'fuel_system_status_1': 'closed_loop_o2_feedback',
        'fuel_system_status_2': 'not_supported',
        'secondary_air_status': 'outside_atmosphere_or_off',
        'o2_sensors_present': ['B1S1', 'B1S2'],
        'o2_b1s1_voltage_v': round(random.uniform(0.05, 0.9), 3),
        'o2_b1s1_stft_pct': round(random.uniform(-8, 8), 1),
        'o2_b1s2_voltage_v': round(random.uniform(0.05, 0.9), 3),
        'obd_standard': 'eobd',
        'adapter_voltage_v': round(battery, 1),
        'mil_on': False,
        'distance_with_mil_km': 0,
        'active_dtcs': [],
        'pending_dtcs': [],
    })

    inferred.update({
        'engine_on': True,
        'stationary': speed < 1,
        'fuel_rate_l_h_gasoline_e27': round(random.uniform(0.7, 1.8), 2),
        'fuel_rate_l_h_ethanol': round(random.uniform(0.9, 2.2), 2),
        'selected_fuel_rate_l_h': round(random.uniform(0.7, 1.8), 2),
        'instant_km_l': round(instant, 1),
        'instant_l_100km': round(100 / instant, 1),
        'trip_consumed_l': round(inferred.get('trip_consumed_l', 0.0) + random.uniform(0.01, 0.04), 3),
        'trip_distance_km': round(inferred.get('trip_distance_km', 0.0) + speed / 3600, 2),
        'trip_average_km_l': round(random.uniform(8.8, 14.5), 1),
        'coolant_alert': False,
        'battery_alert': False,
    })

    connection.update({
        'connected': True,
        'port': connection.get('port') or '/dev/ttyUSB0',
        'stable_port': connection.get('stable_port') or '/dev/ttyUSB0',
        'fallback_port': connection.get('fallback_port') or '/dev/ttyUSB0',
        'baudrate': connection.get('baudrate') or 38400,
        'adapter': connection.get('adapter') or 'ELM327 TEST',
        'protocol': connection.get('protocol') or 'AUTO',
        'ecu_ready': True,
    })

    metadata.update({
        'vehicle': metadata.get('vehicle') or 'PiCASSO Test Vehicle',
        'vin': 'TESTVIN123456789',
        'sample_time': sample_time,
        'last_dynamic_sample_time': sample_time,
        'dynamic_stale': False,
        'dynamic_stale_age_s': 0.0,
        'last_successful_command': 'TEST',
    })

    obd_data['connected'] = True
    obd_data['error'] = None
    obd_data['supported_commands'] = [
        'STATUS', 'FUEL_STATUS', 'ENGINE_LOAD', 'COOLANT_TEMP', 'SHORT_FUEL_TRIM_1',
        'LONG_FUEL_TRIM_1', 'INTAKE_PRESSURE', 'RPM', 'SPEED', 'TIMING_ADVANCE',
        'INTAKE_TEMP', 'THROTTLE_POS', 'SECONDARY_AIR_STATUS', 'O2_SENSORS_PRESENT',
        'O2_B1S1', 'O2_B1S2', 'OBD_STANDARD', 'DISTANCE_WITH_MIL',
    ]
    obd_data['metrics'] = {
        'RPM': {'value': direct['rpm'], 'label': 'RPM', 'unit': 'rpm'},
        'SPEED': {'value': direct['speed_kmh'], 'label': 'Speed', 'unit': 'km/h'},
        'COOLANT_TEMP': {'value': direct['coolant_temp_c'], 'label': 'Coolant', 'unit': 'C'},
        'INTAKE_TEMP': {'value': direct['intake_temp_c'], 'label': 'Intake', 'unit': 'C'},
        'INTAKE_PRESSURE': {'value': direct['map_kpa'], 'label': 'MAP', 'unit': 'kPa'},
        'ENGINE_LOAD': {'value': direct['engine_load_pct'], 'label': 'Load', 'unit': '%'},
        'THROTTLE_POS': {'value': direct['throttle_pct'], 'label': 'Throttle', 'unit': '%'},
        'TIMING_ADVANCE': {'value': direct['timing_advance_deg'], 'label': 'Timing', 'unit': 'deg'},
        'SHORT_FUEL_TRIM_1': {'value': direct['short_fuel_trim_b1_pct'], 'label': 'STFT B1', 'unit': '%'},
        'LONG_FUEL_TRIM_1': {'value': direct['long_fuel_trim_b1_pct'], 'label': 'LTFT B1', 'unit': '%'},
        'O2_B1S1_VOLTAGE': {'value': direct['o2_b1s1_voltage_v'], 'label': 'O2 B1S1', 'unit': 'V'},
        'O2_B1S1_TRIM': {'value': direct['o2_b1s1_stft_pct'], 'label': 'O2 B1S1 STFT', 'unit': '%'},
        'O2_B1S2_VOLTAGE': {'value': direct['o2_b1s2_voltage_v'], 'label': 'O2 B1S2', 'unit': 'V'},
        'ELM_VOLTAGE': {'value': direct['adapter_voltage_v'], 'label': 'Battery', 'unit': 'V'},
        'FUEL_RATE_GASOLINE_E27': {'value': inferred['fuel_rate_l_h_gasoline_e27'], 'label': 'Fuel E27', 'unit': 'L/h'},
        'FUEL_RATE_ETHANOL': {'value': inferred['fuel_rate_l_h_ethanol'], 'label': 'Fuel EtOH', 'unit': 'L/h'},
        'INSTANT_KM_L': {'value': inferred['instant_km_l'], 'label': 'Instant', 'unit': 'km/L'},
        'TRIP_AVERAGE_KM_L': {'value': inferred['trip_average_km_l'], 'label': 'Trip Avg', 'unit': 'km/L'},
    }

    radio_data.update({
        'connected': True,
        'playing': random.choice([True, False]),
        'frequency': random.choice([88.3, 91.1, 95.7, 97.5, 100.1, 102.7]),
        'mode': random.choice(['FM', 'AM']),
        'volume': random.randint(35, 92),
        'squelch': 0,
        'gain': 'auto',
        'sample_rate': 2.4,
        'signal_strength': random.uniform(-92, -38),
        'error': None,
    })

    wifi_data.update({
        'connected': True,
        'state': 'connected',
        'ssid': 'PiCASSO Test AP',
        'interface': 'wlan0',
        'source': 'test-mode',
        'last_checked_at': sample_time,
    })


def _start_test_telemetry_loop(gps_data, obd_data, radio_data, wifi_data):
    def _run():
        while True:
            _update_test_telemetry(gps_data, obd_data, radio_data, wifi_data)
            time.sleep(max(0.2, float(getattr(config, 'OBD_POLL_INTERVAL', 0.8))))

    threading.Thread(target=_run, daemon=True, name='test-telemetry').start()


def _install_test_dependency_stubs():
    fake_library_tracks = [
        {
            'file': 'PiCASSO/Daft Punk - Instant Crush.mp3',
            'title': 'Instant Crush',
            'artist': 'Daft Punk',
            'artists_all': 'Daft Punk',
            'album': 'Random Access Memories',
        },
        {
            'file': 'PiCASSO/Kavinsky - Nightcall.mp3',
            'title': 'Nightcall',
            'artist': 'Kavinsky',
            'artists_all': 'Kavinsky',
            'album': 'OutRun',
        },
        {
            'file': 'PiCASSO/Alan Walker - Faded.mp3',
            'title': 'Faded',
            'artist': 'Alan Walker',
            'artists_all': 'Alan Walker',
            'album': 'Different World',
        },
        {
            'file': 'PiCASSO/M83 - Midnight City.mp3',
            'title': 'Midnight City',
            'artist': 'M83',
            'artists_all': 'M83',
            'album': 'Hurry Up, We\'re Dreaming',
        },
        {
            'file': 'PiCASSO/Test - Long Title Wraps Two Lines.mp3',
            'title': 'A Reasonably Long Song Title That Wraps',
            'artist': 'Test Artist With A Long Name',
            'artists_all': 'Test Artist With A Long Name',
            'album': 'Layout Test Album',
        },
        {
            'file': 'PiCASSO/Test - Extremely Long Title For Truncation.mp3',
            'title': 'An Extremely Long Song Title That Should Definitely Overflow Three Lines And Trigger Ellipsis Truncation Behavior',
            'artist': 'A Very Long Artist Name Featuring Several Other Performers',
            'artists_all': 'A Very Long Artist Name Featuring Several Other Performers',
            'album': 'Truncation Stress Test Album',
        },
    ]

    fake_playlists = {
        'Night Drive': ['PiCASSO/Daft Punk - Instant Crush.mp3', 'PiCASSO/Kavinsky - Nightcall.mp3'],
        'Electro': ['PiCASSO/Alan Walker - Faded.mp3', 'PiCASSO/M83 - Midnight City.mp3'],
    }

    fake_music_state = {
        'playlist': [track['file'] for track in fake_library_tracks[:2]],
        'current_index': 0,
        'state': 'play',
        'volume': 72,
        'elapsed': 12.0,
        'duration': 537.0,
        'random': False,
        'repeat': 'playlist',
    }

    class FakeMusicLibrary:
        def refresh(self, force: bool = False):
            return copy.deepcopy(fake_library_tracks)

        def get_track_by_file(self, file_name: str):
            target = (file_name or '').strip()
            for track in fake_library_tracks:
                if track['file'] == target or track['file'].split('/')[-1] == target:
                    return copy.deepcopy(track)
            return None

        def search(self, query: str):
            needle = (query or '').strip().casefold()
            if not needle:
                return self.refresh(force=True)
            results = []
            for track in fake_library_tracks:
                haystacks = (
                    track['title'],
                    track['artist'],
                    track['artists_all'],
                    track['album'],
                    track['file'],
                )
                if any(needle in value.casefold() for value in haystacks if value):
                    results.append(copy.deepcopy(track))
            return results

        def list_artists(self):
            artists = sorted({track['artist'] for track in fake_library_tracks})
            return artists

        def list_by_artist(self, artist: str):
            needle = (artist or '').strip().casefold()
            return [
                copy.deepcopy(track)
                for track in fake_library_tracks
                if track['artist'].casefold() == needle or needle in track['artists_all'].casefold()
            ]

    def _current_track():
        if not fake_music_state['playlist']:
            return copy.deepcopy(fake_library_tracks[0])
        idx = max(0, min(fake_music_state['current_index'], len(fake_music_state['playlist']) - 1))
        current_file = fake_music_state['playlist'][idx]
        track = next((t for t in fake_library_tracks if t['file'] == current_file), None)
        return copy.deepcopy(track or fake_library_tracks[0])

    def _advance_track():
        if not fake_music_state['playlist']:
            return
        fake_music_state['current_index'] = (fake_music_state['current_index'] + 1) % len(fake_music_state['playlist'])
        fake_music_state['elapsed'] = 0.0

    class FakeMPDClient:
        timeout = 10

        def connect(self, *args, **kwargs):
            return None

        def status(self):
            if fake_music_state['state'] == 'play':
                fake_music_state['elapsed'] += 1.0
                if fake_music_state['elapsed'] >= fake_music_state['duration']:
                    fake_music_state['elapsed'] = 0.0
                    if fake_music_state['repeat'] == 'playlist' and fake_music_state['playlist']:
                        _advance_track()
                    elif fake_music_state['playlist']:
                        fake_music_state['current_index'] = min(fake_music_state['current_index'] + 1, len(fake_music_state['playlist']) - 1)
            repeat = fake_music_state['repeat']
            return {
                'state': fake_music_state['state'],
                'volume': str(fake_music_state['volume']),
                'elapsed': f"{fake_music_state['elapsed']:.1f}",
                'duration': f"{fake_music_state['duration']:.1f}",
                'random': '1' if fake_music_state['random'] else '0',
                'repeat': '1' if repeat in ('playlist', 'song') else '0',
                'single': '1' if repeat == 'song' else '0',
            }

        def currentsong(self):
            track = _current_track()
            return {
                'file': track['file'],
                'title': track['title'],
                'artist': track['artist'],
                'artists_all': track['artists_all'],
                'album': track['album'],
            }

        def playlistinfo(self):
            songs = []
            for pos, file_name in enumerate(fake_music_state['playlist']):
                track = next((t for t in fake_library_tracks if t['file'] == file_name), None)
                if not track:
                    continue
                songs.append({
                    'pos': pos,
                    'file': track['file'],
                    'title': track['title'],
                    'artist': track['artist'],
                    'artists_all': track['artists_all'],
                    'album': track['album'],
                })
            return songs

        def play(self, pos=None):
            if pos is not None:
                fake_music_state['current_index'] = max(0, min(int(pos), max(len(fake_music_state['playlist']) - 1, 0)))
            fake_music_state['state'] = 'play'

        def pause(self):
            fake_music_state['state'] = 'pause'

        def stop(self):
            fake_music_state['state'] = 'stop'

        def next(self):
            _advance_track()

        def previous(self):
            if fake_music_state['playlist']:
                fake_music_state['current_index'] = max(0, fake_music_state['current_index'] - 1)
                fake_music_state['elapsed'] = 0.0

        def setvol(self, volume):
            fake_music_state['volume'] = max(0, min(100, int(volume)))

        def random(self, value):
            fake_music_state['random'] = bool(int(value))

        def repeat(self, value):
            fake_music_state['repeat'] = 'playlist' if int(value) else 'off'

        def single(self, value):
            if int(value):
                fake_music_state['repeat'] = 'song'
            elif fake_music_state['repeat'] == 'song':
                fake_music_state['repeat'] = 'off'

        def clear(self):
            fake_music_state['playlist'] = []
            fake_music_state['current_index'] = 0
            fake_music_state['elapsed'] = 0.0

        def delete(self, pos):
            if 0 <= int(pos) < len(fake_music_state['playlist']):
                del fake_music_state['playlist'][int(pos)]
                fake_music_state['current_index'] = min(fake_music_state['current_index'], max(len(fake_music_state['playlist']) - 1, 0))

        def add(self, uri):
            target = (uri or '').strip()
            track = next((t for t in fake_library_tracks if t['file'] == target or t['file'].split('/')[-1] == target), None)
            if track:
                fake_music_state['playlist'].append(track['file'])

        def load(self, name):
            files = fake_playlists.get(name, [])
            fake_music_state['playlist'].extend(files)

        def save(self, name):
            fake_playlists[name] = list(fake_music_state['playlist'])

        def rm(self, name):
            fake_playlists.pop(name, None)

        def listplaylists(self):
            return [{'playlist': name} for name in sorted(fake_playlists)]

        def seekcur(self, position):
            fake_music_state['elapsed'] = max(0.0, float(position))

        def close(self):
            return None

        def disconnect(self):
            return None

    mutagen_module = types.ModuleType('mutagen')
    mutagen_module.File = lambda *args, **kwargs: None
    sys.modules['mutagen'] = mutagen_module

    mutagen_easyid3 = types.ModuleType('mutagen.easyid3')

    class EasyID3(dict):
        def __init__(self, *args, **kwargs):
            super().__init__()

    mutagen_easyid3.EasyID3 = EasyID3
    sys.modules['mutagen.easyid3'] = mutagen_easyid3

    mutagen_id3 = types.ModuleType('mutagen.id3')

    class ID3:
        def __init__(self, *args, **kwargs):
            return None

        def getall(self, *args, **kwargs):
            return []

    class ID3NoHeaderError(Exception):
        pass

    mutagen_id3.ID3 = ID3
    mutagen_id3.ID3NoHeaderError = ID3NoHeaderError
    sys.modules['mutagen.id3'] = mutagen_id3

    mpd_module = types.ModuleType('mpd')
    mpd_module.MPDClient = FakeMPDClient
    sys.modules['mpd'] = mpd_module

    return FakeMusicLibrary()


def create_app():
    if TEST_MODE:
        fake_library = _install_test_dependency_stubs()
    else:
        fake_library = None

    app = Flask(
        __name__,
        template_folder='frontend/templates',
        static_folder='frontend/static'
    )

    from backend.routes import music_bp, gps_bp, vehicle_bp, system_bp, radio_bp
    from backend.services import gps_data, obd_data, radio_data, set_obd_service, set_rtlsdr_service, wifi_data

    app.register_blueprint(music_bp, url_prefix='/api/music')
    app.register_blueprint(gps_bp, url_prefix='/api/gps')
    app.register_blueprint(vehicle_bp, url_prefix='/api/vehicle')
    app.register_blueprint(system_bp, url_prefix='/api')
    app.register_blueprint(radio_bp, url_prefix='/api/radio')

    if TEST_MODE:
        from backend.services import mpd_service as mpd_service_module
        from backend.services.obd_logger_service import obd_logger_service
        from backend.services.obd_service import OBDService
        from backend.services.network_service import network_service
        from backend.services.rtlsdr_service import RTLSDRService

        mpd_service_module.music_library = fake_library
        mpd_service_module.music_data.update({
            'state': 'play',
            'artist': 'Daft Punk',
            'artists_all': 'Daft Punk',
            'title': 'Instant Crush',
            'album': 'Random Access Memories',
            'elapsed': 12.0,
            'duration': 537.0,
            'volume': 72,
            'random': False,
            'repeat_mode': 'playlist',
            'connected': True,
        })

        class FakeOBDService:
            def __init__(self):
                self._state = copy.deepcopy(OBDService().get_status() if False else None)
                self._volume = 13.8

            def get_status(self):
                return copy.deepcopy(obd_data)

            def update_settings(self, settings):
                return self.get_status()

            def reset_trip(self):
                obd_data['inferred']['trip_consumed_l'] = 0.0
                obd_data['inferred']['trip_distance_km'] = 0.0
                obd_data['inferred']['trip_average_km_l'] = None

            def get_supported_commands(self):
                return list(obd_data.get('supported_commands', []))

        class FakeRTLSDRService:
            def get_status(self):
                return copy.deepcopy(radio_data)

            def set_mode(self, mode):
                radio_data['mode'] = mode.upper()
                return {'success': True, 'mode': radio_data['mode']}

            def tune(self, frequency):
                radio_data['frequency'] = float(frequency)
                radio_data['connected'] = True
                return {'success': True, 'frequency': radio_data['frequency'], 'mode': radio_data['mode']}

            def set_gain(self, gain):
                radio_data['gain'] = gain
                return {'success': True, 'gain': gain}

            def get_valid_gains(self):
                return [0, 10, 20, 30, 40, 49.6]

            def get_fft(self, center_freq=None, span_mhz=2.0, integration_time=0.1):
                return {'success': True, 'bins': [random.uniform(-80, -30) for _ in range(256)]}

            def start_spectrum_mode(self):
                radio_data['connected'] = True
                return {'success': True, 'spectrum_mode': True}

            def stop_spectrum_mode(self):
                return {'success': True, 'spectrum_mode': False}

            def add_favorite(self, *args, **kwargs):
                return {'success': True}

        set_obd_service(FakeOBDService())
        set_rtlsdr_service(FakeRTLSDRService())
        network_service.get_wifi_status = lambda force=False: copy.deepcopy(wifi_data)
        _update_test_telemetry(gps_data, obd_data, radio_data, wifi_data)
        _start_test_telemetry_loop(gps_data, obd_data, radio_data, wifi_data)
        from backend.services.obd_logger_service import obd_logger_service
        obd_logger_service.start()
        obd_logger_service.start()

        @app.before_request
        def _test_tick():
            if not request.path.startswith('/api/'):
                return None
            _update_test_telemetry(gps_data, obd_data, radio_data, wifi_data)

            return None

    print("Iniciando Central Multimidia em modo de teste...")
    return app


app = create_app()


@app.route('/')
def index():
    """Pagina principal"""
    return render_template('index.html')


def _start_real_services():
    print("Iniciando Central Multimidia...")

    from backend.services import GPSService, get_obd_service, get_rtlsdr_service
    from backend.services.obd_logger_service import obd_logger_service

    gps_service = GPSService()
    gps_service.start()
    print("GPS thread started")

    obd_service = get_obd_service()
    if obd_service.start():
        print("OBD thread started")
        obd_logger_service.start()
        print("OBD logger thread started")
    else:
        print(f"OBD not available (check USB connection at {config.OBD_DEVICE} or {config.OBD_FALLBACK_DEVICE})")

    rtlsdr_service = get_rtlsdr_service()
    if rtlsdr_service.start():
        print("Thread RTL-SDR iniciada")
    else:
        print("RTL-SDR nao disponivel (verifique conexao USB)")

    print("")
    print("=" * 50)
    print(f"Acesse: http://localhost:{FLASK_PORT}")
    print("=" * 50)
    print("")


if __name__ == '__main__':
    if not TEST_MODE:
        _start_real_services()
    else:
        print("")
        print("=" * 50)
        print(f"Teste ativo: http://localhost:{FLASK_PORT}")
        print("=" * 50)
        print("")

    app.run(
        host=config.FLASK_HOST,
        port=FLASK_PORT,
        debug=config.FLASK_DEBUG,
        threaded=True
    )
