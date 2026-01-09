#!/usr/bin/env python3
"""
RTL-SDR Connection Test Script

This script tests the RTL-SDR device connectivity and basic functionality.
Run on Raspberry Pi to validate hardware setup before integrating with Pi-Car.

Usage:
    python3 rtlsdr_test.py

Requirements:
    - RTL-SDR device connected via USB
    - rtl-sdr package installed (apt install rtl-sdr)
    - pyrtlsdr installed (pip3 install pyrtlsdr)
"""

import sys
import time
import subprocess
from typing import Optional, Dict, Any

# Test results
results: Dict[str, Any] = {
    'system_tools': False,
    'device_detected': False,
    'pyrtlsdr_import': False,
    'device_open': False,
    'sample_read': False,
    'frequency_tune': False,
    'device_info': {}
}


def print_header(text: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_result(test: str, success: bool, details: str = "") -> None:
    """Print test result with color coding."""
    status = "\033[92mPASS\033[0m" if success else "\033[91mFAIL\033[0m"
    print(f"  [{status}] {test}")
    if details:
        print(f"         {details}")


def test_system_tools() -> bool:
    """Test if RTL-SDR system tools are installed."""
    print_header("Testing System Tools (rtl-sdr package)")

    tools = ['rtl_test', 'rtl_fm', 'rtl_power']
    all_found = True

    for tool in tools:
        try:
            result = subprocess.run(
                ['which', tool],
                capture_output=True,
                text=True
            )
            found = result.returncode == 0
            if not found:
                all_found = False
            print_result(f"{tool} installed", found,
                        result.stdout.strip() if found else "Not found in PATH")
        except Exception as e:
            print_result(f"{tool} installed", False, str(e))
            all_found = False

    return all_found


def test_device_detection() -> bool:
    """Test if RTL-SDR device is detected by the system."""
    print_header("Testing Device Detection")

    # Check lsusb for RTL-SDR (common vendor IDs)
    rtlsdr_ids = [
        '0bda:2832',  # RTL2832U
        '0bda:2838',  # RTL2838
    ]

    try:
        result = subprocess.run(
            ['lsusb'],
            capture_output=True,
            text=True
        )

        device_found = False
        for line in result.stdout.split('\n'):
            for vid_pid in rtlsdr_ids:
                if vid_pid in line.lower():
                    print_result("RTL-SDR USB device", True, line.strip())
                    device_found = True
                    break
            # Also check for "RTL" or "Realtek" in description
            if 'rtl' in line.lower() or 'realtek' in line.lower():
                if '2832' in line or '2838' in line:
                    print_result("RTL-SDR USB device", True, line.strip())
                    device_found = True

        if not device_found:
            print_result("RTL-SDR USB device", False,
                        "No RTL-SDR device found. Check USB connection.")
            print("\n  Available USB devices:")
            for line in result.stdout.split('\n'):
                if line.strip():
                    print(f"    {line}")

        return device_found

    except FileNotFoundError:
        print_result("lsusb command", False, "lsusb not installed")
        return False
    except Exception as e:
        print_result("Device detection", False, str(e))
        return False


def test_rtl_test_command() -> Optional[Dict[str, Any]]:
    """Run rtl_test to get device info."""
    print_header("Running rtl_test")

    try:
        # Run rtl_test with timeout (it runs indefinitely otherwise)
        result = subprocess.run(
            ['rtl_test', '-t'],
            capture_output=True,
            text=True,
            timeout=10
        )

        output = result.stdout + result.stderr
        print(f"\n  Output:\n{output}")

        # Parse device info
        device_info = {}
        for line in output.split('\n'):
            if 'Found' in line and 'device' in line:
                device_info['devices_found'] = line
            if 'Using device' in line:
                device_info['device_name'] = line
            if 'Tuner type' in line:
                device_info['tuner_type'] = line.split(':')[-1].strip()

        return device_info

    except subprocess.TimeoutExpired:
        print("  rtl_test timed out (this is normal)")
        return {}
    except FileNotFoundError:
        print_result("rtl_test", False, "Command not found")
        return None
    except Exception as e:
        print_result("rtl_test", False, str(e))
        return None


def test_pyrtlsdr_import() -> bool:
    """Test if pyrtlsdr library can be imported."""
    print_header("Testing pyrtlsdr Library")

    try:
        from rtlsdr import RtlSdr
        print_result("pyrtlsdr import", True, "Library loaded successfully")
        return True
    except ImportError as e:
        print_result("pyrtlsdr import", False, str(e))
        print("\n  To install: pip3 install pyrtlsdr --break-system-packages")
        return False
    except Exception as e:
        print_result("pyrtlsdr import", False, str(e))
        return False


def test_device_open() -> Optional[Any]:
    """Test opening the RTL-SDR device."""
    print_header("Testing Device Open")

    try:
        from rtlsdr import RtlSdr

        sdr = RtlSdr()
        print_result("Device open", True, "Successfully opened RTL-SDR")

        # Get device info
        results['device_info'] = {
            'sample_rate': sdr.sample_rate,
            'center_freq': sdr.center_freq,
            'gain': sdr.gain,
        }

        print(f"\n  Device Information:")
        print(f"    Sample Rate: {sdr.sample_rate / 1e6:.2f} MHz")
        print(f"    Center Freq: {sdr.center_freq / 1e6:.2f} MHz")
        print(f"    Gain: {sdr.gain} dB")

        return sdr

    except Exception as e:
        print_result("Device open", False, str(e))

        # Check if device is busy
        if 'busy' in str(e).lower() or 'resource' in str(e).lower():
            print("\n  The device may be in use by another program.")
            print("  Try: sudo killall rtl_fm rtl_test gqrx")

        return None


def test_frequency_tune(sdr) -> bool:
    """Test tuning to different frequencies."""
    print_header("Testing Frequency Tuning")

    test_frequencies = [
        (99.5e6, "FM Radio (99.5 MHz)"),
        (118.5e6, "Aviation (118.5 MHz - Tower)"),
        (433.92e6, "ISM Band (433.92 MHz)"),
    ]

    all_passed = True

    for freq, description in test_frequencies:
        try:
            sdr.center_freq = freq
            actual_freq = sdr.center_freq

            # Allow small deviation (some tuners have offset)
            deviation = abs(actual_freq - freq)
            passed = deviation < 1000  # Within 1 kHz

            if not passed:
                all_passed = False

            print_result(
                f"Tune to {description}",
                passed,
                f"Set: {freq/1e6:.3f} MHz, Actual: {actual_freq/1e6:.3f} MHz"
            )

        except Exception as e:
            print_result(f"Tune to {description}", False, str(e))
            all_passed = False

    return all_passed


def test_sample_read(sdr) -> bool:
    """Test reading samples from the device."""
    print_header("Testing Sample Read")

    try:
        # Configure for reading
        sdr.sample_rate = 2.4e6
        sdr.center_freq = 99.5e6
        sdr.gain = 'auto'

        print(f"  Reading 1024 samples at {sdr.center_freq/1e6:.1f} MHz...")

        start_time = time.time()
        samples = sdr.read_samples(1024)
        elapsed = time.time() - start_time

        print_result(
            "Sample read",
            True,
            f"Read {len(samples)} samples in {elapsed*1000:.1f}ms"
        )

        # Basic sample statistics
        import numpy as np
        samples_np = np.array(samples)

        print(f"\n  Sample Statistics:")
        print(f"    Count: {len(samples)}")
        print(f"    Mean magnitude: {np.mean(np.abs(samples_np)):.4f}")
        print(f"    Max magnitude: {np.max(np.abs(samples_np)):.4f}")
        print(f"    Sample type: {samples_np.dtype}")

        return True

    except Exception as e:
        print_result("Sample read", False, str(e))
        return False


def test_gain_settings(sdr) -> bool:
    """Test gain adjustment."""
    print_header("Testing Gain Settings")

    try:
        # Get available gains
        gains = sdr.valid_gains_db
        print(f"  Available gains: {gains}")

        # Test a few gain settings
        test_gains = [gains[0], gains[len(gains)//2], gains[-1]]

        for gain in test_gains:
            sdr.gain = gain
            actual = sdr.gain
            print_result(
                f"Set gain {gain} dB",
                True,
                f"Actual: {actual} dB"
            )

        # Test auto gain
        sdr.gain = 'auto'
        print_result("Auto gain", True)

        return True

    except Exception as e:
        print_result("Gain settings", False, str(e))
        return False


def run_all_tests() -> Dict[str, bool]:
    """Run all tests and return results."""
    print("\n")
    print("=" * 60)
    print("       RTL-SDR Connection Test for Pi-Car")
    print("=" * 60)

    sdr = None

    try:
        # System tools test
        results['system_tools'] = test_system_tools()

        # Device detection
        results['device_detected'] = test_device_detection()

        # Run rtl_test
        device_info = test_rtl_test_command()
        if device_info:
            results['device_info'].update(device_info)

        # PyRTLSDR import
        results['pyrtlsdr_import'] = test_pyrtlsdr_import()

        if not results['pyrtlsdr_import']:
            print("\n\033[93mSkipping device tests - pyrtlsdr not available\033[0m")
            return results

        # Device open
        sdr = test_device_open()
        results['device_open'] = sdr is not None

        if not results['device_open']:
            print("\n\033[93mSkipping remaining tests - device not open\033[0m")
            return results

        # Frequency tuning
        results['frequency_tune'] = test_frequency_tune(sdr)

        # Sample read
        results['sample_read'] = test_sample_read(sdr)

        # Gain settings
        test_gain_settings(sdr)

    finally:
        # Always close the device
        if sdr is not None:
            try:
                sdr.close()
                print("\n  Device closed successfully.")
            except:
                pass

    return results


def print_summary(results: Dict[str, bool]) -> None:
    """Print final test summary."""
    print_header("Test Summary")

    passed = sum(1 for v in results.values() if v is True)
    total = sum(1 for v in results.values() if isinstance(v, bool))

    print(f"\n  Tests passed: {passed}/{total}")

    if all(v for k, v in results.items() if isinstance(v, bool) and k != 'system_tools'):
        print("\n  \033[92mRTL-SDR is ready for Pi-Car!\033[0m")
        print("  You can proceed with the radio module integration.")
    else:
        print("\n  \033[93mSome tests failed. Please check:\033[0m")
        if not results.get('device_detected'):
            print("    - Is the RTL-SDR connected via USB?")
            print("    - Try a different USB port")
        if not results.get('pyrtlsdr_import'):
            print("    - Install pyrtlsdr: pip3 install pyrtlsdr --break-system-packages")
        if not results.get('device_open'):
            print("    - Is another program using the device? (gqrx, rtl_fm, etc.)")
            print("    - Try: sudo killall rtl_fm rtl_test gqrx")
            print("    - Check permissions: sudo usermod -a -G plugdev $USER")


def main():
    """Main entry point."""
    try:
        results = run_all_tests()
        print_summary(results)

        # Return exit code based on critical tests
        if results.get('device_open') and results.get('sample_read'):
            sys.exit(0)
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\033[91mUnexpected error: {e}\033[0m")
        sys.exit(1)


if __name__ == '__main__':
    main()
