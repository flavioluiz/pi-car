#!/bin/bash
#===============================================================================
#
#   Pi-Car Boot Splash Installer
#
#   Installs a custom Plymouth theme (ASCII-art classic car) and silences
#   boot-time kernel/console output so nothing but the splash shows until X
#   starts the dashboard.
#
#   Usage: sudo ./bootsplash/install.sh
#   Revert: sudo ./bootsplash/uninstall.sh
#
#===============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THEME_NAME="pi-car"
THEME_DIR="/usr/share/plymouth/themes/${THEME_NAME}"

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

#-------------------------------------------------------------------------------
# 1. Dependencies
#-------------------------------------------------------------------------------
info "Installing dependencies (plymouth, pillow, fonts)..."
apt-get update -qq
apt-get install -y \
    plymouth plymouth-themes plymouth-label \
    initramfs-tools \
    python3-pil \
    fonts-dejavu-core

#-------------------------------------------------------------------------------
# 2. Render the ASCII art into a PNG and install the theme
#-------------------------------------------------------------------------------
info "Rendering splash PNG from ASCII source..."
mkdir -p "$THEME_DIR"
python3 "$SCRIPT_DIR/render_splash.py" \
    "$SCRIPT_DIR/splash.txt" \
    "$THEME_DIR/splash.png"

info "Installing Plymouth theme files..."
install -m 0644 "$SCRIPT_DIR/pi-car.plymouth" "$THEME_DIR/pi-car.plymouth"
install -m 0644 "$SCRIPT_DIR/pi-car.script"   "$THEME_DIR/pi-car.script"

info "Setting '${THEME_NAME}' as default Plymouth theme..."
plymouth-set-default-theme -R "$THEME_NAME"

#-------------------------------------------------------------------------------
# 3. Patch /boot/firmware/cmdline.txt (kernel args: quiet splash + no cursor)
#-------------------------------------------------------------------------------
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
    for opt in quiet splash loglevel=0 logo.nologo vt.global_cursor_default=0 plymouth.ignore-serial-consoles; do
        if ! grep -qw -- "$opt" "$CMDLINE"; then
            MISSING="$MISSING $opt"
        fi
    done
    if [ -n "$MISSING" ]; then
        # cmdline.txt must stay on a single line — append options in-place
        CONTENT="$(tr -d '\n' < "$CMDLINE")"
        printf '%s%s\n' "$CONTENT" "$MISSING" > "$CMDLINE"
        ok "Added:$MISSING"
    else
        ok "All kernel options already present."
    fi
fi

#-------------------------------------------------------------------------------
# 4. Patch config.txt (disable rainbow splash)
#-------------------------------------------------------------------------------
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

#-------------------------------------------------------------------------------
# 5. Keep Plymouth visible until X takes over
#-------------------------------------------------------------------------------
info "Keeping Plymouth visible until the display server starts..."
systemctl disable plymouth-quit.service       >/dev/null 2>&1 || true
systemctl enable  plymouth-quit-wait.service  >/dev/null 2>&1 || true

#-------------------------------------------------------------------------------
# Done
#-------------------------------------------------------------------------------
echo ""
ok "Boot splash installed."
echo ""
echo "   Backups:"
[ -n "$CMDLINE" ] && echo "     ${CMDLINE}.pi-car.bak"
[ -n "$CONFIG"  ] && echo "     ${CONFIG}.pi-car.bak"
echo ""
echo "   Reboot to see the new splash:   sudo reboot"
echo "   Revert:                         sudo $SCRIPT_DIR/uninstall.sh"
