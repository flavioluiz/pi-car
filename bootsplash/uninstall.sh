#!/bin/bash
#===============================================================================
#
#   Pi-Car Boot Splash Uninstaller
#
#   Restores the default Plymouth theme, removes the pi-car theme files,
#   and restores the cmdline.txt / config.txt backups created by install.sh.
#
#   Usage: sudo ./bootsplash/uninstall.sh
#
#===============================================================================

set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

info() { echo -e "${CYAN}==>${NC} $*"; }
ok()   { echo -e "${GREEN}✓${NC} $*"; }

if [ "$EUID" -ne 0 ]; then
    echo "This script must be run with sudo." >&2
    exit 1
fi

THEME_DIR="/usr/share/plymouth/themes/pi-car"

info "Restoring default Plymouth theme..."
if plymouth-set-default-theme -R spinner >/dev/null 2>&1; then
    ok "Reset to 'spinner'"
else
    plymouth-set-default-theme -R text >/dev/null 2>&1 || true
    ok "Reset to 'text'"
fi

info "Removing pi-car theme files..."
rm -rf "$THEME_DIR"
ok "Removed $THEME_DIR"

info "Restoring boot configuration backups..."
for f in /boot/firmware/cmdline.txt /boot/cmdline.txt /boot/firmware/config.txt /boot/config.txt; do
    if [ -f "${f}.pi-car.bak" ]; then
        mv "${f}.pi-car.bak" "$f"
        ok "Restored $f"
    fi
done

info "Restoring plymouth-quit service..."
systemctl enable  plymouth-quit.service       >/dev/null 2>&1 || true
systemctl disable plymouth-quit-wait.service  >/dev/null 2>&1 || true

echo ""
ok "Uninstall complete. Reboot to apply: sudo reboot"
