// ============ TABS ============
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        // Remove active from all tabs
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));

        // Activate clicked tab
        tab.classList.add('active');
        document.getElementById('panel-' + tab.dataset.panel).classList.add('active');
    });
});

// ============ CLOCK ============
function updateClock() {
    const now = new Date();
    document.getElementById('clock').textContent =
        now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
}
updateClock();
setInterval(updateClock, 1000);

// ============ FORMAT TIME ============
function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return mins + ':' + secs.toString().padStart(2, '0');
}

// ============ UPDATE DATA ============
let currentDuration = 0; // Store duration for seek

function updateData() {
    fetch('/api/status')
        .then(r => r.json())
        .then(data => {
            // Connection indicators
            document.getElementById('ind-music').classList.toggle('connected', data.music.connected);
            document.getElementById('ind-gps').classList.toggle('connected', data.gps.connected);
            document.getElementById('ind-obd').classList.toggle('connected', data.obd.connected);

            // Music
            document.getElementById('music-title').textContent = data.music.title || 'No music';
            document.getElementById('music-artist').textContent = data.music.artist || '-';
            document.getElementById('volume-display').textContent = data.music.volume + '%';
            document.getElementById('time-elapsed').textContent = formatTime(data.music.elapsed);
            document.getElementById('time-duration').textContent = formatTime(data.music.duration);

            // Store duration for seek
            currentDuration = data.music.duration || 0;

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

            // Shuffle and Repeat
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
        .catch(err => console.error('Error updating:', err));
}

// Update every 1 second
updateData();
setInterval(updateData, 1000);

// ============ MUSIC CONTROLS ============
function musicControl(action) {
    fetch('/api/music/' + action)
        .then(r => r.json())
        .then(() => updateData())
        .catch(err => console.error('Error:', err));
}

// Seek to clicked position on progress bar
function seekToPosition(event) {
    if (currentDuration <= 0) return;

    const bar = document.getElementById('progress-bar');
    const rect = bar.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const percentage = clickX / rect.width;
    const position = percentage * currentDuration;

    fetch('/api/music/seek', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ position: position })
    })
        .then(r => r.json())
        .then(() => updateData())
        .catch(err => console.error('Error:', err));
}

// Restart current song
function restartSong() {
    fetch('/api/music/restart', { method: 'POST' })
        .then(r => r.json())
        .then(() => updateData())
        .catch(err => console.error('Error:', err));
}

// ============ OPEN EXTERNAL APPS ============
function openNavit() {
    fetch('/api/launch/navit').catch(() => {});
    alert('Opening Navit...');
}

function openGqrx() {
    fetch('/api/launch/gqrx').catch(() => {});
    alert('Opening GQRX...');
}

// ============ SHUFFLE AND REPEAT ============
function toggleShuffle() {
    fetch('/api/music/shuffle', { method: 'POST' })
        .then(r => r.json())
        .then(() => updateData())
        .catch(err => console.error('Error:', err));
}

function toggleRepeat() {
    fetch('/api/music/repeat', { method: 'POST' })
        .then(r => r.json())
        .then(() => updateData())
        .catch(err => console.error('Error:', err));
}

// ============ MUSIC SUBMENU ============

// Music submenu tabs
document.querySelectorAll('.music-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.music-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.music-panel').forEach(p => p.classList.remove('active'));

        tab.classList.add('active');
        const panelId = 'music-' + tab.dataset.music;
        document.getElementById(panelId).classList.add('active');

        // Load tab content
        loadMusicContent(tab.dataset.music);
    });
});

// Load content based on tab
function loadMusicContent(type) {
    switch (type) {
        case 'playing':
            // Player updates automatically
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
            // Search is triggered by user
            break;
    }
}

// Store queue URIs to mark icons
let queueFiles = new Set();

// Load current queue
function loadQueue() {
    fetch('/api/music/playlist')
        .then(r => r.json())
        .then(queue => {
            const list = document.getElementById('queue-list');
            if (!queue || queue.length === 0 || queue.error) {
                queueFiles.clear();
                list.innerHTML = '<div class="browser-empty"><div class="browser-empty-icon">&#9835;</div>Queue empty</div>';
                return;
            }

            // Update queue files set
            queueFiles = new Set(queue.map(s => s.file));

            list.innerHTML = `
                <div class="browser-header">
                    <span>${queue.length} song${queue.length > 1 ? 's' : ''}</span>
                    <button class="browser-header-btn" onclick="clearQueue()">Clear</button>
                </div>
            ` + queue.map((song, i) => `
                <div class="browser-item" onclick="playPosition(${song.pos || i})">
                    <div class="browser-item-icon">&#9835;</div>
                    <div class="browser-item-info">
                        <div class="browser-item-title">${song.title || song.file || 'Untitled'}</div>
                        <div class="browser-item-subtitle">${song.artist || 'Unknown artist'}</div>
                    </div>
                    <button class="browser-item-remove" onclick="event.stopPropagation(); removeFromQueue(${song.pos || i})">&#10005;</button>
                </div>
            `).join('');
        })
        .catch(err => console.error('Error loading queue:', err));
}

// Remove from queue
function removeFromQueue(pos) {
    fetch('/api/music/remove/' + pos, { method: 'POST' })
        .then(r => r.json())
        .then(() => loadQueue())
        .catch(err => console.error('Error:', err));
}

// Clear queue
function clearQueue() {
    fetch('/api/music/clear', { method: 'POST' })
        .then(r => r.json())
        .then(() => {
            queueFiles.clear();
            loadQueue();
            updateData();
        })
        .catch(err => console.error('Error:', err));
}

// Load artists list
function loadArtists() {
    fetch('/api/music/artists')
        .then(r => r.json())
        .then(artists => {
            const list = document.getElementById('artists-list');
            if (!artists || artists.length === 0 || artists.error) {
                list.innerHTML = '<div class="browser-empty"><div class="browser-empty-icon">&#128100;</div>No artists</div>';
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
        .catch(err => console.error('Error loading artists:', err));
}

// Load songs by artist
function loadArtistSongs(artist) {
    fetch('/api/music/artist/' + encodeURIComponent(artist))
        .then(r => r.json())
        .then(songs => {
            const list = document.getElementById('artists-list');
            if (!songs || songs.length === 0 || songs.error) {
                list.innerHTML = '<div class="browser-empty">No songs</div>';
                return;
            }

            // Back button + song list
            list.innerHTML = `
                <div class="browser-item" onclick="loadArtists()">
                    <div class="browser-item-icon">&#8592;</div>
                    <div class="browser-item-info">
                        <div class="browser-item-title">Back</div>
                    </div>
                </div>
            ` + songs.map(song => {
                const file = (song.file || '').replace(/'/g, "\\'");
                const inQueue = queueFiles.has(song.file);
                return `
                <div class="browser-item" data-file="${song.file || ''}">
                    <div class="browser-item-icon ${inQueue ? 'in-queue' : ''}">&#9835;</div>
                    <div class="browser-item-info">
                        <div class="browser-item-title">${song.title || song.file || 'Untitled'}</div>
                        <div class="browser-item-subtitle">${song.album || ''}</div>
                    </div>
                    <button class="browser-item-action play" onclick="event.stopPropagation(); playSong('${file}')">&#9654;</button>
                    <button class="browser-item-action ${inQueue ? 'added' : ''}" onclick="event.stopPropagation(); addToQueueAndMark(this, '${file}')">+</button>
                </div>
            `}).join('');
        })
        .catch(err => console.error('Error loading songs:', err));
}

// Load saved playlists
function loadPlaylists() {
    fetch('/api/music/playlists')
        .then(r => r.json())
        .then(playlists => {
            const list = document.getElementById('playlists-list');
            if (!playlists || playlists.length === 0 || playlists.error) {
                list.innerHTML = '<div class="browser-empty"><div class="browser-empty-icon">&#128195;</div>No playlists</div>';
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
        .catch(err => console.error('Error loading playlists:', err));
}

// Play playlist (replaces queue)
function playPlaylist(name) {
    fetch('/api/music/playlists/' + encodeURIComponent(name) + '/play', { method: 'POST' })
        .then(r => r.json())
        .then(() => {
            document.querySelector('.music-tab[data-music="playing"]').click();
            updateData();
        })
        .catch(err => console.error('Error:', err));
}

// Add playlist to queue
function addPlaylistToQueue(name) {
    fetch('/api/music/playlists/' + encodeURIComponent(name) + '/add', { method: 'POST' })
        .then(r => r.json())
        .then(() => {
            loadQueue();
        })
        .catch(err => console.error('Error:', err));
}

// ============ SEARCH ============
function handleSearch(event) {
    if (event.key === 'Enter') {
        doSearch();
    }
}

function doSearch() {
    const query = document.getElementById('search-input').value.trim();
    // If empty, search all songs
    const url = query ? '/api/music/search?q=' + encodeURIComponent(query) : '/api/music/all';

    fetch(url)
        .then(r => r.json())
        .then(results => {
            const list = document.getElementById('search-results');
            if (!results || results.length === 0 || results.error) {
                list.innerHTML = '<div class="browser-empty"><div class="browser-empty-icon">&#128269;</div>No results</div>';
                return;
            }

            list.innerHTML = results.map(song => {
                const file = (song.file || '').replace(/'/g, "\\'");
                const inQueue = queueFiles.has(song.file);
                return `
                <div class="browser-item" data-file="${song.file || ''}">
                    <div class="browser-item-icon ${inQueue ? 'in-queue' : ''}">&#9835;</div>
                    <div class="browser-item-info">
                        <div class="browser-item-title">${song.title || song.file || 'Untitled'}</div>
                        <div class="browser-item-subtitle">${song.artist || 'Unknown artist'}</div>
                    </div>
                    <button class="browser-item-action play" onclick="event.stopPropagation(); playSong('${file}')">&#9654;</button>
                    <button class="browser-item-action ${inQueue ? 'added' : ''}" onclick="event.stopPropagation(); addToQueueAndMark(this, '${file}')">+</button>
                </div>
            `}).join('');
        })
        .catch(err => console.error('Search error:', err));
}

// Render song list (used in search and artists)
function renderSongList(songs, listElement) {
    listElement.innerHTML = songs.map(song => {
        const file = (song.file || '').replace(/'/g, "\\'");
        const inQueue = queueFiles.has(song.file);
        return `
            <div class="browser-item" data-file="${song.file || ''}">
                <div class="browser-item-icon ${inQueue ? 'in-queue' : ''}">&#9835;</div>
                <div class="browser-item-info">
                    <div class="browser-item-title">${song.title || song.file || 'Untitled'}</div>
                    <div class="browser-item-subtitle">${song.artist || song.album || 'Unknown artist'}</div>
                </div>
                <button class="browser-item-action play" onclick="event.stopPropagation(); playSong('${file}')">&#9654;</button>
                <button class="browser-item-action ${inQueue ? 'added' : ''}" onclick="event.stopPropagation(); addToQueueAndMark(this, '${file}')">+</button>
            </div>
        `;
    }).join('');
}

// ============ BROWSER ACTIONS ============
function playPosition(pos) {
    fetch('/api/music/play/' + pos, { method: 'POST' })
        .then(r => r.json())
        .then(() => updateData())
        .catch(err => console.error('Error:', err));
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
        .catch(err => console.error('Error:', err));
}

// Add and mark visually
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
            // Mark the icon too
            const item = btn.closest('.browser-item');
            if (item) {
                const icon = item.querySelector('.browser-item-icon');
                if (icon) icon.classList.add('in-queue');
            }
        })
        .catch(err => console.error('Error:', err));
}

// Play song (replaces queue)
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
        .catch(err => console.error('Error:', err));
}

// ============ VIRTUAL KEYBOARD ============
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
                ? `<button class="keyboard-key space" onclick="keyPress(' ')">SPACE</button>`
                : `<button class="keyboard-key" onclick="keyPress('${key}')">${key}</button>`
        ).join('')}</div>`
    ).join('') + `
        <div class="keyboard-row">
            <button class="keyboard-key special" onclick="keyBackspace()">&#9003;</button>
            <button class="keyboard-key special" onclick="keyClear()">CLEAR</button>
            <button class="keyboard-key special search" onclick="doSearch()">SEARCH</button>
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

// Initialize keyboard
createKeyboard();

// Load initial queue
loadQueue();

// ============ RADIO SDR ============

// Current radio state
let currentRadioFreq = 99.5;
let currentRadioMode = 'FM';

// Radio tab navigation
document.querySelectorAll('.radio-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.radio-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.radio-panel').forEach(p => p.classList.remove('active'));

        tab.classList.add('active');
        const panelId = 'radio-' + tab.dataset.radio;
        document.getElementById(panelId).classList.add('active');

        // Load content when switching tabs
        if (tab.dataset.radio === 'presets') {
            loadRadioPresets();
        } else if (tab.dataset.radio === 'favorites') {
            loadRadioFavorites();
        } else if (tab.dataset.radio === 'spectrum') {
            startSpectrogram();
        }
    });
});

// Update radio display from status data
function updateRadioDisplay(radioData) {
    if (!radioData) return;

    // Update connection indicator
    document.getElementById('ind-radio').classList.toggle('connected', radioData.connected);

    // Show/hide connected content
    if (radioData.connected) {
        document.getElementById('radio-content').style.display = 'block';
        document.getElementById('radio-disconnected').style.display = 'none';

        // Update display
        currentRadioFreq = radioData.frequency || 99.5;
        currentRadioMode = radioData.mode || 'FM';

        document.getElementById('radio-freq').textContent = currentRadioFreq.toFixed(1);
        document.getElementById('radio-mode').textContent = currentRadioMode;
        document.getElementById('freq-input').value = currentRadioFreq.toFixed(1);

        // Update mode selector buttons
        document.getElementById('mode-fm').classList.toggle('active', currentRadioMode === 'FM');
        document.getElementById('mode-am').classList.toggle('active', currentRadioMode === 'AM');

        // Update signal strength
        updateSignalStrength(radioData.signal_strength || -100);

        // Update spectrum info
        document.getElementById('spectrum-center').textContent = currentRadioFreq.toFixed(1);
        document.getElementById('spectrum-span').textContent = (radioData.sample_rate || 2.4).toFixed(1);
    } else {
        document.getElementById('radio-content').style.display = 'none';
        document.getElementById('radio-disconnected').style.display = 'block';
    }
}

// Update signal strength bars
function updateSignalStrength(dbm) {
    const bars = document.querySelectorAll('.signal-bar');
    document.getElementById('signal-dbm').textContent = dbm.toFixed(0) + ' dBm';

    // Map dBm to number of bars (rough approximation)
    // -100 dBm = 0 bars, -30 dBm = 5 bars
    const normalized = Math.max(0, Math.min(5, Math.floor((dbm + 100) / 14)));

    bars.forEach((bar, i) => {
        bar.classList.toggle('active', i < normalized);
    });
}

// Tune to frequency with step
function radioTuneStep(step) {
    const newFreq = currentRadioFreq + step;
    radioTune(newFreq, currentRadioMode);
}

// Tune from manual input
function radioTuneManual() {
    const freq = parseFloat(document.getElementById('freq-input').value);
    if (!isNaN(freq) && freq >= 24 && freq <= 1800) {
        radioTune(freq, currentRadioMode);
    }
}

// Tune to specific frequency and mode
function radioTune(freq, mode) {
    fetch('/api/radio/tune', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ frequency: freq, mode: mode })
    })
        .then(r => r.json())
        .then(result => {
            if (result.success) {
                currentRadioFreq = result.frequency;
                document.getElementById('radio-freq').textContent = currentRadioFreq.toFixed(1);
                document.getElementById('freq-input').value = currentRadioFreq.toFixed(1);
            }
        })
        .catch(err => console.error('Radio tune error:', err));
}

// Set radio mode (FM/AM)
function radioSetMode(mode) {
    fetch('/api/radio/mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: mode })
    })
        .then(r => r.json())
        .then(result => {
            if (result.success) {
                currentRadioMode = mode;
                document.getElementById('radio-mode').textContent = mode;
                document.getElementById('mode-fm').classList.toggle('active', mode === 'FM');
                document.getElementById('mode-am').classList.toggle('active', mode === 'AM');
            }
        })
        .catch(err => console.error('Radio mode error:', err));
}

// Load presets from server
function loadRadioPresets() {
    fetch('/api/radio/presets')
        .then(r => r.json())
        .then(data => {
            // FM Presets
            const fmList = document.getElementById('fm-presets');
            if (data.fm && data.fm.length > 0) {
                fmList.innerHTML = data.fm.map(p => `
                    <div class="preset-item" onclick="radioTune(${p.freq}, '${p.mode}')">
                        <div class="freq">${p.freq.toFixed(1)}</div>
                        <div class="label">${p.label}</div>
                        <div class="mode-badge">${p.mode}</div>
                    </div>
                `).join('');
            }

            // Airport Presets - SBSJ
            if (data.airports && data.airports.SBSJ) {
                const sbsjList = document.getElementById('airport-presets-sbsj');
                sbsjList.innerHTML = data.airports.SBSJ.frequencies.map(p => `
                    <div class="preset-item" onclick="radioTune(${p.freq}, '${p.mode}')">
                        <div class="freq">${p.freq.toFixed(3)}</div>
                        <div class="label">${p.label}</div>
                        <div class="mode-badge">${p.mode}</div>
                    </div>
                `).join('');
            }

            // Airport Presets - SBGR
            if (data.airports && data.airports.SBGR) {
                const sbgrList = document.getElementById('airport-presets-sbgr');
                sbgrList.innerHTML = data.airports.SBGR.frequencies.map(p => `
                    <div class="preset-item" onclick="radioTune(${p.freq}, '${p.mode}')">
                        <div class="freq">${p.freq.toFixed(3)}</div>
                        <div class="label">${p.label}</div>
                        <div class="mode-badge">${p.mode}</div>
                    </div>
                `).join('');
            }
        })
        .catch(err => console.error('Error loading presets:', err));
}

// Load favorites
function loadRadioFavorites() {
    fetch('/api/radio/favorites')
        .then(r => r.json())
        .then(data => {
            const list = document.getElementById('favorites-list');
            if (!data.favorites || data.favorites.length === 0) {
                list.innerHTML = '<div class="empty-message">No favorites yet. Tune to a frequency and tap "+ FAV"</div>';
                return;
            }

            list.innerHTML = data.favorites.map((fav, i) => `
                <div class="favorite-item" onclick="radioTune(${fav.freq}, '${fav.mode}')">
                    <div class="favorite-info">
                        <span class="favorite-freq">${fav.freq.toFixed(3)}</span>
                        <span class="favorite-name">${fav.name || ''}</span>
                        <span class="favorite-mode">${fav.mode}</span>
                    </div>
                    <button class="favorite-remove" onclick="event.stopPropagation(); radioRemoveFavorite(${i})">&#10005;</button>
                </div>
            `).join('');
        })
        .catch(err => console.error('Error loading favorites:', err));
}

// Add current frequency to favorites
function radioAddFavorite() {
    const name = prompt('Name for this favorite (optional):') || '';

    fetch('/api/radio/favorites', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            freq: currentRadioFreq,
            mode: currentRadioMode,
            name: name
        })
    })
        .then(r => r.json())
        .then(result => {
            if (result.success) {
                alert('Added to favorites!');
            } else if (result.error) {
                alert(result.error);
            }
        })
        .catch(err => console.error('Error adding favorite:', err));
}

// Remove favorite
function radioRemoveFavorite(index) {
    fetch('/api/radio/favorites/' + index, { method: 'DELETE' })
        .then(r => r.json())
        .then(() => loadRadioFavorites())
        .catch(err => console.error('Error removing favorite:', err));
}

// Clear all favorites
function radioClearFavorites() {
    if (confirm('Remove all favorites?')) {
        fetch('/api/radio/favorites/clear', { method: 'POST' })
            .then(r => r.json())
            .then(() => loadRadioFavorites())
            .catch(err => console.error('Error clearing favorites:', err));
    }
}

// ============ SPECTROGRAM ============

let spectrogramCanvas = null;
let spectrogramCtx = null;
let spectrogramInterval = null;

function startSpectrogram() {
    spectrogramCanvas = document.getElementById('spectrogram');
    if (!spectrogramCanvas) return;

    spectrogramCtx = spectrogramCanvas.getContext('2d');

    // Set canvas size
    spectrogramCanvas.width = spectrogramCanvas.offsetWidth;
    spectrogramCanvas.height = spectrogramCanvas.offsetHeight;

    // Clear any existing interval
    if (spectrogramInterval) {
        clearInterval(spectrogramInterval);
    }

    // Start fetching FFT data
    spectrogramInterval = setInterval(updateSpectrogram, 100);
}

function stopSpectrogram() {
    if (spectrogramInterval) {
        clearInterval(spectrogramInterval);
        spectrogramInterval = null;
    }
}

function updateSpectrogram() {
    if (!spectrogramCtx) return;

    fetch('/api/radio/fft')
        .then(r => r.json())
        .then(data => {
            if (data.error || !data.fft) return;

            drawSpectrogram(data.fft);
        })
        .catch(() => {});
}

function drawSpectrogram(fftData) {
    const width = spectrogramCanvas.width;
    const height = spectrogramCanvas.height;
    const bins = fftData.length;

    // Clear canvas
    spectrogramCtx.fillStyle = '#0a0a0f';
    spectrogramCtx.fillRect(0, 0, width, height);

    // Draw grid lines
    spectrogramCtx.strokeStyle = '#2a2a3a';
    spectrogramCtx.lineWidth = 1;

    // Horizontal grid lines
    for (let i = 0; i < 5; i++) {
        const y = (height / 5) * i;
        spectrogramCtx.beginPath();
        spectrogramCtx.moveTo(0, y);
        spectrogramCtx.lineTo(width, y);
        spectrogramCtx.stroke();
    }

    // Draw FFT data
    const barWidth = width / bins;
    const gradient = spectrogramCtx.createLinearGradient(0, height, 0, 0);
    gradient.addColorStop(0, '#00ff88');
    gradient.addColorStop(0.5, '#00f5ff');
    gradient.addColorStop(1, '#ff6b35');

    spectrogramCtx.fillStyle = gradient;
    spectrogramCtx.beginPath();
    spectrogramCtx.moveTo(0, height);

    for (let i = 0; i < bins; i++) {
        // Normalize FFT value (typically -100 to 0 dB)
        const normalized = Math.max(0, Math.min(1, (fftData[i] + 100) / 80));
        const barHeight = normalized * height;
        const x = i * barWidth;

        spectrogramCtx.lineTo(x, height - barHeight);
    }

    spectrogramCtx.lineTo(width, height);
    spectrogramCtx.closePath();
    spectrogramCtx.fill();

    // Draw center line
    spectrogramCtx.strokeStyle = '#ff6b35';
    spectrogramCtx.lineWidth = 2;
    spectrogramCtx.beginPath();
    spectrogramCtx.moveTo(width / 2, 0);
    spectrogramCtx.lineTo(width / 2, height);
    spectrogramCtx.stroke();
}

// Stop spectrogram when leaving spectrum tab
document.querySelectorAll('.radio-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        if (tab.dataset.radio !== 'spectrum') {
            stopSpectrogram();
        }
    });
});

// ============ INTEGRATE RADIO INTO UPDATE LOOP ============

// Modify updateData to include radio
const originalUpdateData = updateData;
updateData = function() {
    fetch('/api/status')
        .then(r => r.json())
        .then(data => {
            // Connection indicators
            document.getElementById('ind-music').classList.toggle('connected', data.music.connected);
            document.getElementById('ind-gps').classList.toggle('connected', data.gps.connected);
            document.getElementById('ind-obd').classList.toggle('connected', data.obd.connected);

            // Radio indicator and display
            if (data.radio) {
                updateRadioDisplay(data.radio);
            }

            // Music
            document.getElementById('music-title').textContent = data.music.title || 'No music';
            document.getElementById('music-artist').textContent = data.music.artist || '-';
            document.getElementById('volume-display').textContent = data.music.volume + '%';
            document.getElementById('time-elapsed').textContent = formatTime(data.music.elapsed);
            document.getElementById('time-duration').textContent = formatTime(data.music.duration);

            // Store duration for seek
            currentDuration = data.music.duration || 0;

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

            // Shuffle and Repeat
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
        .catch(err => console.error('Error updating:', err));
};

// Load presets on page load if radio panel exists
if (document.getElementById('fm-presets')) {
    loadRadioPresets();
}
