"""
RTL-SDR Service for Pi-Car

Provides RTL-SDR device control for software-defined radio functionality.
Uses rtl_fm for demodulation and aplay for audio output.
"""

import subprocess
import threading
import time
import logging
import shutil
import os
from typing import Optional, List, Dict, Any

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
    'playing': False,
    'frequency': 97.5,  # MHz - Nativa FM SJC
    'mode': 'FM',
    'volume': 80,  # 0-100
    'squelch': 0,  # squelch level
    'gain': 'auto',
    'sample_rate': 2.4,  # MHz
    'signal_strength': -60,  # dBm (estimated)
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

# FM stations - Sao Jose dos Campos region
FM_PRESETS: List[Dict[str, Any]] = [
    {'freq': 88.3, 'label': 'Band News', 'mode': 'FM'},
    {'freq': 91.1, 'label': 'Metropolitana', 'mode': 'FM'},
    {'freq': 93.5, 'label': 'Band FM Vale', 'mode': 'FM'},
    {'freq': 95.7, 'label': 'Jovem Pan', 'mode': 'FM'},
    {'freq': 97.5, 'label': 'Nativa FM', 'mode': 'FM'},
    {'freq': 98.3, 'label': 'FM Vale', 'mode': 'FM'},
    {'freq': 100.1, 'label': 'Gospel FM', 'mode': 'FM'},
    {'freq': 102.7, 'label': 'Difusora', 'mode': 'FM'},
    {'freq': 105.5, 'label': 'Transamérica', 'mode': 'FM'},
    {'freq': 107.1, 'label': 'Mix FM', 'mode': 'FM'},
]


class RTLSDRService:
    """Service class for RTL-SDR device control using rtl_fm."""

    def __init__(self):
        """Initialize RTL-SDR service."""
        self._rtl_fm_process: Optional[subprocess.Popen] = None
        self._aplay_process: Optional[subprocess.Popen] = None
        self._running = False
        self._lock = threading.Lock()

        # Check if rtl_fm is available
        self._rtl_fm_path = shutil.which('rtl_fm')
        self._aplay_path = shutil.which('aplay')

        # FFT data for spectrogram (optional, uses rtl_power)
        self._fft_data: Optional[List[float]] = None
        self._fft_thread: Optional[threading.Thread] = None

    def _pause_music(self) -> None:
        """Pause MPD music playback when radio starts."""
        try:
            from mpd import MPDClient
            import config
            client = MPDClient()
            client.timeout = 2
            client.connect(config.MPD_HOST, config.MPD_PORT)
            status = client.status()
            if status.get('state') == 'play':
                client.pause()
                logger.info("Paused music for radio")
            client.close()
            client.disconnect()
        except Exception as e:
            logger.debug(f"Could not pause music: {e}")

    def start(self) -> bool:
        """
        Start the RTL-SDR service.

        Returns:
            True if started successfully, False otherwise.
        """
        logger.info(f"start() called. rtl_fm={self._rtl_fm_path}, aplay={self._aplay_path}")

        if not self._rtl_fm_path:
            logger.error("rtl_fm not found. Install: sudo apt install rtl-sdr")
            radio_data['error'] = 'rtl_fm not installed'
            return False

        if not self._aplay_path:
            logger.error("aplay not found. Install: sudo apt install alsa-utils")
            radio_data['error'] = 'aplay not installed'
            return False

        # Test if RTL-SDR device is available
        logger.info("Testing RTL-SDR device...")
        try:
            result = subprocess.run(
                ['rtl_test', '-t'],
                capture_output=True,
                text=True,
                timeout=5
            )
            logger.info(f"rtl_test result: returncode={result.returncode}")
            if 'No supported devices found' in result.stderr:
                logger.error("No RTL-SDR device found")
                radio_data['error'] = 'No RTL-SDR device found'
                radio_data['connected'] = False
                return False
        except subprocess.TimeoutExpired:
            logger.info("rtl_test timed out (expected, device likely OK)")
        except Exception as e:
            logger.warning(f"rtl_test check failed: {e}")

        self._running = True
        radio_data['connected'] = True
        radio_data['error'] = None
        logger.info("RTL-SDR marked as running")

        # Start playing at default frequency
        logger.info("Starting initial playback...")
        result = self._start_playback()
        logger.info(f"Initial playback result: {result}")

        logger.info("RTL-SDR service started successfully")
        return True

    def stop(self) -> None:
        """Stop the RTL-SDR service."""
        self._running = False
        self._stop_playback()
        radio_data['connected'] = False
        radio_data['playing'] = False
        logger.info("RTL-SDR service stopped")

    def _start_playback(self) -> bool:
        """Start rtl_fm -> aplay pipeline."""
        # Pause music before starting radio (in background to not block)
        threading.Thread(target=self._pause_music, daemon=True).start()

        with self._lock:
            # Stop existing playback
            self._stop_playback_internal()

            freq_hz = int(radio_data['frequency'] * 1e6)
            mode = radio_data['mode']
            squelch = radio_data['squelch']

            # Build rtl_fm command
            # FM: -M wbfm (wide FM for broadcast)
            # AM: -M am (for aviation - 25 kHz channel spacing)
            if mode == 'FM':
                modulation = 'wbfm'  # Wide FM for broadcast
                sample_rate = 170000  # Good for FM broadcast
                audio_rate = 48000
                gain = '40'
            else:  # AM (aviation)
                modulation = 'am'
                sample_rate = 25000  # 25 kHz for aviation AM
                audio_rate = 48000
                gain = '49.6'  # Max gain for weak signals
                # Aviation uses squelch to reduce noise
                if squelch == 0:
                    squelch = 50  # Default squelch for aviation

            rtl_fm_cmd = [
                'rtl_fm',
                '-M', modulation,
                '-f', str(freq_hz),
                '-s', str(sample_rate),
                '-r', str(audio_rate),
                '-l', str(squelch),  # squelch level
                '-g', gain,  # gain
            ]

            aplay_cmd = [
                'aplay',
                '-r', str(audio_rate),
                '-f', 'S16_LE',
                '-t', 'raw',
                '-c', '1',  # mono
                '-q',  # quiet
            ]

            try:
                logger.info(f"Starting radio: {freq_hz/1e6:.3f} MHz, mode={mode}")
                logger.info(f"rtl_fm cmd: {' '.join(rtl_fm_cmd)}")

                # Start rtl_fm
                self._rtl_fm_process = subprocess.Popen(
                    rtl_fm_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                logger.info(f"rtl_fm started, pid={self._rtl_fm_process.pid}")

                # Pipe to aplay
                self._aplay_process = subprocess.Popen(
                    aplay_cmd,
                    stdin=self._rtl_fm_process.stdout,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                logger.info(f"aplay started, pid={self._aplay_process.pid}")

                radio_data['playing'] = True
                return True

            except Exception as e:
                logger.error(f"Failed to start playback: {e}")
                import traceback
                logger.error(traceback.format_exc())
                radio_data['error'] = str(e)
                self._stop_playback_internal()
                return False

    def _stop_playback(self) -> None:
        """Stop playback (with lock)."""
        with self._lock:
            self._stop_playback_internal()

    def _stop_playback_internal(self) -> None:
        """Stop playback (internal, no lock)."""
        if self._aplay_process:
            try:
                self._aplay_process.terminate()
                self._aplay_process.wait(timeout=1)
            except:
                try:
                    self._aplay_process.kill()
                except:
                    pass
            self._aplay_process = None

        if self._rtl_fm_process:
            try:
                self._rtl_fm_process.terminate()
                self._rtl_fm_process.wait(timeout=1)
            except:
                try:
                    self._rtl_fm_process.kill()
                except:
                    pass
            self._rtl_fm_process = None

        radio_data['playing'] = False

    def tune(self, frequency_mhz: float) -> Dict[str, Any]:
        """
        Tune to a specific frequency.

        Args:
            frequency_mhz: Frequency in MHz

        Returns:
            Dict with result status
        """
        logger.info(f"tune() called: freq={frequency_mhz}, running={self._running}")

        if not self._running:
            # Try to start if not running
            logger.warning("RTL-SDR not running, attempting to start...")
            if not self.start():
                return {'error': 'RTL-SDR not running and could not start'}

        # Validate frequency range
        if frequency_mhz < 24 or frequency_mhz > 1800:
            return {'error': f'Frequency {frequency_mhz} MHz out of range (24-1800 MHz)'}

        radio_data['frequency'] = frequency_mhz

        # Restart playback with new frequency
        if self._start_playback():
            logger.info(f"Tuned to {frequency_mhz:.3f} MHz")
            return {
                'success': True,
                'frequency': frequency_mhz
            }
        else:
            return {'error': 'Failed to tune'}

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

        # Restart playback with new mode
        if self._running and radio_data['playing']:
            self._start_playback()

        return {
            'success': True,
            'mode': mode
        }

    def set_volume(self, volume: int) -> Dict[str, Any]:
        """
        Set volume level using amixer.

        Args:
            volume: Volume level 0-100

        Returns:
            Dict with result status
        """
        volume = max(0, min(100, volume))
        radio_data['volume'] = volume

        try:
            # Try different mixer controls
            for control in ['Master', 'PCM', 'Headphone']:
                result = subprocess.run(
                    ['amixer', 'set', control, f'{volume}%'],
                    capture_output=True,
                    timeout=2
                )
                if result.returncode == 0:
                    return {'success': True, 'volume': volume}

            return {'error': 'No mixer control found'}

        except Exception as e:
            logger.error(f"Volume set error: {e}")
            return {'error': str(e)}

    def set_squelch(self, level: int) -> Dict[str, Any]:
        """
        Set squelch level.

        Args:
            level: Squelch level (0 = off, higher = more filtering)

        Returns:
            Dict with result status
        """
        level = max(0, min(100, level))
        radio_data['squelch'] = level

        # Restart playback with new squelch
        if self._running and radio_data['playing']:
            self._start_playback()

        return {'success': True, 'squelch': level}

    def play(self) -> Dict[str, Any]:
        """Start playback."""
        if not self._running:
            return {'error': 'RTL-SDR not running'}

        if self._start_playback():
            return {'success': True, 'playing': True}
        else:
            return {'error': 'Failed to start playback'}

    def stop_playback(self) -> Dict[str, Any]:
        """Stop playback (pause)."""
        self._stop_playback()
        return {'success': True, 'playing': False}

    def get_fft(self) -> Dict[str, Any]:
        """
        Get FFT data for spectrogram.
        Note: This is a simplified implementation.

        Returns:
            Dict with FFT data and metadata
        """
        # Generate simulated FFT data for now
        # Real implementation would use rtl_power or separate SDR access
        if not NUMPY_AVAILABLE:
            return {'error': 'numpy not available'}

        # Generate noise floor with a peak at center
        bins = 256
        noise = np.random.normal(-80, 5, bins)

        # Add signal peak at center if playing
        if radio_data['playing']:
            center = bins // 2
            signal = np.exp(-((np.arange(bins) - center) ** 2) / 100) * 30
            fft_data = noise + signal
        else:
            fft_data = noise

        return {
            'fft': fft_data.tolist(),
            'frequency': radio_data['frequency'],
            'sample_rate': radio_data['sample_rate'],
            'bins': bins
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current radio status."""
        # Check if processes are still running
        if self._rtl_fm_process and self._rtl_fm_process.poll() is not None:
            radio_data['playing'] = False

        return radio_data.copy()

    def get_presets(self) -> Dict[str, Any]:
        """Get all available presets."""
        return {
            'fm': FM_PRESETS,
            'airports': AIRPORT_PRESETS
        }

    def get_valid_gains(self) -> List[float]:
        """Get list of valid gain values."""
        # Common RTL-SDR gain values
        return [0, 0.9, 1.4, 2.7, 3.7, 7.7, 8.7, 12.5, 14.4, 15.7,
                16.6, 19.7, 20.7, 22.9, 25.4, 28.0, 29.7, 32.8, 33.8,
                36.4, 37.2, 38.6, 40.2, 42.1, 43.4, 43.9, 44.5, 48.0, 49.6]


# Singleton instance for use by routes
_service_instance: Optional[RTLSDRService] = None


def get_rtlsdr_service() -> RTLSDRService:
    """Get or create the RTL-SDR service singleton."""
    global _service_instance
    if _service_instance is None:
        logger.info("Creating new RTLSDRService singleton")
        _service_instance = RTLSDRService()
    else:
        logger.debug(f"Returning existing singleton (running={_service_instance._running})")
    return _service_instance


def set_rtlsdr_service(service: RTLSDRService) -> None:
    """Set the RTL-SDR service singleton (for initialization)."""
    global _service_instance
    _service_instance = service
    logger.info("RTLSDRService singleton set externally")
