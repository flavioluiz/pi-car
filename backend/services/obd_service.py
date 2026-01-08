"""
Pi-Car - Servico OBD-II

Gerencia conexao e leitura de dados do veiculo via OBD-II.
"""

import threading
import time
import config

# Dados globais de OBD (atualizados pela thread)
obd_data = {
    'rpm': 0,
    'speed': 0,
    'coolant_temp': 0,
    'throttle': 0,
    'fuel_level': 0,
    'connected': False
}


class OBDService:
    """Servico para interacao com OBD-II"""

    def __init__(self, device=None):
        self.device = device or config.OBD_DEVICE
        self._thread = None
        self._running = False

    def start(self):
        """Inicia thread de monitoramento OBD"""
        if self._thread is None or not self._thread.is_alive():
            self._running = True
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._thread.start()
            print("Thread OBD iniciada")

    def stop(self):
        """Para thread de monitoramento"""
        self._running = False

    def _monitor_loop(self):
        """Loop de monitoramento OBD-II"""
        global obd_data

        try:
            import obd
            connection = obd.OBD(self.device)

            if connection.is_connected():
                obd_data['connected'] = True

                while self._running:
                    try:
                        # RPM
                        rpm = connection.query(obd.commands.RPM)
                        if rpm.value:
                            obd_data['rpm'] = rpm.value.magnitude

                        # Velocidade
                        speed = connection.query(obd.commands.SPEED)
                        if speed.value:
                            obd_data['speed'] = speed.value.magnitude

                        # Temperatura
                        temp = connection.query(obd.commands.COOLANT_TEMP)
                        if temp.value:
                            obd_data['coolant_temp'] = temp.value.magnitude

                        # Acelerador
                        throttle = connection.query(obd.commands.THROTTLE_POS)
                        if throttle.value:
                            obd_data['throttle'] = throttle.value.magnitude

                        time.sleep(0.5)

                    except Exception as e:
                        print(f"OBD query erro: {e}")
                        time.sleep(2)
            else:
                obd_data['connected'] = False

        except Exception as e:
            obd_data['connected'] = False
            print(f"OBD thread erro: {e}")

    def get_data(self):
        """Retorna dados atuais do OBD"""
        return obd_data
