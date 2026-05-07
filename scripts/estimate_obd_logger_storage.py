#!/usr/bin/env python3
"""
Estimate PiCASSO OBD logger storage usage.

Modes:
- Analyze an existing JSONL log file for exact byte counts.
- Fall back to a representative synthetic record using the current schema.

Examples:
  python3 scripts/estimate_obd_logger_storage.py
  python3 scripts/estimate_obd_logger_storage.py --input telemetry/obd/2026/05/06/935fckfvydb000000.jsonl
  python3 scripts/estimate_obd_logger_storage.py --interval 1.0 --days 30
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def synthetic_record() -> dict:
    now = utc_now_iso()
    return {
        "logged_at": now,
        "device_name": "c3-picasso-2013",
        "vehicle": "Citroen C3 Picasso 2013 1.5 Flex",
        "vin": "935FCKFVYDB000000",
        "supported_commands": [
            "STATUS",
            "FUEL_STATUS",
            "ENGINE_LOAD",
            "COOLANT_TEMP",
            "SHORT_FUEL_TRIM_1",
            "LONG_FUEL_TRIM_1",
            "INTAKE_PRESSURE",
            "RPM",
            "SPEED",
            "TIMING_ADVANCE",
            "INTAKE_TEMP",
            "THROTTLE_POS",
            "SECONDARY_AIR_STATUS",
            "O2_SENSORS_PRESENT",
            "O2_B1S1",
            "O2_B1S2",
            "OBD_STANDARD",
            "DISTANCE_WITH_MIL",
        ],
        "time_context": {
            "sample_time": now,
            "logged_at": now,
            "wifi_connected": False,
            "wifi_last_checked_at": now,
            "gps_connected": True,
            "gps_has_fix": True,
            "clock_confidence": "offline_unverified",
        },
        "connection": {
            "adapter": "ELM327 v2.1",
            "protocol": "ISO 15765-4 (CAN 11/500)",
            "port": "/dev/ttyUSB0",
            "baudrate": 38400,
            "ecu_ready": True,
        },
        "metadata": {
            "sample_time": now,
            "last_dynamic_sample_time": now,
            "dynamic_stale": False,
            "dynamic_stale_age_s": 0.4,
            "last_successful_command": "010C",
        },
        "gps": {
            "lat": -23.2,
            "lon": -45.9,
            "speed": 54.3,
            "altitude": 560.4,
            "satellites": 8,
            "connected": True,
        },
        "wifi": {
            "connected": False,
            "state": "disconnected",
            "ssid": "",
            "interface": "wlan0",
            "last_checked_at": now,
            "source": "iwgetid",
        },
        "direct": {
            "rpm": 2103.0,
            "speed_kmh": 54,
            "coolant_temp_c": 92,
            "intake_temp_c": 31,
            "map_kpa": 41,
            "engine_load_pct": 32.2,
            "throttle_pct": 14.1,
            "timing_advance_deg": 6.0,
            "short_fuel_trim_b1_pct": 4.7,
            "long_fuel_trim_b1_pct": 2.3,
            "fuel_system_status_1": "closed_loop_o2_feedback",
            "fuel_system_status_2": "not_supported",
            "secondary_air_status": "outside_atmosphere_or_off",
            "o2_sensors_present": ["B1S1", "B1S2"],
            "o2_b1s1_voltage_v": 0.72,
            "o2_b1s1_stft_pct": 3.1,
            "o2_b1s2_voltage_v": 0.11,
            "obd_standard": "eobd",
            "adapter_voltage_v": 13.8,
            "mil_on": False,
            "distance_with_mil_km": 0,
            "active_dtcs": [],
            "pending_dtcs": [],
        },
        "inferred": {
            "engine_on": True,
            "stationary": False,
            "fuel": "gasoline_e27",
            "fuel_rate_l_h_gasoline_e27": 3.12,
            "fuel_rate_l_h_ethanol": 4.41,
            "selected_fuel_rate_l_h": 3.12,
            "instant_km_l": 17.3,
            "instant_l_100km": 5.8,
            "trip_consumed_l": 0.321,
            "trip_distance_km": 5.72,
            "trip_average_km_l": 17.8,
            "coolant_alert": False,
            "battery_alert": False,
        },
        "metrics": {
            "RPM": 2103.0,
            "SPEED": 54,
            "COOLANT_TEMP": 92,
            "INTAKE_TEMP": 31,
            "INTAKE_PRESSURE": 41,
            "ENGINE_LOAD": 32.2,
            "THROTTLE_POS": 14.1,
            "TIMING_ADVANCE": 6.0,
            "SHORT_FUEL_TRIM_1": 4.7,
            "LONG_FUEL_TRIM_1": 2.3,
            "O2_B1S1_VOLTAGE": 0.72,
            "O2_B1S1_TRIM": 3.1,
            "O2_B1S2_VOLTAGE": 0.11,
            "ELM_VOLTAGE": 13.8,
            "FUEL_RATE_GASOLINE_E27": 3.12,
            "FUEL_RATE_ETHANOL": 4.41,
            "INSTANT_KM_L": 17.3,
            "TRIP_AVERAGE_KM_L": 17.8,
        },
    }


def compact_json_size(record: dict) -> int:
    return len(json.dumps(record, ensure_ascii=True, separators=(",", ":")).encode("utf-8")) + 1


def read_jsonl_sizes(path: Path) -> list[int]:
    sizes: list[int] = []
    with path.open("rb") as handle:
        for raw_line in handle:
            if raw_line.strip():
                sizes.append(len(raw_line))
    return sizes


def human_bytes(size: float) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def project(bytes_per_record: float, interval_s: float, days: int) -> dict:
    records_per_second = 1.0 / interval_s
    records_per_minute = records_per_second * 60
    records_per_hour = records_per_second * 3600
    records_per_day = records_per_hour * 24
    return {
        "bytes_per_record": bytes_per_record,
        "records_per_minute": records_per_minute,
        "records_per_hour": records_per_hour,
        "records_per_day": records_per_day,
        "per_minute_bytes": bytes_per_record * records_per_minute,
        "per_hour_bytes": bytes_per_record * records_per_hour,
        "per_day_bytes": bytes_per_record * records_per_day,
        "for_days_bytes": bytes_per_record * records_per_day * days,
    }


def print_projection(label: str, p: dict, interval_s: float, days: int) -> None:
    print(label)
    print(f"  Interval: {interval_s:.3f} s")
    print(f"  Avg bytes/record: {p['bytes_per_record']:.1f} B")
    print(f"  Records/minute: {p['records_per_minute']:.1f}")
    print(f"  Per minute: {human_bytes(p['per_minute_bytes'])}")
    print(f"  Per hour: {human_bytes(p['per_hour_bytes'])}")
    print(f"  Per day: {human_bytes(p['per_day_bytes'])}")
    print(f"  For {days} days: {human_bytes(p['for_days_bytes'])}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Estimate OBD logger storage usage.")
    parser.add_argument("--input", type=Path, help="Existing JSONL file to analyze exactly.")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between records. Default: 1.0")
    parser.add_argument("--days", type=int, default=30, help="Retention period to project. Default: 30")
    args = parser.parse_args()

    if args.interval <= 0:
        raise SystemExit("--interval must be > 0")
    if args.days <= 0:
        raise SystemExit("--days must be > 0")

    if args.input:
        sizes = read_jsonl_sizes(args.input)
        if not sizes:
            raise SystemExit(f"No non-empty JSONL lines found in {args.input}")
        avg_size = mean(sizes)
        print(f"Source: existing JSONL file {args.input}")
        print(f"  Records analyzed: {len(sizes)}")
        print(f"  Min record size: {human_bytes(min(sizes))}")
        print(f"  Avg record size: {human_bytes(avg_size)}")
        print(f"  Max record size: {human_bytes(max(sizes))}")
        print_projection("Projection", project(avg_size, args.interval, args.days), args.interval, args.days)
        return 0

    sample = synthetic_record()
    sample_size = compact_json_size(sample)
    print("Source: synthetic representative record for current logger schema")
    print(f"  Sample size: {human_bytes(sample_size)}")
    print_projection("Projection", project(sample_size, args.interval, args.days), args.interval, args.days)
    print("")
    print("Tip:")
    print("  Run again with --input on a real JSONL file from the Raspberry Pi to get exact numbers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
