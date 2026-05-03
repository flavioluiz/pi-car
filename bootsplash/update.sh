#!/bin/bash
#===============================================================================
#
#   Pi-Car Boot Splash Quick Updater
#
#   Updates only the already-installed Plymouth theme files, hold service and
#   boot parameters. It does not run apt or reinstall packages.
#
#   Usage: sudo ./bootsplash/update.sh
#
#===============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THEME_NAME="pi-car"
THEME_DIR="/usr/share/plymouth/themes/${THEME_NAME}"
HOLD_SERVICE="/etc/systemd/system/pi-car-plymouth-hold.service"
HOLD_SCRIPT="/usr/local/bin/pi-car-plymouth-hold"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}==>${NC} $*"; }
warn()  { echo -e "${YELLOW}WARNING:${NC} $*" >&2; }
ok()    { echo -e "${GREEN}✓${NC} $*"; }

if [ "$EUID" -ne 0 ]; then
    echo "This script must be run with sudo." >&2
    exit 1
fi

if ! command -v plymouth-set-default-theme >/dev/null 2>&1; then
    echo "Plymouth is not installed. Run sudo ./bootsplash/install.sh once first." >&2
    exit 1
fi

if ! python3 - <<'PY' >/dev/null 2>&1
from PIL import Image
PY
then
    echo "python3-pil is not installed. Run sudo ./bootsplash/install.sh once first." >&2
    exit 1
fi

if [ -f "$SCRIPT_DIR/../picasso.jpg" ]; then
    SPLASH_SOURCE="$SCRIPT_DIR/../picasso.jpg"
else
    SPLASH_SOURCE="$SCRIPT_DIR/splash.txt"
fi

info "Updating Plymouth theme image from $SPLASH_SOURCE ..."
mkdir -p "$THEME_DIR"
python3 "$SCRIPT_DIR/render_splash.py" "$SPLASH_SOURCE" "$THEME_DIR/splash.png"
install -m 0644 "$SCRIPT_DIR/pi-car.plymouth" "$THEME_DIR/pi-car.plymouth"
install -m 0644 "$SCRIPT_DIR/pi-car.script" "$THEME_DIR/pi-car.script"

info "Setting '${THEME_NAME}' as default Plymouth theme..."
plymouth-set-default-theme -R "$THEME_NAME"

if [ -f /boot/firmware/cmdline.txt ]; then
    CMDLINE=/boot/firmware/cmdline.txt
elif [ -f /boot/cmdline.txt ]; then
    CMDLINE=/boot/cmdline.txt
else
    CMDLINE=""
    warn "cmdline.txt not found, skipping kernel parameter changes."
fi

if [ -n "$CMDLINE" ]; then
    info "Patching $CMDLINE ..."
    [ -f "${CMDLINE}.pi-car.bak" ] || cp "$CMDLINE" "${CMDLINE}.pi-car.bak"

    MISSING=""
    for opt in quiet splash loglevel=0 systemd.show_status=false rd.udev.log_level=0 logo.nologo vt.global_cursor_default=0 plymouth.ignore-serial-consoles; do
        if ! grep -qw -- "$opt" "$CMDLINE"; then
            MISSING="$MISSING $opt"
        fi
    done
    if [ -n "$MISSING" ]; then
        CONTENT="$(tr -d '\n' < "$CMDLINE")"
        printf '%s%s\n' "$CONTENT" "$MISSING" > "$CMDLINE"
        ok "Added:$MISSING"
    else
        ok "All kernel options already present."
    fi
fi

if [ -f /boot/firmware/config.txt ]; then
    CONFIG=/boot/firmware/config.txt
elif [ -f /boot/config.txt ]; then
    CONFIG=/boot/config.txt
else
    CONFIG=""
    warn "config.txt not found, skipping disable_splash."
fi

if [ -n "$CONFIG" ]; then
    info "Patching $CONFIG ..."
    [ -f "${CONFIG}.pi-car.bak" ] || cp "$CONFIG" "${CONFIG}.pi-car.bak"
    if ! grep -q "^disable_splash=1" "$CONFIG"; then
        printf '\n# Pi-Car: disable rainbow splash\ndisable_splash=1\n' >> "$CONFIG"
        ok "Appended disable_splash=1"
    else
        ok "disable_splash=1 already set."
    fi
fi

info "Restoring safe Plymouth handoff before X starts..."
systemctl disable pi-car-plymouth-hold.service >/dev/null 2>&1 || true
rm -f "$HOLD_SERVICE" "$HOLD_SCRIPT"
systemctl daemon-reload
systemctl unmask plymouth-quit.service       >/dev/null 2>&1 || true
systemctl unmask plymouth-quit-wait.service  >/dev/null 2>&1 || true
systemctl disable plymouth-quit.service      >/dev/null 2>&1 || true
systemctl enable  plymouth-quit-wait.service >/dev/null 2>&1 || true

echo ""
ok "Boot splash updated without reinstalling packages."
echo "   Reboot to test: sudo reboot"
