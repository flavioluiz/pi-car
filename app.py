#!/usr/bin/env python3
"""
Central Multimídia Veicular - Interface Web Unificada
Integra: MPD (música), GPS (gpsd), OBD-II (diagnóstico)

Autor: Flavio @ ITA
Uso: python3 app.py
Acesse: http://localhost:5000
"""

from flask import Flask, render_template_string, jsonify, request
from mpd import MPDClient
import threading
import time
import json

app = Flask(__name__)

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

MPD_HOST = 'localhost'
MPD_PORT = 6600
GPS_HOST = 'localhost'
GPS_PORT = 2947

# Dados globais (atualizados por threads)
car_data = {
    'gps': {
        'lat': None,
        'lon': None,
        'speed': 0,
        'altitude': None,
        'satellites': 0,
        'connected': False
    },
    'obd': {
        'rpm': 0,
        'speed': 0,
        'coolant_temp': 0,
        'throttle': 0,
        'fuel_level': 0,
        'connected': False
    },
    'music': {
        'state': 'stop',
        'artist': '',
        'title': '',
        'album': '',
        'elapsed': 0,
        'duration': 0,
        'volume': 100,
        'connected': False
    }
}

# ============================================================================
# MPD (MÚSICA)
# ============================================================================

def get_mpd_client():
    """Retorna cliente MPD conectado"""
    try:
        client = MPDClient()
        client.timeout = 10
        client.connect(MPD_HOST, MPD_PORT)
        return client
    except Exception as e:
        print(f"MPD erro: {e}")
        return None

def update_music_data():
    """Atualiza dados do MPD"""
    client = get_mpd_client()
    if client:
        try:
            status = client.status()
            song = client.currentsong()
            
            car_data['music']['connected'] = True
            car_data['music']['state'] = status.get('state', 'stop')
            car_data['music']['volume'] = int(status.get('volume', 100))
            car_data['music']['elapsed'] = float(status.get('elapsed', 0))
            car_data['music']['duration'] = float(status.get('duration', 0))
            car_data['music']['artist'] = song.get('artist', 'Desconhecido')
            car_data['music']['title'] = song.get('title', song.get('file', 'Sem título'))
            car_data['music']['album'] = song.get('album', '')
            
            client.close()
            client.disconnect()
        except Exception as e:
            car_data['music']['connected'] = False
            print(f"MPD update erro: {e}")
    else:
        car_data['music']['connected'] = False

# ============================================================================
# GPS (GPSD)
# ============================================================================

def gps_thread():
    """Thread que monitora GPS continuamente"""
    try:
        from gps3 import gps3
        gps_socket = gps3.GPSDSocket()
        data_stream = gps3.DataStream()
        gps_socket.connect(host=GPS_HOST, port=GPS_PORT)
        gps_socket.watch()
        
        for new_data in gps_socket:
            if new_data:
                data_stream.unpack(new_data)
                
                if data_stream.TPV['lat'] != 'n/a':
                    car_data['gps']['connected'] = True
                    car_data['gps']['lat'] = data_stream.TPV['lat']
                    car_data['gps']['lon'] = data_stream.TPV['lon']
                    car_data['gps']['speed'] = float(data_stream.TPV['speed'] or 0) * 3.6  # m/s -> km/h
                    car_data['gps']['altitude'] = data_stream.TPV['alt']
                    
                if data_stream.SKY['satellites'] != 'n/a':
                    sats = data_stream.SKY['satellites']
                    if isinstance(sats, list):
                        car_data['gps']['satellites'] = len([s for s in sats if s.get('used')])
                        
    except Exception as e:
        car_data['gps']['connected'] = False
        print(f"GPS thread erro: {e}")

# ============================================================================
# OBD-II
# ============================================================================

def obd_thread():
    """Thread que monitora OBD-II continuamente"""
    try:
        import obd
        connection = obd.OBD("/dev/rfcomm0")
        
        if connection.is_connected():
            car_data['obd']['connected'] = True
            
            while True:
                try:
                    # RPM
                    rpm = connection.query(obd.commands.RPM)
                    if rpm.value:
                        car_data['obd']['rpm'] = rpm.value.magnitude
                    
                    # Velocidade
                    speed = connection.query(obd.commands.SPEED)
                    if speed.value:
                        car_data['obd']['speed'] = speed.value.magnitude
                    
                    # Temperatura
                    temp = connection.query(obd.commands.COOLANT_TEMP)
                    if temp.value:
                        car_data['obd']['coolant_temp'] = temp.value.magnitude
                    
                    # Acelerador
                    throttle = connection.query(obd.commands.THROTTLE_POS)
                    if throttle.value:
                        car_data['obd']['throttle'] = throttle.value.magnitude
                        
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"OBD query erro: {e}")
                    time.sleep(2)
        else:
            car_data['obd']['connected'] = False
            
    except Exception as e:
        car_data['obd']['connected'] = False
        print(f"OBD thread erro: {e}")

# ============================================================================
# ROTAS DA API
# ============================================================================

@app.route('/api/status')
def api_status():
    """Retorna todos os dados do veículo"""
    update_music_data()
    return jsonify(car_data)

@app.route('/api/music/<action>')
def api_music(action):
    """Controle do player de música"""
    client = get_mpd_client()
    if not client:
        return jsonify({'error': 'MPD não conectado'}), 500
    
    try:
        if action == 'play':
            client.play()
        elif action == 'pause':
            client.pause()
        elif action == 'stop':
            client.stop()
        elif action == 'next':
            client.next()
        elif action == 'prev':
            client.previous()
        elif action == 'volup':
            status = client.status()
            vol = min(100, int(status.get('volume', 0)) + 5)
            client.setvol(vol)
        elif action == 'voldown':
            status = client.status()
            vol = max(0, int(status.get('volume', 0)) - 5)
            client.setvol(vol)
            
        client.close()
        client.disconnect()
        return jsonify({'success': True, 'action': action})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/playlist')
def api_playlist():
    """Retorna playlist atual"""
    client = get_mpd_client()
    if not client:
        return jsonify({'error': 'MPD não conectado'}), 500
    
    try:
        playlist = client.playlistinfo()
        client.close()
        client.disconnect()
        return jsonify(playlist)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/library')
def api_library():
    """Retorna biblioteca de músicas"""
    client = get_mpd_client()
    if not client:
        return jsonify({'error': 'MPD não conectado'}), 500
    
    try:
        songs = client.listall()
        client.close()
        client.disconnect()
        return jsonify(songs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/music/add', methods=['POST'])
def api_music_add():
    """Adiciona música à playlist"""
    client = get_mpd_client()
    if not client:
        return jsonify({'error': 'MPD não conectado'}), 500
    
    try:
        data = request.json
        uri = data.get('uri')
        if uri:
            client.add(uri)
        client.close()
        client.disconnect()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# INTERFACE HTML
# ============================================================================

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Car Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
            user-select: none;
        }
        
        :root {
            --bg-dark: #0a0a0f;
            --bg-card: #12121a;
            --bg-card-hover: #1a1a25;
            --accent-cyan: #00f5ff;
            --accent-orange: #ff6b35;
            --accent-green: #00ff88;
            --accent-red: #ff3355;
            --accent-purple: #a855f7;
            --text-primary: #ffffff;
            --text-secondary: #8888aa;
            --border-color: #2a2a3a;
        }
        
        body {
            font-family: 'Rajdhani', sans-serif;
            background: var(--bg-dark);
            color: var(--text-primary);
            min-height: 100vh;
            overflow-x: hidden;
        }
        
        /* Background animado */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: 
                radial-gradient(circle at 20% 80%, rgba(0, 245, 255, 0.05) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(255, 107, 53, 0.05) 0%, transparent 50%),
                radial-gradient(circle at 50% 50%, rgba(168, 85, 247, 0.03) 0%, transparent 70%);
            pointer-events: none;
            z-index: -1;
        }
        
        /* Grid de scanlines sutil */
        body::after {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: repeating-linear-gradient(
                0deg,
                transparent,
                transparent 2px,
                rgba(0, 0, 0, 0.1) 2px,
                rgba(0, 0, 0, 0.1) 4px
            );
            pointer-events: none;
            z-index: 1000;
            opacity: 0.3;
        }
        
        /* Header */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 20px;
            background: linear-gradient(180deg, rgba(18, 18, 26, 0.95) 0%, rgba(10, 10, 15, 0.8) 100%);
            border-bottom: 1px solid var(--border-color);
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .logo {
            font-family: 'Orbitron', monospace;
            font-size: 1.5rem;
            font-weight: 900;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-transform: uppercase;
            letter-spacing: 3px;
        }
        
        .clock {
            font-family: 'Orbitron', monospace;
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--accent-cyan);
            text-shadow: 0 0 20px rgba(0, 245, 255, 0.5);
        }
        
        .status-indicators {
            display: flex;
            gap: 15px;
        }
        
        .indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: var(--accent-red);
            box-shadow: 0 0 10px currentColor;
            transition: all 0.3s;
        }
        
        .indicator.connected {
            background: var(--accent-green);
        }
        
        /* Navegação por abas */
        .tabs {
            display: flex;
            background: var(--bg-card);
            border-bottom: 1px solid var(--border-color);
            overflow-x: auto;
        }
        
        .tab {
            flex: 1;
            min-width: 80px;
            padding: 15px 20px;
            text-align: center;
            font-size: 1rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 2px;
            color: var(--text-secondary);
            background: transparent;
            border: none;
            cursor: pointer;
            transition: all 0.3s;
            position: relative;
        }
        
        .tab:hover {
            color: var(--text-primary);
            background: var(--bg-card-hover);
        }
        
        .tab.active {
            color: var(--accent-cyan);
        }
        
        .tab.active::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple));
            box-shadow: 0 0 15px var(--accent-cyan);
        }
        
        .tab-icon {
            font-size: 1.5rem;
            display: block;
            margin-bottom: 5px;
        }
        
        /* Painéis */
        .panels {
            padding: 20px;
        }
        
        .panel {
            display: none;
            animation: fadeIn 0.3s ease;
        }
        
        .panel.active {
            display: block;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* Cards */
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            position: relative;
            overflow: hidden;
        }
        
        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--accent-cyan), transparent);
        }
        
        .card-title {
            font-family: 'Orbitron', monospace;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 2px;
            color: var(--text-secondary);
            margin-bottom: 15px;
        }
        
        /* ============ PAINEL DE MÚSICA ============ */
        .music-now-playing {
            display: flex;
            align-items: center;
            padding: 15px 20px;
            gap: 20px;
        }

        .music-artwork {
            width: 80px;
            height: 80px;
            min-width: 80px;
            background: linear-gradient(135deg, var(--bg-card-hover), var(--bg-dark));
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            color: var(--accent-cyan);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
            position: relative;
            overflow: hidden;
        }

        .music-artwork::after {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: conic-gradient(from 0deg, transparent, rgba(0, 245, 255, 0.15), transparent);
            animation: rotate 8s linear infinite;
        }

        @keyframes rotate {
            to { transform: rotate(360deg); }
        }

        .music-artwork.playing::after {
            animation-duration: 2s;
        }

        .music-info {
            flex: 1;
            min-width: 0;
        }

        .music-title {
            font-size: 1.3rem;
            font-weight: 700;
            margin-bottom: 4px;
            color: var(--text-primary);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .music-artist {
            font-size: 1rem;
            color: var(--accent-cyan);
            margin-bottom: 10px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .music-progress {
            margin-bottom: 10px;
        }
        
        .progress-bar {
            height: 6px;
            background: var(--bg-dark);
            border-radius: 3px;
            overflow: hidden;
            margin-bottom: 10px;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple));
            border-radius: 3px;
            transition: width 0.5s linear;
            box-shadow: 0 0 15px var(--accent-cyan);
        }
        
        .progress-time {
            display: flex;
            justify-content: space-between;
            font-family: 'Orbitron', monospace;
            font-size: 0.9rem;
            color: var(--text-secondary);
        }
        
        .music-controls {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
        }

        .control-btn {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            border: 2px solid var(--border-color);
            background: var(--bg-card);
            color: var(--text-primary);
            font-size: 1rem;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .control-btn:hover {
            border-color: var(--accent-cyan);
            box-shadow: 0 0 15px rgba(0, 245, 255, 0.3);
            transform: scale(1.05);
        }

        .control-btn:active {
            transform: scale(0.95);
        }

        .control-btn.play-pause {
            width: 54px;
            height: 54px;
            font-size: 1.2rem;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            border: none;
            color: var(--bg-dark);
        }

        .volume-control {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }

        .volume-btn {
            width: 36px;
            height: 36px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            background: var(--bg-card);
            color: var(--text-primary);
            font-size: 1rem;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.2s;
        }

        .volume-btn:hover {
            border-color: var(--accent-orange);
            color: var(--accent-orange);
        }

        .volume-display {
            font-family: 'Orbitron', monospace;
            font-size: 1rem;
            color: var(--accent-orange);
            min-width: 50px;
            text-align: center;
        }
        
        /* ============ PAINEL DE VEÍCULO (OBD) ============ */
        .gauges-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }
        
        .gauge {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            position: relative;
        }
        
        .gauge-value {
            font-family: 'Orbitron', monospace;
            font-size: 2.5rem;
            font-weight: 900;
            background: linear-gradient(135deg, var(--accent-cyan), var(--text-primary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            line-height: 1;
            margin-bottom: 5px;
        }
        
        .gauge-unit {
            font-size: 1rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 2px;
        }
        
        .gauge-label {
            font-size: 0.8rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 10px;
        }
        
        .gauge.rpm .gauge-value {
            background: linear-gradient(135deg, var(--accent-orange), var(--accent-red));
            -webkit-background-clip: text;
            background-clip: text;
        }
        
        .gauge.temp .gauge-value {
            background: linear-gradient(135deg, var(--accent-green), var(--accent-cyan));
            -webkit-background-clip: text;
            background-clip: text;
        }
        
        /* ============ PAINEL GPS ============ */
        .gps-info {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }
        
        .gps-stat {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 15px;
            text-align: center;
        }
        
        .gps-stat-value {
            font-family: 'Orbitron', monospace;
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--accent-green);
        }
        
        .gps-stat-label {
            font-size: 0.75rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 5px;
        }
        
        .gps-coords {
            grid-column: span 2;
            font-family: 'Orbitron', monospace;
            font-size: 0.9rem;
            color: var(--text-secondary);
        }
        
        .navit-btn {
            grid-column: span 2;
            padding: 20px;
            background: linear-gradient(135deg, var(--accent-green), var(--accent-cyan));
            border: none;
            border-radius: 12px;
            color: var(--bg-dark);
            font-family: 'Rajdhani', sans-serif;
            font-size: 1.2rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 2px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .navit-btn:hover {
            transform: scale(1.02);
            box-shadow: 0 10px 30px rgba(0, 255, 136, 0.3);
        }
        
        /* ============ STATUS DESCONECTADO ============ */
        .disconnected-msg {
            text-align: center;
            padding: 40px;
            color: var(--text-secondary);
        }
        
        .disconnected-msg .icon {
            font-size: 3rem;
            margin-bottom: 15px;
            opacity: 0.5;
        }
        
        /* ============ RESPONSIVO ============ */
        @media (max-width: 480px) {
            .header {
                padding: 10px 15px;
            }

            .logo {
                font-size: 1.1rem;
            }

            .clock {
                font-size: 1.3rem;
            }

            .tab {
                padding: 10px 8px;
                font-size: 0.75rem;
            }

            .music-artwork {
                width: 60px;
                height: 60px;
                min-width: 60px;
            }

            .music-title {
                font-size: 1.1rem;
            }

            .gauges-grid {
                grid-template-columns: 1fr;
            }

            .gauge-value {
                font-size: 2rem;
            }
        }
    </style>
</head>
<body>
    <!-- Header -->
    <header class="header">
        <div class="logo">Pi·Car</div>
        <div class="clock" id="clock">00:00</div>
        <div class="status-indicators">
            <div class="indicator" id="ind-music" title="Música"></div>
            <div class="indicator" id="ind-gps" title="GPS"></div>
            <div class="indicator" id="ind-obd" title="OBD-II"></div>
        </div>
    </header>
    
    <!-- Abas de navegação -->
    <nav class="tabs">
        <button class="tab active" data-panel="music">MUSICA</button>
        <button class="tab" data-panel="vehicle">VEICULO</button>
        <button class="tab" data-panel="gps">GPS</button>
        <button class="tab" data-panel="radio">RADIO</button>
    </nav>
    
    <!-- Painéis -->
    <main class="panels">
        
        <!-- Painel: Música -->
        <section class="panel active" id="panel-music">
            <div class="music-now-playing">
                <div class="music-artwork" id="music-artwork">&#9835;</div>
                <div class="music-info">
                    <div class="music-title" id="music-title">Nenhuma musica</div>
                    <div class="music-artist" id="music-artist">-</div>
                    <div class="music-progress">
                        <div class="progress-bar">
                            <div class="progress-fill" id="progress-fill" style="width: 0%"></div>
                        </div>
                        <div class="progress-time">
                            <span id="time-elapsed">0:00</span>
                            <span id="time-duration">0:00</span>
                        </div>
                    </div>
                    <div class="music-controls">
                        <button class="control-btn" onclick="musicControl('prev')">&#9664;&#9664;</button>
                        <button class="control-btn play-pause" id="btn-play" onclick="musicControl('play')">&#9654;</button>
                        <button class="control-btn" onclick="musicControl('next')">&#9654;&#9654;</button>
                    </div>
                    <div class="volume-control">
                        <button class="volume-btn" onclick="musicControl('voldown')">-</button>
                        <span class="volume-display" id="volume-display">100%</span>
                        <button class="volume-btn" onclick="musicControl('volup')">+</button>
                    </div>
                </div>
            </div>
        </section>
        
        <!-- Painel: Veículo (OBD) -->
        <section class="panel" id="panel-vehicle">
            <div id="obd-content">
                <div class="gauges-grid">
                    <div class="gauge rpm">
                        <div class="gauge-value" id="obd-rpm">0</div>
                        <div class="gauge-unit">RPM</div>
                        <div class="gauge-label">Rotação</div>
                    </div>
                    <div class="gauge speed">
                        <div class="gauge-value" id="obd-speed">0</div>
                        <div class="gauge-unit">km/h</div>
                        <div class="gauge-label">Velocidade</div>
                    </div>
                    <div class="gauge temp">
                        <div class="gauge-value" id="obd-temp">0</div>
                        <div class="gauge-unit">°C</div>
                        <div class="gauge-label">Temperatura</div>
                    </div>
                    <div class="gauge throttle">
                        <div class="gauge-value" id="obd-throttle">0</div>
                        <div class="gauge-unit">%</div>
                        <div class="gauge-label">Acelerador</div>
                    </div>
                </div>
            </div>
            <div id="obd-disconnected" class="disconnected-msg" style="display: none;">
                <div class="icon">[OBD]</div>
                <p>OBD-II nao conectado</p>
                <p style="font-size: 0.9rem; margin-top: 10px;">Conecte o adaptador ELM327</p>
            </div>
        </section>
        
        <!-- Painel: GPS -->
        <section class="panel" id="panel-gps">
            <div id="gps-content">
                <div class="gps-info">
                    <div class="gps-stat">
                        <div class="gps-stat-value" id="gps-speed">0</div>
                        <div class="gps-stat-label">km/h</div>
                    </div>
                    <div class="gps-stat">
                        <div class="gps-stat-value" id="gps-sats">0</div>
                        <div class="gps-stat-label">Satélites</div>
                    </div>
                    <div class="gps-stat gps-coords">
                        <div id="gps-coords">Aguardando sinal GPS...</div>
                    </div>
                    <button class="navit-btn" onclick="openNavit()">
                        ABRIR NAVEGACAO
                    </button>
                </div>
            </div>
            <div id="gps-disconnected" class="disconnected-msg" style="display: none;">
                <div class="icon">[GPS]</div>
                <p>GPS nao conectado</p>
                <p style="font-size: 0.9rem; margin-top: 10px;">Verifique o modulo GPS</p>
            </div>
        </section>

        <!-- Painel: Rádio SDR -->
        <section class="panel" id="panel-radio">
            <div class="card">
                <div class="card-title">Radio SDR</div>
                <div class="disconnected-msg">
                    <div class="icon">[SDR]</div>
                    <p>RTL-SDR</p>
                    <p style="font-size: 0.9rem; margin-top: 10px; color: var(--text-secondary);">
                        Em desenvolvimento...
                    </p>
                    <button class="navit-btn" style="margin-top: 20px;" onclick="openGqrx()">
                        ABRIR GQRX
                    </button>
                </div>
            </div>
        </section>
        
    </main>
    
    <script>
        // ============ TABS ============
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                // Remove active de todas as tabs
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
                
                // Ativa a tab clicada
                tab.classList.add('active');
                document.getElementById('panel-' + tab.dataset.panel).classList.add('active');
            });
        });
        
        // ============ RELÓGIO ============
        function updateClock() {
            const now = new Date();
            document.getElementById('clock').textContent = 
                now.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
        }
        updateClock();
        setInterval(updateClock, 1000);
        
        // ============ FORMATAR TEMPO ============
        function formatTime(seconds) {
            if (!seconds || isNaN(seconds)) return '0:00';
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return mins + ':' + secs.toString().padStart(2, '0');
        }
        
        // ============ ATUALIZAR DADOS ============
        function updateData() {
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    // Indicadores de conexão
                    document.getElementById('ind-music').classList.toggle('connected', data.music.connected);
                    document.getElementById('ind-gps').classList.toggle('connected', data.gps.connected);
                    document.getElementById('ind-obd').classList.toggle('connected', data.obd.connected);
                    
                    // Musica
                    document.getElementById('music-title').textContent = data.music.title || 'Nenhuma musica';
                    document.getElementById('music-artist').textContent = data.music.artist || '-';
                    document.getElementById('volume-display').textContent = data.music.volume + '%';
                    document.getElementById('time-elapsed').textContent = formatTime(data.music.elapsed);
                    document.getElementById('time-duration').textContent = formatTime(data.music.duration);
                    
                    const progress = data.music.duration > 0 ? (data.music.elapsed / data.music.duration * 100) : 0;
                    document.getElementById('progress-fill').style.width = progress + '%';
                    
                    const btnPlay = document.getElementById('btn-play');
                    const artwork = document.getElementById('music-artwork');
                    if (data.music.state === 'play') {
                        btnPlay.innerHTML = '&#9612;&#9612;';
                        btnPlay.onclick = () => musicControl('pause');
                        artwork.classList.add('playing');
                    } else {
                        btnPlay.innerHTML = '&#9654;';
                        btnPlay.onclick = () => musicControl('play');
                        artwork.classList.remove('playing');
                    }
                    
                    // OBD
                    if (data.obd.connected) {
                        document.getElementById('obd-content').style.display = 'block';
                        document.getElementById('obd-disconnected').style.display = 'none';
                        document.getElementById('obd-rpm').textContent = Math.round(data.obd.rpm);
                        document.getElementById('obd-speed').textContent = Math.round(data.obd.speed);
                        document.getElementById('obd-temp').textContent = Math.round(data.obd.coolant_temp);
                        document.getElementById('obd-throttle').textContent = Math.round(data.obd.throttle);
                    } else {
                        document.getElementById('obd-content').style.display = 'none';
                        document.getElementById('obd-disconnected').style.display = 'block';
                    }
                    
                    // GPS
                    if (data.gps.connected && data.gps.lat) {
                        document.getElementById('gps-content').style.display = 'block';
                        document.getElementById('gps-disconnected').style.display = 'none';
                        document.getElementById('gps-speed').textContent = Math.round(data.gps.speed);
                        document.getElementById('gps-sats').textContent = data.gps.satellites;
                        document.getElementById('gps-coords').textContent = 
                            `${data.gps.lat.toFixed(6)}, ${data.gps.lon.toFixed(6)}`;
                    } else {
                        document.getElementById('gps-content').style.display = 'none';
                        document.getElementById('gps-disconnected').style.display = 'block';
                    }
                })
                .catch(err => console.error('Erro ao atualizar:', err));
        }
        
        // Atualizar a cada 1 segundo
        updateData();
        setInterval(updateData, 1000);
        
        // ============ CONTROLES DE MÚSICA ============
        function musicControl(action) {
            fetch('/api/music/' + action)
                .then(r => r.json())
                .then(() => updateData())
                .catch(err => console.error('Erro:', err));
        }
        
        // ============ ABRIR APPS EXTERNOS ============
        function openNavit() {
            fetch('/api/launch/navit').catch(() => {});
            alert('Abrindo Navit...');
        }
        
        function openGqrx() {
            fetch('/api/launch/gqrx').catch(() => {});
            alert('Abrindo GQRX...');
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/launch/<app_name>')
def launch_app(app_name):
    """Lança aplicativos externos"""
    import subprocess
    apps = {
        'navit': 'navit',
        'gqrx': 'gqrx',
        'terminal': 'lxterminal'
    }
    if app_name in apps:
        try:
            subprocess.Popen([apps[app_name]], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'App não encontrado'}), 404

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Iniciar threads de monitoramento
    print("🚗 Iniciando Central Multimídia...")
    
    # Thread GPS
    gps_t = threading.Thread(target=gps_thread, daemon=True)
    gps_t.start()
    print("📍 Thread GPS iniciada")
    
    # Thread OBD (só inicia se tiver dispositivo)
    obd_t = threading.Thread(target=obd_thread, daemon=True)
    obd_t.start()
    print("🔧 Thread OBD iniciada")
    
    print("\n" + "="*50)
    print("🌐 Acesse: http://localhost:5000")
    print("="*50 + "\n")
    
    # Iniciar servidor Flask
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
