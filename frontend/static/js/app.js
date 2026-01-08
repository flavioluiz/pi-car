// ============ TABS ============
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        // Remove active de todas as tabs
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));

        // Ativa a tab clicada
        tab.classList.add('active');
        document.getElementById('panel-' + tab.dataset.panel).classList.add('active');
    });
});

// ============ RELOGIO ============
function updateClock() {
    const now = new Date();
    document.getElementById('clock').textContent =
        now.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}
updateClock();
setInterval(updateClock, 1000);

// ============ FORMATAR TEMPO ============
function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return mins + ':' + secs.toString().padStart(2, '0');
}

// ============ ATUALIZAR DADOS ============
function updateData() {
    fetch('/api/status')
        .then(r => r.json())
        .then(data => {
            // Indicadores de conexao
            document.getElementById('ind-music').classList.toggle('connected', data.music.connected);
            document.getElementById('ind-gps').classList.toggle('connected', data.gps.connected);
            document.getElementById('ind-obd').classList.toggle('connected', data.obd.connected);

            // Musica
            document.getElementById('music-title').textContent = data.music.title || 'Nenhuma musica';
            document.getElementById('music-artist').textContent = data.music.artist || '-';
            document.getElementById('volume-display').textContent = data.music.volume + '%';
            document.getElementById('time-elapsed').textContent = formatTime(data.music.elapsed);
            document.getElementById('time-duration').textContent = formatTime(data.music.duration);

            const progress = data.music.duration > 0 ? (data.music.elapsed / data.music.duration * 100) : 0;
            document.getElementById('progress-fill').style.width = progress + '%';

            const btnPlay = document.getElementById('btn-play');
            const artwork = document.getElementById('music-artwork');
            if (data.music.state === 'play') {
                btnPlay.innerHTML = '&#9612;&#9612;';
                btnPlay.onclick = () => musicControl('pause');
                artwork.classList.add('playing');
            } else {
                btnPlay.innerHTML = '&#9654;';
                btnPlay.onclick = () => musicControl('play');
                artwork.classList.remove('playing');
            }

            // OBD
            if (data.obd.connected) {
                document.getElementById('obd-content').style.display = 'block';
                document.getElementById('obd-disconnected').style.display = 'none';
                document.getElementById('obd-rpm').textContent = Math.round(data.obd.rpm);
                document.getElementById('obd-speed').textContent = Math.round(data.obd.speed);
                document.getElementById('obd-temp').textContent = Math.round(data.obd.coolant_temp);
                document.getElementById('obd-throttle').textContent = Math.round(data.obd.throttle);
            } else {
                document.getElementById('obd-content').style.display = 'none';
                document.getElementById('obd-disconnected').style.display = 'block';
            }

            // GPS
            if (data.gps.connected && data.gps.lat) {
                document.getElementById('gps-content').style.display = 'block';
                document.getElementById('gps-disconnected').style.display = 'none';
                document.getElementById('gps-speed').textContent = Math.round(data.gps.speed);
                document.getElementById('gps-sats').textContent = data.gps.satellites;
                document.getElementById('gps-coords').textContent =
                    `${data.gps.lat.toFixed(6)}, ${data.gps.lon.toFixed(6)}`;
            } else {
                document.getElementById('gps-content').style.display = 'none';
                document.getElementById('gps-disconnected').style.display = 'block';
            }
        })
        .catch(err => console.error('Erro ao atualizar:', err));
}

// Atualizar a cada 1 segundo
updateData();
setInterval(updateData, 1000);

// ============ CONTROLES DE MUSICA ============
function musicControl(action) {
    fetch('/api/music/' + action)
        .then(r => r.json())
        .then(() => updateData())
        .catch(err => console.error('Erro:', err));
}

// ============ ABRIR APPS EXTERNOS ============
function openNavit() {
    fetch('/api/launch/navit').catch(() => {});
    alert('Abrindo Navit...');
}

function openGqrx() {
    fetch('/api/launch/gqrx').catch(() => {});
    alert('Abrindo GQRX...');
}
