"""
Pi-Car - OBD-II Service

Reads an ELM327/FTDI USB adapter directly over serial and publishes a
normalized vehicle snapshot for the dashboard.
"""

import copy
import logging
import os
import re
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STABLE_PORT = getattr(config, 'OBD_DEVICE', '/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_ABAQJ7HX-if00-port0')
FALLBACK_PORT = getattr(config, 'OBD_FALLBACK_DEVICE', '/dev/ttyUSB0')
BAUDRATE = getattr(config, 'OBD_BAUDRATE', 38400)
POLL_INTERVAL = getattr(config, 'OBD_POLL_INTERVAL', 0.8)
SECONDARY_POLL_INTERVAL = getattr(config, 'OBD_SECONDARY_POLL_INTERVAL', 0.5)
STALE_TIMEOUT = getattr(config, 'OBD_STALE_TIMEOUT', 6.0)

PID_INFO = {
    'RPM': {'label': 'RPM', 'unit': 'rpm'},
    'SPEED': {'label': 'Speed', 'unit': 'km/h'},
    'COOLANT_TEMP': {'label': 'Coolant', 'unit': 'C'},
    'INTAKE_TEMP': {'label': 'Intake', 'unit': 'C'},
    'INTAKE_PRESSURE': {'label': 'MAP', 'unit': 'kPa'},
    'ENGINE_LOAD': {'label': 'Load', 'unit': '%'},
    'THROTTLE_POS': {'label': 'Throttle', 'unit': '%'},
    'TIMING_ADVANCE': {'label': 'Timing', 'unit': 'deg'},
    'SHORT_FUEL_TRIM_1': {'label': 'STFT B1', 'unit': '%'},
    'LONG_FUEL_TRIM_1': {'label': 'LTFT B1', 'unit': '%'},
    'O2_B1S1_VOLTAGE': {'label': 'O2 B1S1', 'unit': 'V'},
    'O2_B1S1_TRIM': {'label': 'O2 B1S1 STFT', 'unit': '%'},
    'O2_B1S2_VOLTAGE': {'label': 'O2 B1S2', 'unit': 'V'},
    'ELM_VOLTAGE': {'label': 'Battery', 'unit': 'V'},
    'FUEL_RATE_GASOLINE_E27': {'label': 'Fuel E27', 'unit': 'L/h'},
    'FUEL_RATE_ETHANOL': {'label': 'Fuel EtOH', 'unit': 'L/h'},
    'INSTANT_KM_L': {'label': 'Instant', 'unit': 'km/L'},
    'TRIP_AVERAGE_KM_L': {'label': 'Trip Avg', 'unit': 'km/L'},
}

GEAR_UNKNOWN_HOLD_S = 2.0
GEAR_CONFIRMATION_TIME_S = 0.8
GEAR_RECENT_CONFIRMATION_S = 1.0
GEAR_UPSHIFT_RPM = 3000
GEAR_DOWNSHIFT_RPM = 1300

GEAR_ENTRY_BANDS = {
    1: (120.0, None),
    2: (75.0, 120.0),
    3: (50.0, 75.0),
    4: (39.0, 50.0),
    5: (31.0, 39.0),
}

GEAR_HOLD_BANDS = {
    1: (118.0, None),
    2: (73.0, 122.0),
    3: (48.0, 77.0),
    4: (37.0, 52.0),
    5: (29.0, 41.0),
}

INITIAL_DATA: Dict[str, Any] = {
    'connected': False,
    'supported_commands': [],
    'metrics': {},
    'connection': {
        'connected': False,
        'port': None,
        'stable_port': STABLE_PORT,
        'fallback_port': FALLBACK_PORT,
        'baudrate': BAUDRATE,
        'adapter': None,
        'protocol': None,
        'ecu_ready': False,
    },
    'direct': {
        'rpm': None,
        'speed_kmh': None,
        'coolant_temp_c': None,
        'intake_temp_c': None,
        'map_kpa': None,
        'engine_load_pct': None,
        'throttle_pct': None,
        'timing_advance_deg': None,
        'short_fuel_trim_b1_pct': None,
        'long_fuel_trim_b1_pct': None,
        'fuel_system_status_1': None,
        'fuel_system_status_2': None,
        'secondary_air_status': None,
        'o2_sensors_present': [],
        'o2_b1s1_voltage_v': None,
        'o2_b1s1_stft_pct': None,
        'o2_b1s2_voltage_v': None,
        'obd_standard': None,
        'adapter_voltage_v': None,
        'mil_on': None,
        'distance_with_mil_km': None,
        'active_dtcs': [],
        'pending_dtcs': [],
    },
    'inferred': {
        'engine_on': False,
        'stationary': True,
        'fuel': getattr(config, 'OBD_DEFAULT_FUEL', 'gasoline_e27'),
        'fuel_rate_l_h_gasoline_e27': None,
        'fuel_rate_l_h_ethanol': None,
        'selected_fuel_rate_l_h': None,
        'instant_km_l': None,
        'instant_l_100km': None,
        'trip_consumed_l': 0.0,
        'trip_distance_km': 0.0,
        'trip_average_km_l': None,
        'gear_state': 'UNKNOWN',
        'gear': None,
        'gear_ratio': None,
        'gear_confidence': 'none',
        'gear_reason': 'not_initialized',
        'gear_display': '--',
        'shift_hint': 'none',
        'shift_hint_display': '',
        'coolant_alert': False,
        'battery_alert': False,
    },
    'metadata': {
        'vehicle': getattr(config, 'OBD_VEHICLE_NAME', 'Citroen C3 Picasso 2013 1.5 Flex'),
        'vin': None,
        'sample_time': None,
        'last_dynamic_sample_time': None,
        'dynamic_stale': False,
        'dynamic_stale_age_s': None,
        'last_successful_command': None,
    },
    'error': None,
}

obd_data: Dict[str, Any] = copy.deepcopy(INITIAL_DATA)


def _bytes_from_hex(response: str, prefix: str, expected_count: int) -> Optional[List[int]]:
    frame = _find_hex_frame(response, prefix)
    if not frame:
        return None
    payload = frame[len(prefix):]
    if len(payload) < expected_count * 2:
        return None
    return [int(payload[i:i + 2], 16) for i in range(0, expected_count * 2, 2)]


def _find_hex_frame(response: str, prefix: str) -> Optional[str]:
    compact = re.sub(r'[^0-9A-F]', '', response.upper())
    index = compact.find(prefix)
    if index < 0:
        return None
    return compact[index:]


def _round(value: Optional[float], digits: int = 1) -> Optional[float]:
    if value is None:
        return None
    return round(value, digits)


def _decode_dtcs(response: str, prefix: str) -> List[str]:
    frame = _find_hex_frame(response, prefix)
    if not frame:
        return []
    payload = frame[len(prefix):]
    codes = []
    type_chars = ['P', 'C', 'B', 'U']
    for i in range(0, len(payload) - 3, 4):
        raw = payload[i:i + 4]
        if raw == '0000':
            continue
        first = int(raw[0], 16)
        codes.append(f"{type_chars[first >> 2]}{first & 0x3}{raw[1:]}")
    return codes


def _set_valid(target: Dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        target[key] = value


def _decode_fuel_system_status(value: int) -> Optional[str]:
    mapping = {
        0x00: 'not_supported',
        0x01: 'open_loop_insufficient_temp',
        0x02: 'closed_loop_o2_feedback',
        0x04: 'open_loop_engine_load_or_decel',
        0x08: 'open_loop_system_failure',
        0x10: 'closed_loop_fault_detected',
    }
    return mapping.get(value, f'unknown_0x{value:02X}')


def _decode_secondary_air_status(value: int) -> Optional[str]:
    mapping = {
        0x01: 'upstream',
        0x02: 'downstream_of_catalyst',
        0x04: 'outside_atmosphere_or_off',
        0x08: 'pump_commanded_on_diagnostic',
    }
    return mapping.get(value, f'unknown_0x{value:02X}')


def _decode_o2_sensors_present(value: int) -> List[str]:
    sensors = []
    if value & 0x01:
        sensors.append('B1S1')
    if value & 0x02:
        sensors.append('B1S2')
    if value & 0x04:
        sensors.append('B1S3')
    if value & 0x08:
        sensors.append('B1S4')
    if value & 0x10:
        sensors.append('B2S1')
    if value & 0x20:
        sensors.append('B2S2')
    if value & 0x40:
        sensors.append('B2S3')
    if value & 0x80:
        sensors.append('B2S4')
    return sensors


def _decode_obd_standard(value: int) -> Optional[str]:
    mapping = {
        0x01: 'obd_ii_carb',
        0x02: 'obd_epa',
        0x03: 'obd_and_obd_ii',
        0x04: 'obd_i',
        0x05: 'not_obd_compliant',
        0x06: 'eobd',
        0x07: 'eobd_and_obd_ii',
        0x08: 'eobd_and_obd',
        0x09: 'eobd_obd_obd_ii',
        0x0A: 'jobd',
        0x0B: 'jobd_and_obd_ii',
        0x0C: 'jobd_and_eobd',
        0x0D: 'jobd_eobd_obd_ii',
    }
    return mapping.get(value, f'unknown_0x{value:02X}')


class OBDService:
    """Persistent ELM327 monitor for the vehicle dashboard."""

    def __init__(self, device: str = None):
        self.device = device or STABLE_PORT
        self.fallback_device = FALLBACK_PORT
        self.baudrate = BAUDRATE
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self._serial = None
        self._retry_delay = 5
        self._supported_commands = ['RPM', 'SPEED', 'COOLANT_TEMP', 'INTAKE_PRESSURE']
        self._last_sample_at: Optional[float] = None
        self._fuel = getattr(config, 'OBD_DEFAULT_FUEL', 'gasoline_e27')
        self._trip_consumed_l = 0.0
        self._trip_distance_km = 0.0
        self._last_secondary_poll_at = 0.0
        self._last_medium_poll_at = 0.0
        self._last_slow_poll_at = 0.0
        self._last_extended_poll_at = 0.0
        self._last_dynamic_pid_at = 0.0
        self._last_dynamic_sample_time: Optional[str] = None
        self._last_successful_command: Optional[str] = None
        self._gear_confirmed_state: str = 'UNKNOWN'
        self._gear_confirmed_gear: Optional[int] = None
        self._gear_confirmed_at: Optional[float] = None
        self._gear_candidate_key: Optional[str] = None
        self._gear_candidate_count = 0
        self._gear_candidate_since: Optional[float] = None
        self._last_confirmed_gear: Optional[int] = None
        self._last_confirmed_gear_at: Optional[float] = None

    def _resolve_device(self) -> Optional[str]:
        if os.path.exists(self.device):
            return self.device
        if os.path.exists(self.fallback_device):
            return self.fallback_device
        return None

    def start(self) -> bool:
        port = self._resolve_device()
        if not port:
            self._set_error(f'Device not found: {self.device} or {self.fallback_device}')
            return False

        if self._thread is None or not self._thread.is_alive():
            self._running = True
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._thread.start()
            logger.info("OBD monitoring thread started")
        return True

    def stop(self) -> None:
        self._running = False
        self._close_serial()
        self._reset_gear_state()
        with self._lock:
            obd_data['connected'] = False
            obd_data['connection']['connected'] = False
        logger.info("OBD service stopped")

    def reset_trip(self) -> None:
        with self._lock:
            self._trip_consumed_l = 0.0
            self._trip_distance_km = 0.0
            obd_data['inferred']['trip_consumed_l'] = 0.0
            obd_data['inferred']['trip_distance_km'] = 0.0
            obd_data['inferred']['trip_average_km_l'] = None

    def update_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        fuel = settings.get('fuel')
        if fuel in ('gasoline_e27', 'ethanol'):
            with self._lock:
                self._fuel = fuel
                obd_data['inferred']['fuel'] = fuel
        return self.get_status()

    def _set_error(self, message: str) -> None:
        with self._lock:
            obd_data['connected'] = False
            obd_data['connection']['connected'] = False
            obd_data['error'] = message

    def _remember_successful_command(self, command: str) -> None:
        self._last_dynamic_pid_at = time.monotonic()
        self._last_dynamic_sample_time = datetime.now(timezone.utc).isoformat()
        self._last_successful_command = command

    def _open_serial(self, port: str):
        import serial

        return serial.Serial(
            port=port,
            baudrate=self.baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.15,
            write_timeout=1,
        )

    def _close_serial(self) -> None:
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
        self._serial = None

    def _command(self, command: str, timeout: float = 1.2) -> str:
        if not self._serial:
            return ''
        self._serial.reset_input_buffer()
        self._serial.write((command + '\r').encode('ascii'))
        deadline = time.monotonic() + timeout
        chunks = []
        while time.monotonic() < deadline:
            data = self._serial.read(256)
            if data:
                text = data.decode('ascii', errors='ignore')
                chunks.append(text)
                if '>' in text:
                    break
            else:
                time.sleep(0.02)
        return ''.join(chunks).replace('\r', '\n').replace('>', '').strip()

    def _initialize_elm(self) -> Dict[str, Any]:
        adapter = self._command('ATZ', timeout=2.5)
        for command in ('ATE0', 'ATL0', 'ATS0', 'ATH0', 'ATSP0'):
            self._command(command)

        ready_response = self._command('0100', timeout=2.5)
        protocol_response = self._command('ATDP', timeout=1.5)

        supported = self._decode_supported_pids(ready_response)
        if supported:
            self._supported_commands = supported

        vin = self._read_vin()
        return {
            'adapter': self._clean_adapter_name(adapter),
            'protocol': self._clean_protocol_name(protocol_response),
            'ecu_ready': bool(_find_hex_frame(ready_response, '4100')),
            'supported_commands': self._supported_commands,
            'vin': vin,
        }

    def _clean_adapter_name(self, response: str) -> Optional[str]:
        for line in response.splitlines():
            clean = line.strip()
            if clean and not clean.startswith('AT'):
                return clean
        return None

    def _clean_protocol_name(self, response: str) -> Optional[str]:
        clean = response.replace('ATDP', '').strip()
        if clean.upper().startswith('AUTO,'):
            clean = clean[5:].strip()
        return clean or None

    def _decode_supported_pids(self, response: str) -> List[str]:
        pid_names = {
            0x01: 'STATUS',
            0x03: 'FUEL_STATUS',
            0x04: 'ENGINE_LOAD',
            0x05: 'COOLANT_TEMP',
            0x06: 'SHORT_FUEL_TRIM_1',
            0x07: 'LONG_FUEL_TRIM_1',
            0x0B: 'INTAKE_PRESSURE',
            0x0C: 'RPM',
            0x0D: 'SPEED',
            0x0E: 'TIMING_ADVANCE',
            0x0F: 'INTAKE_TEMP',
            0x11: 'THROTTLE_POS',
            0x12: 'SECONDARY_AIR_STATUS',
            0x13: 'O2_SENSORS_PRESENT',
            0x14: 'O2_B1S1',
            0x15: 'O2_B1S2',
            0x1C: 'OBD_STANDARD',
            0x21: 'DISTANCE_WITH_MIL',
        }
        data = _bytes_from_hex(response, '4100', 4)
        if not data:
            return list(pid_names.values())

        bitfield = int.from_bytes(bytes(data), 'big')
        supported = []
        for pid in range(1, 33):
            if bitfield & (1 << (32 - pid)) and pid in pid_names:
                supported.append(pid_names[pid])
        return supported

    def _read_vin(self) -> Optional[str]:
        response = self._command('0902', timeout=3)
        compact = re.sub(r'[^0-9A-F]', '', response.upper())
        if '4902' not in compact:
            return None
        bytes_out = []
        for i in range(0, len(compact) - 1, 2):
            try:
                byte = int(compact[i:i + 2], 16)
            except ValueError:
                continue
            if 32 <= byte <= 126:
                bytes_out.append(chr(byte))
        text = ''.join(bytes_out)
        match = re.search(r'[A-HJ-NPR-Z0-9]{17}', text)
        return match.group(0) if match else None

    def _read_direct_data(self, now: float) -> Dict[str, Any]:
        direct = copy.deepcopy(obd_data['direct'])
        primary_values = {
            'rpm': self._parse_two_byte('010C', '410C', lambda a, b: ((a * 256) + b) / 4, timeout=0.55),
            'speed_kmh': self._parse_one_byte('010D', '410D', lambda a: a, timeout=0.45),
        }
        for key, value in primary_values.items():
            _set_valid(direct, key, value)

        if now - self._last_secondary_poll_at >= SECONDARY_POLL_INTERVAL:
            secondary_values = {
                'map_kpa': self._parse_one_byte('010B', '410B', lambda a: a, timeout=0.55),
                'engine_load_pct': self._parse_one_byte('0104', '4104', lambda a: a * 100 / 255, timeout=0.55),
                'throttle_pct': self._parse_one_byte('0111', '4111', lambda a: a * 100 / 255, timeout=0.55),
            }
            for key, value in secondary_values.items():
                _set_valid(direct, key, value)
            self._last_secondary_poll_at = now

        if now - self._last_medium_poll_at >= 1:
            medium_values = {
                'coolant_temp_c': self._parse_one_byte('0105', '4105', lambda a: a - 40, timeout=0.65),
                'intake_temp_c': self._parse_one_byte('010F', '410F', lambda a: a - 40, timeout=0.65),
                'short_fuel_trim_b1_pct': self._parse_one_byte('0106', '4106', lambda a: (a - 128) * 100 / 128, timeout=0.65),
                'long_fuel_trim_b1_pct': self._parse_one_byte('0107', '4107', lambda a: (a - 128) * 100 / 128, timeout=0.65),
                'timing_advance_deg': self._parse_one_byte('010E', '410E', lambda a: (a / 2) - 64, timeout=0.65),
            }
            for key, value in medium_values.items():
                _set_valid(direct, key, value)

            voltage_response = self._command('ATRV', timeout=0.6)
            voltage_match = re.search(r'(\d+(?:\.\d+)?)\s*V', voltage_response, re.IGNORECASE)
            if voltage_match:
                direct['adapter_voltage_v'] = float(voltage_match.group(1))
            self._last_medium_poll_at = now

        if now - self._last_extended_poll_at >= 5:
            fuel_status = _bytes_from_hex(self._command('0103', timeout=0.8), '4103', 2)
            if fuel_status:
                direct['fuel_system_status_1'] = _decode_fuel_system_status(fuel_status[0])
                direct['fuel_system_status_2'] = _decode_fuel_system_status(fuel_status[1])

            secondary_air = _bytes_from_hex(self._command('0112', timeout=0.8), '4112', 1)
            if secondary_air:
                direct['secondary_air_status'] = _decode_secondary_air_status(secondary_air[0])

            o2_present = _bytes_from_hex(self._command('0113', timeout=0.8), '4113', 1)
            if o2_present:
                direct['o2_sensors_present'] = _decode_o2_sensors_present(o2_present[0])

            o2_b1s1 = _bytes_from_hex(self._command('0114', timeout=0.8), '4114', 2)
            if o2_b1s1:
                direct['o2_b1s1_voltage_v'] = o2_b1s1[0] / 200
                direct['o2_b1s1_stft_pct'] = (o2_b1s1[1] - 128) * 100 / 128

            o2_b1s2 = _bytes_from_hex(self._command('0115', timeout=0.8), '4115', 2)
            if o2_b1s2:
                direct['o2_b1s2_voltage_v'] = o2_b1s2[0] / 200

            obd_standard = _bytes_from_hex(self._command('011C', timeout=0.8), '411C', 1)
            if obd_standard:
                direct['obd_standard'] = _decode_obd_standard(obd_standard[0])

            self._last_extended_poll_at = now

        if now - self._last_slow_poll_at >= 30:
            status = _bytes_from_hex(self._command('0101', timeout=0.8), '4101', 4)
            if status:
                direct['mil_on'] = bool(status[0] & 0x80)

            distance_with_mil_km = self._parse_two_byte(
                '0121',
                '4121',
                lambda a, b: (a * 256) + b,
                timeout=0.8,
            )
            _set_valid(direct, 'distance_with_mil_km', distance_with_mil_km)

            active_response = self._command('03', timeout=0.9)
            pending_response = self._command('07', timeout=0.9)
            if _find_hex_frame(active_response, '43'):
                direct['active_dtcs'] = _decode_dtcs(active_response, '43')
            if _find_hex_frame(pending_response, '47'):
                direct['pending_dtcs'] = _decode_dtcs(pending_response, '47')
            self._last_slow_poll_at = now

        return direct

    def _parse_one_byte(self, command: str, prefix: str, convert, timeout: float = 1.2) -> Optional[float]:
        data = _bytes_from_hex(self._command(command, timeout=timeout), prefix, 1)
        if not data:
            return None
        self._remember_successful_command(command)
        return convert(data[0])

    def _parse_two_byte(self, command: str, prefix: str, convert, timeout: float = 1.2) -> Optional[float]:
        data = _bytes_from_hex(self._command(command, timeout=timeout), prefix, 2)
        if not data:
            return None
        self._remember_successful_command(command)
        return convert(data[0], data[1])

    def _calculate_inferred(self, direct: Dict[str, Any], now: float) -> Dict[str, Any]:
        rpm = direct.get('rpm') or 0
        speed = direct.get('speed_kmh') or 0
        coolant = direct.get('coolant_temp_c')
        voltage = direct.get('adapter_voltage_v')
        gasoline_l_h = self._estimate_fuel_rate(direct, 'gasoline_e27')
        ethanol_l_h = self._estimate_fuel_rate(direct, 'ethanol')
        selected_rate = gasoline_l_h if self._fuel == 'gasoline_e27' else ethanol_l_h

        if self._last_sample_at is not None and selected_rate is not None:
            dt_h = max(0, min(now - self._last_sample_at, 5)) / 3600
            self._trip_consumed_l += selected_rate * dt_h
            self._trip_distance_km += speed * dt_h
        self._last_sample_at = now

        instant_km_l = None
        instant_l_100km = None
        if selected_rate and speed > 0:
            instant_km_l = speed / selected_rate
            instant_l_100km = 100 / instant_km_l if instant_km_l else None

        trip_average = None
        if self._trip_consumed_l > 0 and self._trip_distance_km > 0:
            trip_average = self._trip_distance_km / self._trip_consumed_l

        stale_age = round(max(0.0, time.monotonic() - self._last_dynamic_pid_at), 1)
        dynamic_stale = stale_age > 1.5
        gear = self._calculate_gear_inference(
            direct,
            dynamic_stale=dynamic_stale,
            dynamic_stale_age_s=stale_age,
            now=now,
        )
        shift_hint = self._calculate_shift_hint(direct, gear)

        return {
            'engine_on': rpm > 0,
            'stationary': speed == 0,
            'fuel': self._fuel,
            'fuel_rate_l_h_gasoline_e27': _round(gasoline_l_h, 2),
            'fuel_rate_l_h_ethanol': _round(ethanol_l_h, 2),
            'selected_fuel_rate_l_h': _round(selected_rate, 2),
            'instant_km_l': _round(instant_km_l, 1),
            'instant_l_100km': _round(instant_l_100km, 1),
            'trip_consumed_l': _round(self._trip_consumed_l, 3),
            'trip_distance_km': _round(self._trip_distance_km, 2),
            'trip_average_km_l': _round(trip_average, 1),
            'gear_state': gear['state'],
            'gear': gear['gear'],
            'gear_ratio': gear['ratio'],
            'gear_confidence': gear['confidence'],
            'gear_reason': gear['reason'],
            'gear_display': gear['display'],
            'shift_hint': shift_hint,
            'shift_hint_display': '↑' if shift_hint == 'up' else '↓' if shift_hint == 'down' else '',
            'coolant_alert': coolant is not None and coolant >= 105,
            'battery_alert': rpm > 0 and voltage is not None and voltage < 13.0,
        }

    def _reset_gear_state(self) -> None:
        self._gear_confirmed_state = 'UNKNOWN'
        self._gear_confirmed_gear = None
        self._gear_confirmed_at = None
        self._gear_candidate_key = None
        self._gear_candidate_count = 0
        self._gear_candidate_since = None
        self._last_confirmed_gear = None
        self._last_confirmed_gear_at = None

    def _classify_gear_candidate(
        self,
        direct: Dict[str, Any],
        *,
        dynamic_stale: bool,
        dynamic_stale_age_s: Optional[float],
    ) -> Dict[str, Any]:
        rpm = direct.get('rpm')
        speed = direct.get('speed_kmh')
        engine_on = True if rpm is None else rpm > 0

        if rpm is None or speed is None or speed < 0 or rpm < 0:
            return {'state': 'UNKNOWN', 'gear': None, 'ratio': None, 'reason': 'missing_or_invalid_dynamic_data'}
        if rpm < 400 or engine_on is False:
            return {'state': 'OFF', 'gear': None, 'ratio': None, 'reason': 'engine_off_or_invalid_rpm'}
        if dynamic_stale or (dynamic_stale_age_s is not None and dynamic_stale_age_s > 1.5):
            return {'state': 'UNKNOWN', 'gear': None, 'ratio': None, 'reason': 'stale_dynamic_sample'}
        if speed < 8:
            return {'state': 'STOPPED', 'gear': None, 'ratio': None, 'reason': 'speed_below_inference_threshold'}

        ratio = rpm / speed

        if self._gear_confirmed_gear is not None:
            lower, upper = GEAR_HOLD_BANDS[self._gear_confirmed_gear]
            if ratio >= lower and (upper is None or ratio < upper):
                return {'state': 'IN_GEAR', 'gear': self._gear_confirmed_gear, 'ratio': _round(ratio, 1), 'reason': 'confirmed_gear_hysteresis_hold'}

        if self._gear_confirmed_state == 'DISENGAGED' and ratio < 33:
            return {'state': 'DISENGAGED', 'gear': None, 'ratio': _round(ratio, 1), 'reason': 'disengaged_hysteresis_hold'}
        if ratio < 31:
            return {'state': 'DISENGAGED', 'gear': None, 'ratio': _round(ratio, 1), 'reason': 'ratio_below_engaged_threshold'}

        for gear, (lower, upper) in GEAR_ENTRY_BANDS.items():
            if ratio >= lower and (upper is None or ratio < upper):
                return {'state': 'IN_GEAR', 'gear': gear, 'ratio': _round(ratio, 1), 'reason': 'ratio_in_gear_band'}

        return {'state': 'UNKNOWN', 'gear': None, 'ratio': _round(ratio, 1), 'reason': 'ratio_outside_known_bands'}

    def _build_gear_output(
        self,
        *,
        state: str,
        gear: Optional[int],
        ratio: Optional[float],
        confidence: str,
        reason: str,
        retain_confirmed_gear: bool = False,
    ) -> Dict[str, Any]:
        if state == 'IN_GEAR' and gear is not None:
            display = str(gear)
        elif state == 'DISENGAGED':
            display = 'N'
        else:
            display = '--'

        output_gear = gear
        if retain_confirmed_gear and output_gear is None:
            output_gear = self._last_confirmed_gear
            if output_gear is not None:
                display = str(output_gear)

        return {
            'state': state,
            'gear': output_gear,
            'ratio': ratio,
            'confidence': confidence,
            'display': display,
            'reason': reason,
        }

    def _gear_boundary_distance(self, gear: Optional[int], ratio: Optional[float]) -> Optional[float]:
        if gear is None or ratio is None:
            return None
        lower, upper = GEAR_ENTRY_BANDS[gear]
        distances = [abs(ratio - lower)]
        if upper is not None:
            distances.append(abs(upper - ratio))
        return min(distances)

    def _gear_candidate_key_for(self, candidate: Dict[str, Any]) -> str:
        return f"{candidate['state']}:{candidate['gear'] if candidate['gear'] is not None else '-'}"

    def _gear_confidence(self, gear: Optional[int], ratio: Optional[float], now: float) -> str:
        if gear is None:
            return 'none'
        boundary_distance = self._gear_boundary_distance(gear, ratio)
        recently_confirmed = self._gear_confirmed_at is None or (now - self._gear_confirmed_at) < GEAR_RECENT_CONFIRMATION_S
        if recently_confirmed or (boundary_distance is not None and boundary_distance < 3.0):
            return 'medium'
        return 'high'

    def _calculate_shift_hint(self, direct: Dict[str, Any], gear: Dict[str, Any]) -> str:
        if gear.get('state') != 'IN_GEAR':
            return 'none'

        current_gear = gear.get('gear')
        rpm = direct.get('rpm')
        speed = direct.get('speed_kmh')
        if current_gear is None or rpm is None or speed is None or speed < 8:
            return 'none'

        if current_gear < max(GEAR_ENTRY_BANDS) and rpm >= GEAR_UPSHIFT_RPM:
            return 'up'
        if current_gear > min(GEAR_ENTRY_BANDS) and rpm <= GEAR_DOWNSHIFT_RPM:
            return 'down'
        return 'none'

    def _calculate_gear_inference(
        self,
        direct: Dict[str, Any],
        *,
        dynamic_stale: bool,
        dynamic_stale_age_s: Optional[float],
        now: float,
    ) -> Dict[str, Any]:
        candidate = self._classify_gear_candidate(
            direct,
            dynamic_stale=dynamic_stale,
            dynamic_stale_age_s=dynamic_stale_age_s,
        )
        candidate_key = self._gear_candidate_key_for(candidate)

        if candidate['state'] == 'UNKNOWN':
            self._gear_candidate_key = None
            self._gear_candidate_count = 0
            self._gear_candidate_since = None
            if self._last_confirmed_gear is not None and self._last_confirmed_gear_at is not None:
                if now - self._last_confirmed_gear_at <= GEAR_UNKNOWN_HOLD_S:
                    return self._build_gear_output(
                        state='UNKNOWN',
                        gear=None,
                        ratio=None,
                        confidence='low',
                        reason='stale_sample_retaining_last_confirmed_gear',
                        retain_confirmed_gear=True,
                    )
            return self._build_gear_output(
                state='UNKNOWN',
                gear=None,
                ratio=None,
                confidence='none',
                reason=candidate['reason'],
            )

        if candidate['state'] == 'OFF':
            self._gear_confirmed_state = 'OFF'
            self._gear_confirmed_gear = None
            self._gear_confirmed_at = now
            self._gear_candidate_key = None
            self._gear_candidate_count = 0
            self._gear_candidate_since = None
            self._last_confirmed_gear = None
            self._last_confirmed_gear_at = None
            return self._build_gear_output(state='OFF', gear=None, ratio=None, confidence='none', reason=candidate['reason'])

        if candidate['state'] == 'STOPPED':
            self._gear_confirmed_state = 'STOPPED'
            self._gear_confirmed_gear = None
            self._gear_confirmed_at = now
            self._gear_candidate_key = None
            self._gear_candidate_count = 0
            self._gear_candidate_since = None
            return self._build_gear_output(state='STOPPED', gear=None, ratio=None, confidence='none', reason=candidate['reason'])

        if candidate_key == self._gear_candidate_key:
            self._gear_candidate_count += 1
        else:
            self._gear_candidate_key = candidate_key
            self._gear_candidate_count = 1
            self._gear_candidate_since = now

        candidate_elapsed = now - (self._gear_candidate_since or now)

        if candidate['state'] == 'DISENGAGED':
            if self._gear_confirmed_state == 'DISENGAGED':
                return self._build_gear_output(
                    state='DISENGAGED',
                    gear=None,
                    ratio=candidate['ratio'],
                    confidence='none',
                    reason=candidate['reason'],
                )
            should_confirm = candidate['ratio'] is not None and (
                candidate['ratio'] < 24 or self._gear_candidate_count >= 2
            )
            if should_confirm:
                self._gear_confirmed_state = 'DISENGAGED'
                self._gear_confirmed_gear = None
                self._gear_confirmed_at = now
                return self._build_gear_output(
                    state='DISENGAGED',
                    gear=None,
                    ratio=candidate['ratio'],
                    confidence='none',
                    reason=candidate['reason'],
                )
            if self._gear_confirmed_gear is not None:
                return self._build_gear_output(
                    state='IN_GEAR',
                    gear=self._gear_confirmed_gear,
                    ratio=candidate['ratio'],
                    confidence=self._gear_confidence(self._gear_confirmed_gear, candidate['ratio'], now),
                    reason='awaiting_disengaged_confirmation',
                )
            return self._build_gear_output(state='UNKNOWN', gear=None, ratio=candidate['ratio'], confidence='none', reason='disengaged_pending_confirmation')

        if self._gear_confirmed_state == 'IN_GEAR' and self._gear_confirmed_gear == candidate['gear']:
            return self._build_gear_output(
                state='IN_GEAR',
                gear=candidate['gear'],
                ratio=candidate['ratio'],
                confidence=self._gear_confidence(candidate['gear'], candidate['ratio'], now),
                reason=candidate['reason'],
            )

        should_confirm = self._gear_candidate_count >= 2 or candidate_elapsed >= GEAR_CONFIRMATION_TIME_S
        if should_confirm:
            self._gear_confirmed_state = 'IN_GEAR'
            self._gear_confirmed_gear = candidate['gear']
            self._gear_confirmed_at = now
            self._last_confirmed_gear = candidate['gear']
            self._last_confirmed_gear_at = now
            return self._build_gear_output(
                state='IN_GEAR',
                gear=candidate['gear'],
                ratio=candidate['ratio'],
                confidence=self._gear_confidence(candidate['gear'], candidate['ratio'], now),
                reason=candidate['reason'],
            )

        if self._gear_confirmed_gear is not None:
            return self._build_gear_output(
                state='IN_GEAR',
                gear=self._gear_confirmed_gear,
                ratio=candidate['ratio'],
                confidence=self._gear_confidence(self._gear_confirmed_gear, candidate['ratio'], now),
                reason='holding_last_confirmed_gear',
            )

        return self._build_gear_output(
            state='UNKNOWN',
            gear=None,
            ratio=candidate['ratio'],
            confidence='none',
            reason='gear_candidate_not_yet_confirmed',
        )

    def _estimate_fuel_rate(self, direct: Dict[str, Any], fuel: str) -> Optional[float]:
        map_kpa = direct.get('map_kpa')
        rpm = direct.get('rpm')
        iat_c = direct.get('intake_temp_c')
        if not map_kpa or not rpm or iat_c is None:
            return None

        stft = direct.get('short_fuel_trim_b1_pct') or 0
        ltft = direct.get('long_fuel_trim_b1_pct') or 0
        displacement_l = getattr(config, 'OBD_ENGINE_DISPLACEMENT_L', 1.449)
        ve = getattr(config, 'OBD_VOLUMETRIC_EFFICIENCY', 0.78)
        afr = 13.2 if fuel == 'gasoline_e27' else 9.0
        fuel_density_g_l = 745 if fuel == 'gasoline_e27' else 789

        map_pa = map_kpa * 1000
        temp_k = iat_c + 273.15
        intake_events_per_s = rpm / 2 / 60
        volume_m3_s = displacement_l / 1000 * intake_events_per_s * ve
        air_g_s = (map_pa * volume_m3_s / (8.314 * temp_k)) * 28.97
        air_g_s *= 1 + ((stft + ltft) / 100)
        fuel_g_s = air_g_s / afr
        return fuel_g_s * 3600 / fuel_density_g_l

    def _metrics_from_snapshot(self, direct: Dict[str, Any], inferred: Dict[str, Any]) -> Dict[str, Any]:
        values = {
            'RPM': direct.get('rpm'),
            'SPEED': direct.get('speed_kmh'),
            'COOLANT_TEMP': direct.get('coolant_temp_c'),
            'INTAKE_TEMP': direct.get('intake_temp_c'),
            'INTAKE_PRESSURE': direct.get('map_kpa'),
            'ENGINE_LOAD': direct.get('engine_load_pct'),
            'THROTTLE_POS': direct.get('throttle_pct'),
            'TIMING_ADVANCE': direct.get('timing_advance_deg'),
            'SHORT_FUEL_TRIM_1': direct.get('short_fuel_trim_b1_pct'),
            'LONG_FUEL_TRIM_1': direct.get('long_fuel_trim_b1_pct'),
            'O2_B1S1_VOLTAGE': direct.get('o2_b1s1_voltage_v'),
            'O2_B1S1_TRIM': direct.get('o2_b1s1_stft_pct'),
            'O2_B1S2_VOLTAGE': direct.get('o2_b1s2_voltage_v'),
            'ELM_VOLTAGE': direct.get('adapter_voltage_v'),
            'FUEL_RATE_GASOLINE_E27': inferred.get('fuel_rate_l_h_gasoline_e27'),
            'FUEL_RATE_ETHANOL': inferred.get('fuel_rate_l_h_ethanol'),
            'INSTANT_KM_L': inferred.get('instant_km_l'),
            'TRIP_AVERAGE_KM_L': inferred.get('trip_average_km_l'),
        }
        return {
            key: {
                'value': _round(value, 1) if isinstance(value, float) else value,
                'label': PID_INFO[key]['label'],
                'unit': PID_INFO[key]['unit'],
            }
            for key, value in values.items()
            if value is not None
        }

    def _monitor_loop(self) -> None:
        while self._running:
            port = self._resolve_device()
            if not port:
                self._set_error(f'Device not found: {self.device} or {self.fallback_device}')
                time.sleep(self._retry_delay)
                continue

            try:
                logger.info(f"Connecting to OBD at {port} ({self.baudrate} baud)...")
                self._serial = self._open_serial(port)
                init = self._initialize_elm()
                self._last_secondary_poll_at = 0.0
                self._last_medium_poll_at = 0.0
                self._last_slow_poll_at = 0.0
                self._last_extended_poll_at = 0.0
                self._last_dynamic_pid_at = time.monotonic()
                self._last_dynamic_sample_time = None
                self._last_successful_command = None
                with self._lock:
                    obd_data['connected'] = True
                    obd_data['error'] = None
                    obd_data['supported_commands'] = init['supported_commands']
                    obd_data['connection'].update({
                        'connected': True,
                        'port': port,
                        'stable_port': self.device,
                        'fallback_port': self.fallback_device,
                        'baudrate': self.baudrate,
                        'adapter': init['adapter'],
                        'protocol': init['protocol'],
                        'ecu_ready': init['ecu_ready'],
                    })
                    obd_data['metadata']['vin'] = init['vin']

                while self._running:
                    loop_started_at = time.monotonic()
                    direct = self._read_direct_data(loop_started_at)
                    stale_age = time.monotonic() - self._last_dynamic_pid_at
                    if stale_age > STALE_TIMEOUT:
                        raise TimeoutError(f'OBD dynamic data stale for {stale_age:.1f}s')

                    inferred = self._calculate_inferred(direct, loop_started_at)
                    metrics = self._metrics_from_snapshot(direct, inferred)

                    with self._lock:
                        obd_data['connected'] = True
                        obd_data['connection']['connected'] = True
                        obd_data['direct'].update(direct)
                        obd_data['inferred'].update(inferred)
                        obd_data['metrics'] = metrics
                        obd_data['metadata']['sample_time'] = datetime.now(timezone.utc).isoformat()
                        obd_data['metadata']['last_dynamic_sample_time'] = self._last_dynamic_sample_time
                        obd_data['metadata']['dynamic_stale_age_s'] = round(stale_age, 1)
                        obd_data['metadata']['dynamic_stale'] = stale_age > 1.5
                        obd_data['metadata']['last_successful_command'] = self._last_successful_command
                        obd_data['error'] = None

                    loop_elapsed = time.monotonic() - loop_started_at
                    time.sleep(max(0.0, POLL_INTERVAL - loop_elapsed))

            except Exception as exc:
                logger.warning(f"OBD connection error: {exc}")
                self._set_error(str(exc))
            finally:
                self._last_sample_at = None
                self._reset_gear_state()
                self._close_serial()

            if self._running:
                time.sleep(self._retry_delay)

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return copy.deepcopy(obd_data)

    def get_supported_commands(self) -> List[str]:
        with self._lock:
            return list(obd_data.get('supported_commands', []))


_service_instance: Optional[OBDService] = None


def get_obd_service() -> OBDService:
    global _service_instance
    if _service_instance is None:
        _service_instance = OBDService()
    return _service_instance


def set_obd_service(service: OBDService) -> None:
    global _service_instance
    _service_instance = service
