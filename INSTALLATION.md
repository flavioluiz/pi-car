# Pi-Car Installation on Raspberry Pi OS 64 Lite

Complete guide to set up the development and production environment for Pi-Car.

## Requirements

- Raspberry Pi 4 (2GB+ RAM recommended)
- **Raspberry Pi OS Lite (64-bit)** - Debian Bookworm/Trixie
  - Important: Use the **Lite** version (no desktop), the script will install only what's needed
- Internet connection
- SSH access or physical terminal

## Automated Installation

### 1. Install git

Git is not installed by default on Raspberry Pi OS Lite:

```bash
sudo apt update && sudo apt install -y git
```

### 2. Clone the repository

```bash
git clone https://github.com/flavioluiz/pi-car.git
cd pi-car
```

### 3. Run installation script

```bash
chmod +x install.sh
./install.sh
```

The script will automatically install and configure:
- **System**: Full update (apt update/upgrade)
- **GUI**: X11 + Openbox (minimal required)
- **Audio**: ALSA, MPD (Music Player Daemon), MPC
- **GPS**: GPSD, gpsd-clients, Navit (offline navigation)
- **Browser**: Chromium (kiosk mode)
- **SDR Radio**: RTL-SDR, GQRX (if available)
- **Bluetooth**: For ELM327 connection (OBD-II)
- **Python**: Flask, python-mpd2, gps3, obd
- **Autostart**: Flask server + Chromium in kiosk mode

### 4. Reboot

```bash
sudo reboot
```

After reboot, the system will automatically start Chromium in kiosk mode with the Pi-Car dashboard in fullscreen.

## Manual Installation

If you prefer to install each component manually:

### Update system

```bash
sudo apt update && sudo apt upgrade -y
```

### GUI

```bash
sudo apt install -y xorg openbox lxterminal pcmanfm
```

### MPD (Music)

```bash
sudo apt install -y mpd mpc alsa-utils
mkdir -p ~/Music ~/.mpd/playlists
touch ~/.mpd/database ~/.mpd/log ~/.mpd/pid ~/.mpd/state
```

Configure `/etc/mpd.conf`:

```conf
music_directory    "/home/YOUR_USER/Music"
playlist_directory "/home/YOUR_USER/.mpd/playlists"
db_file            "/home/YOUR_USER/.mpd/database"
log_file           "/home/YOUR_USER/.mpd/log"
pid_file           "/home/YOUR_USER/.mpd/pid"
state_file         "/home/YOUR_USER/.mpd/state"

audio_output {
    type    "alsa"
    name    "Headphones"
    device  "hw:0,0"
}

bind_to_address "localhost"
port            "6600"
```

```bash
sudo systemctl enable mpd
sudo systemctl start mpd
```

### GPS

```bash
sudo apt install -y gpsd gpsd-clients navit
sudo systemctl stop gpsd.socket
sudo systemctl disable gpsd.socket
sudo systemctl enable gpsd
sudo systemctl start gpsd
```

### Browser

```bash
sudo apt install -y chromium
```

### Python Dependencies

```bash
sudo apt install -y python3-pip python3-dev
pip3 install flask python-mpd2 gps3 obd --break-system-packages
```

## Configure Autostart

### X Auto-start

Add to the end of `~/.bash_profile`:

```bash
[[ -z $DISPLAY && $XDG_VTNR -eq 1 ]] && startx
```

### Dashboard Auto-start

Create `~/.config/openbox/autostart`:

```bash
# Disable screensaver
xset s off
xset -dpms
xset s noblank

# Start dashboard
~/pi-car/start_dashboard.sh &

# Wait for server
sleep 4

# Chromium in kiosk mode
chromium --kiosk --noerrdialogs --disable-infobars --no-first-run --disable-session-crashed-bubble --disable-restore-session-state http://localhost:5000 &
```

## Test Without Autostart

To test manually without rebooting:

### Start GUI
```bash
startx
```

### In another terminal, start the dashboard
```bash
cd pi-car
chmod +x start_dashboard.sh
./start_dashboard.sh
```

### Open browser
```bash
chromium http://localhost:5000
```

## Configure Hardware Modules

### GPS

Connect the USB GPS module and verify:

```bash
ls -l /dev/ttyUSB* /dev/ttyACM*
```

Configure gpsd:

```bash
sudo systemctl stop gpsd
sudo gpsd /dev/ttyUSB0 -F /var/run/gpsd.sock
sudo systemctl start gpsd
```

### OBD-II

Pair the ELM327 Bluetooth adapter:

```bash
sudo bluetoothctl
scan on
pair XX:XX:XX:XX:XX:XX
connect XX:XX:XX:XX:XX:XX
trust XX:XX:XX:XX:XX:XX
exit
```

Connect to the serial device:

```bash
sudo rfcomm bind 0 XX:XX:XX:XX:XX:XX
```

## Troubleshooting

### MPD not starting

```bash
sudo systemctl status mpd
cat ~/.mpd/log
```

### GPS not working

```bash
sudo systemctl status gpsd
cgps -s
```

### OBD not connecting

```bash
bluetoothctl
info XX:XX:XX:XX:XX:XX
ls -l /dev/rfcomm*
```

### Browser not opening

```bash
chromium --version
export DISPLAY=:0
chromium http://localhost:5000
```

## Logs

- **MPD**: `~/.mpd/log`
- **GPSD**: `sudo journalctl -u gpsd -f`
- **Dashboard**: Terminal where the script is running
- **Kernel**: `sudo journalctl -k -f`

## Project Structure

The project is organized in modules:

```
pi-car/
├── app.py                  # Entry point
├── config.py               # Configuration
├── backend/
│   ├── routes/             # API endpoints
│   └── services/           # Business logic (MPD, GPS, OBD)
└── frontend/
    ├── static/css/         # Styles
    ├── static/js/          # JavaScript
    └── templates/          # HTML
```

## Next Steps

- [ ] Add music to `~/Music` folder
- [ ] Configure MPD playlist
- [ ] Test GPS module with speed
- [ ] Pair OBD-II adapter
- [ ] Configure vehicle electrical installation

## Useful Links

- [Raspberry Pi OS Downloads](https://www.raspberrypi.com/software/operating-systems/)
- [MPD Documentation](https://mpd.readthedocs.io/)
- [GPSD Documentation](https://gpsd.gitlab.io/gpsd/)
- [python-obd](https://python-obd.readthedocs.io/)
