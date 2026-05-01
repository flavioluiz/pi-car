"""
Pi-Car - Configuracoes centralizadas

Todas as configuracoes do sistema ficam aqui.
"""

from pathlib import Path

# MPD (Music Player Daemon)
MPD_HOST = 'localhost'
MPD_PORT = 6600
MUSIC_DIRECTORY = str(Path.home() / 'Music')

# GPS (gpsd)
GPS_HOST = 'localhost'
GPS_PORT = 2947

# OBD-II (USB ELM327/FTDI adapter)
OBD_DEVICE = '/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_ABAQJ7HX-if00-port0'
OBD_FALLBACK_DEVICE = '/dev/ttyUSB0'
OBD_BAUDRATE = 38400
OBD_POLL_INTERVAL = 0.8
OBD_VEHICLE_NAME = 'Citroen C3 Picasso 2013 1.5 Flex'
OBD_ENGINE_DISPLACEMENT_L = 1.449
OBD_VOLUMETRIC_EFFICIENCY = 0.78
OBD_DEFAULT_FUEL = 'gasoline_e27'

# RTL-SDR (Software Defined Radio)
RTL_DEVICE_INDEX = 0              # Device index (0 for first RTL-SDR)
RTL_SAMPLE_RATE = 2400000         # 2.4 MHz sample rate
RTL_DEFAULT_FREQ = 99500000       # Default frequency: 99.5 MHz FM
RTL_GAIN = 'auto'                 # 'auto' or gain in dB

# Flask
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 5000
FLASK_DEBUG = False
