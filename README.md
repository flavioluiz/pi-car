# Pi-Car

**DIY Vehicle Infotainment System with Raspberry Pi**

A vehicle infotainment system for older cars using Raspberry Pi 4 with a touchscreen web interface. Integrates music player, offline GPS navigation, OBD-II diagnostics, and SDR radio.

![Status](https://img.shields.io/badge/status-in%20development-yellow)
![Version](https://img.shields.io/badge/version-0.3.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Features

| Module | Description | Status |
|--------|-------------|--------|
| **Music** | MPD player with library browsing, playlists, shuffle, repeat | Working |
| **SDR Radio** | RTL-SDR receiver for FM/AM, aviation frequencies, waterfall spectrum | Working |
| **OBD-II** | RPM, speed, temperature, throttle position | v0.4 |
| **GPS** | Speed, satellites, coordinates + Navit integration | v0.5 |

---

## Screenshots

*Coming soon*

---

## Required Hardware

### Essential
- Raspberry Pi 4 (2GB+ RAM)
- Touchscreen monitor (HDMI)
- microSD card (16GB+)
- 5V 3A power supply

### Optional Modules
| Component | Suggested Model | Est. Price (USD) |
|-----------|-----------------|------------------|
| USB GPS | VK-162 (u-blox 7) | $15-30 |
| OBD-II | ELM327 Bluetooth | $10-25 |
| SDR Radio | RTL-SDR V3 | $25-40 |

### Vehicle Installation
| Component | Description | Est. Price (USD) |
|-----------|-------------|------------------|
| DC-DC Converter | 12V → 5V 3A+ USB | $8-15 |
| Inline Fuse | 5A with fuse holder | $5-10 |
| Add-a-fuse | For fuse box tap | $5-8 |

---

## Installation

**Automated installation available!**

### Quick Method (Recommended)

**Prerequisite:** Raspberry Pi OS **Lite** (64-bit) installed and configured with internet access.

```bash
# Install git (not included in OS Lite)
sudo apt update && sudo apt install -y git

# Clone repository
git clone https://github.com/flavioluiz/pi-car.git
cd pi-car

# Make executable and run
chmod +x install.sh
./install.sh

# Reboot
sudo reboot
```

The installation script will:
- Update the system (apt update/upgrade)
- Install minimal GUI (X11 + Openbox)
- Install MPD, GPSD, Navit, Chromium
- Install RTL-SDR and radio tools
- Configure Bluetooth for OBD-II
- Install Python dependencies (Flask, python-mpd2, gps3, obd)
- Configure autostart for Flask server and Chromium kiosk mode

After reboot, the system will automatically start with the Pi-Car dashboard in fullscreen.

**Full details**: See [INSTALLATION.md](INSTALLATION.md) for detailed instructions.

### Manual Installation

If you prefer to install each component manually, see the [INSTALLATION.md](INSTALLATION.md) guide.

### Run Manually (without autostart)

```bash
cd ~/pi-car
./start_dashboard.sh
```

Access: **http://localhost:5000**

### Kiosk Mode (Fullscreen)

```bash
chromium --kiosk --noerrdialogs --disable-infobars --no-first-run http://localhost:5000
```

Exit: `Alt+F4` or `Ctrl+W`

---

## Autostart

The installation script configures autostart automatically. For manual configuration:

### Configure Openbox autostart

```bash
mkdir -p ~/.config/openbox
nano ~/.config/openbox/autostart
```

Add:

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

### Configure .xinitrc

```bash
echo "exec openbox-session" > ~/.xinitrc
```

### Auto-login to X

To start X automatically on boot, add to `~/.bash_profile`:

```bash
[[ -z $DISPLAY && $XDG_VTNR -eq 1 ]] && startx
```

---

## Vehicle Electrical Installation

```
┌─────────────────┐
│    Fuse Box     │
│                 │
│  ┌───────────┐  │      ┌─────────────┐      ┌─────────────┐
│  │ ACC Fuse  │──┼──────│  5A Fuse    │──────│  DC-DC      │──── 5V USB ──→ RPi
│  │ (add-a-   │  │      │  (inline)   │      │  12V → 5V   │
│  │  fuse)    │  │      └─────────────┘      └──────┬──────┘
│  └───────────┘  │                                  │
│                 │                                  │
└─────────────────┘                             GND ─┴─→ Chassis
```

**Important:** Use the ACC line so the system only powers on with ignition.

---

## Project Structure

```
pi-car/
├── app.py                      # Entry point - Flask server
├── config.py                   # Centralized configuration
├── start_dashboard.sh          # Startup script
├── update_music.sh             # Music library update script
├── install.sh                  # Automated installation script
├── README.md                   # This file
├── INSTALLATION.md             # Detailed installation guide
│
├── backend/                    # Server logic
│   ├── __init__.py
│   ├── routes/                 # API endpoints (Flask Blueprints)
│   │   ├── __init__.py
│   │   ├── music.py            # /api/music/* - MPD control
│   │   ├── gps.py              # /api/gps/* - GPS data
│   │   ├── vehicle.py          # /api/vehicle/* - OBD-II data
│   │   ├── radio.py            # /api/radio/* - SDR radio control
│   │   └── system.py           # /api/status, /api/launch/*
│   │
│   └── services/               # Integration services
│       ├── __init__.py
│       ├── mpd_service.py      # MPD connection and control
│       ├── gps_service.py      # GPS monitoring thread
│       ├── obd_service.py      # OBD-II monitoring thread
│       └── rtlsdr_service.py   # RTL-SDR radio control
│
└── frontend/                   # Web interface
    ├── static/
    │   ├── css/
    │   │   └── style.css       # Interface styles
    │   └── js/
    │       └── app.js          # JavaScript logic
    │
    └── templates/
        └── index.html          # Main page
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Chromium (Kiosk Mode)                    │
│                    http://localhost:5000                    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              frontend/ (HTML/CSS/JS)                 │   │
│  │     templates/index.html + static/css + static/js   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│            Flask Server (:5000) - app.py + config.py        │
│                                                             │
│  ┌─────────────────── backend/routes/ ──────────────────────┐   │
│  │  music.py   gps.py   vehicle.py   radio.py   system.py  │   │
│  │  /api/music/* /api/gps/* /api/vehicle/* /api/radio/*    │   │
│  └──────────────────────────┬──────────────────────────────┘   │
│                             │                                   │
│  ┌─────────────────── backend/services/ ───────────────────┐   │
│  │  mpd_service   gps_service   obd_service   rtlsdr_service│   │
│  └────┬───────────────┬─────────────┬───────────────┬──────┘   │
└───────┼───────────────┼─────────────┼───────────────┼──────────┘
        │               │             │               │
        ▼               ▼             ▼               ▼
  ┌───────────┐  ┌───────────┐  ┌─────────────┐  ┌─────────────┐
  │    MPD    │  │   gpsd    │  │  python-obd │  │  rtl_fm/    │
  │  (:6600)  │  │  (:2947)  │  │             │  │  rtl_power  │
  └───────────┘  └─────┬─────┘  └──────┬──────┘  └──────┬──────┘
                       │               │                │
                 ┌─────▼─────┐   ┌─────▼─────┐   ┌──────▼──────┐
                 │  GPS USB  │   │  ELM327   │   │  RTL-SDR    │
                 │  VK-162   │   │ Bluetooth │   │  USB dongle │
                 └───────────┘   └───────────┘   └─────────────┘
```

---

## Roadmap

### v0.1
- [x] Basic web interface with tab navigation
- [x] Basic music control (play, pause, next, prev, volume)
- [x] Modular backend/frontend structure
- [x] Kiosk mode with Chromium

### v0.2 - Music
- [x] Browsable music library
- [x] Artist listing
- [x] Playlist management
- [x] Shuffle and repeat
- [x] Queue management
- [x] Search functionality
- [x] Seek and restart

### v0.3 - SDR Radio (Current)
- [x] RTL-SDR integration with rtl_fm/rtl_power
- [x] FM/AM frequency tuning
- [x] Radio control interface with presets
- [x] Aviation frequency presets (SBSJ, SBGR)
- [x] Favorites management
- [x] Real-time waterfall spectrum analyzer
- [x] Touch-friendly frequency adjustment buttons
- [x] Configurable spectrum parameters

### v0.4 - OBD-II
- [ ] Vehicle data reading (RPM, speed, temperature)
- [ ] Real-time gauge display
- [ ] Bluetooth connection with ELM327

### v0.5 - GPS
- [ ] Position reading via gpsd
- [ ] Speed and satellite display
- [ ] Navit navigation integration

### Future
- [ ] Themes (light/dark/auto)
- [ ] Settings via interface
- [ ] OBD error codes with descriptions
- [ ] Trip history
- [ ] Ready-to-download image

---

## Contributing

Contributions are welcome! Please:

1. Fork the project
2. Create a branch for your feature (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -m 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Open a Pull Request

---

## License

This project is under the MIT license. See the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [MPD](https://www.musicpd.org/) - Music Player Daemon
- [Navit](https://www.navit-project.org/) - Open source navigation
- [python-obd](https://python-obd.readthedocs.io/) - OBD-II library
- [RTL-SDR](https://www.rtl-sdr.com/) - Software Defined Radio

---

## Contact

Flavio

Project link: [https://github.com/flavioluiz/pi-car](https://github.com/flavioluiz/pi-car)
