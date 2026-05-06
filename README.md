# Pi-Car

**DIY Vehicle Infotainment System with Raspberry Pi**

A vehicle infotainment system for older cars using Raspberry Pi 4 with a touchscreen web interface. Integrates music player, offline GPS navigation, OBD-II diagnostics, and SDR radio.

![Status](https://img.shields.io/badge/status-in%20development-yellow)
![Version](https://img.shields.io/badge/version-0.5.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Features

| Module | Description | Status |
|--------|-------------|--------|
| **Music** | MPD player with library browsing, playlists, shuffle, repeat | Working |
| **SDR Radio** | RTL-SDR receiver for FM/AM, aviation frequencies, waterfall spectrum | Working |
| **OBD-II** | Dynamic vehicle metrics display (RPM, speed, temps, throttle, etc.) | Working |
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
| OBD-II | ELM327 USB adapter | $10-25 |
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

## Media Sync via SSH

The Settings page can sync the remote media repository into the Raspberry Pi:

- `root@picasso-repo:/repository/Musics/` -> `~/Music/`
- `root@picasso-repo:/repository/Playlists/` -> `~/.mpd/playlists/`

The backend expects the SSH key at `~/.ssh/id_ed25519`.

### 1. Generate the SSH key on the Raspberry Pi

Run on the Raspberry Pi:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -C "pi-car-media-sync"
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub
```

If the file already exists and you want to keep using it, do not overwrite it.

### 2. Install the public key on `picasso-repo`

Show the public key:

```bash
cat ~/.ssh/id_ed25519.pub
```

Copy that output and append it to the server's `authorized_keys`:

```bash
mkdir -p /root/.ssh
chmod 700 /root/.ssh
echo "PASTE_THE_PUBLIC_KEY_HERE" >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
```

If you have password SSH access to `picasso-repo`, you can also use:

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@picasso-repo
```

### 3. Test SSH access

From the Raspberry Pi:

```bash
ssh -i ~/.ssh/id_ed25519 root@picasso-repo 'echo ok'
```

Expected output:

```text
ok
```

### 4. Test rsync manually

Music:

```bash
rsync -avz --delete -e "ssh -i ~/.ssh/id_ed25519" root@picasso-repo:/repository/Musics/ ~/Music/
```

Playlists:

```bash
rsync -avz --delete -e "ssh -i ~/.ssh/id_ed25519" root@picasso-repo:/repository/Playlists/ ~/.mpd/playlists/
```

If both commands work, the `Sync now` button in Settings should work too.

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
                 │  VK-162   │   │    USB    │   │  USB dongle │
                 └───────────┘   └───────────┘   └─────────────┘
```

---

## Testing OBD-II

The OBD-II module uses a USB ELM327 adapter connected at `/dev/ttyACM0`.

### Quick Test

```bash
# 1. Connect USB OBD-II adapter to vehicle and Raspberry Pi
# 2. Turn vehicle ignition ON (engine can be off)

# 3. Check if device is detected
ls -la /dev/ttyACM0

# 4. Run discovery script to see supported commands
cd ~/pi-car
python3 experiments/obd-macos/obd_discovery.py

# 5. Start the dashboard
python3 app.py

# 6. Open browser to http://localhost:5000
# 7. Click VEHICLE tab - gauges will display available metrics

# Optional: run the UI without hardware using simulated data
python3 app.py --teste
```

### Supported Metrics

The system automatically discovers which OBD-II PIDs your vehicle supports. Common metrics include:

| Metric | Description | Unit |
|--------|-------------|------|
| RPM | Engine revolutions | rpm |
| SPEED | Vehicle speed | km/h |
| COOLANT_TEMP | Engine coolant temperature | °C |
| THROTTLE_POS | Throttle position | % |
| ENGINE_LOAD | Calculated engine load | % |
| INTAKE_TEMP | Intake air temperature | °C |
| FUEL_LEVEL | Fuel tank level | % |
| OIL_TEMP | Engine oil temperature | °C |

### Troubleshooting

- **Device not found**: Check USB connection, try `dmesg | tail` to see device messages
- **No data**: Ensure ignition is ON, some vehicles require engine running
- **Permission denied**: Add user to dialout group: `sudo usermod -a -G dialout $USER`

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

### v0.3 - SDR Radio
- [x] RTL-SDR integration with rtl_fm/rtl_power
- [x] FM/AM frequency tuning
- [x] Radio control interface with presets
- [x] Aviation frequency presets (SBSJ, SBGR)
- [x] Favorites management
- [x] Real-time waterfall spectrum analyzer
- [x] Touch-friendly frequency adjustment buttons
- [x] Configurable spectrum parameters

### v0.4 - OBD-II (Current)
- [x] USB OBD-II adapter support (/dev/ttyACM0)
- [x] Automatic command discovery (queries vehicle for supported PIDs)
- [x] Dynamic gauge display (shows all available metrics)
- [x] Real-time vehicle data (RPM, speed, temperatures, throttle, etc.)
- [x] Connection retry with error handling

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
2. Enable the shared git hooks once: `git config core.hooksPath .githooks`
3. Create a branch for your feature (`git checkout -b feature/new-feature`)
4. Commit your changes (`git commit -m 'Add new feature'`)
5. Push to the branch (`git push origin feature/new-feature`)
6. Open a Pull Request

### Versioning

The project version lives in [`VERSION`](VERSION) and is mirrored in the README badge.

- Each commit auto-bumps the **patch** number via the `pre-commit` hook in `.githooks/`. Enable it once with `git config core.hooksPath .githooks`.
- For **minor** or **major** bumps, run `scripts/bump.sh minor` (or `major`) and stage the change before committing — the hook detects an already-staged `VERSION` and skips the auto-bump.
- The hook is skipped during rebase, merge, cherry-pick, and revert.

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
