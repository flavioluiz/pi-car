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
    def __init__(self, cache_ttl_s: float = 5.0, command_timeout_s: float = 0.35, scan_cache_ttl_s: float = 20.0):
        self._cache_ttl_s = cache_ttl_s
        self._command_timeout_s = command_timeout_s
        self._scan_cache_ttl_s = scan_cache_ttl_s
        self._lock = threading.Lock()
        self._last_refresh_monotonic = 0.0
        self._last_scan_monotonic = 0.0
        self._last_scan_results: list[Dict[str, Any]] = []

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

    def get_wifi_overview(self, force: bool = False) -> Dict[str, Any]:
        status = self.get_wifi_status(force=force)
        networks = self.list_wifi_networks(force=force)
        return {
            'status': status,
            'networks': networks,
        }

    def list_wifi_networks(self, force: bool = False) -> list[Dict[str, Any]]:
        now = time.monotonic()
        if not force and (now - self._last_scan_monotonic) < self._scan_cache_ttl_s:
            with self._lock:
                return copy.deepcopy(self._last_scan_results)

        status = self.get_wifi_status(force=force)
        networks = self._scan_wifi_networks(status=status, force=force)
        with self._lock:
            self._last_scan_monotonic = now
            self._last_scan_results = copy.deepcopy(networks)
            return copy.deepcopy(self._last_scan_results)

    def connect_wifi(self, ssid: str, password: str | None = None, interface: str | None = None) -> Dict[str, Any]:
        target_ssid = (ssid or '').strip()
        if not target_ssid:
            return {
                'success': False,
                'message': 'SSID is required.',
                'status': self.get_wifi_status(force=True),
                'networks': self.list_wifi_networks(force=True),
            }

        if which('nmcli') is None:
            return {
                'success': False,
                'message': 'nmcli is not available on this system.',
                'status': self.get_wifi_status(force=True),
                'networks': [],
            }

        command = ['nmcli', 'device', 'wifi', 'connect', target_ssid]
        if password:
            command.extend(['password', password])
        if interface:
            command.extend(['ifname', interface])

        result = self._run_command(command, timeout_s=25.0)
        if result is None:
            return {
                'success': False,
                'message': 'Wi-Fi connection command failed to start.',
                'status': self.get_wifi_status(force=True),
                'networks': self.list_wifi_networks(force=True),
            }

        status = self.get_wifi_status(force=True)
        networks = self.list_wifi_networks(force=True)
        stdout = (result.stdout or '').strip()
        stderr = (result.stderr or '').strip()
        if result.returncode != 0:
            return {
                'success': False,
                'message': stderr or stdout or f'nmcli failed with exit code {result.returncode}.',
                'status': status,
                'networks': networks,
            }

        return {
            'success': True,
            'message': stdout or f'Connected to {target_ssid}.',
            'status': status,
            'networks': networks,
        }

    def _run_command(self, args: list[str], timeout_s: float | None = None) -> subprocess.CompletedProcess[str] | None:
        if not args or which(args[0]) is None:
            return None

        try:
            return subprocess.run(
                args,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_s if timeout_s is not None else self._command_timeout_s,
            )
        except (subprocess.TimeoutExpired, OSError):
            return None

    def _split_nmcli_fields(self, line: str) -> list[str]:
        fields = []
        current = []
        escaped = False
        for char in line:
            if escaped:
                current.append(char)
                escaped = False
                continue
            if char == '\\':
                escaped = True
                continue
            if char == ':':
                fields.append(''.join(current))
                current = []
                continue
            current.append(char)
        fields.append(''.join(current))
        return fields

    def _scan_wifi_networks(self, *, status: Dict[str, Any], force: bool = False) -> list[Dict[str, Any]]:
        result = self._run_command(
            ['nmcli', '-t', '-f', 'IN-USE,SSID,SIGNAL,SECURITY', 'device', 'wifi', 'list', '--rescan', 'yes' if force else 'auto'],
            timeout_s=12.0,
        )
        if result is None:
            return []

        connected_ssid = (status.get('ssid') or '').strip()
        deduped: Dict[str, Dict[str, Any]] = {}
        for line in (result.stdout or '').splitlines():
            raw = line.strip()
            if not raw:
                continue
            fields = self._split_nmcli_fields(raw)
            if len(fields) < 4:
                continue
            in_use, ssid, signal, security = fields[0], fields[1].strip(), fields[2], fields[3].strip()
            if not ssid:
                continue
            try:
                signal_value = int(signal)
            except ValueError:
                signal_value = 0
            network = {
                'ssid': ssid,
                'signal': signal_value,
                'security': security or 'Open',
                'requires_password': bool(security and security != '--'),
                'connected': in_use == '*' or ssid == connected_ssid,
            }
            existing = deduped.get(ssid)
            if existing is None or network['signal'] > existing['signal'] or network['connected']:
                deduped[ssid] = network

        return sorted(
            deduped.values(),
            key=lambda item: (
                0 if item['connected'] else 1,
                -item['signal'],
                item['ssid'].casefold(),
            ),
        )

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
