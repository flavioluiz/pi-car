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

**Instalação automatizada disponível!**

### Método Rápido (Recomendado)

**Pré-requisito:** Raspberry Pi OS **Lite** (64-bit) instalado e configurado com acesso à internet.

```bash
# Instalar git (não vem instalado no OS Lite)
sudo apt update && sudo apt install -y git

# Clonar repositório
git clone https://github.com/flavioluiz/pi-car.git
cd pi-car

# Dar permissão de execução e executar
chmod +x install.sh
./install.sh

# Reiniciar
sudo reboot
```

O script de instalação irá:
- Atualizar o sistema (apt update/upgrade)
- Instalar interface gráfica mínima (X11 + Openbox)
- Instalar MPD, GPSD, Navit, Chromium
- Instalar RTL-SDR e ferramentas de rádio
- Configurar Bluetooth para OBD-II
- Instalar dependências Python (Flask, python-mpd2, gps3, obd)
- Configurar autostart do servidor Flask e Chromium em modo kiosk

Após o reinício, o sistema iniciará automaticamente com o dashboard Pi-Car em tela cheia.

📖 **Detalhes completos**: Veja [INSTALACAO.md](INSTALACAO.md) para instruções detalhadas.

### Instalação Manual

Se preferir instalar cada componente manualmente, consulte o guia [INSTALACAO.md](INSTALACAO.md).

### Executar Manualmente (sem autostart)

```bash
cd ~/pi-car
./start_dashboard.sh
```

Acesse: **http://localhost:5000**

### Modo Kiosk (Tela Cheia)

```bash
chromium --kiosk --noerrdialogs --disable-infobars --no-first-run http://localhost:5000
```

Sair: `Alt+F4` ou `Ctrl+W`

---

## 🚀 Autostart

O script de instalação configura o autostart automaticamente. Se precisar configurar manualmente:

### Configurar autostart do Openbox

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
~/pi-car/start_dashboard.sh &

# Aguardar servidor
sleep 4

# Chromium em modo kiosk
chromium --kiosk --noerrdialogs --disable-infobars --no-first-run --disable-session-crashed-bubble --disable-restore-session-state http://localhost:5000 &
```

### Configurar .xinitrc

```bash
echo "exec openbox-session" > ~/.xinitrc
```

### Auto-login no X

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
├── app.py                      # Entry point - servidor Flask
├── config.py                   # Configuracoes centralizadas
├── start_dashboard.sh          # Script de inicializacao
├── update_music.sh             # Script para atualizar biblioteca de musicas
├── install.sh                  # Script de instalacao automatizada
├── README.md                   # Este arquivo
├── INSTALACAO.md               # Guia detalhado de instalacao
│
├── backend/                    # Logica do servidor
│   ├── __init__.py
│   ├── routes/                 # Endpoints da API (Flask Blueprints)
│   │   ├── __init__.py
│   │   ├── music.py            # /api/music/* - controle MPD
│   │   ├── gps.py              # /api/gps/* - dados GPS
│   │   ├── vehicle.py          # /api/vehicle/* - dados OBD-II
│   │   └── system.py           # /api/status, /api/launch/*
│   │
│   └── services/               # Servicos de integracao
│       ├── __init__.py
│       ├── mpd_service.py      # Conexao e controle MPD
│       ├── gps_service.py      # Thread de monitoramento GPS
│       └── obd_service.py      # Thread de monitoramento OBD-II
│
└── frontend/                   # Interface web
    ├── static/
    │   ├── css/
    │   │   └── style.css       # Estilos da interface
    │   └── js/
    │       └── app.js          # Logica JavaScript
    │
    └── templates/
        └── index.html          # Pagina principal
```

---

## 🔧 Arquitetura

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
│  ┌─────────────────── backend/routes/ ─────────────────┐   │
│  │  music.py      gps.py      vehicle.py    system.py  │   │
│  │  /api/music/*  /api/gps/*  /api/vehicle/* /api/*    │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         │                                   │
│  ┌─────────────────── backend/services/ ───────────────┐   │
│  │  mpd_service.py   gps_service.py   obd_service.py   │   │
│  └──────┬─────────────────┬─────────────────┬──────────┘   │
└─────────┼─────────────────┼─────────────────┼──────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
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
