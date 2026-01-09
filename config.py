"""
Pi-Car - Configuracoes centralizadas

Todas as configuracoes do sistema ficam aqui.
"""

# MPD (Music Player Daemon)
MPD_HOST = 'localhost'
MPD_PORT = 6600

# GPS (gpsd)
GPS_HOST = 'localhost'
GPS_PORT = 2947

# OBD-II
OBD_DEVICE = '/dev/rfcomm0'

# RTL-SDR (Software Defined Radio)
RTL_DEVICE_INDEX = 0              # Device index (0 for first RTL-SDR)
RTL_SAMPLE_RATE = 2400000         # 2.4 MHz sample rate
RTL_DEFAULT_FREQ = 99500000       # Default frequency: 99.5 MHz FM
RTL_GAIN = 'auto'                 # 'auto' or gain in dB

# Flask
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 5000
FLASK_DEBUG = False
