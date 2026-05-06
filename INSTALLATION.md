# PiCASSO Installation on Raspberry Pi OS 64 Lite

Complete guide to set up the development and production environment for PiCASSO. The repository directory is still named `pi-car`.

## Requirements

- Raspberry Pi 4 (2GB+ RAM recommended)
- **Raspberry Pi OS Lite (64-bit)** — Debian Bookworm/Trixie
  - Use the **Lite** version (no desktop). The script installs only what is needed.
- Internet connection
- SSH access or physical terminal
- Touchscreen at 800×480 (recommended) — the UI is tuned for this resolution

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

### 3. Run the installation script

```bash
chmod +x install.sh
./install.sh
```

The script installs and configures:
- **System**: full update (`apt update`/`apt upgrade`)
- **GUI**: X11 + Openbox (minimal)
- **Audio**: ALSA, MPD (Music Player Daemon), MPC
- **GPS**: GPSD, gpsd-clients, Navit (offline navigation)
- **Browser**: Chromium (kiosk mode)
- **SDR Radio**: RTL-SDR tools
- **Python**: Flask, python-mpd2, gps3, obd, mutagen
- **Autostart**: Flask server + Chromium kiosk

### 4. Reboot

```bash
sudo reboot
```

After reboot, the system boots into the PiCASSO dashboard in fullscreen.

### 5. Enable shared git hooks (contributors only)

```bash
git config core.hooksPath .githooks
```

This activates the auto-bump `pre-commit` hook used by the project — see [README — Versioning](README.md#versioning).

### 6. Install the Plymouth boot splash (optional)

```bash
cd bootsplash
sudo ./install.sh
```

Use `sudo ./update.sh` to refresh the splash after a logo change, and `sudo ./uninstall.sh` to remove it.

---

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

### Python dependencies

```bash
sudo apt install -y python3-pip python3-dev
pip3 install flask python-mpd2 gps3 obd mutagen --break-system-packages
```

---

## Configure Autostart

### X auto-start

Append to `~/.bash_profile`:

```bash
[[ -z $DISPLAY && $XDG_VTNR -eq 1 ]] && startx
```

### Dashboard auto-start

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

---

## Test Without Autostart

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

### Hardware-free test mode

Run the full UI without MPD / GPS / OBD / SDR connected:

```bash
python3 app.py --teste
```

---

## Configure Hardware Modules

### Interactive helper

For the common case of a USB ELM327 + USB GPS, run:

```bash
./scripts/setup_usb_devices.sh
```

The script detects the adapters and prints the configuration to use.

### GPS (manual)

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

### OBD-II (manual)

PiCASSO uses a **USB ELM327** adapter exposed at `/dev/ttyACM0`. Bluetooth ELM327 adapters are not supported.

```bash
ls -l /dev/ttyACM0
sudo usermod -a -G dialout $USER   # log out / back in afterwards
```

Run the discovery script to confirm the adapter and the vehicle reply with PIDs:

```bash
python3 experiments/obd-macos/obd_discovery.py
```

---

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
ls -l /dev/ttyACM0
dmesg | tail
groups   # must include 'dialout'
```

### Browser not opening

```bash
chromium --version
export DISPLAY=:0
chromium http://localhost:5000
```

---

## Logs

- **MPD**: `~/.mpd/log`
- **GPSD**: `sudo journalctl -u gpsd -f`
- **Dashboard**: terminal where the script is running
- **Kernel**: `sudo journalctl -k -f`

---

## Project Structure

The project is organized in modules:

```
pi-car/
├── app.py                  # Entry point (--teste for hardware-free mode)
├── config.py               # Configuration
├── VERSION                 # Project version (auto-bumped on commit)
├── .githooks/              # Shared git hooks
├── scripts/                # bump.sh, setup_usb_devices.sh
├── bootsplash/             # Plymouth boot splash assets
├── backend/
│   ├── routes/             # API endpoints
│   └── services/           # MPD, GPS, OBD, RTL-SDR, network, media sync, maintenance
├── frontend/
│   ├── static/css/         # Styles
│   ├── static/js/          # JavaScript
│   └── templates/          # HTML
├── docs/screenshots/       # README screenshots
├── logos/                  # PiCASSO brand assets
├── tests/                  # pytest suite
└── experiments/            # Prototypes (not part of the shipped product)
```

---

## Next Steps

- [ ] Add music to the `~/Music` folder
- [ ] Configure MPD playlists
- [ ] Test the GPS module with speed
- [ ] Plug and verify the USB ELM327 adapter
- [ ] Configure the vehicle electrical installation

---

## Useful Links

- [Raspberry Pi OS Downloads](https://www.raspberrypi.com/software/operating-systems/)
- [MPD Documentation](https://mpd.readthedocs.io/)
- [GPSD Documentation](https://gpsd.gitlab.io/gpsd/)
- [python-obd](https://python-obd.readthedocs.io/)
- [Plymouth](https://www.freedesktop.org/wiki/Software/Plymouth/)
