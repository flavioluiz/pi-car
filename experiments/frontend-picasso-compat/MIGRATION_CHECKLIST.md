# PiCASSO Compat Migration Checklist

Use this checklist during the real migration from the current frontend to the PiCASSO compat frontend.

Mark items only after verifying the actual behavior.

## 1. Pre-Migration

- [x] Create a dedicated migration branch.
- [x] Keep the current production frontend restorable in one commit.
- [x] Confirm target runtime is still `800x480`.
- [x] Confirm migration scope for v1:
  - [x] new shell
  - [x] Music
  - [x] GPS
  - [x] Vehicle with tabs
  - [x] Radio
  - [x] Themes-only Settings
- [x] Freeze nonessential design changes until after first live test.

## 2. DOM Hook Audit

- [x] Confirm all current JS-critical ids exist in the migrated template.
- [ ] Confirm every new field added by the new UI is backed by real data or explicitly marked unavailable.
- [ ] Confirm production logos are served from `frontend/static/logos` via `url_for('static', ...)`.
- [x] Validate status indicators:
  - [x] `ind-music`
  - [x] `ind-gps`
  - [x] `ind-obd`
  - [x] `ind-radio`
- [x] Validate Music hooks:
  - [x] `music-title`
  - [x] `music-artist`
  - [x] `btn-play`
  - [x] `btn-shuffle`
  - [x] `btn-repeat`
  - [x] `volume-display`
  - [x] `progress-bar`
  - [x] `progress-fill`
  - [x] `time-elapsed`
  - [x] `time-duration`
  - [x] `queue-list`
  - [x] `artists-list`
  - [x] `playlists-list`
  - [x] `search-input`
  - [x] `virtual-keyboard`
  - [x] `search-results`
- [x] Validate Vehicle hooks:
  - [x] `obd-content`
  - [x] `obd-disconnected`
  - [x] `obd-error`
  - [x] `obd-error-text`
  - [x] `obd-vehicle-name`
  - [x] `obd-connection-line`
  - [x] `obd-fuel-select`
  - [x] `obd-alerts`
  - [x] `obd-speed`
  - [x] `obd-rpm`
  - [x] `obd-coolant`
  - [x] `obd-consumption`
  - [x] `obd-consumption-unit`
  - [x] `obd-trip-distance`
  - [x] `obd-trip-fuel`
  - [x] `obd-trip-average`
  - [x] `obd-voltage`
  - [x] `gauges-grid`
- [x] Validate GPS hooks:
  - [x] `gps-content`
  - [x] `gps-disconnected`
  - [x] `gps-speed`
  - [x] `gps-sats`
  - [x] `gps-coords`
- [x] Validate Radio hooks:
  - [x] `radio-content`
  - [x] `radio-disconnected`
  - [x] `radio-mode`
  - [x] `radio-freq`
  - [x] `signal-bars`
  - [x] `signal-dbm`
  - [x] `freq-input`
  - [x] `mode-fm`
  - [x] `mode-am`
  - [x] `radio-play-btn`
  - [x] `radio-play-icon`
  - [x] `radio-vol`
  - [x] `spectrogram`
  - [x] `spectrum-mode-indicator`
  - [x] `spectrum-start`
  - [x] `spectrum-center`
  - [x] `spectrum-end`
  - [x] `spectrum-freq-display`
  - [x] `spectrum-update-interval`
  - [x] `spectrum-integration-time`
  - [x] `spectrum-max-rows`
  - [x] `spectrum-db-smoothing`
  - [x] `spectrum-db-margin`
  - [x] `spectrum-min-range`
  - [x] `fm-presets`
  - [x] `airport-presets-sbsj`
  - [x] `airport-presets-sbgr`
  - [x] `favorites-list`

## 3. Shell Migration

- [x] Port topbar into production template.
- [x] Port sidebar/navigation into production template.
- [x] Preserve main panel ids:
  - [x] `panel-music`
  - [x] `panel-vehicle`
  - [x] `panel-gps`
  - [x] `panel-radio`
- [ ] Confirm panel switching still works.
- [ ] Confirm clock still updates.
- [ ] Confirm no hidden panel remains focusable/clickable.

## 4. Music Migration

- [x] Port `music-tabs`, `music-tab`, `music-panel` structure.
- [x] Port `Now Playing` layout.
- [x] Port `Queue` browser layout.
- [x] Port `Artists` browser layout.
- [x] Port `Playlists` browser layout.
- [x] Port `Search` layout.
- [ ] Confirm music subtab switching works.
- [ ] Confirm title updates.
- [ ] Confirm artist updates.
- [ ] Confirm progress updates.
- [ ] Confirm play/pause works.
- [ ] Confirm prev/next works.
- [ ] Confirm restart works if still exposed.
- [ ] Confirm shuffle state updates.
- [ ] Confirm repeat state updates.
- [ ] Confirm volume updates.
- [ ] Confirm queue play/remove/clear works.
- [ ] Confirm artists play/add works.
- [ ] Confirm playlists play/add works.
- [ ] Confirm search results play/add works.
- [ ] Confirm virtual keyboard still renders and works.

## 5. GPS Migration

- [x] Port GPS panel layout.
- [ ] Confirm connected state renders.
- [ ] Confirm disconnected state renders.
- [ ] Confirm speed updates.
- [ ] Confirm satellites update.
- [ ] Confirm coordinates update.
- [ ] Confirm GPS panel fits in `800x480`.

## 6. Vehicle Migration

### Drive

- [x] Port `Drive` tab as default.
- [ ] Confirm `obd-speed` updates.
- [ ] Confirm `obd-rpm` updates.
- [ ] Confirm `obd-coolant` updates.
- [ ] Confirm `obd-consumption` updates.
- [ ] Confirm `obd-trip-distance` updates.
- [ ] Confirm `obd-trip-fuel` updates.
- [ ] Confirm `obd-trip-average` updates.
- [ ] Confirm `obd-voltage` updates.
- [ ] Confirm `obd-alerts` render correctly.
- [ ] Confirm `obd-fuel-select` still behaves correctly.
- [ ] Confirm `gauges-grid` still renders technical data.
- [ ] Confirm `Drive` fits in `800x480` without scroll.

### Engine

- [x] Populate/validate (markup structure in place):
  - [ ] `0104` load
  - [ ] `010B` MAP
  - [ ] `010E` timing advance
  - [ ] `010F` intake air temp
  - [ ] `0111` throttle position
  - [ ] `0103` fuel system status

### Fuel & O2

- [x] Populate/validate (markup structure in place):
  - [ ] `0106` STFT
  - [ ] `0107` LTFT
  - [ ] `0114` O2 B1S1
  - [ ] `0115` O2 B1S2
  - [ ] `0113` O2 sensors present
- [x] Explicitly label inferred consumption as estimated.

### Diagnostics

- [x] Validate (markup structure in place):
  - [ ] `0101` MIL / monitors
  - [ ] `03` active DTCs
  - [ ] `07` pending DTCs
  - [ ] `0121` distance with MIL
  - [ ] `011C` OBD standard
  - [ ] adapter/baud/protocol info

### Vehicle ID

- [x] Validate (markup structure in place):
  - [ ] VIN `0902`
  - [ ] Calibration ID `0904`
  - [ ] CVN `0906`

### Advanced

- [x] Keep `Mode 06` outside high-frequency realtime loop.
- [x] Confirm no expensive polling was added accidentally.

## 7. Radio Migration

- [x] Port `radio-tab` and `radio-panel` structure.
- [x] Port tuner layout.
- [x] Port spectrum layout.
- [x] Port presets layout.
- [x] Port favorites layout.
- [ ] Confirm radio subtab switching works.
- [ ] Confirm connected/disconnected switching works.
- [ ] Confirm frequency updates.
- [ ] Confirm mode updates.
- [ ] Confirm signal bars update.
- [ ] Confirm volume updates.
- [ ] Confirm tuner controls work.
- [ ] Confirm presets render.
- [ ] Confirm favorites render.
- [ ] Confirm spectrum does not freeze the UI.

## 8. Themes

- [x] Keep Settings restricted to Themes only.
- [ ] Confirm `PiCASSO Red` works.
- [ ] Confirm `Signal Cyan` works.
- [ ] Confirm `Amber Dusk` works.
- [ ] Confirm theme switch applies immediately.
- [ ] Confirm theme persistence works if enabled.
- [ ] Confirm themes do not affect layout geometry.
- [ ] Confirm all themes retain acceptable contrast.

## 9. CSS and Performance

- [ ] Remove duplicate/obsolete CSS only after the new UI is stable.
- [ ] Confirm no main panel scroll on `800x480`.
- [ ] Confirm no clipped controls in Music.
- [ ] Confirm Vehicle `Drive` still fits.
- [ ] Confirm Radio tabs still fit.
- [ ] Confirm no obvious GPU-heavy effect is hurting render stability.
- [ ] Confirm frequent updates do not cause flicker.

## 10. First Raspberry Pi Test

- [ ] Open frontend on target device.
- [ ] Confirm the app loads without missing assets.
- [ ] Confirm no obvious JS errors in console.
- [ ] Confirm Music live updates work.
- [ ] Confirm OBD live updates work.
- [ ] Confirm GPS live updates work.
- [ ] Confirm Radio live updates work.
- [ ] Confirm disconnected states still behave correctly.
- [ ] Confirm top bar indicators still reflect actual status.
- [ ] Confirm all major tabs are usable by touch.

## 11. First In-Car Test

- [ ] Engine off / ignition on behavior checked.
- [ ] Engine running behavior checked.
- [ ] OBD reconnect behavior checked.
- [ ] GPS startup latency checked.
- [ ] Music control during driving checked.
- [ ] Radio control during driving checked.
- [ ] Theme remains readable in car lighting.
- [ ] No critical interaction requires precision too high for touch.

## 12. Final Go / No-Go

- [ ] No critical feature from current frontend is missing.
- [ ] No panel is unusable in `800x480`.
- [ ] No blocking JS regression remains.
- [ ] No blocking OBD regression remains.
- [ ] No blocking Radio regression remains.
- [ ] Rollback path still available.

If any item above fails, do not call the migration ready.
