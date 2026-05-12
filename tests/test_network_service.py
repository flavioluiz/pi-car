import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "backend" / "services" / "network_service.py"
MODULE_SPEC = importlib.util.spec_from_file_location("network_service_under_test", MODULE_PATH)
network_service_module = importlib.util.module_from_spec(MODULE_SPEC)
assert MODULE_SPEC and MODULE_SPEC.loader
MODULE_SPEC.loader.exec_module(network_service_module)
NetworkService = network_service_module.NetworkService


class NetworkServiceTest(unittest.TestCase):
    def test_split_nmcli_fields_keeps_escaped_colons(self):
        service = NetworkService()
        parts = service._split_nmcli_fields(r"*:Cafe\:Office:67:WPA2")
        self.assertEqual(parts, ["*", "Cafe:Office", "67", "WPA2"])

    def test_scan_wifi_networks_dedupes_ssids_and_marks_connected(self):
        service = NetworkService()

        class Result:
            stdout = "*:PiCASSO\\:Lab:60:WPA2\n:PiCASSO\\:Lab:88:WPA2\n:Guest:41:\n"

        service._run_command = lambda *args, **kwargs: Result()
        networks = service._scan_wifi_networks(
            status={"ssid": "PiCASSO:Lab"},
            force=True,
        )

        self.assertEqual(len(networks), 2)
        self.assertEqual(networks[0]["ssid"], "PiCASSO:Lab")
        self.assertTrue(networks[0]["connected"])
        self.assertEqual(networks[0]["signal"], 88)
        self.assertEqual(networks[1]["ssid"], "Guest")
        self.assertFalse(networks[1]["requires_password"])


if __name__ == "__main__":
    unittest.main()
