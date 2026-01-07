#!/bin/bash
# Inicia a Central Multimídia Veicular
# Uso: ./start_dashboard.sh

cd "$(dirname "$0")"

echo "🚗 Central Multimídia Veicular"
echo "=============================="
echo ""

# Verificar se MPD está rodando
if ! systemctl is-active --quiet mpd; then
    echo "▶ Iniciando MPD..."
    sudo systemctl start mpd
fi

# Verificar se gpsd está rodando (ignora erro se não tiver GPS)
if ! systemctl is-active --quiet gpsd 2>/dev/null; then
    echo "📍 GPSD não está rodando (normal se não tiver GPS conectado)"
fi

echo ""
echo "🌐 Iniciando servidor web..."
echo "   Acesse: http://localhost:5000"
echo ""
echo "   Pressione Ctrl+C para encerrar"
echo ""

python3 app.py
