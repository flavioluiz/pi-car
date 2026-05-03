"""
Servicos de rede leves para status de Wi-Fi.

O foco aqui e resiliencia: a interface consulta este modulo com frequencia,
entao toda deteccao usa cache curto e subprocessos com timeout agressivo.
"""

from __future__ import annotations

import copy
import subprocess
import threading
import time
from datetime import datetime, timezone
from shutil import which
from typing import Any, Dict


INITIAL_WIFI_DATA: Dict[str, Any] = {
    'connected': False,
    'state': 'unknown',
    'ssid': '',
    'interface': '',
    'last_checked_at': None,
    'source': '',
}

wifi_data: Dict[str, Any] = copy.deepcopy(INITIAL_WIFI_DATA)


class NetworkService:
    def __init__(self, cache_ttl_s: float = 5.0, command_timeout_s: float = 0.35):
        self._cache_ttl_s = cache_ttl_s
        self._command_timeout_s = command_timeout_s
        self._lock = threading.Lock()
        self._last_refresh_monotonic = 0.0

    def get_wifi_status(self, force: bool = False) -> Dict[str, Any]:
        now = time.monotonic()
        if not force and (now - self._last_refresh_monotonic) < self._cache_ttl_s:
            with self._lock:
                return copy.deepcopy(wifi_data)

        refreshed = self._probe_wifi()
        refreshed['last_checked_at'] = datetime.now(timezone.utc).isoformat()

        with self._lock:
            wifi_data.update(refreshed)
            self._last_refresh_monotonic = now
            return copy.deepcopy(wifi_data)

    def _probe_wifi(self) -> Dict[str, Any]:
        for probe in (self._probe_iwgetid, self._probe_nmcli, self._probe_ip_link):
            result = probe()
            if result:
                return result
        return {
            'connected': False,
            'state': 'unknown',
            'ssid': '',
            'interface': '',
            'source': 'unavailable',
        }

    def _run_command(self, args: list[str]) -> subprocess.CompletedProcess[str] | None:
        if not args or which(args[0]) is None:
            return None

        try:
            return subprocess.run(
                args,
                capture_output=True,
                text=True,
                check=False,
                timeout=self._command_timeout_s,
            )
        except (subprocess.TimeoutExpired, OSError):
            return None

    def _probe_iwgetid(self) -> Dict[str, Any] | None:
        ssid_cmd = self._run_command(['iwgetid', '-r'])
        if ssid_cmd is None:
            return None

        ssid = (ssid_cmd.stdout or '').strip()
        if ssid:
            iface_cmd = self._run_command(['iwgetid', '-a'])
            interface = ''
            if iface_cmd and iface_cmd.stdout:
                interface = iface_cmd.stdout.split()[0].strip()

            return {
                'connected': True,
                'state': 'connected',
                'ssid': ssid,
                'interface': interface,
                'source': 'iwgetid',
            }

        return {
            'connected': False,
            'state': 'disconnected',
            'ssid': '',
            'interface': '',
            'source': 'iwgetid',
        }

    def _probe_nmcli(self) -> Dict[str, Any] | None:
        result = self._run_command(['nmcli', '-t', '-f', 'DEVICE,TYPE,STATE,CONNECTION', 'device'])
        if result is None:
            return None

        lines = [line.strip() for line in (result.stdout or '').splitlines() if line.strip()]
        wifi_entries = [line.split(':', 3) for line in lines if ':wifi:' in line or ':802-11-wireless:' in line]
        if not wifi_entries:
            return {
                'connected': False,
                'state': 'unknown',
                'ssid': '',
                'interface': '',
                'source': 'nmcli',
            }

        for entry in wifi_entries:
            if len(entry) < 4:
                continue
            device, _kind, state, connection = entry
            normalized_state = (state or '').strip().lower()
            if normalized_state == 'connected':
                return {
                    'connected': True,
                    'state': 'connected',
                    'ssid': '' if connection == '--' else connection,
                    'interface': device,
                    'source': 'nmcli',
                }

        device = wifi_entries[0][0] if wifi_entries and wifi_entries[0] else ''
        return {
            'connected': False,
            'state': 'disconnected',
            'ssid': '',
            'interface': device,
            'source': 'nmcli',
        }

    def _probe_ip_link(self) -> Dict[str, Any] | None:
        result = self._run_command(['ip', '-o', 'link', 'show'])
        if result is None:
            return None

        lines = [line.strip() for line in (result.stdout or '').splitlines() if line.strip()]
        wifi_interface = ''
        for line in lines:
            if ': wl' in line or ': wlan' in line:
                try:
                    wifi_interface = line.split(':', 2)[1].strip()
                except IndexError:
                    wifi_interface = ''
                break

        if not wifi_interface:
            return {
                'connected': False,
                'state': 'unknown',
                'ssid': '',
                'interface': '',
                'source': 'ip',
            }

        return {
            'connected': False,
            'state': 'disconnected',
            'ssid': '',
            'interface': wifi_interface,
            'source': 'ip',
        }


network_service = NetworkService()
