// ============================================================================
// SPECTROGRAM CONFIGURATION PARAMETERS
// ============================================================================
// These parameters can be adjusted dynamically via UI controls

// Update interval for spectrogram in milliseconds
// Lower = more frequent updates but more CPU/network usage
// Default: 100ms (10 updates per second)
let SPECTROGRAM_UPDATE_INTERVAL_MS = 100;

// Integration time for RTL-SDR recording in seconds
// This is how long rtl_power collects data for each FFT sweep
// Lower = faster updates but potentially noisier data
// Higher = smoother data but slower updates
// Default: 0.1 seconds
let SPECTROGRAM_INTEGRATION_TIME_S = 0.1;

// Maximum number of waterfall rows to keep in history
// More rows = longer history visible in waterfall but more memory
// Default: 100 rows
let SPECTROGRAM_MAX_ROWS = 100;

// Dynamic dB range smoothing factor (0-1)
// Lower = slower adaptation to signal level changes, more stable contrast
// Higher = faster adaptation, more responsive but may flicker
// Default: 0.1
let SPECTROGRAM_DB_SMOOTHING = 0.1;

// Extra margin in dB for dynamic range
// Adds headroom above/below detected signal levels for better visibility
// Default: 5 dB
let SPECTROGRAM_DB_MARGIN = 5;

// Minimum dB range for visibility
// Ensures at least this much range even if signals are very uniform
// Default: 10 dB
let SPECTROGRAM_MIN_RANGE = 10;

// ============================================================================

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

// Current radio playing state
let currentRadioPlaying = false;
let currentRadioVolume = 80;

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
        currentRadioPlaying = radioData.playing || false;
        currentRadioVolume = radioData.volume || 80;

        document.getElementById('radio-freq').textContent = currentRadioFreq.toFixed(1);
        document.getElementById('radio-mode').textContent = currentRadioMode;
        document.getElementById('freq-input').value = currentRadioFreq.toFixed(1);

        // Update mode selector buttons
        document.getElementById('mode-fm').classList.toggle('active', currentRadioMode === 'FM');
        document.getElementById('mode-am').classList.toggle('active', currentRadioMode === 'AM');

        // Update play button
        const playBtn = document.getElementById('radio-play-btn');
        const playIcon = document.getElementById('radio-play-icon');
        if (currentRadioPlaying) {
            playBtn.classList.add('playing');
            playIcon.innerHTML = '&#9632;'; // Stop symbol
        } else {
            playBtn.classList.remove('playing');
            playIcon.innerHTML = '&#9654;'; // Play symbol
        }

        // Update volume display
        document.getElementById('radio-vol').textContent = currentRadioVolume + '%';

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

// Toggle play/stop
function radioTogglePlay() {
    const endpoint = currentRadioPlaying ? '/api/radio/stop' : '/api/radio/play';
    fetch(endpoint, { method: 'POST' })
        .then(r => r.json())
        .then(result => {
            if (result.success) {
                currentRadioPlaying = result.playing;
                const playBtn = document.getElementById('radio-play-btn');
                const playIcon = document.getElementById('radio-play-icon');
                if (currentRadioPlaying) {
                    playBtn.classList.add('playing');
                    playIcon.innerHTML = '&#9632;';
                } else {
                    playBtn.classList.remove('playing');
                    playIcon.innerHTML = '&#9654;';
                }
            }
        })
        .catch(err => console.error('Radio play error:', err));
}

// Volume up
function radioVolumeUp() {
    fetch('/api/radio/volume/up', { method: 'POST' })
        .then(r => r.json())
        .then(result => {
            if (result.success) {
                currentRadioVolume = result.volume;
                document.getElementById('radio-vol').textContent = currentRadioVolume + '%';
            }
        })
        .catch(err => console.error('Volume error:', err));
}

// Volume down
function radioVolumeDown() {
    fetch('/api/radio/volume/down', { method: 'POST' })
        .then(r => r.json())
        .then(result => {
            if (result.success) {
                currentRadioVolume = result.volume;
                document.getElementById('radio-vol').textContent = currentRadioVolume + '%';
            }
        })
        .catch(err => console.error('Volume error:', err));
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

// ============ SPECTROGRAM (WATERFALL) ============

let spectrogramCanvas = null;
let spectrogramCtx = null;
let spectrogramInterval = null;
let spectrumModeActive = false;
let spectrumSpan = 2.0; // MHz

// Dynamic dB range tracking for better contrast
let waterfallMinDb = -80;  // Will be dynamically adjusted based on signal levels
let waterfallMaxDb = -30;  // Will be dynamically adjusted based on signal levels

// Waterfall history buffer - stores previous FFT rows for scrolling display
let waterfallHistory = [];

// Color map for waterfall (converts dB value to RGB color)
// Based on typical SDR color schemes: dark blue (weak) -> cyan -> green -> yellow -> red (strong)
function dbToColor(db) {
    // Use dynamic range for normalization
    const range = waterfallMaxDb - waterfallMinDb;
    const normalized = range > 0 
        ? Math.max(0, Math.min(1, (db - waterfallMinDb) / range))
        : 0.5;
    
    // Color gradient: dark blue -> blue -> cyan -> green -> yellow -> red
    let r, g, b;
    if (normalized < 0.2) {
        // Dark blue to blue
        const t = normalized / 0.2;
        r = 0;
        g = 0;
        b = Math.floor(50 + t * 155);
    } else if (normalized < 0.4) {
        // Blue to cyan
        const t = (normalized - 0.2) / 0.2;
        r = 0;
        g = Math.floor(t * 255);
        b = 255;
    } else if (normalized < 0.6) {
        // Cyan to green
        const t = (normalized - 0.4) / 0.2;
        r = 0;
        g = 255;
        b = Math.floor(255 * (1 - t));
    } else if (normalized < 0.8) {
        // Green to yellow
        const t = (normalized - 0.6) / 0.2;
        r = Math.floor(t * 255);
        g = 255;
        b = 0;
    } else {
        // Yellow to red
        const t = (normalized - 0.8) / 0.2;
        r = 255;
        g = Math.floor(255 * (1 - t));
        b = 0;
    }
    
    return `rgb(${r}, ${g}, ${b})`;
}

function startSpectrogram() {
    spectrogramCanvas = document.getElementById('spectrogram');
    if (!spectrogramCanvas) return;

    spectrogramCtx = spectrogramCanvas.getContext('2d');

    // Set canvas size
    spectrogramCanvas.width = spectrogramCanvas.offsetWidth;
    spectrogramCanvas.height = spectrogramCanvas.offsetHeight;

    // DO NOT clear waterfall history when starting - keep existing data
    // This allows resuming where we left off
    
    // Reset dynamic dB range only if history is empty
    if (waterfallHistory.length === 0) {
        waterfallMinDb = -80;
        waterfallMaxDb = -30;
    }

    // Initialize center frequency input with current frequency
    const centerInput = document.getElementById('spectrum-center-input');
    if (centerInput) {
        centerInput.value = currentRadioFreq.toFixed(1);
    }

    // Update frequency labels to match current tuner frequency
    updateSpectrumFrequencyLabels();

    // Clear canvas with dark background only if no history
    if (waterfallHistory.length === 0) {
        spectrogramCtx.fillStyle = '#0a0a0f';
        spectrogramCtx.fillRect(0, 0, spectrogramCanvas.width, spectrogramCanvas.height);
    }

    // Clear any existing interval
    if (spectrogramInterval) {
        clearInterval(spectrogramInterval);
    }

    // Start spectrum mode on server (pauses audio)
    fetch('/api/radio/spectrum/start', { method: 'POST' })
        .then(r => r.json())
        .then(result => {
            spectrumModeActive = result.spectrum_mode || false;
            updateSpectrumIndicator();
            // Start fetching FFT data
            spectrogramInterval = setInterval(updateSpectrogram, SPECTROGRAM_UPDATE_INTERVAL_MS);
        })
        .catch(() => {
            // If spectrum mode fails, still start the interval but show waiting message
            spectrumModeActive = false;
            updateSpectrumIndicator();
            spectrogramInterval = setInterval(updateSpectrogram, SPECTROGRAM_UPDATE_INTERVAL_MS);
        });
}

function stopSpectrogram() {
    if (spectrogramInterval) {
        clearInterval(spectrogramInterval);
        spectrogramInterval = null;
    }

    // Stop spectrum mode on server (resumes audio)
    if (spectrumModeActive) {
        fetch('/api/radio/spectrum/stop', { method: 'POST' })
            .then(r => r.json())
            .then(() => {
                spectrumModeActive = false;
                updateSpectrumIndicator();
            })
            .catch(() => {});
    }
}

function updateSpectrumIndicator() {
    const indicator = document.getElementById('spectrum-mode-indicator');
    if (indicator) {
        indicator.textContent = spectrumModeActive ? 'LIVE' : 'WAITING';
        indicator.classList.toggle('live', spectrumModeActive);
    }
}

// Update spectrum frequency labels based on current tuner frequency and span
function updateSpectrumFrequencyLabels() {
    const center = currentRadioFreq;
    const startLabel = document.getElementById('spectrum-start');
    const endLabel = document.getElementById('spectrum-end');
    const centerLabel = document.getElementById('spectrum-center');
    
    if (startLabel) startLabel.textContent = (center - spectrumSpan / 2).toFixed(1);
    if (endLabel) endLabel.textContent = (center + spectrumSpan / 2).toFixed(1);
    if (centerLabel) centerLabel.textContent = center.toFixed(1);
}

function updateSpectrogram() {
    if (!spectrogramCtx) return;

    const center = currentRadioFreq;
    fetch(`/api/radio/fft?center=${center}&span=${spectrumSpan}&integration_time=${SPECTROGRAM_INTEGRATION_TIME_S}`)
        .then(r => r.json())
        .then(data => {
            // Update indicator based on real data availability
            const indicator = document.getElementById('spectrum-mode-indicator');
            
            if (data.error || !data.fft) {
                // No data available - show waiting state
                if (indicator) {
                    indicator.textContent = 'WAITING';
                    indicator.classList.remove('live');
                }
                return;
            }

            // We have real data
            if (indicator) {
                indicator.textContent = 'LIVE';
                indicator.classList.add('live');
            }

            // Update frequency labels
            if (data.start_freq !== undefined && data.end_freq !== undefined) {
                const startLabel = document.getElementById('spectrum-start');
                const endLabel = document.getElementById('spectrum-end');
                const centerLabel = document.getElementById('spectrum-center');
                if (startLabel) startLabel.textContent = data.start_freq.toFixed(1);
                if (endLabel) endLabel.textContent = data.end_freq.toFixed(1);
                if (centerLabel) centerLabel.textContent = center.toFixed(1);
            }

            drawWaterfall(data.fft);
        })
        .catch(() => {
            // On error, show waiting state
            const indicator = document.getElementById('spectrum-mode-indicator');
            if (indicator) {
                indicator.textContent = 'WAITING';
                indicator.classList.remove('live');
            }
        });
}

function setSpectrumSpan(span) {
    spectrumSpan = span;
    
    // Update span display if element exists
    const spanDisplay = document.getElementById('spectrum-span');
    if (spanDisplay) {
        spanDisplay.textContent = span.toFixed(1);
    }

    // Update active button state
    document.querySelectorAll('.span-btn').forEach(btn => {
        btn.classList.toggle('active', parseFloat(btn.textContent) === span);
    });

    // Update frequency range labels using helper function
    updateSpectrumFrequencyLabels();

    // DO NOT clear waterfall history - let it continue accumulating
    // This allows users to see the change over time
}

// Apply new center frequency for spectrum
function applySpectrumCenterFreq() {
    const input = document.getElementById('spectrum-center-input');
    const freq = parseFloat(input.value);
    
    if (!isNaN(freq) && freq >= 24 && freq <= 1800) {
        currentRadioFreq = freq;
        updateSpectrumFrequencyLabels();
        // Update the tuner display as well
        document.getElementById('radio-freq').textContent = freq.toFixed(1);
        document.getElementById('freq-input').value = freq.toFixed(1);
        // DO NOT clear history - continue with new frequency
    } else {
        alert('Invalid frequency. Must be between 24 and 1800 MHz.');
    }
}

// Apply new update interval
function applySpectrumUpdateInterval() {
    const select = document.getElementById('spectrum-update-interval');
    SPECTROGRAM_UPDATE_INTERVAL_MS = parseInt(select.value);
    
    // Restart spectrogram with new interval if active
    if (spectrogramInterval) {
        clearInterval(spectrogramInterval);
        spectrogramInterval = setInterval(updateSpectrogram, SPECTROGRAM_UPDATE_INTERVAL_MS);
    }
}

// Apply new integration time
function applySpectrumIntegrationTime() {
    const select = document.getElementById('spectrum-integration-time');
    SPECTROGRAM_INTEGRATION_TIME_S = parseFloat(select.value);
    // Will be used in next FFT request
}

// Apply new max rows
function applySpectrumMaxRows() {
    const select = document.getElementById('spectrum-max-rows');
    SPECTROGRAM_MAX_ROWS = parseInt(select.value);
    
    // Trim history if it exceeds new max
    if (waterfallHistory.length > SPECTROGRAM_MAX_ROWS) {
        waterfallHistory = waterfallHistory.slice(waterfallHistory.length - SPECTROGRAM_MAX_ROWS);
    }
}

// Apply new DB smoothing
function applySpectrumDbSmoothing() {
    const select = document.getElementById('spectrum-db-smoothing');
    SPECTROGRAM_DB_SMOOTHING = parseFloat(select.value);
}

// Apply new DB margin
function applySpectrumDbMargin() {
    const select = document.getElementById('spectrum-db-margin');
    SPECTROGRAM_DB_MARGIN = parseFloat(select.value);
}

// Apply new MIN range
function applySpectrumMinRange() {
    const select = document.getElementById('spectrum-min-range');
    SPECTROGRAM_MIN_RANGE = parseFloat(select.value);
}

function drawWaterfall(fftData) {
    const width = spectrogramCanvas.width;
    const height = spectrogramCanvas.height;
    const bins = fftData.length;

    // Calculate min/max of current FFT data for dynamic range adjustment
    let currentMin = Infinity;
    let currentMax = -Infinity;
    for (let i = 0; i < fftData.length; i++) {
        if (fftData[i] < currentMin) currentMin = fftData[i];
        if (fftData[i] > currentMax) currentMax = fftData[i];
    }
    
    // Smoothly adapt the dynamic range to the actual signal levels
    if (isFinite(currentMin) && isFinite(currentMax)) {
        // Apply margin for better contrast
        const targetMin = currentMin - SPECTROGRAM_DB_MARGIN;
        const targetMax = currentMax + SPECTROGRAM_DB_MARGIN;
        
        waterfallMinDb = waterfallMinDb + (targetMin - waterfallMinDb) * SPECTROGRAM_DB_SMOOTHING;
        waterfallMaxDb = waterfallMaxDb + (targetMax - waterfallMaxDb) * SPECTROGRAM_DB_SMOOTHING;
        
        // Ensure minimum range for visibility
        if (waterfallMaxDb - waterfallMinDb < SPECTROGRAM_MIN_RANGE) {
            const mid = (waterfallMaxDb + waterfallMinDb) / 2;
            waterfallMinDb = mid - SPECTROGRAM_MIN_RANGE / 2;
            waterfallMaxDb = mid + SPECTROGRAM_MIN_RANGE / 2;
        }
    }

    // Add new FFT row to history
    waterfallHistory.push(fftData.slice()); // Make a copy
    
    // Limit history size
    if (waterfallHistory.length > SPECTROGRAM_MAX_ROWS) {
        waterfallHistory.shift(); // Remove oldest row
    }

    // Clear canvas
    spectrogramCtx.fillStyle = '#0a0a0f';
    spectrogramCtx.fillRect(0, 0, width, height);

    // Calculate row height based on available height and history
    const rowHeight = Math.max(2, height / SPECTROGRAM_MAX_ROWS);
    const pixelWidth = width / bins;

    // Draw waterfall - newest data at bottom, oldest at top
    for (let row = 0; row < waterfallHistory.length; row++) {
        const fftRow = waterfallHistory[row];
        // Calculate y position - newest row (last in array) should be at bottom
        const y = height - (waterfallHistory.length - row) * rowHeight;
        
        for (let bin = 0; bin < fftRow.length; bin++) {
            const x = bin * pixelWidth;
            const db = fftRow[bin];
            spectrogramCtx.fillStyle = dbToColor(db);
            spectrogramCtx.fillRect(x, y, Math.ceil(pixelWidth), Math.ceil(rowHeight));
        }
    }

    // Draw center frequency marker (thin vertical line)
    spectrogramCtx.strokeStyle = 'rgba(255, 107, 53, 0.5)';
    spectrogramCtx.lineWidth = 1;
    spectrogramCtx.beginPath();
    spectrogramCtx.moveTo(width / 2, 0);
    spectrogramCtx.lineTo(width / 2, height);
    spectrogramCtx.stroke();

    // Draw frequency grid lines (vertical)
    spectrogramCtx.strokeStyle = 'rgba(100, 100, 120, 0.3)';
    spectrogramCtx.lineWidth = 1;
    for (let i = 1; i < 4; i++) {
        const x = (width / 4) * i;
        spectrogramCtx.beginPath();
        spectrogramCtx.moveTo(x, 0);
        spectrogramCtx.lineTo(x, height);
        spectrogramCtx.stroke();
    }
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
