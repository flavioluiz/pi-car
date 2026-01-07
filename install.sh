#!/bin/bash
# Script de instalação Pi-Car para Raspberry Pi OS 64 Lite
# Autor: Flavio @ ITA

set -e

echo "=== Instalação Pi-Car ==="
echo "Este script instalará todas as dependências necessárias"
echo ""

# Verificar se está rodando como root
if [ "$EUID" -eq 0 ]; then 
    echo "⚠️  Não execute este script como root!"
    echo "Execute como usuário pi normal (o script usará sudo quando necessário)"
    exit 1
fi

# Atualizar sistema
echo "📦 Atualizando pacotes..."
sudo apt update && sudo apt upgrade -y

# Instalar dependências do sistema
echo "🖥️  Instalando interface gráfica..."
sudo apt install -y xorg openbox lxterminal pcmanfm

echo "🎵 Instalando MPD..."
sudo apt install -y mpd mpc alsa-utils

echo "📍 Instalando GPS..."
sudo apt install -y gpsd gpsd-clients navit

echo "🌐 Instalando navegador..."
sudo apt install -y chromium-browser

echo "🐍 Instalando dependências Python..."
sudo apt install -y python3-pip python3-dev

# Instalar pacotes Python
echo "📚 Instalando pacotes Python..."
pip3 install flask python-mpd2 gps3 obd --break-system-packages

# Configurar MPD
echo "⚙️  Configurando MPD..."
mkdir -p ~/Music ~/.mpd/playlists
touch ~/.mpd/database ~/.mpd/log ~/.mpd/pid ~/.mpd/state

if [ ! -f /etc/mpd.conf.backup ]; then
    sudo cp /etc/mpd.conf /etc/mpd.conf.backup
fi

# Backup e configuração do MPD
cat > /tmp/mpd.conf << EOF
music_directory    "/home/$USER/Music"
playlist_directory "/home/$USER/.mpd/playlists"
db_file            "/home/$USER/.mpd/database"
log_file           "/home/$USER/.mpd/log"
pid_file           "/home/$USER/.mpd/pid"
state_file         "/home/$USER/.mpd/state"

audio_output {
    type    "alsa"
    name    "Headphones"
    device  "hw:0,0"
}

bind_to_address "localhost"
port            "6600"
EOF

sudo cp /tmp/mpd.conf /etc/mpd.conf
sudo systemctl enable mpd
sudo systemctl start mpd

# Configurar gpsd
echo "⚙️  Configurando gpsd..."
sudo systemctl stop gpsd.socket
sudo systemctl disable gpsd.socket
sudo systemctl enable gpsd
sudo systemctl start gpsd

# Configurar auto-start do X
echo "⚙️  Configurando auto-start..."
if ! grep -q "startx" ~/.bash_profile; then
    echo '[[ -z $DISPLAY && $XDG_VTNR -eq 1 ]] && startx' >> ~/.bash_profile
fi

# Configurar autostart do Openbox
mkdir -p ~/.config/openbox
cat > ~/.config/openbox/autostart << EOF
# Desativar screensaver
xset s off
xset -dpms
xset s noblank

# Iniciar dashboard
sleep 2
$(pwd)/start_dashboard.sh &

# Aguardar servidor
sleep 3

# Chromium em modo kiosk
chromium-browser --kiosk --noerrdialogs --disable-infobars --no-first-run http://localhost:5000 &
EOF

# Permissões
chmod +x start_dashboard.sh

echo ""
echo "✅ Instalação concluída!"
echo ""
echo "🔄 Para aplicar as mudanças, execute:"
echo "   sudo reboot"
echo ""
echo "🌐 Após o reboot, acesse:"
echo "   http://localhost:5000"
echo ""
echo "📝 Logs:"
echo "   MPD:     ~/.mpd/log"
echo "   GPSD:    sudo journalctl -u gpsd"
echo ""