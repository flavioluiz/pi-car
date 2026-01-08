#!/bin/bash
#===============================================================================
#
#   Pi-Car - Atualizar Biblioteca de Músicas
#
#   Uso: ./update_music.sh
#
#   Este script atualiza o banco de dados do MPD e adiciona todas as músicas
#   da pasta ~/Music à playlist.
#
#===============================================================================

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "========================================"
echo "  Pi-Car - Atualizar Biblioteca"
echo "========================================"
echo -e "${NC}"

# Verificar se MPD está rodando
if ! systemctl is-active --quiet mpd; then
    echo -e "${YELLOW}[WARN]${NC} MPD não está rodando. Iniciando..."
    sudo systemctl start mpd
    sleep 2
fi

# Contar músicas na pasta
MUSIC_DIR="$HOME/Music"
if [ -d "$MUSIC_DIR" ]; then
    MUSIC_COUNT=$(find "$MUSIC_DIR" -type f \( -iname "*.mp3" -o -iname "*.flac" -o -iname "*.ogg" -o -iname "*.wav" -o -iname "*.m4a" -o -iname "*.wma" \) 2>/dev/null | wc -l)
    echo -e "${GREEN}[INFO]${NC} Encontrados $MUSIC_COUNT arquivos de música em $MUSIC_DIR"
else
    echo -e "${YELLOW}[WARN]${NC} Pasta $MUSIC_DIR não encontrada. Criando..."
    mkdir -p "$MUSIC_DIR"
    MUSIC_COUNT=0
fi

if [ "$MUSIC_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}[WARN]${NC} Nenhuma música encontrada em $MUSIC_DIR"
    echo ""
    echo "Copie suas músicas para $MUSIC_DIR e execute este script novamente."
    echo ""
    exit 0
fi

# Atualizar banco de dados do MPD
echo -e "${GREEN}[INFO]${NC} Atualizando banco de dados do MPD..."
mpc update --wait

# Limpar playlist atual
echo -e "${GREEN}[INFO]${NC} Limpando playlist atual..."
mpc clear

# Adicionar todas as músicas
echo -e "${GREEN}[INFO]${NC} Adicionando músicas à playlist..."
mpc add /

# Mostrar estatísticas
PLAYLIST_COUNT=$(mpc playlist | wc -l)
echo ""
echo -e "${GREEN}========================================"
echo -e "  Biblioteca atualizada!"
echo -e "  $PLAYLIST_COUNT músicas na playlist"
echo -e "========================================${NC}"
echo ""
echo "Comandos úteis:"
echo "  mpc play      - Tocar"
echo "  mpc pause     - Pausar"
echo "  mpc next      - Próxima"
echo "  mpc prev      - Anterior"
echo "  mpc volume 80 - Volume 80%"
echo ""
