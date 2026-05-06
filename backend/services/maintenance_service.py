"""
Pi-Car - rotinas simples de manutencao do app.

Expõe:
- git pull no repositorio local
- reinicio do processo atual
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


class MaintenanceService:
    def __init__(self):
        self.repo_dir = Path(__file__).resolve().parents[2]
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._status = {
            'running': False,
            'last_action': None,
            'last_started_at': None,
            'last_finished_at': None,
            'last_success_at': None,
            'last_error': None,
            'last_summary': 'No maintenance action has run yet.',
            'last_output': '',
            'repo_dir': str(self.repo_dir),
            'branch': self._current_branch(),
            'head': self._current_head(),
        }

    def _snapshot(self) -> dict:
        status = dict(self._status)
        for key in ('last_started_at', 'last_finished_at', 'last_success_at'):
            status[key] = _isoformat(status[key])
        status['git_available'] = shutil.which('git') is not None
        return status

    def get_status(self) -> dict:
        with self._lock:
            return self._snapshot()

    def start_action(self, action: str) -> dict:
        action = (action or '').strip().lower()
        if action not in {'update', 'restart'}:
            return {'accepted': False, 'message': 'Unknown maintenance action.'}

        with self._lock:
            if self._status['running']:
                status = self._snapshot()
                status['accepted'] = False
                status['message'] = 'A maintenance action is already running.'
                return status

            if action == 'update' and shutil.which('git') is None:
                self._status.update({
                    'last_error': 'git is not installed on this system.',
                    'last_summary': 'Maintenance tools are unavailable.',
                    'last_output': 'git is not installed on this system.',
                })
                status = self._snapshot()
                status['accepted'] = False
                status['message'] = 'git is not installed on this system.'
                return status

            self._status.update({
                'running': True,
                'last_action': action,
                'last_started_at': _utc_now(),
                'last_finished_at': None,
                'last_error': None,
                'last_summary': 'Action started.',
                'last_output': '',
                'branch': self._current_branch(),
                'head': self._current_head(),
            })
            self._thread = threading.Thread(
                target=self._run_action,
                kwargs={'action': action},
                daemon=True,
                name=f'maintenance-{action}',
            )
            self._thread.start()
            status = self._snapshot()
            status['accepted'] = True
            status['message'] = f'{action} started.'
            return status

    def _run_action(self, *, action: str) -> None:
        output = []
        error = None
        summary = ''

        try:
            if action == 'update':
                summary, action_output = self._run_update()
                output.append(action_output)
            elif action == 'restart':
                summary, action_output = self._schedule_restart()
                output.append(action_output)
            else:
                raise RuntimeError(f'Unsupported action: {action}')
        except Exception as exc:
            error = str(exc)
            summary = 'Maintenance action failed.'
            output.append(error)
        finally:
            finished_at = _utc_now()
            with self._lock:
                self._status.update({
                    'running': False,
                    'last_finished_at': finished_at,
                    'last_error': error,
                    'last_summary': summary or 'Maintenance action finished.',
                    'last_output': '\n\n'.join(chunk for chunk in output if chunk).strip(),
                    'branch': self._current_branch(),
                    'head': self._current_head(),
                })
                if error is None:
                    self._status['last_success_at'] = finished_at

    def _run_update(self) -> tuple[str, str]:
        completed = subprocess.run(
            ['git', 'pull', '--ff-only'],
            cwd=self.repo_dir,
            check=False,
            capture_output=True,
            text=True,
        )
        stdout = (completed.stdout or '').strip()
        stderr = (completed.stderr or '').strip()
        combined = '\n'.join(part for part in (stdout, stderr) if part).strip() or 'No output.'
        if completed.returncode != 0:
            raise RuntimeError(f'git pull failed (exit {completed.returncode}): {combined}')
        if 'Already up to date.' in combined:
            return 'Repository is already up to date.', combined
        return 'Update completed successfully.', combined

    def _schedule_restart(self) -> tuple[str, str]:
        parent_pid = os.getpid()
        command_line = [sys.executable, *sys.argv]
        helper_code = f"""
import os
import subprocess
import time

parent_pid = {parent_pid!r}
cwd = {str(self.repo_dir)!r}
cmd = {command_line!r}

while True:
    try:
        os.kill(parent_pid, 0)
    except OSError:
        break
    time.sleep(0.2)

subprocess.Popen(cmd, cwd=cwd, start_new_session=True)
"""

        subprocess.Popen(
            [sys.executable, '-c', helper_code],
            cwd=self.repo_dir,
            start_new_session=True,
        )

        def _shutdown_current():
            time.sleep(0.5)
            os._exit(0)

        threading.Thread(target=_shutdown_current, daemon=True, name='app-restart-exit').start()
        output = (
            "Restart scheduled.\n"
            f"Current PID: {parent_pid}\n"
            f"Exec after exit: {' '.join(command_line)}"
        )
        return 'Application restart scheduled.', output

    def _current_branch(self) -> str:
        return self._git_read(['git', 'branch', '--show-current']) or 'detached'

    def _current_head(self) -> str:
        return self._git_read(['git', 'rev-parse', '--short', 'HEAD']) or '--'

    def _git_read(self, command: list[str]) -> str:
        completed = subprocess.run(
            command,
            cwd=self.repo_dir,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            return ''
        return (completed.stdout or '').strip()


maintenance_service = MaintenanceService()
