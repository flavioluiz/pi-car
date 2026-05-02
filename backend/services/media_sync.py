"""
Pi-Car - Sincronizacao de biblioteca musical remota.

Baixa `Musics` e `Playlists` via rsync/ssh e atualiza o MPD ao final.
"""

from __future__ import annotations

import shutil
import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import config
from backend.services.mpd_service import MPDService, music_library


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


@dataclass(frozen=True)
class SyncTarget:
    label: str
    remote_dir: str
    local_dir: Path


class MediaSyncService:
    """Executa sync em background e expõe status simples para a UI."""

    def __init__(self):
        self.remote = config.MEDIA_SYNC_REMOTE
        self.ssh_key = Path(config.MEDIA_SYNC_SSH_KEY).expanduser()
        self.min_interval_seconds = int(config.MEDIA_SYNC_MIN_INTERVAL_SECONDS)
        self.targets = (
            SyncTarget(
                label='musics',
                remote_dir=config.MEDIA_SYNC_REMOTE_MUSIC_DIRECTORY,
                local_dir=Path(config.MEDIA_SYNC_LOCAL_MUSIC_DIRECTORY).expanduser(),
            ),
            SyncTarget(
                label='playlists',
                remote_dir=config.MEDIA_SYNC_REMOTE_PLAYLIST_DIRECTORY,
                local_dir=Path(config.MEDIA_SYNC_LOCAL_PLAYLIST_DIRECTORY).expanduser(),
            ),
        )
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._status = {
            'running': False,
            'last_reason': None,
            'last_started_at': None,
            'last_finished_at': None,
            'last_success_at': None,
            'last_error': None,
            'last_summary': 'Sync has not run yet.',
            'last_output': '',
            'cooldown_seconds': self.min_interval_seconds,
            'remote': self.remote,
            'music_local_dir': str(self.targets[0].local_dir),
            'playlist_local_dir': str(self.targets[1].local_dir),
            'music_remote_dir': self.targets[0].remote_dir,
            'playlist_remote_dir': self.targets[1].remote_dir,
        }

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
        for key in ('last_started_at', 'last_finished_at', 'last_success_at'):
            status[key] = _isoformat(status[key])
        preflight_error = self._preflight_error()
        status['preflight_error'] = preflight_error
        status['configured'] = preflight_error is None
        status['can_sync_now'] = preflight_error is None and self._can_sync_now()
        return status

    def _can_sync_now(self) -> bool:
        last_success = self._status.get('last_success_at')
        if not last_success:
            return True
        elapsed = (_utc_now() - last_success).total_seconds()
        return elapsed >= self.min_interval_seconds

    def get_status(self) -> dict:
        with self._lock:
            return self._snapshot()

    def start_sync(self, *, force: bool = False, reason: str = 'manual') -> dict:
        with self._lock:
            if self._status['running']:
                status = self._snapshot()
                status['accepted'] = False
                status['message'] = 'A sync is already running.'
                return status

            preflight_error = self._preflight_error()
            if preflight_error is not None:
                self._status.update({
                    'last_error': preflight_error,
                    'last_summary': 'Media sync is not configured.',
                    'last_output': preflight_error,
                })
                status = self._snapshot()
                status['accepted'] = False
                status['message'] = preflight_error
                return status

            if not force and not self._can_sync_now():
                status = self._snapshot()
                status['accepted'] = False
                status['skipped'] = True
                status['message'] = 'Sync skipped because cooldown is still active.'
                return status

            self._status.update({
                'running': True,
                'last_reason': reason,
                'last_started_at': _utc_now(),
                'last_error': None,
                'last_summary': 'Sync started.',
                'last_output': '',
            })
            self._thread = threading.Thread(
                target=self._run_sync,
                kwargs={'reason': reason},
                daemon=True,
                name='media-sync',
            )
            self._thread.start()
            status = self._snapshot()
            status['accepted'] = True
            status['message'] = 'Sync started.'
            return status

    def _run_sync(self, *, reason: str) -> None:
        started_at = _utc_now()
        output_chunks: list[str] = []
        summary = 'Sync finished.'
        error = None

        try:
            for target in self.targets:
                target.local_dir.mkdir(parents=True, exist_ok=True)
                output_chunks.append(self._run_rsync(target))

            mpd_summary = MPDService().refresh_database(wait=True)
            music_library.refresh(force=True)
            output_chunks.append(mpd_summary)
            summary = 'Musics and playlists synced successfully.'
        except Exception as exc:
            error = str(exc)
            summary = 'Sync failed.'
            output_chunks.append(error)
        finally:
            finished_at = _utc_now()
            with self._lock:
                self._status.update({
                    'running': False,
                    'last_finished_at': finished_at,
                    'last_error': error,
                    'last_summary': summary,
                    'last_output': '\n\n'.join(chunk for chunk in output_chunks if chunk).strip(),
                })
                if error is None:
                    self._status['last_success_at'] = finished_at
                elif self._status.get('last_started_at') is None:
                    self._status['last_started_at'] = started_at

    def _run_rsync(self, target: SyncTarget) -> str:
        command = [
            'rsync',
            '-avz',
            '--delete',
            '-e',
            f'ssh -i {self.ssh_key} -o StrictHostKeyChecking=accept-new',
            f'{self.remote}:{target.remote_dir}',
            f'{target.local_dir}/',
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
                f"rsync failed for {target.label} (exit {completed.returncode}): {stderr or stdout or 'no output'}"
            )
        return f"[{target.label}]\n{stdout or 'No changes.'}"


media_sync_service = MediaSyncService()
