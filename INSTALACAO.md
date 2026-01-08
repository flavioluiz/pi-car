# Instalação Pi-Car no Raspberry Pi OS 64 Lite

Guia completo para configurar o ambiente de desenvolvimento e produção do Pi-Car.

## Requisitos

- Raspberry Pi 4 (2GB+ RAM recomendado)
- **Raspberry Pi OS Lite (64-bit)** - Debian Bookworm/Trixie
  - Importante: Use a versão **Lite** (sem desktop), o script instalará apenas o necessário
- Conexão com internet
- Acesso SSH ou terminal físico

## Instalação Automática

### 1. Instalar git

O git não vem instalado por padrão no Raspberry Pi OS Lite:

```bash
sudo apt update && sudo apt install -y git
```

### 2. Clonar o repositório

```bash
git clone https://github.com/flavioluiz/pi-car.git
cd pi-car
```

### 3. Executar script de instalação

```bash
chmod +x install.sh
./install.sh
```

O script instalará e configurará automaticamente:
- **Sistema**: Atualização completa (apt update/upgrade)
- **Interface gráfica**: X11 + Openbox (mínimo necessário)
- **Áudio**: ALSA, MPD (Music Player Daemon), MPC
- **GPS**: GPSD, gpsd-clients, Navit (navegação offline)
- **Navegador**: Chromium (modo kiosk)
- **Rádio SDR**: RTL-SDR, GQRX (se disponível)
- **Bluetooth**: Para conexão com ELM327 (OBD-II)
- **Python**: Flask, python-mpd2, gps3, obd
- **Autostart**: Servidor Flask + Chromium em modo kiosk

### 4. Reiniciar

```bash
sudo reboot
```

Após o reinício, o sistema iniciará automaticamente o Chromium em modo kiosk com o dashboard Pi-Car em tela cheia.

## Instalação Manual

Se preferir instalar cada componente manualmente:

### Atualizar sistema

```bash
sudo apt update && sudo apt upgrade -y
```

### Interface gráfica

```bash
sudo apt install -y xorg openbox lxterminal pcmanfm
```

### MPD (Música)

```bash
sudo apt install -y mpd mpc alsa-utils
mkdir -p ~/Music ~/.mpd/playlists
touch ~/.mpd/database ~/.mpd/log ~/.mpd/pid ~/.mpd/state
```

Configure `/etc/mpd.conf`:

```conf
music_directory    "/home/SEU_USUARIO/Music"
playlist_directory "/home/SEU_USUARIO/.mpd/playlists"
db_file            "/home/SEU_USUARIO/.mpd/database"
log_file           "/home/SEU_USUARIO/.mpd/log"
pid_file           "/home/SEU_USUARIO/.mpd/pid"
state_file         "/home/SEU_USUARIO/.mpd/state"

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

### Navegador

```bash
sudo apt install -y chromium
```

### Dependências Python

```bash
sudo apt install -y python3-pip python3-dev
pip3 install flask python-mpd2 gps3 obd --break-system-packages
```

## Configurar Autostart

### Auto-start do X

Adicione ao final de `~/.bash_profile`:

```bash
[[ -z $DISPLAY && $XDG_VTNR -eq 1 ]] && startx
```

### Auto-start do Dashboard

Crie `~/.config/openbox/autostart`:

```bash
# Desativar screensaver
xset s off
xset -dpms
xset s noblank

# Iniciar dashboard
~/pi-car/start_dashboard.sh &

# Aguardar servidor
sleep 4

# Chromium em modo kiosk
chromium --kiosk --noerrdialogs --disable-infobars --no-first-run --disable-session-crashed-bubble --disable-restore-session-state http://localhost:5000 &
```

## Testar sem Autostart

Para testar manualmente sem reiniciar:

### Iniciar interface gráfica
```bash
startx
```

### Em outro terminal, iniciar o dashboard
```bash
cd pi-car
chmod +x start_dashboard.sh
./start_dashboard.sh
```

### Abrir navegador
```bash
chromium http://localhost:5000
```

## Configurar Módulos de Hardware

### GPS

Conecte o módulo GPS USB e verifique:

```bash
ls -l /dev/ttyUSB* /dev/ttyACM*
```

Configure o gpsd:

```bash
sudo systemctl stop gpsd
sudo gpsd /dev/ttyUSB0 -F /var/run/gpsd.sock
sudo systemctl start gpsd
```

### OBD-II

Pareie o adaptador ELM327 Bluetooth:

```bash
sudo bluetoothctl
scan on
pair XX:XX:XX:XX:XX:XX
connect XX:XX:XX:XX:XX:XX
trust XX:XX:XX:XX:XX:XX
exit
```

Conecte ao dispositivo serial:

```bash
sudo rfcomm bind 0 XX:XX:XX:XX:XX:XX
```

## Solução de Problemas

### MPD não inicia

```bash
sudo systemctl status mpd
cat ~/.mpd/log
```

### GPS não funciona

```bash
sudo systemctl status gpsd
cgps -s
```

### OBD não conecta

```bash
bluetoothctl
info XX:XX:XX:XX:XX:XX
ls -l /dev/rfcomm*
```

### Navegador não abre

```bash
chromium --version
export DISPLAY=:0
chromium http://localhost:5000
```

## Logs

- **MPD**: `~/.mpd/log`
- **GPSD**: `sudo journalctl -u gpsd -f`
- **Dashboard**: Terminal onde o script esta rodando
- **Kernel**: `sudo journalctl -k -f`

## Estrutura do Projeto

O projeto esta organizado em modulos:

```
pi-car/
├── app.py                  # Entry point
├── config.py               # Configuracoes
├── backend/
│   ├── routes/             # Endpoints da API
│   └── services/           # Logica de negocio (MPD, GPS, OBD)
└── frontend/
    ├── static/css/         # Estilos
    ├── static/js/          # JavaScript
    └── templates/          # HTML
```

## Próximos Passos

- [ ] Adicionar músicas na pasta `~/Music`
- [ ] Configurar playlist do MPD
- [ ] Testar módulo GPS com velocidade
- [ ] Parear adaptador OBD-II
- [ ] Configurar instalação elétrica no veículo

## Link Úteis

- [Raspberry Pi OS Downloads](https://www.raspberrypi.com/software/operating-systems/)
- [MPD Documentation](https://mpd.readthedocs.io/)
- [GPSD Documentation](https://gpsd.gitlab.io/gpsd/)
- [python-obd](https://python-obd.readthedocs.io/)