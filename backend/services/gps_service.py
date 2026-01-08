"""
Pi-Car - Servico GPS (gpsd)

Gerencia conexao e leitura de dados GPS.
"""

import threading
import config

# Dados globais de GPS (atualizados pela thread)
gps_data = {
    'lat': None,
    'lon': None,
    'speed': 0,
    'altitude': None,
    'satellites': 0,
    'connected': False
}


class GPSService:
    """Servico para interacao com GPS via gpsd"""

    def __init__(self, host=None, port=None):
        self.host = host or config.GPS_HOST
        self.port = port or config.GPS_PORT
        self._thread = None
        self._running = False

    def start(self):
        """Inicia thread de monitoramento GPS"""
        if self._thread is None or not self._thread.is_alive():
            self._running = True
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._thread.start()
            print("Thread GPS iniciada")

    def stop(self):
        """Para thread de monitoramento"""
        self._running = False

    def _monitor_loop(self):
        """Loop de monitoramento GPS"""
        global gps_data

        try:
            from gps3 import gps3
            gps_socket = gps3.GPSDSocket()
            data_stream = gps3.DataStream()
            gps_socket.connect(host=self.host, port=self.port)
            gps_socket.watch()

            for new_data in gps_socket:
                if not self._running:
                    break

                if new_data:
                    data_stream.unpack(new_data)

                    if data_stream.TPV['lat'] != 'n/a':
                        gps_data['connected'] = True
                        gps_data['lat'] = data_stream.TPV['lat']
                        gps_data['lon'] = data_stream.TPV['lon']
                        gps_data['speed'] = float(data_stream.TPV['speed'] or 0) * 3.6  # m/s -> km/h
                        gps_data['altitude'] = data_stream.TPV['alt']

                    if data_stream.SKY['satellites'] != 'n/a':
                        sats = data_stream.SKY['satellites']
                        if isinstance(sats, list):
                            gps_data['satellites'] = len([s for s in sats if s.get('used')])

        except Exception as e:
            gps_data['connected'] = False
            print(f"GPS thread erro: {e}")

    def get_data(self):
        """Retorna dados atuais do GPS"""
        return gps_data
