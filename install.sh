#!/bin/bash
#===============================================================================
#
#   Pi-Car Installer
#   DIY Vehicle Infotainment System for Raspberry Pi
#
#   Usage: curl -sSL https://raw.githubusercontent.com/flavioluiz/pi-car/main/install.sh | bash
#   Or:    ./install.sh
#
#   Tested on: Raspberry Pi OS Lite (Debian Trixie/Bookworm) 64-bit
#
#===============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Installation directory
INSTALL_DIR="$HOME/pi-car"
USER=$(whoami)

#-------------------------------------------------------------------------------
# Helper functions
#-------------------------------------------------------------------------------

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║                                                                   ║"
    echo "║     Pi-Car - DIY Vehicle Infotainment System                      ║"
    echo "║                                                                   ║"
    echo "║     Automated installer for Raspberry Pi OS Lite                  ║"
    echo "║                                                                   ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}▶ $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

check_root() {
    if [ "$EUID" -eq 0 ]; then
        log_error "Do not run as root! Use your normal user."
        log_error "The script will ask for sudo when needed."
        exit 1
    fi
}

check_raspberry_pi() {
    if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
        log_warn "This does not appear to be a Raspberry Pi."
        read -p "Do you want to continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

#-------------------------------------------------------------------------------
# System packages installation
#-------------------------------------------------------------------------------

install_system_packages() {
    log_step "Updating system and installing packages"

    sudo apt update
    sudo apt upgrade -y

    log_info "Installing minimal GUI (X11 + Openbox)..."
    sudo apt install -y \
        xorg \
        openbox \
        lxterminal \
        pcmanfm

    log_info "Installing audio and music player..."
    sudo apt install -y \
        alsa-utils \
        mpd \
        mpc \
        ario

    log_info "Installing GPS and navigation..."
    sudo apt install -y \
        gpsd \
        gpsd-clients \
        navit

    log_info "Installing web browser..."
    sudo apt install -y chromium

    log_info "Installing RTL-SDR (radio)..."
    sudo apt install -y \
        rtl-sdr \
        gqrx-sdr || log_warn "GQRX not available, skipping..."

    log_info "Installing auxiliary tools..."
    sudo apt install -y \
        git \
        python3-pip \
        python3-venv \
        bluetooth \
        bluez \
        htop \
        nano

    log_info "Installing fonts (emoji and symbols)..."
    sudo apt install -y \
        fonts-noto-color-emoji \
        fonts-symbola || log_warn "Some fonts not available, skipping..."

    log_info "System packages installed!"
}

#-------------------------------------------------------------------------------
# Python dependencies installation
#-------------------------------------------------------------------------------

install_python_packages() {
    log_step "Installing Python dependencies"

    pip3 install --break-system-packages \
        flask \
        python-mpd2 \
        gps3 \
        obd \
        pyrtlsdr \
        numpy \
        scipy

    log_info "Python packages installed!"
}

#-------------------------------------------------------------------------------
# MPD configuration
#-------------------------------------------------------------------------------

configure_mpd() {
    log_step "Configuring MPD (Music Player Daemon)"

    # Fix permissions if directory was created as root
    if [ -d "$HOME/.mpd" ]; then
        log_info "Fixing permissions for $HOME/.mpd..."
        sudo chown -R "$USER:$USER" "$HOME/.mpd"
    fi

    # Create necessary directories
    mkdir -p "$HOME/Music"
    mkdir -p "$HOME/.mpd/playlists"
    touch "$HOME/.mpd/database"

    # Backup original configuration
    if [ -f /etc/mpd.conf ]; then
        sudo cp /etc/mpd.conf /etc/mpd.conf.backup
    fi

    # Create new configuration
    sudo tee /etc/mpd.conf > /dev/null << MPDCONF
# Pi-Car MPD Configuration
# Automatically generated by installer

music_directory     "$HOME/Music"
playlist_directory  "$HOME/.mpd/playlists"
db_file             "$HOME/.mpd/database"
log_file            "$HOME/.mpd/log"
pid_file            "$HOME/.mpd/pid"
state_file          "$HOME/.mpd/state"
sticker_file        "$HOME/.mpd/sticker.sql"

user                "$USER"
bind_to_address     "localhost"
port                "6600"

auto_update         "yes"
auto_update_depth   "3"

# Audio output - 3.5mm Jack
audio_output {
    type        "alsa"
    name        "Headphones"
    device      "hw:Headphones,0"
    mixer_type  "software"
}

# HDMI output (backup)
audio_output {
    type        "alsa"
    name        "HDMI"
    device      "hw:vc4hdmi0,0"
    mixer_type  "software"
    enabled     "no"
}

# Software volume
mixer_type          "software"
volume_normalization "no"
MPDCONF

    # Enable and start MPD
    sudo systemctl enable mpd
    sudo systemctl restart mpd

    log_info "MPD configured!"
}

#-------------------------------------------------------------------------------
# GPS configuration
#-------------------------------------------------------------------------------

configure_gps() {
    log_step "Configuring GPSD"

    # Configure gpsd for common USB GPS (VK-162)
    sudo tee /etc/default/gpsd > /dev/null << GPSDCONF
# Pi-Car GPSD Configuration
START_DAEMON="true"
USBAUTO="true"
DEVICES="/dev/ttyACM0 /dev/ttyUSB0"
GPSD_OPTIONS="-n"
GPSD_SOCKET="/var/run/gpsd.sock"
GPSDCONF

    # Enable gpsd
    sudo systemctl enable gpsd

    log_info "GPSD configured!"
    log_warn "GPSD will start automatically when a USB GPS is connected."
}

#-------------------------------------------------------------------------------
# Bluetooth configuration (OBD-II)
#-------------------------------------------------------------------------------

configure_bluetooth() {
    log_step "Configuring Bluetooth for OBD-II"

    # Enable bluetooth
    sudo systemctl enable bluetooth
    sudo systemctl start bluetooth

    # Add user to bluetooth group
    sudo usermod -a -G bluetooth "$USER"

    log_info "Bluetooth enabled!"
    log_warn "To pair the ELM327, use: bluetoothctl"
    echo ""
    echo "    bluetoothctl commands:"
    echo "    > power on"
    echo "    > agent on"
    echo "    > scan on"
    echo "    > pair XX:XX:XX:XX:XX:XX"
    echo "    > trust XX:XX:XX:XX:XX:XX"
    echo ""
}

#-------------------------------------------------------------------------------
# Pi-Car installation
#-------------------------------------------------------------------------------

install_picar() {
    log_step "Installing Pi-Car"

    # Determine script source directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    # If running from inside a repository clone, use that directory
    if [ -f "$SCRIPT_DIR/app.py" ] && [ -d "$SCRIPT_DIR/backend" ] && [ -d "$SCRIPT_DIR/frontend" ]; then
        log_info "Local repository found at: $SCRIPT_DIR"
        INSTALL_DIR="$SCRIPT_DIR"
    else
        # Otherwise, clone from GitHub
        if [ -d "$INSTALL_DIR/.git" ]; then
            log_info "Existing repository found, updating..."
            cd "$INSTALL_DIR"
            git pull
        else
            log_info "Cloning repository from GitHub..."
            git clone https://github.com/flavioluiz/pi-car.git "$INSTALL_DIR"
        fi
    fi

    # Ensure execute permissions
    chmod +x "$INSTALL_DIR/start_dashboard.sh"
    chmod +x "$INSTALL_DIR/update_music.sh"
    chmod +x "$INSTALL_DIR/app.py" 2>/dev/null || true

    log_info "Pi-Car installed at: $INSTALL_DIR"
}

#-------------------------------------------------------------------------------
# Autostart configuration
#-------------------------------------------------------------------------------

configure_autostart() {
    log_step "Configuring automatic startup"

    # Create Openbox configuration directory
    mkdir -p "$HOME/.config/openbox"

    # Configure Openbox autostart
    cat > "$HOME/.config/openbox/autostart" << AUTOSTART
# Pi-Car Autostart
# Disable screensaver
xset s off
xset -dpms
xset s noblank

# Hide cursor after 3 seconds of inactivity
# unclutter -idle 3 &

# Start Pi-Car
$INSTALL_DIR/start_dashboard.sh &

# Wait for server to start
sleep 4

# Open Chromium in kiosk mode
chromium --kiosk --noerrdialogs --disable-infobars --no-first-run --disable-session-crashed-bubble --disable-restore-session-state http://localhost:5000 &
AUTOSTART

    # Configure .xinitrc
    echo "exec openbox-session" > "$HOME/.xinitrc"

    # Ask about X auto-login
    echo ""
    read -p "Do you want to start X automatically on boot? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        # Add to .bash_profile
        if ! grep -q "startx" "$HOME/.bash_profile" 2>/dev/null; then
            echo '[[ -z $DISPLAY && $XDG_VTNR -eq 1 ]] && startx' >> "$HOME/.bash_profile"
            log_info "X auto-login configured!"
        fi
    fi

    log_info "Autostart configured!"
}

#-------------------------------------------------------------------------------
# Final configuration and cleanup
#-------------------------------------------------------------------------------

finalize() {
    log_step "Finalizing installation"

    # Update music library (if any)
    log_info "Updating music library..."
    if [ -d "$HOME/Music" ] && [ "$(find "$HOME/Music" -type f \( -iname "*.mp3" -o -iname "*.flac" -o -iname "*.ogg" -o -iname "*.wav" -o -iname "*.m4a" \) 2>/dev/null | head -1)" ]; then
        mpc update --wait 2>/dev/null || true
        mpc clear 2>/dev/null || true
        mpc add / 2>/dev/null || true
        log_info "Music added to playlist!"
    else
        log_warn "No music found in ~/Music"
        log_info "Copy music to ~/Music and run: ./update_music.sh"
    fi

    # Clean apt cache
    sudo apt autoremove -y
    sudo apt clean

    log_info "Cleanup complete!"
}

#-------------------------------------------------------------------------------
# Final summary
#-------------------------------------------------------------------------------

print_summary() {
    echo ""
    echo -e "${GREEN}"
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║                                                                   ║"
    echo "║     Installation completed successfully!                          ║"
    echo "║                                                                   ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
    echo "Installation directory: $INSTALL_DIR"
    echo "Music directory:        $HOME/Music"
    echo ""
    echo -e "${CYAN}To start manually:${NC}"
    echo "   cd $INSTALL_DIR && ./start_dashboard.sh"
    echo ""
    echo -e "${CYAN}To start GUI:${NC}"
    echo "   startx"
    echo ""
    echo -e "${CYAN}For kiosk mode (fullscreen):${NC}"
    echo "   chromium --kiosk http://localhost:5000"
    echo ""
    echo -e "${YELLOW}Recommended next steps:${NC}"
    echo "   1. Copy music to ~/Music"
    echo "   2. Run 'mpc update' to update library"
    echo "   3. Pair ELM327 via 'bluetoothctl' (if available)"
    echo "   4. Connect USB GPS (if available)"
    echo "   5. Reboot to test autostart: sudo reboot"
    echo ""
    echo -e "${GREEN}Thank you for using Pi-Car!${NC}"
    echo ""
}

#-------------------------------------------------------------------------------
# Main
#-------------------------------------------------------------------------------

main() {
    print_banner
    check_root
    check_raspberry_pi

    echo ""
    echo "This script will install and configure Pi-Car."
    echo ""
    read -p "Do you want to continue? (Y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi

    install_system_packages
    install_python_packages
    configure_mpd
    configure_gps
    configure_bluetooth
    install_picar
    configure_autostart
    finalize
    print_summary
}

# Execute
main "$@"
