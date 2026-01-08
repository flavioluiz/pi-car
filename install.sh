#!/bin/bash
#===============================================================================
#
#   Pi-Car Installer
#   Central Multimídia Veicular para Raspberry Pi
#
#   Uso: curl -sSL https://raw.githubusercontent.com/flavioluiz/pi-car/main/install.sh | bash
#   Ou:  ./install.sh
#
#   Testado em: Raspberry Pi OS Lite (Debian Trixie/Bookworm) 64-bit
#
#===============================================================================

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Diretório de instalação
INSTALL_DIR="$HOME/pi-car"
USER=$(whoami)

#-------------------------------------------------------------------------------
# Funções auxiliares
#-------------------------------------------------------------------------------

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║                                                                   ║"
    echo "║     🚗  Pi-Car - Central Multimídia Veicular                      ║"
    echo "║                                                                   ║"
    echo "║     Instalador automático para Raspberry Pi OS Lite               ║"
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
    echo -e "${RED}[ERRO]${NC} $1"
}

log_step() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}▶ $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

check_root() {
    if [ "$EUID" -eq 0 ]; then
        log_error "Não execute como root! Use seu usuário normal."
        log_error "O script pedirá sudo quando necessário."
        exit 1
    fi
}

check_raspberry_pi() {
    if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
        log_warn "Este não parece ser um Raspberry Pi."
        read -p "Deseja continuar mesmo assim? (s/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Ss]$ ]]; then
            exit 1
        fi
    fi
}

#-------------------------------------------------------------------------------
# Instalação de pacotes do sistema
#-------------------------------------------------------------------------------

install_system_packages() {
    log_step "Atualizando sistema e instalando pacotes"

    sudo apt update
    sudo apt upgrade -y

    log_info "Instalando interface gráfica mínima (X11 + Openbox)..."
    sudo apt install -y \
        xorg \
        openbox \
        lxterminal \
        pcmanfm

    log_info "Instalando áudio e player de música..."
    sudo apt install -y \
        alsa-utils \
        mpd \
        mpc \
        ario

    log_info "Instalando GPS e navegação..."
    sudo apt install -y \
        gpsd \
        gpsd-clients \
        navit

    log_info "Instalando navegador web..."
    sudo apt install -y chromium

    log_info "Instalando RTL-SDR (rádio)..."
    sudo apt install -y \
        rtl-sdr \
        gqrx-sdr || log_warn "GQRX não disponível, pulando..."

    log_info "Instalando ferramentas auxiliares..."
    sudo apt install -y \
        git \
        python3-pip \
        python3-venv \
        bluetooth \
        bluez \
        htop \
        nano

    log_info "Pacotes do sistema instalados!"
}

#-------------------------------------------------------------------------------
# Instalação de dependências Python
#-------------------------------------------------------------------------------

install_python_packages() {
    log_step "Instalando dependências Python"

    pip3 install --break-system-packages \
        flask \
        python-mpd2 \
        gps3 \
        obd

    log_info "Pacotes Python instalados!"
}

#-------------------------------------------------------------------------------
# Configuração do MPD
#-------------------------------------------------------------------------------

configure_mpd() {
    log_step "Configurando MPD (Music Player Daemon)"

    # Criar diretórios necessários (corrigir permissões se necessário)
    mkdir -p "$HOME/Music"
    mkdir -p "$HOME/.mpd"

    # Corrigir permissões caso diretório tenha sido criado como root
    if [ -d "$HOME/.mpd" ] && [ ! -w "$HOME/.mpd" ]; then
        log_warn "Corrigindo permissões de $HOME/.mpd..."
        sudo chown -R "$USER:$USER" "$HOME/.mpd"
    fi

    mkdir -p "$HOME/.mpd/playlists"
    touch "$HOME/.mpd/database"

    # Backup da configuração original
    if [ -f /etc/mpd.conf ]; then
        sudo cp /etc/mpd.conf /etc/mpd.conf.backup
    fi

    # Criar nova configuração
    sudo tee /etc/mpd.conf > /dev/null << MPDCONF
# Pi-Car MPD Configuration
# Gerado automaticamente pelo instalador

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

# Saída de áudio - Jack 3.5mm
audio_output {
    type        "alsa"
    name        "Headphones"
    device      "hw:Headphones,0"
    mixer_type  "software"
}

# Saída HDMI (backup)
audio_output {
    type        "alsa"
    name        "HDMI"
    device      "hw:vc4hdmi0,0"
    mixer_type  "software"
    enabled     "no"
}

# Volume por software
mixer_type          "software"
volume_normalization "no"
MPDCONF

    # Habilitar e iniciar MPD
    sudo systemctl enable mpd
    sudo systemctl restart mpd

    log_info "MPD configurado!"
}

#-------------------------------------------------------------------------------
# Configuração do GPS
#-------------------------------------------------------------------------------

configure_gps() {
    log_step "Configurando GPSD"

    # Configurar gpsd para GPS USB comum (VK-162)
    sudo tee /etc/default/gpsd > /dev/null << GPSDCONF
# Pi-Car GPSD Configuration
START_DAEMON="true"
USBAUTO="true"
DEVICES="/dev/ttyACM0 /dev/ttyUSB0"
GPSD_OPTIONS="-n"
GPSD_SOCKET="/var/run/gpsd.sock"
GPSDCONF

    # Habilitar gpsd
    sudo systemctl enable gpsd

    log_info "GPSD configurado!"
    log_warn "GPSD iniciará automaticamente quando um GPS USB for conectado."
}

#-------------------------------------------------------------------------------
# Configuração do Bluetooth (OBD-II)
#-------------------------------------------------------------------------------

configure_bluetooth() {
    log_step "Configurando Bluetooth para OBD-II"

    # Habilitar bluetooth
    sudo systemctl enable bluetooth
    sudo systemctl start bluetooth

    # Adicionar usuário ao grupo bluetooth
    sudo usermod -a -G bluetooth "$USER"

    log_info "Bluetooth habilitado!"
    log_warn "Para parear o ELM327, use: bluetoothctl"
    echo ""
    echo "    Comandos do bluetoothctl:"
    echo "    > power on"
    echo "    > agent on"
    echo "    > scan on"
    echo "    > pair XX:XX:XX:XX:XX:XX"
    echo "    > trust XX:XX:XX:XX:XX:XX"
    echo ""
}

#-------------------------------------------------------------------------------
# Instalação do Pi-Car
#-------------------------------------------------------------------------------

install_picar() {
    log_step "Instalando Pi-Car"

    # Determinar diretório de origem do script
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    # Se estamos rodando de dentro de um clone do repositório, usar esse diretório
    if [ -f "$SCRIPT_DIR/app.py" ] && [ -f "$SCRIPT_DIR/start_dashboard.sh" ]; then
        log_info "Repositório local encontrado em: $SCRIPT_DIR"
        INSTALL_DIR="$SCRIPT_DIR"
    else
        # Se não, clonar do GitHub
        if [ -d "$INSTALL_DIR/.git" ]; then
            log_info "Repositório existente encontrado, atualizando..."
            cd "$INSTALL_DIR"
            git pull
        else
            log_info "Clonando repositório do GitHub..."
            git clone https://github.com/flavioluiz/pi-car.git "$INSTALL_DIR"
        fi
    fi

    # Garantir permissões de execução
    chmod +x "$INSTALL_DIR/start_dashboard.sh"
    chmod +x "$INSTALL_DIR/app.py" 2>/dev/null || true

    log_info "Pi-Car instalado em: $INSTALL_DIR"
}

#-------------------------------------------------------------------------------
# Configuração do Autostart
#-------------------------------------------------------------------------------

configure_autostart() {
    log_step "Configurando inicialização automática"

    # Criar diretório de configuração do Openbox
    mkdir -p "$HOME/.config/openbox"

    # Configurar autostart do Openbox
    cat > "$HOME/.config/openbox/autostart" << AUTOSTART
# Pi-Car Autostart
# Desativar screensaver
xset s off
xset -dpms
xset s noblank

# Esconder cursor após 3 segundos de inatividade
# unclutter -idle 3 &

# Iniciar Pi-Car
$INSTALL_DIR/start_dashboard.sh &

# Aguardar servidor iniciar
sleep 4

# Abrir Chromium em modo kiosk
chromium --kiosk --noerrdialogs --disable-infobars --no-first-run --disable-session-crashed-bubble --disable-restore-session-state http://localhost:5000 &
AUTOSTART

    # Configurar .xinitrc
    echo "exec openbox-session" > "$HOME/.xinitrc"

    # Perguntar sobre auto-login no X
    echo ""
    read -p "Deseja iniciar X automaticamente no boot? (S/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        # Adicionar ao .bash_profile
        if ! grep -q "startx" "$HOME/.bash_profile" 2>/dev/null; then
            echo '[[ -z $DISPLAY && $XDG_VTNR -eq 1 ]] && startx' >> "$HOME/.bash_profile"
            log_info "Auto-login no X configurado!"
        fi
    fi

    log_info "Autostart configurado!"
}

#-------------------------------------------------------------------------------
# Configurações finais e limpeza
#-------------------------------------------------------------------------------

finalize() {
    log_step "Finalizando instalação"

    # Atualizar banco de dados do MPD
    log_info "Atualizando banco de dados do MPD..."
    mpc update 2>/dev/null || true

    # Limpar cache do apt
    sudo apt autoremove -y
    sudo apt clean

    log_info "Limpeza concluída!"
}

#-------------------------------------------------------------------------------
# Resumo final
#-------------------------------------------------------------------------------

print_summary() {
    echo ""
    echo -e "${GREEN}"
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║                                                                   ║"
    echo "║     ✅  Instalação concluída com sucesso!                         ║"
    echo "║                                                                   ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
    echo "📁 Diretório de instalação: $INSTALL_DIR"
    echo "🎵 Diretório de músicas:    $HOME/Music"
    echo ""
    echo -e "${CYAN}Para iniciar manualmente:${NC}"
    echo "   cd $INSTALL_DIR && ./start_dashboard.sh"
    echo ""
    echo -e "${CYAN}Para iniciar interface gráfica:${NC}"
    echo "   startx"
    echo ""
    echo -e "${CYAN}Para modo kiosk (tela cheia):${NC}"
    echo "   chromium --kiosk http://localhost:5000"
    echo ""
    echo -e "${YELLOW}Próximos passos recomendados:${NC}"
    echo "   1. Copie músicas para ~/Music"
    echo "   2. Execute 'mpc update' para atualizar biblioteca"
    echo "   3. Pareie o ELM327 via 'bluetoothctl' (se tiver)"
    echo "   4. Conecte o GPS USB (se tiver)"
    echo "   5. Reinicie para testar autostart: sudo reboot"
    echo ""
    echo -e "${GREEN}Obrigado por usar o Pi-Car! 🚗${NC}"
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
    echo "Este script irá instalar e configurar o Pi-Car."
    echo ""
    read -p "Deseja continuar? (S/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        echo "Instalação cancelada."
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

# Executar
main "$@"
