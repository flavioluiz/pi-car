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

// Frequency range constants
const FREQ_MIN_MHZ = 24;
const FREQ_MAX_MHZ = 1800;

// ============ TABS ============
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));

        tab.classList.add('active');
        document.getElementById('panel-' + tab.dataset.panel).classList.add('active');

        const appShell = document.querySelector('.app-shell');
        if (appShell) {
            appShell.classList.toggle('page-home-active', tab.dataset.panel === 'home');
        }
    });
});

// ============ VEHICLE SUBTABS ============
document.querySelectorAll('.vehicle-tabs .subtab').forEach(subtab => {
    subtab.addEventListener('click', () => {
        document.querySelectorAll('.vehicle-tabs .subtab').forEach(s => s.classList.remove('active'));
        document.querySelectorAll('#panel-vehicle .subpage').forEach(p => p.classList.remove('active'));
        subtab.classList.add('active');
        const target = document.getElementById(subtab.dataset.subtab);
        if (target) target.classList.add('active');
        hideVehicleHelp();
    });
});

document.querySelectorAll('.settings-tabs .subtab').forEach(subtab => {
    subtab.addEventListener('click', () => {
        document.querySelectorAll('.settings-tabs .subtab').forEach(s => s.classList.remove('active'));
        document.querySelectorAll('#panel-settings .settings-panel').forEach(p => p.classList.remove('active'));
        subtab.classList.add('active');
        const target = document.getElementById(subtab.dataset.subtab);
        if (target) target.classList.add('active');
        if (subtab.dataset.subtab === 'settings-wifi') {
            fetchWifiSettings(true);
        }
    });
});

// ============ THEMES ============
const themeButtons = document.querySelectorAll('.theme-card[data-theme]');
const themePreviewName = document.getElementById('theme-preview-name');
const themePreviewCopy = document.getElementById('theme-preview-copy');
const themeDescriptions = {
    'picasso-red': 'Default cockpit',
    'signal-cyan': 'Cooler telemetry look',
    'amber-dusk': 'Warmer night panel'
};
let mediaSyncStatus = null;
let mediaSyncPoller = null;
let maintenanceStatus = null;
let maintenancePoller = null;
let obdLoggerStatus = null;
let restartReconnectPoller = null;
let restartReconnectStartedAt = null;
let powerActionInFlight = false;
let wifiSettingsStatus = null;
let wifiSettingsNetworks = [];
let wifiConnectBusy = false;
let wifiSelectedNetwork = null;
let wifiPasswordKeyboardMode = 'lower';
let wifiPasswordVisible = false;

function applyTheme(themeName, label) {
    document.body.dataset.theme = themeName;
    themeButtons.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.theme === themeName);
    });
    const resolvedLabel = label || document.querySelector(`[data-theme="${themeName}"]`)?.dataset.themeLabel || themeName;
    if (themePreviewName) themePreviewName.textContent = resolvedLabel;
    if (themePreviewCopy) themePreviewCopy.textContent = themeDescriptions[themeName] || '';
    localStorage.setItem('picasso-compat-theme', themeName);
}

themeButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        applyTheme(btn.dataset.theme, btn.dataset.themeLabel);
    });
});

applyTheme(localStorage.getItem('picasso-compat-theme') || 'picasso-red');

// ============ MEDIA SYNC ============
function formatSyncDate(value) {
    if (!value) return 'Never';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
}

function updateMediaSyncStatus(status) {
    mediaSyncStatus = status;

    const state = document.getElementById('media-sync-state');
    const lastSuccess = document.getElementById('media-sync-last-success');
    const musicDir = document.getElementById('media-sync-music-dir');
    const playlistDir = document.getElementById('media-sync-playlist-dir');
    const summary = document.getElementById('media-sync-summary');
    const output = document.getElementById('media-sync-output');
    const button = document.getElementById('media-sync-button');
    if (!state || !lastSuccess || !musicDir || !playlistDir || !summary || !output || !button) return;

    state.textContent = status.running
        ? 'Running'
        : status.configured === false
            ? 'Not configured'
            : status.last_error
                ? 'Error'
                : 'Idle';
    lastSuccess.textContent = formatSyncDate(status.last_success_at);
    musicDir.textContent = status.music_local_dir || '~/Music';
    playlistDir.textContent = status.playlist_local_dir || '~/.mpd/playlists';
    summary.textContent = status.configured === false
        ? (status.preflight_error || 'Media sync is not configured.')
        : (status.last_summary || 'No sync information available.');
    output.textContent = status.last_output || 'No sync logs yet.';
    button.disabled = Boolean(status.running) || status.configured === false;
    button.textContent = status.running ? 'Syncing...' : 'Sync now';
}

function fetchMediaSyncStatus() {
    fetch('/api/media/sync')
        .then(r => r.json())
        .then(updateMediaSyncStatus)
        .catch(err => console.error('Error loading media sync status:', err));
}

function requestMediaSync(force = true, reason = 'manual') {
    fetch('/api/media/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force, reason })
    })
        .then(r => r.json())
        .then(status => {
            updateMediaSyncStatus(status);
            if (status.accepted) {
                loadedMusicTabs.delete('artists');
                loadedMusicTabs.delete('playlists');
            }
        })
        .catch(err => console.error('Error starting media sync:', err));
}

function maybeAutoSyncMedia(reason = 'browser-online') {
    if (!navigator.onLine) return;
    if (mediaSyncStatus && mediaSyncStatus.configured === false) return;
    fetch('/api/media/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force: false, reason })
    })
        .then(r => r.json())
        .then(updateMediaSyncStatus)
        .catch(err => console.error('Error auto-syncing media:', err));
}

function updateOBDLoggerStatus(status) {
    obdLoggerStatus = status;

    const enabled = document.getElementById('obd-logger-enabled');
    const state = document.getElementById('obd-logger-state');
    const session = document.getElementById('obd-logger-session');
    const file = document.getElementById('obd-logger-file');
    const localDir = document.getElementById('obd-logger-local-dir');
    const lastSuccess = document.getElementById('obd-logger-last-success');
    const summary = document.getElementById('obd-logger-summary');
    const output = document.getElementById('obd-logger-output');
    const toggleButton = document.getElementById('obd-logger-toggle-button');
    const syncButton = document.getElementById('obd-logger-sync-button');
    if (!enabled || !state || !session || !file || !localDir || !lastSuccess || !summary || !output || !toggleButton || !syncButton) return;

    enabled.textContent = status.enabled ? 'Yes' : 'No';
    state.textContent = !status.enabled
        ? 'Disabled'
        : status.sync_running
            ? 'Syncing'
            : status.running
                ? 'Active'
                : status.last_sync_error
                    ? 'Error'
                    : 'Idle';
    session.textContent = status.current_session_id || 'None';
    file.textContent = status.last_file || '--';
    localDir.textContent = status.local_dir || 'telemetry/obd';
    lastSuccess.textContent = formatSyncDate(status.last_sync_success_at);
    summary.textContent = status.enabled
        ? (status.last_sync_summary || 'No logger information available.')
        : 'Logger disabled. No OBD snapshots will be written or synced.';
    output.textContent = status.last_sync_output || 'No logger logs yet.';
    toggleButton.textContent = status.enabled ? 'Disable logger' : 'Enable logger';
    syncButton.disabled = !status.enabled || Boolean(status.sync_running) || status.configured === false;
    syncButton.textContent = status.sync_running ? 'Syncing...' : 'Sync now';
}

function fetchOBDLoggerStatus() {
    fetch('/api/obd/logger')
        .then(r => r.json())
        .then(updateOBDLoggerStatus)
        .catch(err => console.error('Error loading OBD logger status:', err));
}

function requestOBDLoggerSync(force = true, reason = 'manual') {
    fetch('/api/obd/logger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force, reason })
    })
        .then(r => r.json())
        .then(updateOBDLoggerStatus)
        .catch(err => console.error('Error starting OBD logger sync:', err));
}

function toggleOBDLogger() {
    const nextEnabled = !(obdLoggerStatus && obdLoggerStatus.enabled);
    fetch('/api/obd/logger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: nextEnabled })
    })
        .then(r => r.json())
        .then(updateOBDLoggerStatus)
        .catch(err => console.error('Error updating OBD logger setting:', err));
}

function updateMaintenanceStatus(status) {
    maintenanceStatus = status;

    const version = document.getElementById('maintenance-version');
    const repoVersion = document.getElementById('maintenance-repo-version');
    const state = document.getElementById('maintenance-state');
    const lastSuccess = document.getElementById('maintenance-last-success');
    const branch = document.getElementById('maintenance-branch');
    const head = document.getElementById('maintenance-head');
    const summary = document.getElementById('maintenance-summary');
    const output = document.getElementById('maintenance-output');
    const updateButton = document.getElementById('maintenance-update-button');
    const restartButton = document.getElementById('maintenance-restart-button');
    if (!version || !repoVersion || !state || !lastSuccess || !branch || !head || !summary || !output || !updateButton || !restartButton) return;

    version.textContent = status.version || '--';
    repoVersion.textContent = status.repo_version || '--';
    state.textContent = status.running
        ? `Running: ${status.last_action || 'action'}`
        : status.last_error
                ? 'Error'
                : 'Idle';
    lastSuccess.textContent = formatSyncDate(status.last_success_at);
    branch.textContent = status.branch || '--';
    head.textContent = status.head || '--';
    summary.textContent = status.last_summary || 'No maintenance action has run yet.';
    output.textContent = status.last_output || 'No maintenance logs yet.';

    updateButton.disabled = Boolean(status.running) || status.git_available === false;
    restartButton.disabled = Boolean(status.running);
    updateButton.textContent = status.running && status.last_action === 'update' ? 'Updating...' : 'Update now';
    restartButton.textContent = status.running && status.last_action === 'restart' ? 'Restarting...' : 'Restart app';
}

function startRestartReconnect() {
    if (restartReconnectPoller !== null) return;

    restartReconnectStartedAt = Date.now();
    const state = document.getElementById('maintenance-state');
    const summary = document.getElementById('maintenance-summary');
    const output = document.getElementById('maintenance-output');
    const updateButton = document.getElementById('maintenance-update-button');
    const restartButton = document.getElementById('maintenance-restart-button');

    if (state) state.textContent = 'Restarting...';
    if (summary) summary.textContent = 'Waiting for the server to come back online.';
    if (output) output.textContent = 'Restart requested. Reconnecting to the backend and reloading this page automatically.';
    if (updateButton) updateButton.disabled = true;
    if (restartButton) {
        restartButton.disabled = true;
        restartButton.textContent = 'Restarting...';
    }

    const checkServer = () => {
        fetch('/api/status', { cache: 'no-store' })
            .then(response => {
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                window.location.reload();
            })
            .catch(() => {
                const elapsedSeconds = Math.floor((Date.now() - restartReconnectStartedAt) / 1000);
                if (summary && elapsedSeconds >= 15) {
                    summary.textContent = `Still waiting for the server to return (${elapsedSeconds}s).`;
                }
            });
    };

    restartReconnectPoller = setInterval(checkServer, 1000);
    window.setTimeout(checkServer, 700);
}

function fetchMaintenanceStatus() {
    fetch('/api/system/maintenance')
        .then(r => r.json())
        .then(updateMaintenanceStatus)
        .catch(err => {
            if (restartReconnectPoller === null) {
                console.error('Error loading maintenance status:', err);
            }
        });
}

function requestMaintenanceAction(action, extra = {}) {
    fetch('/api/system/maintenance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, ...extra })
    })
        .then(r => r.json())
        .then(status => {
            updateMaintenanceStatus(status);
            if (action === 'restart' && status.accepted) {
                startRestartReconnect();
            }
            if ((action === 'shutdown' || action === 'reboot') && status.accepted) {
                setPowerModalBusy(action);
            } else if (action === 'shutdown' || action === 'reboot') {
                setPowerModalError(status.message || 'Power action was not accepted.');
            }
        })
        .catch(err => {
            if (action === 'shutdown' || action === 'reboot') {
                setPowerModalError('Failed to contact the backend.');
            }
            console.error('Error starting maintenance action:', err);
        });
}

function openPowerModal() {
    const modal = document.getElementById('power-modal');
    if (!modal) return;
    powerActionInFlight = false;
    setPowerModalText('Choose an action for the Raspberry Pi.');
    setPowerModalButtonsDisabled(false);
    modal.classList.remove('hidden');
}

function closePowerModal() {
    if (powerActionInFlight) return;
    const modal = document.getElementById('power-modal');
    if (!modal) return;
    modal.classList.add('hidden');
}

function powerModalOverlayClick(event) {
    if (event.target === document.getElementById('power-modal')) {
        closePowerModal();
    }
}

function setPowerModalText(message) {
    const status = document.getElementById('power-modal-status');
    if (status) status.textContent = message;
}

function setPowerModalButtonsDisabled(disabled) {
    ['power-shutdown-button', 'power-reboot-button', 'power-cancel-button'].forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        if (id === 'power-cancel-button' && powerActionInFlight) {
            el.disabled = true;
            return;
        }
        el.disabled = disabled;
    });
}

function setPowerModalBusy(action) {
    powerActionInFlight = true;
    setPowerModalButtonsDisabled(true);
    setPowerModalText(
        action === 'shutdown'
            ? 'Shutdown requested. The Raspberry Pi is powering off.'
            : 'Reset requested. The Raspberry Pi is rebooting.'
    );
}

function setPowerModalError(message) {
    powerActionInFlight = false;
    setPowerModalButtonsDisabled(false);
    setPowerModalText(message);
}

function confirmPowerAction(action) {
    if (powerActionInFlight) return;
    setPowerModalText(action === 'shutdown' ? 'Requesting full shutdown...' : 'Requesting system reset...');
    requestMaintenanceAction(action);
}

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

// ============ OBD DYNAMIC GAUGES ============

// Priority order for displaying metrics (most important first)
const OBD_PRIORITY = [
    'RPM', 'SPEED', 'COOLANT_TEMP', 'THROTTLE_POS',
    'ENGINE_LOAD', 'INTAKE_PRESSURE', 'INTAKE_TEMP',
    'TIMING_ADVANCE', 'SHORT_FUEL_TRIM_1', 'LONG_FUEL_TRIM_1',
    'ELM_VOLTAGE', 'FUEL_RATE_GASOLINE_E27', 'FUEL_RATE_ETHANOL',
    'INSTANT_KM_L', 'TRIP_AVERAGE_KM_L'
];

// CSS class for different gauge types (for styling)
const OBD_GAUGE_CLASS = {
    'RPM': 'rpm',
    'SPEED': 'speed',
    'COOLANT_TEMP': 'temp',
    'THROTTLE_POS': 'throttle',
    'ENGINE_LOAD': 'load',
    'FUEL_LEVEL': 'fuel',
    'OIL_TEMP': 'temp',
    'ELM_VOLTAGE': 'voltage',
    'FUEL_RATE_GASOLINE_E27': 'fuel',
    'FUEL_RATE_ETHANOL': 'fuel',
    'INSTANT_KM_L': 'fuel',
    'TRIP_AVERAGE_KM_L': 'fuel'
};

const OBD_TECHNICAL_KEYS = [
    'INTAKE_PRESSURE', 'INTAKE_TEMP', 'ENGINE_LOAD', 'THROTTLE_POS',
    'TIMING_ADVANCE', 'SHORT_FUEL_TRIM_1', 'LONG_FUEL_TRIM_1',
    'FUEL_RATE_GASOLINE_E27', 'FUEL_RATE_ETHANOL'
];

function formatOBDValue(value, digits = 0) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return '--';
    return Number(value).toFixed(digits);
}

function setText(id, text) {
    const element = document.getElementById(id);
    if (element) element.textContent = text;
}

let vehicleHelpTimer = null;

function showVehicleHelp(title, body) {
    const overlay = document.getElementById('vehicle-help-overlay');
    const titleEl = document.getElementById('vehicle-help-title');
    const bodyEl = document.getElementById('vehicle-help-body');
    if (!overlay || !titleEl || !bodyEl) return;
    titleEl.textContent = title || 'Vehicle data';
    bodyEl.textContent = body || '';
    overlay.hidden = false;
    overlay.classList.add('visible');
    clearTimeout(vehicleHelpTimer);
    vehicleHelpTimer = setTimeout(hideVehicleHelp, 5000);
}

function hideVehicleHelp() {
    const overlay = document.getElementById('vehicle-help-overlay');
    if (!overlay) return;
    overlay.hidden = true;
    overlay.classList.remove('visible');
    clearTimeout(vehicleHelpTimer);
    vehicleHelpTimer = null;
}

function initVehicleHelp() {
    const panel = document.getElementById('panel-vehicle');
    const overlay = document.getElementById('vehicle-help-overlay');
    if (!panel || !overlay) return;

    panel.addEventListener('click', event => {
        const trigger = event.target.closest('[data-help]');
        if (trigger && panel.contains(trigger)) {
            event.stopPropagation();
            showVehicleHelp(trigger.dataset.helpTitle, trigger.dataset.help);
            return;
        }

        if (!event.target.closest('.vehicle-help-card')) {
            hideVehicleHelp();
        }
    });

    document.addEventListener('click', event => {
        if (!overlay.hidden && !event.target.closest('#panel-vehicle')) {
            hideVehicleHelp();
        }
    });
}

function setWifiIndicator(state = 'disconnected') {
    const dot = document.getElementById('ind-wifi');
    if (!dot) return;

    dot.classList.remove('connected', 'disconnected');
    dot.classList.add(state === 'connected' ? 'connected' : 'disconnected');
}

function updateWifiStatus(wifiData) {
    if (!wifiData) {
        setWifiIndicator('disconnected');
        return;
    }

    if (wifiData.connected) {
        setWifiIndicator('connected');
        return;
    }

    setWifiIndicator('disconnected');
}

const wifiPasswordLayouts = {
    lower: [
        ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
        ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
        ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'],
        ['⇧', 'z', 'x', 'c', 'v', 'b', 'n', 'm', '⌫'],
        ['123', '@', '.', '-', '_', ' ', 'Connect']
    ],
    upper: [
        ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
        ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
        ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
        ['⇩', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', '⌫'],
        ['123', '@', '.', '-', '_', ' ', 'Connect']
    ],
    symbols: [
        ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')'],
        ['[', ']', '{', '}', '/', '\\', '|', ':', ';', '"'],
        ['+', '=', '?', ',', '.', '-', '_', '~', '`'],
        ['ABC', '<', '>', "'", '€', '£', '§', '°', '⌫'],
        ['abc', ' ', 'Connect']
    ],
};

function fetchWifiSettings(force = false) {
    const scanButton = document.getElementById('wifi-scan-button');
    if (scanButton) {
        scanButton.disabled = true;
        scanButton.textContent = 'Refreshing...';
    }

    fetch(`/api/wifi${force ? '?force=1' : ''}`)
        .then(r => r.json())
        .then(updateWifiSettings)
        .catch(err => {
            console.error('Error loading Wi-Fi settings:', err);
            updateWifiSettings({
                status: { connected: false, state: 'error', ssid: '', interface: '', last_checked_at: null },
                networks: [],
                message: 'Failed to load Wi-Fi information.',
            });
        })
        .finally(() => {
            if (scanButton) {
                scanButton.disabled = false;
                scanButton.textContent = 'Refresh';
            }
        });
}

function updateWifiSettings(payload) {
    wifiSettingsStatus = payload?.status || null;
    wifiSettingsNetworks = payload?.networks || [];

    setText(
        'wifi-settings-state',
        wifiSettingsStatus
            ? (wifiSettingsStatus.connected ? 'Connected' : wifiSettingsStatus.state || 'Disconnected')
            : 'Unavailable'
    );
    setText('wifi-settings-ssid', wifiSettingsStatus?.ssid || '--');
    setText('wifi-settings-interface', wifiSettingsStatus?.interface || '--');
    setText('wifi-settings-last-scan', formatSyncDate(wifiSettingsStatus?.last_checked_at));
    setText(
        'wifi-settings-summary',
        payload?.message
            || (wifiSettingsStatus?.connected
                ? `Connected to ${wifiSettingsStatus.ssid || 'Wi-Fi network'}.`
                : 'Select a network below to connect.')
    );

    renderWifiNetworks(wifiSettingsNetworks);
}

function renderWifiNetworks(networks) {
    const list = document.getElementById('wifi-network-list');
    if (!list) return;
    if (!networks.length) {
        list.innerHTML = '<div class="empty-message">No Wi-Fi networks found.</div>';
        return;
    }

    list.innerHTML = networks.map(network => {
        const label = network.connected ? 'Connected' : 'Connect';
        const actionClass = network.connected ? 'wifi-network-action connected' : 'wifi-network-action sync-button';
        const safety = network.requires_password ? 'Secured' : 'Open';
        const subtitle = `${safety} · ${network.signal ?? 0}% signal`;
        return `
            <div class="wifi-network-item ${network.connected ? 'connected' : ''}">
                <div class="wifi-network-copy">
                    <strong>${escapeHtml(network.ssid)}</strong>
                    <span>${escapeHtml(subtitle)}</span>
                </div>
                <button
                    class="${actionClass}"
                    type="button"
                    data-ssid="${escapeHtml(network.ssid)}"
                    data-requires-password="${network.requires_password ? 'true' : 'false'}"
                    ${network.connected || wifiConnectBusy ? 'disabled' : ''}
                    onclick="wifiSelectNetwork(this.dataset.ssid, this.dataset.requiresPassword === 'true')"
                >${label}</button>
            </div>
        `;
    }).join('');
}

function wifiSelectNetwork(ssid, requiresPassword) {
    if (wifiConnectBusy) return;
    wifiSelectedNetwork = {
        ssid,
        interface: wifiSettingsStatus?.interface || '',
    };
    if (requiresPassword) {
        openWifiPasswordModal(ssid);
        return;
    }
    submitWifiConnect(ssid, '');
}

function submitWifiConnect(ssid, password = '') {
    wifiConnectBusy = true;
    setText('wifi-settings-summary', `Connecting to ${ssid}...`);
    renderWifiNetworks(wifiSettingsNetworks);
    fetch('/api/wifi', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            ssid,
            password,
            interface: wifiSelectedNetwork?.interface || wifiSettingsStatus?.interface || '',
        })
    })
        .then(async response => {
            const data = await response.json();
            if (!response.ok) throw data;
            return data;
        })
        .then(result => {
            closeWifiPasswordModal(true);
            updateWifiSettings(result);
        })
        .catch(err => {
            const message = err?.message || err?.error || 'Failed to connect to the selected Wi-Fi network.';
            setText('wifi-settings-summary', message);
            setWifiPasswordModalMessage(message);
        })
        .finally(() => {
            wifiConnectBusy = false;
            renderWifiNetworks(wifiSettingsNetworks);
        });
}

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

function openWifiPasswordModal(ssid) {
    const modal = document.getElementById('wifi-password-modal');
    const ssidInput = document.getElementById('wifi-password-ssid');
    const passwordInput = document.getElementById('wifi-password-input');
    if (!modal || !ssidInput || !passwordInput) return;
    wifiPasswordKeyboardMode = 'lower';
    wifiPasswordVisible = false;
    ssidInput.value = ssid;
    passwordInput.value = '';
    passwordInput.type = 'password';
    setWifiPasswordModalMessage(`Enter the password for ${ssid}.`);
    buildWifiPasswordKeyboard();
    modal.classList.remove('hidden');
}

function closeWifiPasswordModal(force = false) {
    if (wifiConnectBusy && !force) return;
    const modal = document.getElementById('wifi-password-modal');
    if (!modal) return;
    modal.classList.add('hidden');
    wifiSelectedNetwork = null;
}

function wifiPasswordOverlayClick(event) {
    if (event.target === document.getElementById('wifi-password-modal')) {
        closeWifiPasswordModal();
    }
}

function setWifiPasswordModalMessage(message) {
    setText('wifi-password-subtitle', message);
}

function buildWifiPasswordKeyboard() {
    const container = document.getElementById('wifi-password-keyboard');
    if (!container) return;
    const rows = wifiPasswordLayouts[wifiPasswordKeyboardMode] || wifiPasswordLayouts.lower;
    container.innerHTML = rows.map(row => `
        <div class="wifi-password-keyboard-row">
            ${row.map(key => {
                const wide = ['⇧', '⇩', '⌫', '123', 'abc', 'ABC', 'Connect'].includes(key);
                const isSpace = key === ' ';
                const active = (key === '⇧' && wifiPasswordKeyboardMode === 'lower') || (key === '⇩' && wifiPasswordKeyboardMode === 'upper');
                return `<button
                    class="wifi-password-key ${wide ? 'wide' : ''} ${isSpace ? 'space' : ''} ${active ? 'active' : ''}"
                    type="button"
                    onclick="wifiPasswordKeyPress(${JSON.stringify(key)})"
                >${key === ' ' ? 'SPACE' : escapeHtml(key)}</button>`;
            }).join('')}
        </div>
    `).join('');
}

function wifiPasswordKeyPress(key) {
    if (key === '⇧') {
        wifiPasswordKeyboardMode = 'upper';
        buildWifiPasswordKeyboard();
        return;
    }
    if (key === '⇩') {
        wifiPasswordKeyboardMode = 'lower';
        buildWifiPasswordKeyboard();
        return;
    }
    if (key === '123') {
        wifiPasswordKeyboardMode = 'symbols';
        buildWifiPasswordKeyboard();
        return;
    }
    if (key === 'abc') {
        wifiPasswordKeyboardMode = 'lower';
        buildWifiPasswordKeyboard();
        return;
    }
    if (key === 'ABC') {
        wifiPasswordKeyboardMode = 'upper';
        buildWifiPasswordKeyboard();
        return;
    }
    if (key === '⌫') {
        wifiPasswordBackspace();
        return;
    }
    if (key === 'Connect') {
        submitWifiPassword();
        return;
    }
    const input = document.getElementById('wifi-password-input');
    if (!input) return;
    input.value += key;
}

function wifiPasswordBackspace() {
    const input = document.getElementById('wifi-password-input');
    if (!input) return;
    input.value = input.value.slice(0, -1);
}

function wifiPasswordClear() {
    const input = document.getElementById('wifi-password-input');
    if (!input) return;
    input.value = '';
}

function toggleWifiPasswordVisible() {
    const input = document.getElementById('wifi-password-input');
    if (!input) return;
    wifiPasswordVisible = !wifiPasswordVisible;
    input.type = wifiPasswordVisible ? 'text' : 'password';
}

function submitWifiPassword() {
    const input = document.getElementById('wifi-password-input');
    if (!input || !wifiSelectedNetwork?.ssid) return;
    submitWifiConnect(wifiSelectedNetwork.ssid, input.value);
}

function formatStateValue(value, unit = '', digits = 1) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return '--';
    }
    const formatted = Number(value).toFixed(digits);
    return unit ? `${formatted} ${unit}` : formatted;
}

function updatePlaybackSummary(musicData) {
    setText('stat-shuffle', musicData.random ? 'On' : 'Off');
    setText('stat-repeat', musicData.repeat_mode === 'song'
        ? 'Song'
        : musicData.repeat_mode === 'playlist'
            ? 'Playlist'
            : 'Off');
    setText('stat-volume', `${musicData.volume}%`);
    setText('stat-queue-len', `${queueFiles.size} track${queueFiles.size === 1 ? '' : 's'}`);
}

// Update OBD display with dynamic metrics
function updateOBDDisplay(obdData) {
    const obdContent = document.getElementById('obd-content');
    const obdDisconnected = document.getElementById('obd-disconnected');
    const obdError = document.getElementById('obd-error');

    if (!obdData) {
        obdContent.style.display = 'none';
        obdDisconnected.style.display = 'block';
        obdError.style.display = 'none';
        return;
    }

    if (obdData.error && !obdData.connected) {
        obdContent.style.display = 'none';
        obdDisconnected.style.display = 'none';
        obdError.style.display = 'block';
        document.getElementById('obd-error-text').textContent = obdData.error;
        return;
    }

    if (!obdData.connected) {
        obdContent.style.display = 'none';
        obdDisconnected.style.display = 'block';
        obdError.style.display = 'none';
        return;
    }

    // Connected with data
    obdContent.style.display = 'block';
    obdDisconnected.style.display = 'none';
    obdError.style.display = 'none';

    const direct = obdData.direct || {};
    const inferred = obdData.inferred || {};
    const connection = obdData.connection || {};
    const metadata = obdData.metadata || {};

    setText('obd-vehicle-name', metadata.vehicle || 'Veiculo');
    setText(
        'obd-connection-line',
        `${connection.protocol || 'protocolo OBD'} · ${connection.port || 'porta serial'} · ${connection.adapter || 'ELM327'}${metadata.dynamic_stale ? ' · dados atrasados' : ''}`
    );

    const fuelSelect = document.getElementById('obd-fuel-select');
    if (fuelSelect && inferred.fuel && fuelSelect.value !== inferred.fuel) {
        fuelSelect.value = inferred.fuel;
    }

    setText('obd-speed', formatOBDValue(direct.speed_kmh));
    setText('obd-rpm', formatOBDValue(direct.rpm));
    setText('obd-coolant', formatOBDValue(direct.coolant_temp_c));

    if (direct.speed_kmh > 0 && inferred.instant_km_l !== null && inferred.instant_km_l !== undefined) {
        setText('obd-consumption', formatOBDValue(inferred.instant_km_l, 1));
        setText('obd-consumption-unit', 'km/L');
    } else {
        setText('obd-consumption', formatOBDValue(inferred.selected_fuel_rate_l_h, 2));
        setText('obd-consumption-unit', 'L/h');
    }

    setText('obd-trip-distance', formatOBDValue(inferred.trip_distance_km, 1));
    setText('obd-trip-fuel', formatOBDValue(inferred.trip_consumed_l, 2));
    setText('obd-trip-average', formatOBDValue(inferred.trip_average_km_l, 1));
    setText('obd-gear', inferred.gear_display || '--');
    setText('obd-voltage', formatOBDValue(direct.adapter_voltage_v, 1));

    setText('stat-mil', direct.mil_on === true ? 'On' : direct.mil_on === false ? 'Off' : '--');
    setText('stat-battery', direct.adapter_voltage_v ? `${formatOBDValue(direct.adapter_voltage_v, 1)} V` : 'Waiting');
    setText(
        'stat-connection',
        connection.connected
            ? `${connection.adapter || 'ELM327'}${connection.protocol ? ` · ${connection.protocol}` : ''}`
            : 'Disconnected'
    );

    const alerts = [];
    if (direct.mil_on) alerts.push('Check engine aceso');
    if (metadata.dynamic_stale) alerts.push(`Dados OBD atrasados: ${metadata.dynamic_stale_age_s || '?'}s`);
    if (inferred.coolant_alert) alerts.push('Temperatura alta');
    if (inferred.battery_alert) alerts.push('Tensao baixa com motor ligado');
    if ((direct.active_dtcs || []).length > 0) alerts.push(`DTC ativo: ${direct.active_dtcs.join(', ')}`);
    if ((direct.pending_dtcs || []).length > 0) alerts.push(`DTC pendente: ${direct.pending_dtcs.join(', ')}`);
    const alertsElement = document.getElementById('obd-alerts');
    if (alertsElement) {
        alertsElement.innerHTML = alerts.map(alert => `<span>${alert}</span>`).join('');
        alertsElement.style.display = alerts.length ? 'flex' : 'none';
    }

    setText('obd-inst-kml', formatOBDValue(inferred.instant_km_l, 1));

    applyHealthHighlights({ direct, inferred, metadata, metrics: obdData.metrics || {} });

    const metrics = obdData.metrics || {};
    setText('v-engine-load', formatStateValue(metrics.ENGINE_LOAD?.value, '%', 1));
    setText('v-map', formatStateValue(metrics.INTAKE_PRESSURE?.value, 'kPa', 0));
    setText('v-timing', formatStateValue(metrics.TIMING_ADVANCE?.value, 'deg', 1));
    setText('v-intake-temp', formatStateValue(metrics.INTAKE_TEMP?.value, 'C', 0));
    setText('v-throttle', formatStateValue(metrics.THROTTLE_POS?.value, '%', 1));
    setText('v-stft', formatStateValue(metrics.SHORT_FUEL_TRIM_1?.value, '%', 1));
    setText('v-ltft', formatStateValue(metrics.LONG_FUEL_TRIM_1?.value, '%', 1));

    setText(
        'v-mil-status',
        direct.mil_on === true ? 'On' : direct.mil_on === false ? 'Off' : 'Waiting'
    );
    setText(
        'v-mil-distance',
        direct.distance_with_mil_km != null ? `${formatOBDValue(direct.distance_with_mil_km)} km` : '--'
    );
    setText('v-dtc-active', (direct.active_dtcs || []).join(', ') || 'None');
    setText('v-dtc-pending', (direct.pending_dtcs || []).join(', ') || 'None');
    setText('v-atrv', direct.adapter_voltage_v ? `${formatOBDValue(direct.adapter_voltage_v, 1)} V` : '--');
    setText('v-sample-time', formatSampleTime(metadata));

    setText('v-adapter', connection.adapter || '--');
    setText('v-port', connection.port || '--');
    setText('v-baud', connection.baudrate ? `${connection.baudrate}` : '--');
    setText('v-proto', connection.protocol || '--');
    setText('v-last-cmd', metadata.last_successful_command || '--');

    setText('v-vehicle-desc', metadata.vehicle || '--');
    setText('v-vin', metadata.vin || '--');
    setText('v-vin-mfr', decodeVIN(metadata.vin) || '--');
    setText(
        'v-fuel-info',
        inferred.fuel === 'ethanol' ? 'Ethanol' : inferred.fuel === 'gasoline_e27' ? 'Gasoline E27' : '--'
    );
    renderSupportedPids(obdData.supported_commands || []);
}

function formatSampleTime(metadata) {
    if (!metadata || !metadata.sample_time) return '--';
    const stale = metadata.dynamic_stale ? ` · stale ${metadata.dynamic_stale_age_s || '?'}s` : '';
    try {
        const d = new Date(metadata.sample_time);
        return d.toLocaleTimeString() + stale;
    } catch (e) {
        return metadata.sample_time + stale;
    }
}

function renderSupportedPids(list) {
    const wrap = document.getElementById('v-supported-pids');
    if (!wrap) return;
    if (!list.length) {
        wrap.innerHTML = '<span class="pid-chip muted">--</span>';
        return;
    }
    wrap.innerHTML = list.map(pid => `<span class="pid-chip">${pid}</span>`).join('');
}

function setOBDFuel(fuel) {
    fetch('/api/vehicle/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fuel })
    })
        .then(r => r.json())
        .then(updateOBDDisplay)
        .catch(err => console.error('Error updating OBD settings:', err));
}

function resetOBDTrip() {
    fetch('/api/vehicle/trip/reset', { method: 'POST' })
        .then(r => r.json())
        .then(updateOBDDisplay)
        .catch(err => console.error('Error resetting OBD trip:', err));
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
            updateWifiStatus(data.wifi);

            // Music
            document.getElementById('music-title').textContent = data.music.title || 'No music';
            document.getElementById('music-artist').textContent = data.music.artists_all || data.music.artist || '-';
            document.getElementById('volume-display').textContent = data.music.volume + '%';
            document.getElementById('time-elapsed').textContent = formatTime(data.music.elapsed);
            document.getElementById('time-duration').textContent = formatTime(data.music.duration);

            // Store duration for seek
            currentDuration = data.music.duration || 0;

            const progress = data.music.duration > 0 ? (data.music.elapsed / data.music.duration * 100) : 0;
            document.getElementById('progress-fill').style.width = progress + '%';

            updatePlayButton(data.music.state);
            const artwork = document.getElementById('music-artwork');
            if (data.music.state === 'play') artwork.classList.add('playing');
            else artwork.classList.remove('playing');

            // Shuffle and Repeat
            document.getElementById('btn-shuffle').classList.toggle('active', data.music.random);
            updateRepeatButton(data.music.repeat_mode);

            // OBD - Dynamic metrics display
            updateOBDDisplay(data.obd);

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
        .catch(err => {
            setWifiIndicator('disconnected');
            console.error('Error updating:', err);
        });
}

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

    const bar = event.currentTarget || document.getElementById('progress-bar');
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

const REPEAT_SVG = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M7 7h10v3l4-4-4-4v3H5v6h2V7zm10 10H7v-3l-4 4 4 4v-3h12v-6h-2v4z"/></svg>';
const PLAY_SVG = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>';
const PAUSE_SVG = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 5h4v14H6zm8 0h4v14h-4z"/></svg>';

function updatePlayButton(state) {
    const btn = document.getElementById('btn-play');
    if (!btn) return;
    if (state === 'play') {
        btn.innerHTML = PAUSE_SVG;
        btn.dataset.state = 'play';
        btn.onclick = () => musicControl('pause');
    } else {
        btn.innerHTML = PLAY_SVG;
        btn.dataset.state = 'pause';
        btn.onclick = () => musicControl('play');
    }
}

function updateRepeatButton(mode) {
    const btn = document.getElementById('btn-repeat');
    if (!btn) return;
    btn.innerHTML = REPEAT_SVG;
    btn.classList.remove('active', 'repeat-song');
    if (mode === 'playlist') {
        btn.classList.add('active');
        btn.title = 'Repeat playlist';
    } else if (mode === 'song') {
        btn.classList.add('active', 'repeat-song');
        btn.title = 'Repeat song';
    } else {
        btn.title = 'Repeat off';
    }
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
        requestAnimationFrame(() => loadMusicContent(tab.dataset.music));
    });
});

const loadedMusicTabs = new Set();

function invalidateQueueView() {
    loadedMusicTabs.delete('queue');
}

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
            if (loadedMusicTabs.has(type)) break;
            loadedMusicTabs.add(type);
            loadArtists();
            break;
        case 'playlists':
            if (loadedMusicTabs.has(type)) break;
            loadedMusicTabs.add(type);
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
                updatePlaybackSummary({
                    random: document.getElementById('btn-shuffle')?.classList.contains('active'),
                    repeat_mode: document.getElementById('btn-repeat')?.classList.contains('repeat-song')
                        ? 'song'
                        : document.getElementById('btn-repeat')?.classList.contains('active')
                            ? 'playlist'
                            : 'off',
                    volume: parseInt((document.getElementById('volume-display')?.textContent || '0').replace('%', ''), 10) || 0
                });
                list.innerHTML = '<div class="browser-empty"><div class="browser-empty-icon">&#9835;</div>Queue empty</div>';
                return;
            }

            // Update queue files set
            queueFiles = new Set(queue.map(s => s.file));
            updatePlaybackSummary({
                random: document.getElementById('btn-shuffle')?.classList.contains('active'),
                repeat_mode: document.getElementById('btn-repeat')?.classList.contains('repeat-song')
                    ? 'song'
                    : document.getElementById('btn-repeat')?.classList.contains('active')
                        ? 'playlist'
                        : 'off',
                volume: parseInt((document.getElementById('volume-display')?.textContent || '0').replace('%', ''), 10) || 0
            });

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
                        <div class="browser-item-subtitle">${song.artists_all || song.artist || 'Unknown artist'}</div>
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
        .then(() => {
            invalidateQueueView();
            loadQueue();
            updateData();
        })
        .catch(err => console.error('Error:', err));
}

// Clear queue
function clearQueue() {
    fetch('/api/music/clear', { method: 'POST' })
        .then(r => r.json())
        .then(() => {
            queueFiles.clear();
            invalidateQueueView();
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

            list.innerHTML = `
                <div class="browser-item" onclick="loadAllSongs()">
                    <div class="browser-item-icon">&#127925;</div>
                    <div class="browser-item-info">
                        <div class="browser-item-title">All songs</div>
                    </div>
                    <button class="browser-item-action play" onclick="event.stopPropagation(); playAllSongs()">&#9654;</button>
                    <button class="browser-item-action" onclick="event.stopPropagation(); addAllSongsToQueue()">+</button>
                </div>
            ` + artists.map(artist => {
                const escaped = artist.replace(/'/g, "\\'");
                return `
                <div class="browser-item" onclick="loadArtistSongs('${escaped}')">
                    <div class="browser-item-icon">&#128100;</div>
                    <div class="browser-item-info">
                        <div class="browser-item-title">${artist}</div>
                    </div>
                    <button class="browser-item-action play" onclick="event.stopPropagation(); playArtist('${escaped}')">&#9654;</button>
                    <button class="browser-item-action" onclick="event.stopPropagation(); addArtistToQueue('${escaped}')">+</button>
                </div>
            `}).join('');
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
                        <div class="browser-item-subtitle">${song.artists_all || song.artist || ''}</div>
                    </div>
                    <button class="browser-item-action play" onclick="event.stopPropagation(); playSong('${file}')">&#9654;</button>
                    <button class="browser-item-action ${inQueue ? 'added' : ''}" onclick="event.stopPropagation(); addToQueueAndMark(this, '${file}')">+</button>
                </div>
            `}).join('');
        })
        .catch(err => console.error('Error loading songs:', err));
}

// Load all songs list
function loadAllSongs() {
    fetch('/api/music/all')
        .then(r => r.json())
        .then(songs => {
            const list = document.getElementById('artists-list');
            if (!songs || songs.length === 0 || songs.error) {
                list.innerHTML = '<div class="browser-empty">No songs</div>';
                return;
            }

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
                        <div class="browser-item-subtitle">${song.artists_all || song.artist || ''}</div>
                    </div>
                    <button class="browser-item-action play" onclick="event.stopPropagation(); playSong('${file}')">&#9654;</button>
                    <button class="browser-item-action ${inQueue ? 'added' : ''}" onclick="event.stopPropagation(); addToQueueAndMark(this, '${file}')">+</button>
                </div>
            `}).join('');
        })
        .catch(err => console.error('Error loading all songs:', err));
}

// Play all songs (replaces queue)
function playAllSongs() {
    fetch('/api/music/all/play', { method: 'POST' })
        .then(r => r.json())
        .then(() => {
            invalidateQueueView();
            document.querySelector('.music-tab[data-music="playing"]').click();
            updateData();
        })
        .catch(err => console.error('Error:', err));
}

// Add all songs to queue
function addAllSongsToQueue() {
    fetch('/api/music/all/add', { method: 'POST' })
        .then(r => r.json())
        .then(() => {
            invalidateQueueView();
            loadQueue();
        })
        .catch(err => console.error('Error:', err));
}

// Play all songs by artist (replaces queue)
function playArtist(artist) {
    fetch('/api/music/artist/' + encodeURIComponent(artist) + '/play', { method: 'POST' })
        .then(r => r.json())
        .then(() => {
            invalidateQueueView();
            document.querySelector('.music-tab[data-music="playing"]').click();
            updateData();
        })
        .catch(err => console.error('Error:', err));
}

// Add all songs by artist to queue
function addArtistToQueue(artist) {
    fetch('/api/music/artist/' + encodeURIComponent(artist) + '/add', { method: 'POST' })
        .then(r => r.json())
        .then(() => {
            invalidateQueueView();
            loadQueue();
        })
        .catch(err => console.error('Error:', err));
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
            invalidateQueueView();
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
            invalidateQueueView();
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
    hideSearchKeyboard();

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
                        <div class="browser-item-subtitle">${song.artists_all || song.artist || 'Unknown artist'}</div>
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
                    <div class="browser-item-subtitle">${song.artists_all || song.artist || song.album || 'Unknown artist'}</div>
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
            invalidateQueueView();
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
            invalidateQueueView();
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
            invalidateQueueView();
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

    const input = document.getElementById('search-input');
    if (input) {
        input.addEventListener('click', showSearchKeyboard);
        input.addEventListener('focus', showSearchKeyboard);
    }
}

function showSearchKeyboard() {
    const container = document.getElementById('virtual-keyboard');
    if (container) container.classList.remove('hidden');
}

function hideSearchKeyboard() {
    const container = document.getElementById('virtual-keyboard');
    if (container) container.classList.add('hidden');
}

function keyPress(key) {
    const input = document.getElementById('search-input');
    showSearchKeyboard();
    input.value += key;
    input.focus();
}

function keyBackspace() {
    const input = document.getElementById('search-input');
    showSearchKeyboard();
    input.value = input.value.slice(0, -1);
    input.focus();
}

function keyClear() {
    const input = document.getElementById('search-input');
    showSearchKeyboard();
    input.value = '';
    input.focus();
}

// Initialize keyboard
createKeyboard();

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
        document.getElementById('radio-content').style.display = '';
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
        const playLabel = document.getElementById('radio-play-label');
        if (currentRadioPlaying) {
            playBtn.classList.add('playing');
            playIcon.innerHTML = '&#9632;';
            if (playLabel) playLabel.textContent = 'Stop';
        } else {
            playBtn.classList.remove('playing');
            playIcon.innerHTML = '&#9654;';
            if (playLabel) playLabel.textContent = 'Play';
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
                updateTunerFrequencyDisplay(currentRadioFreq);
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
                        <div class="preset-top">
                            <span class="preset-freq">${p.freq.toFixed(1)}</span>
                            <span class="preset-mode-tag">${p.mode}</span>
                        </div>
                        <div class="preset-name">${p.label}</div>
                        ${p.genre ? `<div class="preset-genre">${p.genre}</div>` : ''}
                        <button class="preset-fav-btn" title="Add to favorites"
                            onclick="radioAddFavoriteFromPreset(${p.freq}, '${p.mode}', '${p.label.replace(/'/g,"\\'")}', event)">&#9733;</button>
                    </div>
                `).join('');
            }

            // Airport Presets - SBSJ
            if (data.airports && data.airports.SBSJ) {
                const sbsjList = document.getElementById('airport-presets-sbsj');
                sbsjList.innerHTML = data.airports.SBSJ.frequencies.map(p => `
                    <div class="preset-item" onclick="radioTune(${p.freq}, '${p.mode}')">
                        <div class="preset-top">
                            <span class="preset-freq">${p.freq.toFixed(3)}</span>
                            <span class="preset-mode-tag">${p.mode}</span>
                        </div>
                        <div class="preset-name">${p.label}</div>
                        <button class="preset-fav-btn" title="Add to favorites"
                            onclick="radioAddFavoriteFromPreset(${p.freq}, '${p.mode}', '${p.label.replace(/'/g,"\\'")}', event)">&#9733;</button>
                    </div>
                `).join('');
            }

            // Airport Presets - SBGR
            if (data.airports && data.airports.SBGR) {
                const sbgrList = document.getElementById('airport-presets-sbgr');
                sbgrList.innerHTML = data.airports.SBGR.frequencies.map(p => `
                    <div class="preset-item" onclick="radioTune(${p.freq}, '${p.mode}')">
                        <div class="preset-top">
                            <span class="preset-freq">${p.freq.toFixed(3)}</span>
                            <span class="preset-mode-tag">${p.mode}</span>
                        </div>
                        <div class="preset-name">${p.label}</div>
                        <button class="preset-fav-btn" title="Add to favorites"
                            onclick="radioAddFavoriteFromPreset(${p.freq}, '${p.mode}', '${p.label.replace(/'/g,"\\'")}', event)">&#9733;</button>
                    </div>
                `).join('');
            }
        })
        .catch(err => console.error('Error loading presets:', err));
}

// Load favorites list (Favorites tab)
function loadRadioFavorites() {
    fetch('/api/radio/favorites')
        .then(r => r.json())
        .then(data => {
            const list = document.getElementById('favorites-list');
            if (!data.favorites || data.favorites.length === 0) {
                list.innerHTML = '<div class="empty-message">No favorites yet. Tune to a frequency and tap "+ Favorite".</div>';
                loadTunerFavoriteStrip([]);
                return;
            }
            const favs = data.favorites;
            list.innerHTML = favs.map((fav, i) => `
                <div class="favorite-item ${i < 5 ? 'fav-top5' : ''}" onclick="radioTune(${fav.freq}, '${fav.mode}')">
                    <div class="fav-rank">${i < 5 ? i + 1 : '—'}</div>
                    <div class="favorite-info">
                        <span class="favorite-freq">${fav.freq.toFixed(1)}</span>
                        <span class="fav-mode-tag">${fav.mode}</span>
                        <span class="favorite-name">${fav.name || ''}</span>
                    </div>
                    <div class="fav-actions">
                        <button class="fav-move-btn" onclick="event.stopPropagation(); radioMoveFavorite(${i}, 'up')" ${i === 0 ? 'disabled' : ''}>&#9650;</button>
                        <button class="fav-move-btn" onclick="event.stopPropagation(); radioMoveFavorite(${i}, 'down')" ${i === favs.length - 1 ? 'disabled' : ''}>&#9660;</button>
                        <button class="favorite-remove" onclick="event.stopPropagation(); radioRemoveFavorite(${i})">&#10005;</button>
                    </div>
                </div>
            `).join('');
            loadTunerFavoriteStrip(favs);
        })
        .catch(err => console.error('Error loading favorites:', err));
}

// Render top-5 favorites in the Tuner preset strip
function loadTunerFavoriteStrip(favs) {
    const strip = document.getElementById('tuner-favorites-strip');
    if (!strip) return;
    const top5 = favs.slice(0, 5).map(fav =>
        `<button onclick="radioTune(${fav.freq}, '${fav.mode}')">${fav.freq.toFixed(1)} ${fav.name || fav.mode}</button>`
    ).join('');
    strip.innerHTML = top5 + `<button onclick="radioOpenAddFavorite()">&#9733; + Favorite</button>`;
}

// Open add-favorite modal with virtual keyboard
function radioOpenAddFavorite() {
    document.getElementById('fav-modal-freq-label').textContent =
        `${currentRadioFreq.toFixed(1)} MHz ${currentRadioMode}`;
    document.getElementById('fav-name-input').value = '';
    buildFavKeyboard();
    document.getElementById('fav-modal').classList.remove('hidden');
}

function favModalClose() {
    document.getElementById('fav-modal').classList.add('hidden');
}

function favModalOverlayClick(e) {
    if (e.target === document.getElementById('fav-modal')) favModalClose();
}

function favModalSave() {
    const name = document.getElementById('fav-name-input').value.trim();
    fetch('/api/radio/favorites', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ freq: currentRadioFreq, mode: currentRadioMode, name })
    })
        .then(r => r.json())
        .then(result => {
            favModalClose();
            if (!result.error) loadTunerFavoriteStrip(result.favorites || []);
        })
        .catch(err => console.error('Error adding favorite:', err));
}

// Build the in-modal keyboard
function buildFavKeyboard() {
    const container = document.getElementById('fav-keyboard');
    if (!container || container.dataset.built) return;
    const rows = [
        ['1','2','3','4','5','6','7','8','9','0'],
        ['Q','W','E','R','T','Y','U','I','O','P'],
        ['A','S','D','F','G','H','J','K','L'],
        ['Z','X','C','V','B','N','M',' ']
    ];
    container.innerHTML = rows.map(row =>
        `<div class="fav-kbd-row">${row.map(k =>
            k === ' '
                ? `<button class="fav-kbd-key fav-kbd-space" onclick="favKeyPress(' ')">SPACE</button>`
                : `<button class="fav-kbd-key" onclick="favKeyPress('${k}')">${k}</button>`
        ).join('')}</div>`
    ).join('') + `<div class="fav-kbd-row">
        <button class="fav-kbd-key fav-kbd-special" onclick="favKeyBackspace()">&#9003;</button>
        <button class="fav-kbd-key fav-kbd-special" onclick="favKeyClear()">CLEAR</button>
    </div>`;
    container.dataset.built = '1';
}

function favKeyPress(k) {
    const inp = document.getElementById('fav-name-input');
    inp.value += k;
}
function favKeyBackspace() {
    const inp = document.getElementById('fav-name-input');
    inp.value = inp.value.slice(0, -1);
}
function favKeyClear() {
    document.getElementById('fav-name-input').value = '';
}

// Add favorite directly from a preset card
function radioAddFavoriteFromPreset(freq, mode, name, e) {
    e.stopPropagation();
    fetch('/api/radio/favorites', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ freq, mode, name })
    })
        .then(r => r.json())
        .then(result => { if (!result.error) loadTunerFavoriteStrip(result.favorites || []); })
        .catch(err => console.error('Error adding favorite:', err));
}

// Remove favorite
function radioRemoveFavorite(index) {
    fetch('/api/radio/favorites/' + index, { method: 'DELETE' })
        .then(r => r.json())
        .then(() => loadRadioFavorites())
        .catch(err => console.error('Error removing favorite:', err));
}

// Move favorite up or down
function radioMoveFavorite(index, direction) {
    fetch(`/api/radio/favorites/${index}/move`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ direction })
    })
        .then(r => r.json())
        .then(() => loadRadioFavorites())
        .catch(err => console.error('Error moving favorite:', err));
}

// Clear all favorites
function radioClearFavorites() {
    fetch('/api/radio/favorites/clear', { method: 'POST' })
        .then(r => r.json())
        .then(() => loadRadioFavorites())
        .catch(err => console.error('Error clearing favorites:', err));
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

    // Update frequency display and labels to match current tuner frequency
    updateSpectrumFreqDisplay();
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

// Update tuner frequency display
function updateTunerFrequencyDisplay(freq) {
    document.getElementById('radio-freq').textContent = freq.toFixed(1);
    document.getElementById('freq-input').value = freq.toFixed(1);
}

// Adjust spectrum frequency by delta (in MHz)
function adjustSpectrumFreq(deltaMHz) {
    let newFreq = currentRadioFreq + deltaMHz;

    // Clamp to valid range
    newFreq = Math.max(FREQ_MIN_MHZ, Math.min(FREQ_MAX_MHZ, newFreq));

    // Round to 1 decimal place to avoid floating point issues
    newFreq = Math.round(newFreq * 10) / 10;

    // Update current radio frequency
    currentRadioFreq = newFreq;

    // Update all displays
    updateSpectrumFrequencyLabels();
    updateSpectrumFreqDisplay();
    updateTunerFrequencyDisplay(newFreq);
}

// Update the large frequency display in spectrum panel
function updateSpectrumFreqDisplay() {
    const display = document.getElementById('spectrum-freq-display');
    if (display) {
        display.textContent = currentRadioFreq.toFixed(1);
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
updateData = function() {
    fetch('/api/status')
        .then(r => r.json())
        .then(data => {
            document.getElementById('ind-music').classList.toggle('connected', data.music.connected);
            document.getElementById('ind-gps').classList.toggle('connected', data.gps.connected);
            document.getElementById('ind-obd').classList.toggle('connected', data.obd.connected);
            updateWifiStatus(data.wifi);

            if (data.radio) {
                document.getElementById('ind-radio').classList.toggle('connected', data.radio.connected);
                updateRadioDisplay(data.radio);
            }

            document.getElementById('music-title').textContent = data.music.title || 'No music';
            document.getElementById('music-artist').textContent = data.music.artists_all || data.music.artist || '-';
            document.getElementById('volume-display').textContent = data.music.volume + '%';
            document.getElementById('time-elapsed').textContent = formatTime(data.music.elapsed);
            document.getElementById('time-duration').textContent = formatTime(data.music.duration);

            currentDuration = data.music.duration || 0;

            const progress = data.music.duration > 0 ? (data.music.elapsed / data.music.duration * 100) : 0;
            document.getElementById('progress-fill').style.width = progress + '%';

            updatePlayButton(data.music.state);
            const artwork = document.getElementById('music-artwork');
            if (data.music.state === 'play') artwork.classList.add('playing');
            else artwork.classList.remove('playing');

            document.getElementById('btn-shuffle').classList.toggle('active', data.music.random);
            updateRepeatButton(data.music.repeat_mode);
            updatePlaybackSummary(data.music);

            updateOBDDisplay(data.obd);

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

            // ============ HOME PANEL ============
            const obd = data.obd;
            if (obd && obd.connected) {
                const d = obd.direct || {};
                const inf = obd.inferred || {};
                setText('home-obd-speed', formatOBDValue(d.speed_kmh));
                setText('home-trip-fuel', formatOBDValue(inf.trip_consumed_l, 2));
                setText('home-trip-dist', formatOBDValue(inf.trip_distance_km, 1));
                setText('home-avg-kml', formatOBDValue(inf.trip_average_km_l, 1));
                setText('home-gear', inf.gear_display || '--');
                setText('home-battery', formatOBDValue(d.adapter_voltage_v, 1));
                setText('home-rpm', d.rpm ? Math.round(d.rpm).toString() : '--');
                const speedFill = document.getElementById('home-speed-fill');
                if (speedFill) speedFill.style.width = Math.min(100, (d.speed_kmh || 0) / 200 * 100) + '%';
                const rpmFill = document.getElementById('home-rpm-fill');
                if (rpmFill) rpmFill.style.width = Math.min(100, (d.rpm || 0) / 7000 * 100) + '%';
            } else {
                setText('home-obd-speed', '--');
                setText('home-trip-fuel', '--');
                setText('home-trip-dist', '--');
                setText('home-avg-kml', '--');
                setText('home-gear', '--');
                setText('home-battery', '--');
                setText('home-rpm', '--');
                const speedFill = document.getElementById('home-speed-fill');
                if (speedFill) speedFill.style.width = '0%';
                const rpmFill = document.getElementById('home-rpm-fill');
                if (rpmFill) rpmFill.style.width = '0%';
            }
            setText('home-music-title', data.music.title || 'No music');
            setText('home-music-artist', data.music.artists_all || data.music.artist || '-');
            const homePlay = document.getElementById('home-btn-play');
            if (homePlay) {
                if (data.music.state === 'play') {
                    homePlay.innerHTML = PAUSE_SVG;
                    homePlay.dataset.state = 'play';
                    homePlay.onclick = () => musicControl('pause');
                } else {
                    homePlay.innerHTML = PLAY_SVG;
                    homePlay.dataset.state = 'pause';
                    homePlay.onclick = () => musicControl('play');
                }
            }
            const homeShuffle = document.getElementById('home-btn-shuffle');
            if (homeShuffle) homeShuffle.classList.toggle('active', !!data.music.random);
            const homeRepeat = document.getElementById('home-btn-repeat');
            if (homeRepeat) {
                homeRepeat.innerHTML = REPEAT_SVG;
                homeRepeat.classList.remove('active', 'repeat-song');
                if (data.music.repeat_mode === 'playlist') homeRepeat.classList.add('active');
                else if (data.music.repeat_mode === 'song') homeRepeat.classList.add('active', 'repeat-song');
            }
            setText('home-volume-display', data.music.volume + '%');
            setText('home-vol-pct', data.music.volume + '%');
            const homeVolFill = document.getElementById('home-vol-fill');
            if (homeVolFill) homeVolFill.style.width = data.music.volume + '%';
            setText('home-time-elapsed', formatTime(data.music.elapsed));
            setText('home-time-duration', formatTime(data.music.duration));
            const homeProgress = document.getElementById('home-progress-fill');
            if (homeProgress) {
                const p = data.music.duration > 0 ? (data.music.elapsed / data.music.duration * 100) : 0;
                homeProgress.style.width = p + '%';
            }
        })
        .catch(err => console.error('Error updating:', err));
};

// Load presets and populate tuner favorite strip on page load
if (document.getElementById('fm-presets')) {
    loadRadioPresets();
    loadRadioFavorites();
}

if (document.getElementById('media-sync-state')) {
    fetchMediaSyncStatus();
    mediaSyncPoller = setInterval(fetchMediaSyncStatus, 5000);
    maybeAutoSyncMedia('page-load');
    window.addEventListener('online', () => maybeAutoSyncMedia('browser-online'));
}

if (document.getElementById('maintenance-state')) {
    fetchMaintenanceStatus();
    maintenancePoller = setInterval(fetchMaintenanceStatus, 5000);
}

if (document.getElementById('obd-logger-state')) {
    fetchOBDLoggerStatus();
    setInterval(fetchOBDLoggerStatus, 5000);
}

window.addEventListener('online', () => setWifiIndicator('disconnected'));
window.addEventListener('offline', () => setWifiIndicator('disconnected'));

fetchWifiSettings(false);
updateData();
setInterval(updateData, 1000);

// ============ MUSIC VISUALIZER ============
(function () {
    const canvas = document.getElementById('music-viz-canvas');
    const wrap = document.getElementById('music-visualizer');
    if (!canvas || !wrap) return;
    const ctx = canvas.getContext('2d');
    const NUM_MODES = 4;
    let mode = parseInt(localStorage.getItem('music-viz-mode') || '0', 10);
    if (isNaN(mode) || mode < 0 || mode >= NUM_MODES) mode = 0;
    let t = 0;

    function resize() {
        const dpr = window.devicePixelRatio || 1;
        const r = wrap.getBoundingClientRect();
        canvas.width = Math.max(1, Math.floor(r.width * dpr));
        canvas.height = Math.max(1, Math.floor(r.height * dpr));
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    window.addEventListener('resize', resize);

    function isPlaying() {
        const btn = document.getElementById('btn-play');
        return btn && btn.dataset.state === 'play';
    }

    function colors() {
        const css = getComputedStyle(document.documentElement);
        return {
            red: (css.getPropertyValue('--red') || '#e63946').trim() || '#e63946',
            redDark: (css.getPropertyValue('--red-dark') || '#a4161a').trim() || '#a4161a',
        };
    }

    function drawBars(w, h, playing) {
        const N = 28;
        const bw = w / N;
        const c = colors();
        for (let i = 0; i < N; i++) {
            const phase = playing ? t * 0.06 : 0;
            const v = playing
                ? (Math.sin(i * 0.45 + phase) * 0.4 + Math.sin(i * 0.13 + phase * 1.7) * 0.35 + 0.55)
                : 0.18 + Math.sin(i * 0.3) * 0.04;
            const bh = Math.max(3, Math.min(1, Math.abs(v)) * h * 0.9);
            const grad = ctx.createLinearGradient(0, h - bh, 0, h);
            grad.addColorStop(0, c.red);
            grad.addColorStop(1, c.redDark);
            ctx.fillStyle = grad;
            ctx.fillRect(i * bw + 2, h - bh, bw - 4, bh);
        }
    }

    function drawWave(w, h, playing) {
        const c = colors();
        ctx.lineWidth = 2.5;
        ctx.strokeStyle = c.red;
        ctx.beginPath();
        for (let x = 0; x <= w; x += 2) {
            const phase = playing ? t * 0.05 : 0;
            const y = h / 2 + Math.sin(x * 0.025 + phase) * h * 0.25
                    + (playing ? Math.sin(x * 0.08 + phase * 2.3) * h * 0.12 : 0);
            if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        }
        ctx.stroke();
    }

    function drawRadial(w, h, playing) {
        const c = colors();
        const cx = w / 2, cy = h / 2;
        const baseR = Math.min(w, h) * 0.18;
        const N = 56;
        for (let i = 0; i < N; i++) {
            const a = (i / N) * Math.PI * 2;
            const phase = playing ? t * 0.07 : 0;
            const len = playing
                ? (Math.sin(i * 0.5 + phase) * 0.5 + 0.5) * baseR * 1.4
                : baseR * 0.25;
            const x1 = cx + Math.cos(a) * baseR;
            const y1 = cy + Math.sin(a) * baseR;
            const x2 = cx + Math.cos(a) * (baseR + len);
            const y2 = cy + Math.sin(a) * (baseR + len);
            ctx.strokeStyle = i % 2 ? c.red : c.redDark;
            ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.stroke();
        }
    }

    const dots = Array.from({ length: 55 }, () => ({
        x: Math.random(), y: Math.random(),
        vx: (Math.random() - 0.5) * 0.0025,
        vy: (Math.random() - 0.5) * 0.0025,
        r: 1 + Math.random() * 2.5,
        seed: Math.random() * 10,
    }));
    function drawDots(w, h, playing) {
        const c = colors();
        for (const d of dots) {
            if (playing) {
                d.x += d.vx; d.y += d.vy;
                if (d.x < 0 || d.x > 1) d.vx *= -1;
                if (d.y < 0 || d.y > 1) d.vy *= -1;
            }
            const pulse = playing ? (Math.sin(t * 0.06 + d.seed) * 0.5 + 0.5) : 0.3;
            ctx.fillStyle = c.red;
            ctx.globalAlpha = 0.25 + pulse * 0.7;
            ctx.beginPath();
            ctx.arc(d.x * w, d.y * h, d.r * (0.5 + pulse * 0.9), 0, Math.PI * 2);
            ctx.fill();
        }
        ctx.globalAlpha = 1;
    }

    let lastW = 0, lastH = 0;
    function frame() {
        const r = wrap.getBoundingClientRect();
        const w = r.width, h = r.height;
        if (w !== lastW || h !== lastH) { resize(); lastW = w; lastH = h; }
        ctx.clearRect(0, 0, w, h);
        const playing = isPlaying();
        if (playing) t++;
        if (mode === 0) drawBars(w, h, playing);
        else if (mode === 1) drawWave(w, h, playing);
        else if (mode === 2) drawRadial(w, h, playing);
        else drawDots(w, h, playing);
        requestAnimationFrame(frame);
    }

    wrap.addEventListener('click', () => {
        mode = (mode + 1) % NUM_MODES;
        localStorage.setItem('music-viz-mode', String(mode));
    });

    requestAnimationFrame(frame);
})();

// ============ VEHICLE HEALTH ============
function setHealth(el, level) {
    if (!el) return;
    el.classList.remove('health-warn', 'health-crit');
    if (level === 'warn') el.classList.add('health-warn');
    else if (level === 'crit') el.classList.add('health-crit');
}

function applyHealthHighlights({ direct, inferred, metadata, metrics }) {
    const coolant = direct.coolant_temp_c;
    setHealth(
        document.getElementById('box-coolant'),
        coolant == null ? null : coolant >= 105 ? 'crit' : coolant >= 100 ? 'warn' : null
    );

    const stft = metrics.SHORT_FUEL_TRIM_1?.value;
    const ltft = metrics.LONG_FUEL_TRIM_1?.value;
    const stftLevel = stft == null ? null : Math.abs(stft) >= 15 ? 'crit' : Math.abs(stft) >= 10 ? 'warn' : null;
    const ltftLevel = ltft == null ? null : Math.abs(ltft) >= 15 ? 'crit' : Math.abs(ltft) >= 10 ? 'warn' : null;
    setHealth(document.getElementById('v-stft')?.closest('.metric-box'), stftLevel);
    setHealth(document.getElementById('v-ltft')?.closest('.metric-box'), ltftLevel);

    const voltage = direct.adapter_voltage_v;
    const battLevel = voltage == null ? null
        : (direct.rpm > 0 && voltage < 13) ? 'warn'
        : voltage < 11.8 ? 'crit'
        : null;
    setHealth(document.getElementById('obd-voltage')?.closest('.metric-box'), battLevel);

    const obdContent = document.getElementById('obd-content');
    if (obdContent) {
        const stale = metadata.dynamic_stale && (metadata.dynamic_stale_age_s || 0) > 3;
        obdContent.classList.toggle('obd-stale', !!stale);
    }
}

// ============ VIN HELPERS ============
const VIN_WMI = {
    '8AD': 'Peugeot/Citroën Brasil',
    '935': 'Citroën Brasil',
    '936': 'Peugeot Brasil',
    '8AF': 'Peugeot/Citroën',
    '9BW': 'Volkswagen Brasil',
    '9BG': 'GM Brasil',
    '9BD': 'Fiat Brasil',
    '9BF': 'Ford Brasil',
    'VF7': 'Citroën France',
    'VF3': 'Peugeot France',
    '1G1': 'Chevrolet USA',
    'WVW': 'Volkswagen Germany',
    'WBA': 'BMW',
    'WDB': 'Mercedes-Benz',
    'JHM': 'Honda Japan',
    'JT': 'Toyota Japan',
};

function decodeVIN(vin) {
    if (!vin || vin.length < 3) return null;
    const wmi3 = vin.slice(0, 3).toUpperCase();
    const wmi2 = vin.slice(0, 2).toUpperCase();
    return VIN_WMI[wmi3] || VIN_WMI[wmi2] || null;
}

initVehicleHelp();
