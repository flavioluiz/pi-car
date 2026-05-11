import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

MODULE_PATH = Path(__file__).resolve().parents[1] / "backend" / "services" / "maintenance_service.py"
MODULE_SPEC = importlib.util.spec_from_file_location("maintenance_service_under_test", MODULE_PATH)
maintenance_service_module = importlib.util.module_from_spec(MODULE_SPEC)
assert MODULE_SPEC and MODULE_SPEC.loader
MODULE_SPEC.loader.exec_module(maintenance_service_module)
MaintenanceService = maintenance_service_module.MaintenanceService


class MaintenanceServiceVersionTest(unittest.TestCase):
    def test_update_summary_reports_new_repo_version_without_changing_startup_version(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "VERSION").write_text("0.5.3\n", encoding="utf-8")

            service = MaintenanceService()
            service.repo_dir = repo_dir
            service.version_file = repo_dir / "VERSION"
            service.startup_version = service._read_version()

            original_run = maintenance_service_module.subprocess.run

            def fake_run(command, cwd=None, check=False, capture_output=False, text=False):
                (repo_dir / "VERSION").write_text("0.5.4\n", encoding="utf-8")

                class Result:
                    returncode = 0
                    stdout = "Updating 123..456"
                    stderr = ""

                return Result()

            maintenance_service_module.subprocess.run = fake_run
            try:
                summary, output = service._run_update()
            finally:
                maintenance_service_module.subprocess.run = original_run

            self.assertEqual(
                summary,
                "Update completed. Repo version is now 0.5.4; restart the app to run it.",
            )
            self.assertEqual(output, "Updating 123..456")
            self.assertEqual(service.startup_version, "0.5.3")
            self.assertEqual(service._read_version(), "0.5.4")

    def test_persisted_restart_status_survives_reinitialization(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "VERSION").write_text("0.5.3\n", encoding="utf-8")
            (repo_dir / "README.md").write_text("version-0.5.3-blue\n", encoding="utf-8")

            service = MaintenanceService()
            service.repo_dir = repo_dir
            service.version_file = repo_dir / "VERSION"
            service.readme_file = repo_dir / "README.md"
            service.state_file = repo_dir / ".maintenance_status.json"
            service._status.update({
                "running": True,
                "last_action": "restart",
                "last_summary": "Action started.",
                "last_output": "Restart scheduled.",
            })
            service._persist_status()

            reloaded = MaintenanceService()
            reloaded.repo_dir = repo_dir
            reloaded.version_file = repo_dir / "VERSION"
            reloaded.readme_file = repo_dir / "README.md"
            reloaded.state_file = repo_dir / ".maintenance_status.json"
            reloaded.startup_version = reloaded._read_version()
            reloaded._load_persisted_status()

            self.assertFalse(reloaded._status["running"])
            self.assertEqual(reloaded._status["last_action"], "restart")
            self.assertEqual(reloaded._status["last_summary"], "Application restart completed.")
            self.assertIsNone(reloaded._status["last_error"])
            self.assertIsNotNone(reloaded._status["last_success_at"])
            self.assertEqual(reloaded._status["version"], "0.5.3")
            self.assertEqual(reloaded._status["repo_version"], "0.5.3")

    def test_schedule_system_power_queues_reboot_helper(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "VERSION").write_text("0.5.3\n", encoding="utf-8")

            service = MaintenanceService()
            service.repo_dir = repo_dir
            service.version_file = repo_dir / "VERSION"

            captured = {}
            original_popen = maintenance_service_module.subprocess.Popen

            def fake_popen(command, cwd=None, start_new_session=False):
                captured["command"] = command
                captured["cwd"] = cwd
                captured["start_new_session"] = start_new_session

                class Proc:
                    pass

                return Proc()

            maintenance_service_module.subprocess.Popen = fake_popen
            try:
                summary, output = service._schedule_system_power("reboot")
            finally:
                maintenance_service_module.subprocess.Popen = original_popen

            self.assertEqual(summary, "System reboot scheduled.")
            self.assertIn("Primary command: systemctl reboot", output)
            self.assertEqual(captured["cwd"], repo_dir)
            self.assertTrue(captured["start_new_session"])
            self.assertEqual(captured["command"][:2], [sys.executable, "-c"])
            self.assertIn("systemctl", captured["command"][2])
            self.assertIn("shutdown", captured["command"][2])


if __name__ == "__main__":
    unittest.main()
