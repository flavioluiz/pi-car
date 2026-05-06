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
    def test_set_version_updates_version_file_and_readme_badge(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "VERSION").write_text("0.5.3\n", encoding="utf-8")
            (repo_dir / "README.md").write_text(
                '<img src="https://img.shields.io/badge/version-0.5.3-blue" alt="Version">\n',
                encoding="utf-8",
            )

            service = MaintenanceService()
            service.repo_dir = repo_dir
            service.version_file = repo_dir / "VERSION"
            service.readme_file = repo_dir / "README.md"
            service.startup_version = service._read_version()

            summary, output = service._set_version("0.6.0")

            self.assertEqual(summary, "Version updated to 0.6.0.")
            self.assertIn("Updated VERSION from 0.5.3 to 0.6.0.", output)
            self.assertEqual(service.startup_version, "0.5.3")
            self.assertEqual((repo_dir / "VERSION").read_text(encoding="utf-8"), "0.6.0\n")
            self.assertIn(
                "version-0.6.0-blue",
                (repo_dir / "README.md").read_text(encoding="utf-8"),
            )

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


if __name__ == "__main__":
    unittest.main()
