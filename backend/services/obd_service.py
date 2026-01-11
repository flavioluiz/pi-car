"""
Pi-Car - OBD-II Service

Manages OBD-II connection and vehicle data reading via USB adapter.
Discovers supported commands and queries all available metrics.
"""

import os
import threading
import time
import logging
from typing import Dict, Any, Optional, List

import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global OBD data - shared with routes
obd_data: Dict[str, Any] = {
    'connected': False,
    'supported_commands': [],
    'metrics': {},
    'error': None,
}

# Commands we want to query (in priority order)
# Will only query those that the vehicle supports
DESIRED_COMMANDS = [
    'RPM',
    'SPEED',
    'COOLANT_TEMP',
    'THROTTLE_POS',
    'ENGINE_LOAD',
    'INTAKE_TEMP',
    'MAF',
    'FUEL_LEVEL',
    'INTAKE_PRESSURE',
    'TIMING_ADVANCE',
    'RUN_TIME',
    'FUEL_PRESSURE',
    'BAROMETRIC_PRESSURE',
    'AMBIANT_AIR_TEMP',
    'OIL_TEMP',
    'FUEL_RATE',
]

# Human-readable labels and units for metrics
METRIC_INFO = {
    'RPM': {'label': 'RPM', 'unit': 'rpm'},
    'SPEED': {'label': 'Speed', 'unit': 'km/h'},
    'COOLANT_TEMP': {'label': 'Coolant', 'unit': '°C'},
    'THROTTLE_POS': {'label': 'Throttle', 'unit': '%'},
    'ENGINE_LOAD': {'label': 'Load', 'unit': '%'},
    'INTAKE_TEMP': {'label': 'Intake', 'unit': '°C'},
    'MAF': {'label': 'MAF', 'unit': 'g/s'},
    'FUEL_LEVEL': {'label': 'Fuel', 'unit': '%'},
    'INTAKE_PRESSURE': {'label': 'MAP', 'unit': 'kPa'},
    'TIMING_ADVANCE': {'label': 'Timing', 'unit': '°'},
    'RUN_TIME': {'label': 'Run Time', 'unit': 's'},
    'FUEL_PRESSURE': {'label': 'Fuel Press', 'unit': 'kPa'},
    'BAROMETRIC_PRESSURE': {'label': 'Baro', 'unit': 'kPa'},
    'AMBIANT_AIR_TEMP': {'label': 'Ambient', 'unit': '°C'},
    'OIL_TEMP': {'label': 'Oil', 'unit': '°C'},
    'FUEL_RATE': {'label': 'Fuel Rate', 'unit': 'L/h'},
}


class OBDService:
    """Service class for OBD-II vehicle data reading."""

    _instance_counter = 0

    def __init__(self, device: str = None):
        """Initialize OBD service.

        Args:
            device: Serial device path (default: from config)
        """
        OBDService._instance_counter += 1
        self._instance_id = OBDService._instance_counter
        logger.info(f"OBDService __init__ called, instance_id={self._instance_id}")

        self.device = device or config.OBD_DEVICE
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self._connection = None
        self._supported_commands: List[str] = []
        self._retry_delay = 5  # seconds between connection retries

    def _check_device(self) -> bool:
        """Check if the OBD device exists."""
        if os.path.exists(self.device):
            logger.info(f"OBD device found: {self.device}")
            return True
        else:
            logger.warning(f"OBD device not found: {self.device}")
            return False

    def start(self) -> bool:
        """Start the OBD monitoring thread.

        Returns:
            True if started successfully, False otherwise.
        """
        logger.info(f"start() called, device={self.device}")

        if not self._check_device():
            obd_data['error'] = f'Device not found: {self.device}'
            obd_data['connected'] = False
            return False

        if self._thread is None or not self._thread.is_alive():
            self._running = True
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._thread.start()
            logger.info("OBD monitoring thread started")
            return True

        return True

    def stop(self) -> None:
        """Stop the OBD monitoring thread."""
        self._running = False
        if self._connection:
            try:
                self._connection.close()
            except:
                pass
        obd_data['connected'] = False
        logger.info("OBD service stopped")

    def _discover_commands(self, connection) -> List[str]:
        """Discover which commands the vehicle supports.

        Args:
            connection: OBD connection object

        Returns:
            List of supported command names
        """
        import obd

        supported = []
        for cmd_name in DESIRED_COMMANDS:
            try:
                cmd = getattr(obd.commands, cmd_name, None)
                if cmd and cmd in connection.supported_commands:
                    supported.append(cmd_name)
                    logger.debug(f"Command supported: {cmd_name}")
            except Exception as e:
                logger.debug(f"Error checking command {cmd_name}: {e}")

        logger.info(f"Discovered {len(supported)} supported commands: {supported}")
        return supported

    def _query_metrics(self, connection) -> Dict[str, Any]:
        """Query all supported metrics from the vehicle.

        Args:
            connection: OBD connection object

        Returns:
            Dict of metric values
        """
        import obd

        metrics = {}
        for cmd_name in self._supported_commands:
            try:
                cmd = getattr(obd.commands, cmd_name)
                response = connection.query(cmd)

                if response.value is not None:
                    # Extract numeric value (handle pint units)
                    value = response.value
                    if hasattr(value, 'magnitude'):
                        value = value.magnitude

                    metrics[cmd_name] = {
                        'value': round(value, 1) if isinstance(value, float) else value,
                        'label': METRIC_INFO.get(cmd_name, {}).get('label', cmd_name),
                        'unit': METRIC_INFO.get(cmd_name, {}).get('unit', ''),
                    }
            except Exception as e:
                logger.debug(f"Error querying {cmd_name}: {e}")

        return metrics

    def _monitor_loop(self) -> None:
        """Main monitoring loop - connects and queries OBD data."""
        global obd_data

        while self._running:
            try:
                import obd

                logger.info(f"Connecting to OBD at {self.device}...")
                connection = obd.OBD(self.device)

                if connection.is_connected():
                    logger.info(f"OBD connected! Protocol: {connection.protocol_name()}")
                    self._connection = connection

                    # Discover supported commands
                    self._supported_commands = self._discover_commands(connection)

                    with self._lock:
                        obd_data['connected'] = True
                        obd_data['supported_commands'] = self._supported_commands
                        obd_data['error'] = None

                    # Main query loop
                    while self._running and connection.is_connected():
                        try:
                            metrics = self._query_metrics(connection)

                            with self._lock:
                                obd_data['metrics'] = metrics

                            time.sleep(0.5)

                        except Exception as e:
                            logger.warning(f"Query error: {e}")
                            time.sleep(1)

                    # Connection lost
                    logger.warning("OBD connection lost")
                    with self._lock:
                        obd_data['connected'] = False
                        obd_data['metrics'] = {}

                else:
                    logger.warning("Could not connect to OBD")
                    with self._lock:
                        obd_data['connected'] = False
                        obd_data['error'] = 'Connection failed'

                # Close connection before retry
                try:
                    connection.close()
                except:
                    pass

            except Exception as e:
                logger.error(f"OBD thread error: {e}")
                with self._lock:
                    obd_data['connected'] = False
                    obd_data['error'] = str(e)

            # Wait before retry
            if self._running:
                logger.info(f"Retrying connection in {self._retry_delay}s...")
                time.sleep(self._retry_delay)

    def get_status(self) -> Dict[str, Any]:
        """Get current OBD status and data."""
        with self._lock:
            return obd_data.copy()

    def get_supported_commands(self) -> List[str]:
        """Get list of supported command names."""
        with self._lock:
            return obd_data.get('supported_commands', []).copy()


# Singleton instance
_service_instance: Optional[OBDService] = None


def get_obd_service() -> OBDService:
    """Get or create the OBD service singleton."""
    global _service_instance
    if _service_instance is None:
        logger.info("Creating new OBDService singleton")
        _service_instance = OBDService()
    return _service_instance


def set_obd_service(service: OBDService) -> None:
    """Set the OBD service singleton (for initialization)."""
    global _service_instance
    _service_instance = service
    logger.info("OBDService singleton set externally")
