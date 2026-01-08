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

            // Shuffle e Repeat
            document.getElementById('btn-shuffle').classList.toggle('active', data.music.random);
            document.getElementById('btn-repeat').classList.toggle('active', data.music.repeat);

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

// ============ SHUFFLE E REPEAT ============
function toggleShuffle() {
    fetch('/api/music/shuffle', { method: 'POST' })
        .then(r => r.json())
        .then(() => updateData())
        .catch(err => console.error('Erro:', err));
}

function toggleRepeat() {
    fetch('/api/music/repeat', { method: 'POST' })
        .then(r => r.json())
        .then(() => updateData())
        .catch(err => console.error('Erro:', err));
}

// ============ SUBMENU DE MUSICA ============

// Tabs do submenu de musica
document.querySelectorAll('.music-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.music-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.music-panel').forEach(p => p.classList.remove('active'));

        tab.classList.add('active');
        const panelId = 'music-' + tab.dataset.music;
        document.getElementById(panelId).classList.add('active');

        // Carregar conteudo da tab
        loadMusicContent(tab.dataset.music);
    });
});

// Carregar conteudo baseado na tab
function loadMusicContent(type) {
    switch (type) {
        case 'playing':
            // Player atualiza automaticamente
            break;
        case 'queue':
            loadQueue();
            break;
        case 'artists':
            loadArtists();
            break;
        case 'playlists':
            loadPlaylists();
            break;
        case 'search':
            // Busca e acionada pelo usuario
            break;
    }
}

// Armazena URIs da fila atual para marcar icones
let queueFiles = new Set();

// Carregar fila atual
function loadQueue() {
    fetch('/api/music/playlist')
        .then(r => r.json())
        .then(queue => {
            const list = document.getElementById('queue-list');
            if (!queue || queue.length === 0 || queue.error) {
                queueFiles.clear();
                list.innerHTML = '<div class="browser-empty"><div class="browser-empty-icon">&#9835;</div>Fila vazia</div>';
                return;
            }

            // Atualiza conjunto de arquivos na fila
            queueFiles = new Set(queue.map(s => s.file));

            list.innerHTML = `
                <div class="browser-header">
                    <span>${queue.length} musica${queue.length > 1 ? 's' : ''}</span>
                    <button class="browser-header-btn" onclick="clearQueue()">Limpar</button>
                </div>
            ` + queue.map((song, i) => `
                <div class="browser-item" onclick="playPosition(${song.pos || i})">
                    <div class="browser-item-icon">&#9835;</div>
                    <div class="browser-item-info">
                        <div class="browser-item-title">${song.title || song.file || 'Sem titulo'}</div>
                        <div class="browser-item-subtitle">${song.artist || 'Artista desconhecido'}</div>
                    </div>
                    <button class="browser-item-remove" onclick="event.stopPropagation(); removeFromQueue(${song.pos || i})">&#10005;</button>
                </div>
            `).join('');
        })
        .catch(err => console.error('Erro ao carregar fila:', err));
}

// Remover da fila
function removeFromQueue(pos) {
    fetch('/api/music/remove/' + pos, { method: 'POST' })
        .then(r => r.json())
        .then(() => loadQueue())
        .catch(err => console.error('Erro:', err));
}

// Limpar fila
function clearQueue() {
    fetch('/api/music/clear', { method: 'POST' })
        .then(r => r.json())
        .then(() => {
            queueFiles.clear();
            loadQueue();
            updateData();
        })
        .catch(err => console.error('Erro:', err));
}

// Carregar lista de artistas
function loadArtists() {
    fetch('/api/music/artists')
        .then(r => r.json())
        .then(artists => {
            const list = document.getElementById('artists-list');
            if (!artists || artists.length === 0 || artists.error) {
                list.innerHTML = '<div class="browser-empty"><div class="browser-empty-icon">&#128100;</div>Nenhum artista</div>';
                return;
            }

            list.innerHTML = artists.map(artist => `
                <div class="browser-item" onclick="loadArtistSongs('${artist.replace(/'/g, "\\'")}')">
                    <div class="browser-item-icon">&#128100;</div>
                    <div class="browser-item-info">
                        <div class="browser-item-title">${artist}</div>
                    </div>
                </div>
            `).join('');
        })
        .catch(err => console.error('Erro ao carregar artistas:', err));
}

// Carregar musicas de um artista
function loadArtistSongs(artist) {
    fetch('/api/music/artist/' + encodeURIComponent(artist))
        .then(r => r.json())
        .then(songs => {
            const list = document.getElementById('artists-list');
            if (!songs || songs.length === 0 || songs.error) {
                list.innerHTML = '<div class="browser-empty">Nenhuma musica</div>';
                return;
            }

            // Botao voltar + lista de musicas
            list.innerHTML = `
                <div class="browser-item" onclick="loadArtists()">
                    <div class="browser-item-icon">&#8592;</div>
                    <div class="browser-item-info">
                        <div class="browser-item-title">Voltar</div>
                    </div>
                </div>
            ` + songs.map(song => {
                const file = (song.file || '').replace(/'/g, "\\'");
                const inQueue = queueFiles.has(song.file);
                return `
                <div class="browser-item" data-file="${song.file || ''}">
                    <div class="browser-item-icon ${inQueue ? 'in-queue' : ''}">&#9835;</div>
                    <div class="browser-item-info">
                        <div class="browser-item-title">${song.title || song.file || 'Sem titulo'}</div>
                        <div class="browser-item-subtitle">${song.album || ''}</div>
                    </div>
                    <button class="browser-item-action play" onclick="event.stopPropagation(); playSong('${file}')">&#9654;</button>
                    <button class="browser-item-action ${inQueue ? 'added' : ''}" onclick="event.stopPropagation(); addToQueueAndMark(this, '${file}')">+</button>
                </div>
            `}).join('');
        })
        .catch(err => console.error('Erro ao carregar musicas:', err));
}

// Carregar playlists salvas
function loadPlaylists() {
    fetch('/api/music/playlists')
        .then(r => r.json())
        .then(playlists => {
            const list = document.getElementById('playlists-list');
            if (!playlists || playlists.length === 0 || playlists.error) {
                list.innerHTML = '<div class="browser-empty"><div class="browser-empty-icon">&#128195;</div>Nenhuma playlist</div>';
                return;
            }

            list.innerHTML = playlists.map(pl => `
                <div class="browser-item">
                    <div class="browser-item-icon">&#128195;</div>
                    <div class="browser-item-info">
                        <div class="browser-item-title">${pl.playlist}</div>
                    </div>
                    <button class="browser-item-action play" onclick="event.stopPropagation(); playPlaylist('${(pl.playlist || '').replace(/'/g, "\\'")}')">&#9654;</button>
                    <button class="browser-item-action" onclick="event.stopPropagation(); addPlaylistToQueue('${(pl.playlist || '').replace(/'/g, "\\'")}')">+</button>
                </div>
            `).join('');
        })
        .catch(err => console.error('Erro ao carregar playlists:', err));
}

// Tocar playlist (substitui fila)
function playPlaylist(name) {
    fetch('/api/music/playlists/' + encodeURIComponent(name) + '/play', { method: 'POST' })
        .then(r => r.json())
        .then(() => {
            document.querySelector('.music-tab[data-music="playing"]').click();
            updateData();
        })
        .catch(err => console.error('Erro:', err));
}

// Adicionar playlist a fila
function addPlaylistToQueue(name) {
    fetch('/api/music/playlists/' + encodeURIComponent(name) + '/add', { method: 'POST' })
        .then(r => r.json())
        .then(() => {
            loadQueue();
        })
        .catch(err => console.error('Erro:', err));
}

// ============ BUSCA ============
function handleSearch(event) {
    if (event.key === 'Enter') {
        doSearch();
    }
}

function doSearch() {
    const query = document.getElementById('search-input').value.trim();
    // Se vazio, busca todas as musicas
    const url = query ? '/api/music/search?q=' + encodeURIComponent(query) : '/api/music/all';

    fetch(url)
        .then(r => r.json())
        .then(results => {
            const list = document.getElementById('search-results');
            if (!results || results.length === 0 || results.error) {
                list.innerHTML = '<div class="browser-empty"><div class="browser-empty-icon">&#128269;</div>Nenhum resultado</div>';
                return;
            }

            list.innerHTML = results.map(song => {
                const file = (song.file || '').replace(/'/g, "\\'");
                const inQueue = queueFiles.has(song.file);
                return `
                <div class="browser-item" data-file="${song.file || ''}">
                    <div class="browser-item-icon ${inQueue ? 'in-queue' : ''}">&#9835;</div>
                    <div class="browser-item-info">
                        <div class="browser-item-title">${song.title || song.file || 'Sem titulo'}</div>
                        <div class="browser-item-subtitle">${song.artist || 'Artista desconhecido'}</div>
                    </div>
                    <button class="browser-item-action play" onclick="event.stopPropagation(); playSong('${file}')">&#9654;</button>
                    <button class="browser-item-action ${inQueue ? 'added' : ''}" onclick="event.stopPropagation(); addToQueueAndMark(this, '${file}')">+</button>
                </div>
            `}).join('');
        })
        .catch(err => console.error('Erro na busca:', err));
}

// Renderiza lista de musicas (usado em busca e artistas)
function renderSongList(songs, listElement) {
    listElement.innerHTML = songs.map(song => {
        const file = (song.file || '').replace(/'/g, "\\'");
        const inQueue = queueFiles.has(song.file);
        return `
            <div class="browser-item" data-file="${song.file || ''}">
                <div class="browser-item-icon ${inQueue ? 'in-queue' : ''}">&#9835;</div>
                <div class="browser-item-info">
                    <div class="browser-item-title">${song.title || song.file || 'Sem titulo'}</div>
                    <div class="browser-item-subtitle">${song.artist || song.album || 'Artista desconhecido'}</div>
                </div>
                <button class="browser-item-action play" onclick="event.stopPropagation(); playSong('${file}')">&#9654;</button>
                <button class="browser-item-action ${inQueue ? 'added' : ''}" onclick="event.stopPropagation(); addToQueueAndMark(this, '${file}')">+</button>
            </div>
        `;
    }).join('');
}

// ============ ACOES DO BROWSER ============
function playPosition(pos) {
    fetch('/api/music/play/' + pos, { method: 'POST' })
        .then(r => r.json())
        .then(() => updateData())
        .catch(err => console.error('Erro:', err));
}

function addToQueue(file) {
    fetch('/api/music/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ uri: file })
    })
        .then(r => r.json())
        .then(() => {
            queueFiles.add(file);
            if (document.getElementById('music-queue').classList.contains('active')) {
                loadQueue();
            }
        })
        .catch(err => console.error('Erro:', err));
}

// Adicionar e marcar visualmente
function addToQueueAndMark(btn, file) {
    fetch('/api/music/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ uri: file })
    })
        .then(r => r.json())
        .then(() => {
            queueFiles.add(file);
            btn.classList.add('added');
            // Marca o icone tambem
            const item = btn.closest('.browser-item');
            if (item) {
                const icon = item.querySelector('.browser-item-icon');
                if (icon) icon.classList.add('in-queue');
            }
        })
        .catch(err => console.error('Erro:', err));
}

// Tocar musica (substitui fila)
function playSong(file) {
    fetch('/api/music/play-uri', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ uri: file })
    })
        .then(r => r.json())
        .then(() => {
            queueFiles.clear();
            queueFiles.add(file);
            document.querySelector('.music-tab[data-music="playing"]').click();
            updateData();
        })
        .catch(err => console.error('Erro:', err));
}

// ============ TECLADO VIRTUAL ============
const keyboardLayout = [
    ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
    ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
    ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
    ['Z', 'X', 'C', 'V', 'B', 'N', 'M', ' ']
];

function createKeyboard() {
    const container = document.getElementById('virtual-keyboard');
    if (!container) return;

    container.innerHTML = keyboardLayout.map(row =>
        `<div class="keyboard-row">${row.map(key =>
            key === ' '
                ? `<button class="keyboard-key space" onclick="keyPress(' ')">ESPACO</button>`
                : `<button class="keyboard-key" onclick="keyPress('${key}')">${key}</button>`
        ).join('')}</div>`
    ).join('') + `
        <div class="keyboard-row">
            <button class="keyboard-key special" onclick="keyBackspace()">&#9003;</button>
            <button class="keyboard-key special" onclick="keyClear()">LIMPAR</button>
            <button class="keyboard-key special search" onclick="doSearch()">BUSCAR</button>
        </div>
    `;
}

function keyPress(key) {
    const input = document.getElementById('search-input');
    input.value += key;
    input.focus();
}

function keyBackspace() {
    const input = document.getElementById('search-input');
    input.value = input.value.slice(0, -1);
    input.focus();
}

function keyClear() {
    const input = document.getElementById('search-input');
    input.value = '';
    input.focus();
}

// Inicializar teclado
createKeyboard();

// Carregar fila inicial
loadQueue();
