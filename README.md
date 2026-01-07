# 🚗 Pi-Car

**Central Multimídia Veicular DIY com Raspberry Pi**

Sistema de infotainment para veículos antigos usando Raspberry Pi 4 com interface web touchscreen. Integra player de música, navegação GPS offline, diagnóstico OBD-II e rádio SDR.

![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)
![Versão](https://img.shields.io/badge/versão-0.1.0-blue)
![Licença](https://img.shields.io/badge/licença-MIT-green)

---

## ✨ Funcionalidades

| Módulo | Descrição | Status |
|--------|-----------|--------|
| 🎵 **Música** | Player MPD com controle total (play, pause, volume, playlist) | ✅ Funcionando |
| 📍 **GPS** | Velocidade, satélites, coordenadas + integração Navit | ✅ Pronto |
| 🚗 **OBD-II** | RPM, velocidade, temperatura, posição do acelerador | ✅ Pronto |
| 📻 **Rádio SDR** | Receptor RTL-SDR para FM, aviação, amador | ⏳ Em desenvolvimento |

---

## 🖼️ Screenshots

*Em breve*

---

## 🛠️ Hardware Necessário

### Essencial
- Raspberry Pi 4 (2GB+ RAM)
- Monitor touchscreen (HDMI)
- Cartão microSD (16GB+)
- Fonte de alimentação 5V 3A

### Módulos opcionais
| Componente | Modelo sugerido | Preço estimado (BR) |
|------------|-----------------|---------------------|
| GPS USB | VK-162 (u-blox 7) | R$50-100 |
| OBD-II | ELM327 Bluetooth | R$30-80 |
| Rádio SDR | RTL-SDR V3 | R$80-150 |

### Para instalação veicular
| Componente | Descrição | Preço estimado (BR) |
|------------|-----------|---------------------|
| Conversor DC-DC | 12V → 5V 3A+ USB | R$25-50 |
| Fusível inline | 5A com porta-fusível | R$15-25 |
| Add-a-fuse | Para tap na caixa de fusíveis | R$15-20 |

---

## 📦 Instalação

### 1. Sistema Base

Instale o Raspberry Pi OS Lite (64-bit) e configure:

```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar interface gráfica mínima
sudo apt install -y xorg openbox lxterminal pcmanfm

# Instalar dependências de áudio e música
sudo apt install -y mpd mpc alsa-utils

# Instalar GPS e navegação
sudo apt install -y gpsd gpsd-clients navit

# Instalar navegador
sudo apt install -y chromium

# Instalar dependências Python
pip3 install flask python-mpd2 gps3 obd --break-system-packages
```

### 2. Configurar MPD

Edite `/etc/mpd.conf`:

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

Iniciar MPD:

```bash
mkdir -p ~/.mpd/playlists
touch ~/.mpd/database
sudo systemctl enable mpd
sudo systemctl start mpd
```

### 3. Clonar e Executar

```bash
# Clonar repositório
git clone https://github.com/SEU_USUARIO/pi-car.git
cd pi-car

# Dar permissão de execução
chmod +x start_dashboard.sh

# Executar
./start_dashboard.sh
```

Acesse: **http://localhost:5000**

### 4. Modo Kiosk (Tela Cheia)

```bash
chromium --kiosk --noerrdialogs --disable-infobars --no-first-run http://localhost:5000
```

Sair: `Alt+F4` ou `Ctrl+W`

---

## 🚀 Autostart

Para iniciar automaticamente com o X:

```bash
mkdir -p ~/.config/openbox
nano ~/.config/openbox/autostart
```

Adicione:

```bash
# Desativar screensaver
xset s off
xset -dpms
xset s noblank

# Iniciar dashboard
/home/SEU_USUARIO/pi-car/start_dashboard.sh &

# Aguardar servidor
sleep 3

# Chromium em modo kiosk
chromium --kiosk --noerrdialogs --disable-infobars --no-first-run http://localhost:5000 &
```

Para iniciar X automaticamente no boot, adicione ao `~/.bash_profile`:

```bash
[[ -z $DISPLAY && $XDG_VTNR -eq 1 ]] && startx
```

---

## 🔌 Instalação Elétrica no Veículo

```
┌─────────────────┐
│   Caixa de      │
│   Fusíveis      │
│                 │
│  ┌───────────┐  │      ┌─────────────┐      ┌─────────────┐
│  │ ACC Fuse  │──┼──────│ Fusível 5A  │──────│ Conv DC-DC  │──── 5V USB ──→ RPi
│  │ (add-a-   │  │      │  (inline)   │      │  12V → 5V   │
│  │  fuse)    │  │      └─────────────┘      └──────┬──────┘
│  └───────────┘  │                                  │
│                 │                                  │
└─────────────────┘                             GND ─┴─→ Chassis
```

**Importante:** Use a linha ACC para que o sistema só ligue com a ignição.

---

## 📁 Estrutura do Projeto

```
pi-car/
├── app.py                  # Servidor Flask + interface web
├── start_dashboard.sh      # Script de inicialização
├── car-dashboard.desktop   # Arquivo .desktop para autostart
├── README.md
├── LICENSE
└── docs/
    ├── INSTALL.md          # Guia detalhado de instalação
    ├── HARDWARE.md         # Lista de hardware e conexões
    └── WIRING.md           # Diagramas elétricos
```

---

## 🔧 Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    Chromium (Kiosk Mode)                    │
│                    http://localhost:5000                    │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                     Flask Server (:5000)                    │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   MPD API   │  │   GPS API   │  │      OBD API        │  │
│  │  (música)   │  │  (posição)  │  │   (diagnóstico)     │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
└─────────┼────────────────┼────────────────────┼─────────────┘
          │                │                    │
          ▼                ▼                    ▼
    ┌───────────┐    ┌───────────┐      ┌─────────────┐
    │    MPD    │    │   gpsd    │      │  python-obd │
    │  (:6600)  │    │  (:2947)  │      │             │
    └───────────┘    └─────┬─────┘      └──────┬──────┘
                           │                   │
                     ┌─────▼─────┐       ┌─────▼─────┐
                     │  GPS USB  │       │  ELM327   │
                     │  VK-162   │       │ Bluetooth │
                     └───────────┘       └───────────┘
```

---

## 🎯 Roadmap

### v0.1 (atual)
- [x] Interface web básica
- [x] Controle de música (MPD)
- [x] Integração GPS (gpsd)
- [x] Integração OBD-II
- [x] Modo kiosk

### v0.2
- [ ] Biblioteca de músicas navegável
- [ ] Gerenciamento de playlists
- [ ] Mapas offline (Navit embedded)
- [ ] Integração RTL-SDR

### v0.3
- [ ] Temas (claro/escuro/auto)
- [ ] Configurações pela interface
- [ ] Histórico de viagens
- [ ] Códigos de erro OBD com descrição

### v1.0
- [ ] Backup de configurações
- [ ] Atualizações OTA
- [ ] Documentação completa
- [ ] Imagem pronta para download

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

---

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

## 🙏 Agradecimentos

- [MPD](https://www.musicpd.org/) - Music Player Daemon
- [Navit](https://www.navit-project.org/) - Navegação open source
- [python-obd](https://python-obd.readthedocs.io/) - Biblioteca OBD-II
- [RTL-SDR](https://www.rtl-sdr.com/) - Software Defined Radio

---

## 📬 Contato

Flavio

Link do projeto: [https://github.com/flavioluiz/pi-car](https://github.com/flavioluiz/pi-car)
