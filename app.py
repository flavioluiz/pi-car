#!/usr/bin/env python3
"""
Central Multimidia Veicular - Interface Web Unificada
Integra: MPD (musica), GPS (gpsd), OBD-II (diagnostico)

Autor: Flavio @ ITA
Uso: python3 app.py
Acesse: http://localhost:5000
"""

from flask import Flask, render_template
import config

# Criar aplicacao Flask
app = Flask(
    __name__,
    template_folder='frontend/templates',
    static_folder='frontend/static'
)

# Registrar blueprints
from backend.routes import music_bp, gps_bp, vehicle_bp, system_bp

app.register_blueprint(music_bp, url_prefix='/api/music')
app.register_blueprint(gps_bp, url_prefix='/api/gps')
app.register_blueprint(vehicle_bp, url_prefix='/api/vehicle')
app.register_blueprint(system_bp, url_prefix='/api')


@app.route('/')
def index():
    """Pagina principal"""
    return render_template('index.html')


if __name__ == '__main__':
    # Iniciar servicos de monitoramento
    print("Iniciando Central Multimidia...")

    # Importar e iniciar servicos
    from backend.services import GPSService, OBDService

    # Thread GPS
    gps_service = GPSService()
    gps_service.start()
    print("Thread GPS iniciada")

    # Thread OBD
    obd_service = OBDService()
    obd_service.start()
    print("Thread OBD iniciada")

    print("")
    print("=" * 50)
    print(f"Acesse: http://localhost:{config.FLASK_PORT}")
    print("=" * 50)
    print("")

    # Iniciar servidor Flask
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
        threaded=True
    )
