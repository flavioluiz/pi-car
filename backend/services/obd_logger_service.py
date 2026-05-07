"""
Pi-Car - OBD logger e sincronizacao remota.

Grava snapshots OBD locais em JSONL e faz upload periodico para o
picasso-repo via rsync/ssh, sem depender de git no Raspberry Pi.
"""

from __future__ import annotations

import copy
import json
import os
import re
import shutil
import socket
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import config


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _slugify(value: str) -> str:
    text = re.sub(r'[^a-zA-Z0-9._-]+', '-', (value or '').strip())
    return text.strip('-').lower() or 'unknown'


class OBDLoggerService:
    """Persist OBD snapshots locally and sync them to a remote host."""

    def __init__(self):
        self.repo_dir = Path(__file__).resolve().parents[2]
        self.state_file = self.repo_dir / '.obd_logger_status.json'
        self.local_dir = (self.repo_dir / getattr(config, 'OBD_LOG_LOCAL_DIRECTORY', 'telemetry/obd')).resolve()
        self.remote = getattr(config, 'OBD_LOG_REMOTE', getattr(config, 'MEDIA_SYNC_REMOTE', 'root@picasso-repo'))
        self.remote_dir = getattr(config, 'OBD_LOG_REMOTE_DIRECTORY', '/repository/OBDLogs/')
        self.ssh_key = Path(getattr(config, 'OBD_LOG_SSH_KEY', getattr(config, 'MEDIA_SYNC_SSH_KEY', ''))).expanduser()
        self.log_interval_seconds = float(getattr(config, 'OBD_LOG_INTERVAL_SECONDS', 1.0))
        self.sync_interval_seconds = int(getattr(config, 'OBD_LOG_SYNC_INTERVAL_SECONDS', 900))
        self.device_name = _slugify(getattr(config, 'OBD_LOG_DEVICE_NAME', socket.gethostname()))
        self.enabled = bool(getattr(config, 'OBD_LOG_ENABLED', True))
        self._lock = threading.Lock()
        self._writer_thread: threading.Thread | None = None
        self._sync_thread: threading.Thread | None = None
        self._running = False
        self._last_sample_time: str | None = None
        self._session_id: str | None = None
        self._session_started_at: str | None = None
        self._last_seen_connected_at_monotonic: float | None = None
        self._session_idle_timeout_s = max(self.log_interval_seconds * 3, 10.0)
        self._last_wifi_connected = False
        self._status = {
            'running': False,
            'writer_running': False,
            'sync_running': False,
            'enabled': self.enabled,
            'last_log_at': None,
            'last_sample_time': None,
            'last_file': None,
            'current_session_id': None,
            'current_session_started_at': None,
            'last_sync_started_at': None,
            'last_sync_finished_at': None,
            'last_sync_success_at': None,
            'last_sync_error': None,
            'last_sync_summary': 'OBD log sync has not run yet.',
            'last_sync_output': '',
            'local_dir': str(self.local_dir),
            'remote': self.remote,
            'remote_dir': self.remote_dir,
            'device_name': self.device_name,
            'log_interval_seconds': self.log_interval_seconds,
            'sync_interval_seconds': self.sync_interval_seconds,
            'sync_policy': 'on-first-network-connection-or-manual',
        }
        self._load_persisted_status()

    def _preflight_error(self) -> str | None:
        if shutil.which('rsync') is None:
            return 'rsync is not installed on this system.'
        if not self.ssh_key.exists():
            return f'SSH key not found: {self.ssh_key}'
        if not self.ssh_key.is_file():
            return f'SSH key path is not a regular file: {self.ssh_key}'
        return None

    def _snapshot(self) -> dict:
        status = dict(self._status)
        for key in ('last_log_at', 'last_sync_started_at', 'last_sync_finished_at', 'last_sync_success_at'):
            status[key] = _isoformat(status[key])
        preflight_error = self._preflight_error()
        status['preflight_error'] = preflight_error
        status['configured'] = preflight_error is None
        status['enabled'] = self.enabled
        return status

    def get_status(self) -> dict:
        with self._lock:
            return self._snapshot()

    def start(self) -> None:
        with self._lock:
            if self._running or not self.enabled:
                return
            self._running = True
            self._status['running'] = True
            self._status['enabled'] = self.enabled
            self.local_dir.mkdir(parents=True, exist_ok=True)
            self._writer_thread = threading.Thread(target=self._writer_loop, daemon=True, name='obd-log-writer')
            self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True, name='obd-log-sync')
            self._writer_thread.start()
            self._sync_thread.start()

    def stop(self) -> None:
        with self._lock:
            self._running = False
            self._status['running'] = False
            self._status['writer_running'] = False
            self._status['sync_running'] = False

    def update_settings(self, settings: Dict[str, Any]) -> dict:
        enabled = settings.get('enabled')
        if enabled is None:
            return self.get_status()

        enabled = bool(enabled)
        with self._lock:
            self.enabled = enabled
            self._status['enabled'] = enabled
            self._persist_status()

        if enabled:
            self.start()
        else:
            self.stop()
        return self.get_status()

    def start_sync(self, *, force: bool = False, reason: str = 'manual') -> dict:
        with self._lock:
            if not self.enabled:
                status = self._snapshot()
                status['accepted'] = False
                status['message'] = 'OBD logger is disabled.'
                return status
            if self._status['sync_running']:
                status = self._snapshot()
                status['accepted'] = False
                status['message'] = 'An OBD log sync is already running.'
                return status

            preflight_error = self._preflight_error()
            if preflight_error is not None:
                self._status.update({
                    'last_sync_error': preflight_error,
                    'last_sync_summary': 'OBD log sync is not configured.',
                    'last_sync_output': preflight_error,
                })
                status = self._snapshot()
                status['accepted'] = False
                status['message'] = preflight_error
                return status

            self._status.update({
                'sync_running': True,
                'last_sync_started_at': _utc_now(),
                'last_sync_error': None,
                'last_sync_summary': f'OBD log sync started ({reason}).',
                'last_sync_output': '',
            })
            threading.Thread(
                target=self._run_sync,
                kwargs={'reason': reason, 'force': force},
                daemon=True,
                name='obd-log-sync-manual',
            ).start()
            status = self._snapshot()
            status['accepted'] = True
            status['message'] = 'OBD log sync started.'
            return status

    def _writer_loop(self) -> None:
        while True:
            with self._lock:
                running = self._running
                self._status['writer_running'] = running
            if not running:
                break

            try:
                self._write_latest_snapshot()
            except Exception as exc:
                with self._lock:
                    self._status['last_sync_summary'] = 'OBD logger write failed.'
                    self._status['last_sync_output'] = str(exc)
            time.sleep(self.log_interval_seconds)

        with self._lock:
            self._status['writer_running'] = False

    def _sync_loop(self) -> None:
        from backend.services.network_service import network_service

        while True:
            with self._lock:
                running = self._running
                self._status['sync_running'] = self._status.get('sync_running', False)
            if not running:
                break

            wifi_status = network_service.get_wifi_status(force=True)
            wifi_connected = bool(wifi_status.get('connected'))

            with self._lock:
                should_sync = (
                    self._running
                    and not self._status['sync_running']
                    and wifi_connected
                    and not self._last_wifi_connected
                )
                self._last_wifi_connected = wifi_connected

                if should_sync:
                    preflight_error = self._preflight_error()
                    if preflight_error is not None:
                        self._status['last_sync_error'] = preflight_error
                        self._status['last_sync_summary'] = 'OBD log sync is not configured.'
                        self._status['last_sync_output'] = preflight_error
                    else:
                        self._status['sync_running'] = True
                        self._status['last_sync_started_at'] = _utc_now()
                        self._status['last_sync_error'] = None
                        self._status['last_sync_summary'] = 'OBD log sync started after network connection.'
                        self._status['last_sync_output'] = ''

            if should_sync:
                self._run_sync(reason='network-connected', force=False)

            time.sleep(min(max(self.sync_interval_seconds, 5), 30))

        with self._lock:
            self._status['sync_running'] = False

    def _write_latest_snapshot(self) -> None:
        from backend.services.obd_service import get_obd_service

        snapshot = get_obd_service().get_status()
        if not snapshot.get('connected'):
            self._maybe_close_session()
            return

        self._last_seen_connected_at_monotonic = time.monotonic()
        sample_time = snapshot.get('metadata', {}).get('sample_time')
        if not sample_time or sample_time == self._last_sample_time:
            return

        record = self._build_record(snapshot)
        target_path = self._path_for_record(record)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with target_path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(record, ensure_ascii=True, separators=(',', ':')) + '\n')
            handle.flush()
            os.fsync(handle.fileno())

        self._last_sample_time = sample_time
        with self._lock:
            self._status['last_log_at'] = _utc_now()
            self._status['last_sample_time'] = sample_time
            self._status['last_file'] = str(target_path)
            self._status['current_session_id'] = self._session_id
            self._status['current_session_started_at'] = self._session_started_at

    def _build_record(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        from backend.services.gps_service import gps_data
        from backend.services.network_service import network_service

        metadata = copy.deepcopy(snapshot.get('metadata') or {})
        connection = copy.deepcopy(snapshot.get('connection') or {})
        direct = copy.deepcopy(snapshot.get('direct') or {})
        inferred = copy.deepcopy(snapshot.get('inferred') or {})
        metrics = copy.deepcopy(snapshot.get('metrics') or {})
        gps_snapshot = copy.deepcopy(gps_data)
        wifi_snapshot = network_service.get_wifi_status(force=False)
        wifi_connected = bool(wifi_snapshot.get('connected'))
        gps_connected = bool(gps_snapshot.get('connected'))
        sample_time = metadata.get('sample_time')
        logged_at = _utc_now().isoformat()
        session_id = self._ensure_session(sample_time or logged_at)

        return {
            'logged_at': logged_at,
            'session_id': session_id,
            'device_name': self.device_name,
            'vehicle': metadata.get('vehicle'),
            'vin': metadata.get('vin'),
            'supported_commands': list(snapshot.get('supported_commands') or []),
            'time_context': {
                'sample_time': sample_time,
                'logged_at': logged_at,
                'wifi_connected': wifi_connected,
                'wifi_last_checked_at': wifi_snapshot.get('last_checked_at'),
                'gps_connected': gps_connected,
                'gps_has_fix': gps_connected and gps_snapshot.get('lat') is not None and gps_snapshot.get('lon') is not None,
                'clock_confidence': 'network_likely' if wifi_connected else 'offline_unverified',
            },
            'connection': {
                'adapter': connection.get('adapter'),
                'protocol': connection.get('protocol'),
                'port': connection.get('port'),
                'baudrate': connection.get('baudrate'),
                'ecu_ready': connection.get('ecu_ready'),
            },
            'metadata': {
                'sample_time': sample_time,
                'last_dynamic_sample_time': metadata.get('last_dynamic_sample_time'),
                'dynamic_stale': metadata.get('dynamic_stale'),
                'dynamic_stale_age_s': metadata.get('dynamic_stale_age_s'),
                'last_successful_command': metadata.get('last_successful_command'),
            },
            'gps': gps_snapshot,
            'wifi': wifi_snapshot,
            'direct': direct,
            'inferred': inferred,
            'metrics': {key: value.get('value') for key, value in metrics.items()},
        }

    def _ensure_session(self, timestamp: str) -> str:
        if self._session_id:
            return self._session_id

        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except Exception:
            dt = _utc_now()
        self._session_id = dt.strftime('session-%Y-%m-%dT%H-%M-%SZ')
        self._session_started_at = dt.isoformat()
        return self._session_id

    def _maybe_close_session(self) -> None:
        if not self._session_id or self._last_seen_connected_at_monotonic is None:
            return
        idle_s = time.monotonic() - self._last_seen_connected_at_monotonic
        if idle_s < self._session_idle_timeout_s:
            return

        self._session_id = None
        self._session_started_at = None
        self._last_seen_connected_at_monotonic = None
        with self._lock:
            self._status['current_session_id'] = None
            self._status['current_session_started_at'] = None

    def _path_for_record(self, record: Dict[str, Any]) -> Path:
        timestamp = record.get('metadata', {}).get('sample_time') or record.get('logged_at')
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except Exception:
            dt = _utc_now()
        vin = _slugify(record.get('vin') or self.device_name)
        return (
            self.local_dir
            / f'{dt.year:04d}'
            / f'{dt.month:02d}'
            / f'{dt.day:02d}'
            / vin
            / f"{record.get('session_id') or 'session-unknown'}.jsonl"
        )

    def _run_sync(self, *, reason: str, force: bool) -> None:
        output = []
        error = None
        summary = 'OBD log sync finished.'
        try:
            self.local_dir.mkdir(parents=True, exist_ok=True)
            output.append(self._run_rsync())
            summary = f'OBD logs synced successfully ({reason}).'
        except Exception as exc:
            error = str(exc)
            summary = 'OBD log sync failed.'
            output.append(error)
        finally:
            finished_at = _utc_now()
            with self._lock:
                self._status.update({
                    'sync_running': False,
                    'last_sync_finished_at': finished_at,
                    'last_sync_error': error,
                    'last_sync_summary': summary,
                    'last_sync_output': '\n\n'.join(chunk for chunk in output if chunk).strip(),
                })
                if error is None:
                    self._status['last_sync_success_at'] = finished_at

    def _run_rsync(self) -> str:
        command = [
            'rsync',
            '-avz',
            '--mkpath',
            '-e',
            f'ssh -i {self.ssh_key} -o StrictHostKeyChecking=accept-new',
            f'{self.local_dir}/',
            f'{self.remote}:{self.remote_dir.rstrip("/")}/{self.device_name}/',
        ]
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        if completed.returncode != 0:
            raise RuntimeError(
                f"rsync failed for OBD logs (exit {completed.returncode}): {stderr or stdout or 'no output'}"
            )
        return stdout or 'No changes.'

    def _load_persisted_status(self) -> None:
        if not self.state_file.exists():
            return
        try:
            persisted = json.loads(self.state_file.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return

        enabled = persisted.get('enabled')
        if isinstance(enabled, bool):
            self.enabled = enabled
            self._status['enabled'] = enabled
        for key in ('last_log_at', 'last_sync_started_at', 'last_sync_finished_at', 'last_sync_success_at'):
            parsed = _parse_datetime(persisted.get(key))
            if parsed is not None:
                self._status[key] = parsed

    def _persist_status(self) -> None:
        payload = {
            'enabled': self.enabled,
            'last_log_at': _isoformat(self._status.get('last_log_at')),
            'last_sync_started_at': _isoformat(self._status.get('last_sync_started_at')),
            'last_sync_finished_at': _isoformat(self._status.get('last_sync_finished_at')),
            'last_sync_success_at': _isoformat(self._status.get('last_sync_success_at')),
        }
        try:
            self.state_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')
        except OSError:
            return


obd_logger_service = OBDLoggerService()
