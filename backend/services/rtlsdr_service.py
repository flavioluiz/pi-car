"""
RTL-SDR Service for Pi-Car

Provides RTL-SDR device control for software-defined radio functionality.
Supports FM/AM demodulation, frequency tuning, and FFT data for spectrograms.
"""

import threading
import time
import logging
from typing import Optional, List, Dict, Any

try:
    from rtlsdr import RtlSdr
    RTLSDR_AVAILABLE = True
except ImportError:
    RTLSDR_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global radio data - shared with routes
radio_data: Dict[str, Any] = {
    'connected': False,
    'frequency': 99.5,  # MHz
    'mode': 'FM',
    'gain': 'auto',
    'sample_rate': 2.4,  # MHz
    'signal_strength': -100,  # dBm (placeholder)
    'device_name': None,
    'tuner_type': None,
    'error': None,
}

# Airport presets
AIRPORT_PRESETS: Dict[str, Dict[str, Any]] = {
    'SBSJ': {
        'name': 'Sao Jose dos Campos',
        'icao': 'SBSJ',
        'frequencies': [
            {'freq': 118.500, 'label': 'Torre (TWR)', 'mode': 'AM'},
            {'freq': 119.250, 'label': 'Aproximacao (APP)', 'mode': 'AM'},
            {'freq': 129.050, 'label': 'Aproximacao (APP) Alt', 'mode': 'AM'},
            {'freq': 121.900, 'label': 'Solo (GND)', 'mode': 'AM'},
            {'freq': 127.650, 'label': 'ATIS', 'mode': 'AM'},
        ]
    },
    'SBGR': {
        'name': 'Guarulhos International',
        'icao': 'SBGR',
        'frequencies': [
            {'freq': 121.000, 'label': 'Torre (TWR)', 'mode': 'AM'},
            {'freq': 119.100, 'label': 'Aproximacao (APP)', 'mode': 'AM'},
            {'freq': 121.900, 'label': 'Solo (GND)', 'mode': 'AM'},
            {'freq': 127.750, 'label': 'ATIS', 'mode': 'AM'},
        ]
    },
}

# Common FM stations (can be customized)
FM_PRESETS: List[Dict[str, Any]] = [
    {'freq': 89.1, 'label': 'Cultura FM', 'mode': 'FM'},
    {'freq': 91.3, 'label': 'Band FM', 'mode': 'FM'},
    {'freq': 99.5, 'label': 'Jovem Pan', 'mode': 'FM'},
    {'freq': 105.1, 'label': 'Mix FM', 'mode': 'FM'},
]


class RTLSDRService:
    """Service class for RTL-SDR device control."""

    def __init__(self,
                 device_index: int = None,
                 sample_rate: float = None,
                 default_freq: float = None,
                 gain: str = None):
        """
        Initialize RTL-SDR service.

        Args:
            device_index: RTL-SDR device index (default from config)
            sample_rate: Sample rate in Hz (default from config)
            default_freq: Default frequency in Hz (default from config)
            gain: Gain setting ('auto' or dB value)
        """
        self.device_index = device_index if device_index is not None else config.RTL_DEVICE_INDEX
        self.sample_rate = sample_rate or config.RTL_SAMPLE_RATE
        self.default_freq = default_freq or config.RTL_DEFAULT_FREQ
        self.gain = gain or config.RTL_GAIN

        self._sdr: Optional[RtlSdr] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

        # FFT data buffer
        self._fft_data: Optional[np.ndarray] = None
        self._fft_lock = threading.Lock()

    def start(self) -> bool:
        """
        Start the RTL-SDR service.

        Returns:
            True if started successfully, False otherwise.
        """
        if not RTLSDR_AVAILABLE:
            logger.error("pyrtlsdr not installed. Run: pip3 install pyrtlsdr")
            radio_data['error'] = 'pyrtlsdr not installed'
            return False

        if not NUMPY_AVAILABLE:
            logger.error("numpy not installed. Run: pip3 install numpy")
            radio_data['error'] = 'numpy not installed'
            return False

        if self._running:
            logger.warning("RTL-SDR service already running")
            return True

        try:
            self._connect()

            self._running = True
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._thread.start()

            logger.info("RTL-SDR service started")
            return True

        except Exception as e:
            logger.error(f"Failed to start RTL-SDR service: {e}")
            radio_data['error'] = str(e)
            radio_data['connected'] = False
            return False

    def stop(self) -> None:
        """Stop the RTL-SDR service."""
        self._running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        self._disconnect()
        logger.info("RTL-SDR service stopped")

    def _connect(self) -> None:
        """Connect to RTL-SDR device."""
        with self._lock:
            if self._sdr is not None:
                return

            self._sdr = RtlSdr(device_index=self.device_index)
            self._sdr.sample_rate = self.sample_rate
            self._sdr.center_freq = self.default_freq

            if self.gain == 'auto':
                self._sdr.gain = 'auto'
            else:
                self._sdr.gain = float(self.gain)

            # Update global state
            radio_data['connected'] = True
            radio_data['frequency'] = self._sdr.center_freq / 1e6
            radio_data['sample_rate'] = self._sdr.sample_rate / 1e6
            radio_data['gain'] = self._sdr.gain
            radio_data['error'] = None

            logger.info(f"Connected to RTL-SDR at {radio_data['frequency']} MHz")

    def _disconnect(self) -> None:
        """Disconnect from RTL-SDR device."""
        with self._lock:
            if self._sdr is not None:
                try:
                    self._sdr.close()
                except Exception as e:
                    logger.warning(f"Error closing RTL-SDR: {e}")
                finally:
                    self._sdr = None
                    radio_data['connected'] = False

    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            try:
                if self._sdr is not None:
                    # Read samples and compute FFT
                    self._update_fft()

                    # Update signal strength estimation
                    self._update_signal_strength()

                time.sleep(0.1)  # 10 Hz update rate

            except Exception as e:
                logger.error(f"RTL-SDR monitor error: {e}")
                radio_data['error'] = str(e)

                # Try to reconnect
                self._disconnect()
                time.sleep(1.0)

                try:
                    self._connect()
                except Exception:
                    pass

    def _update_fft(self) -> None:
        """Update FFT data from samples."""
        if self._sdr is None:
            return

        try:
            with self._lock:
                samples = self._sdr.read_samples(1024)

            # Compute FFT
            fft_data = np.fft.fftshift(np.fft.fft(samples))
            fft_magnitude = 20 * np.log10(np.abs(fft_data) + 1e-10)

            with self._fft_lock:
                self._fft_data = fft_magnitude

        except Exception as e:
            logger.debug(f"FFT update error: {e}")

    def _update_signal_strength(self) -> None:
        """Estimate signal strength from FFT data."""
        with self._fft_lock:
            if self._fft_data is not None:
                # Use center bins for signal strength estimation
                center = len(self._fft_data) // 2
                center_power = np.mean(self._fft_data[center-10:center+10])
                radio_data['signal_strength'] = float(center_power)

    def tune(self, frequency_mhz: float) -> Dict[str, Any]:
        """
        Tune to a specific frequency.

        Args:
            frequency_mhz: Frequency in MHz

        Returns:
            Dict with result status
        """
        if self._sdr is None:
            return {'error': 'RTL-SDR not connected'}

        try:
            freq_hz = frequency_mhz * 1e6

            with self._lock:
                self._sdr.center_freq = freq_hz
                actual_freq = self._sdr.center_freq

            radio_data['frequency'] = actual_freq / 1e6

            logger.info(f"Tuned to {radio_data['frequency']:.3f} MHz")

            return {
                'success': True,
                'frequency': radio_data['frequency']
            }

        except Exception as e:
            logger.error(f"Tune error: {e}")
            return {'error': str(e)}

    def set_gain(self, gain: Any) -> Dict[str, Any]:
        """
        Set gain value.

        Args:
            gain: 'auto' or dB value

        Returns:
            Dict with result status
        """
        if self._sdr is None:
            return {'error': 'RTL-SDR not connected'}

        try:
            with self._lock:
                if gain == 'auto':
                    self._sdr.gain = 'auto'
                else:
                    self._sdr.gain = float(gain)
                actual_gain = self._sdr.gain

            radio_data['gain'] = actual_gain

            return {
                'success': True,
                'gain': actual_gain
            }

        except Exception as e:
            logger.error(f"Set gain error: {e}")
            return {'error': str(e)}

    def set_mode(self, mode: str) -> Dict[str, Any]:
        """
        Set demodulation mode (FM/AM).

        Args:
            mode: 'FM' or 'AM'

        Returns:
            Dict with result status
        """
        mode = mode.upper()
        if mode not in ('FM', 'AM'):
            return {'error': f'Invalid mode: {mode}. Use FM or AM.'}

        radio_data['mode'] = mode

        return {
            'success': True,
            'mode': mode
        }

    def get_fft(self) -> Dict[str, Any]:
        """
        Get current FFT data for spectrogram.

        Returns:
            Dict with FFT data and metadata
        """
        with self._fft_lock:
            if self._fft_data is None:
                return {'error': 'No FFT data available'}

            return {
                'fft': self._fft_data.tolist(),
                'frequency': radio_data['frequency'],
                'sample_rate': radio_data['sample_rate'],
                'bins': len(self._fft_data)
            }

    def get_status(self) -> Dict[str, Any]:
        """
        Get current radio status.

        Returns:
            Dict with current status
        """
        return radio_data.copy()

    def get_presets(self) -> Dict[str, Any]:
        """
        Get all available presets.

        Returns:
            Dict with FM and airport presets
        """
        return {
            'fm': FM_PRESETS,
            'airports': AIRPORT_PRESETS
        }

    def get_valid_gains(self) -> List[float]:
        """
        Get list of valid gain values for this device.

        Returns:
            List of valid gain values in dB
        """
        if self._sdr is None:
            return []

        try:
            return list(self._sdr.valid_gains_db)
        except Exception:
            return []


# Singleton instance for use by routes
_service_instance: Optional[RTLSDRService] = None


def get_rtlsdr_service() -> RTLSDRService:
    """Get or create the RTL-SDR service singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = RTLSDRService()
    return _service_instance
