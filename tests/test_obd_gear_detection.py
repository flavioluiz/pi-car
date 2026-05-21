import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

spec = importlib.util.spec_from_file_location("obd_service_under_test", ROOT / "backend/services/obd_service.py")
obd_service = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(obd_service)
OBDService = obd_service.OBDService


class OBDGearDetectionTest(unittest.TestCase):
    def setUp(self):
        self.service = OBDService(device="/tmp/nonexistent-obd")

    def _infer(self, rpm, speed_kmh, now, *, stale=False, stale_age=0.0):
        return self.service._calculate_gear_inference(
            {
                "rpm": rpm,
                "speed_kmh": speed_kmh,
            },
            dynamic_stale=stale,
            dynamic_stale_age_s=stale_age,
            now=now,
        )

    def test_confirms_third_gear_after_two_samples(self):
        first = self._infer(2240, 40, 10.0)
        second = self._infer(2240, 40, 10.4)
        settled = self._infer(2240, 40, 12.0)

        self.assertEqual(first["state"], "UNKNOWN")
        self.assertEqual(first["display"], "--")
        self.assertEqual(second["state"], "IN_GEAR")
        self.assertEqual(second["gear"], 3)
        self.assertEqual(second["display"], "3")
        self.assertEqual(second["confidence"], "medium")
        self.assertEqual(settled["confidence"], "high")

    def test_confirms_disengaged_immediately_when_ratio_is_very_low(self):
        self._infer(2240, 40, 10.0)
        self._infer(2240, 40, 10.4)

        disengaged = self._infer(900, 40, 11.0)

        self.assertEqual(disengaged["state"], "DISENGAGED")
        self.assertIsNone(disengaged["gear"])
        self.assertEqual(disengaged["display"], "N")
        self.assertEqual(disengaged["confidence"], "none")

    def test_retains_last_confirmed_gear_while_data_is_temporarily_stale(self):
        self._infer(1800, 40, 20.0)
        confirmed = self._infer(1800, 40, 20.4)
        retained = self._infer(1800, 40, 21.0, stale=True, stale_age=1.8)
        expired = self._infer(1800, 40, 22.6, stale=True, stale_age=2.1)

        self.assertEqual(confirmed["gear"], 4)
        self.assertEqual(retained["state"], "UNKNOWN")
        self.assertEqual(retained["gear"], 4)
        self.assertEqual(retained["display"], "4")
        self.assertEqual(retained["confidence"], "low")
        self.assertEqual(expired["state"], "UNKNOWN")
        self.assertIsNone(expired["gear"])
        self.assertEqual(expired["display"], "--")

    def test_primary_pids_are_polled_every_cycle_while_secondary_pids_are_throttled(self):
        one_byte_values = {
            '010D': 42,
            '010B': 55,
            '0104': 24.0,
            '0111': 18.0,
            '0105': 92,
            '010F': 31,
            '0106': 1.5,
            '0107': 0.5,
            '010E': 8.0,
        }
        one_byte_calls = []

        def fake_parse_one_byte(command, prefix, convert, timeout=1.2):
            one_byte_calls.append(command)
            return one_byte_values.get(command)

        with patch.object(self.service, '_parse_two_byte', return_value=2100) as parse_two_byte, \
                patch.object(self.service, '_parse_one_byte', side_effect=fake_parse_one_byte), \
                patch.object(self.service, '_command', return_value=''):
            first = self.service._read_direct_data(10.0)
            obd_service.obd_data['direct'].update(first)
            second = self.service._read_direct_data(10.2)

        self.assertEqual(parse_two_byte.call_count, 2)
        self.assertEqual(one_byte_calls.count('010D'), 2)
        self.assertEqual(one_byte_calls.count('010B'), 1)
        self.assertEqual(one_byte_calls.count('0104'), 1)
        self.assertEqual(one_byte_calls.count('0111'), 1)
        self.assertEqual(first['speed_kmh'], 42)
        self.assertEqual(second['speed_kmh'], 42)
        self.assertEqual(second['map_kpa'], 55)

    def test_shift_hint_suggests_upshift_at_high_rpm(self):
        gear = self._infer(3100, 45, 10.0)
        gear = self._infer(3100, 45, 10.4)

        hint = self.service._calculate_shift_hint(
            {"rpm": 3100, "speed_kmh": 45},
            gear,
        )

        self.assertEqual(gear["gear"], 3)
        self.assertEqual(hint, "up")

    def test_shift_hint_suggests_downshift_at_low_rpm(self):
        gear = self._infer(1800, 40, 10.0)
        gear = self._infer(1800, 40, 10.4)

        hint = self.service._calculate_shift_hint(
            {"rpm": 1200, "speed_kmh": 40},
            gear,
        )

        self.assertEqual(gear["gear"], 4)
        self.assertEqual(hint, "down")


if __name__ == "__main__":
    unittest.main()
