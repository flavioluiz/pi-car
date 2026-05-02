# PiCASSO Compat Migration Checklist

Use this checklist during the real migration from the current frontend to the PiCASSO compat frontend.

Mark items only after verifying the actual behavior.

## 1. Pre-Migration

- [ ] Create a dedicated migration branch.
- [ ] Keep the current production frontend restorable in one commit.
- [ ] Confirm target runtime is still `800x480`.
- [ ] Confirm migration scope for v1:
  - [ ] new shell
  - [ ] Music
  - [ ] GPS
  - [ ] Vehicle with tabs
  - [ ] Radio
  - [ ] Themes-only Settings
- [ ] Freeze nonessential design changes until after first live test.

## 2. DOM Hook Audit

- [ ] Confirm all current JS-critical ids exist in the migrated template.
- [ ] Validate status indicators:
  - [ ] `ind-music`
  - [ ] `ind-gps`
  - [ ] `ind-obd`
  - [ ] `ind-radio`
- [ ] Validate Music hooks:
  - [ ] `music-title`
  - [ ] `music-artist`
  - [ ] `btn-play`
  - [ ] `btn-shuffle`
  - [ ] `btn-repeat`
  - [ ] `volume-display`
  - [ ] `progress-bar`
  - [ ] `progress-fill`
  - [ ] `time-elapsed`
  - [ ] `time-duration`
  - [ ] `queue-list`
  - [ ] `artists-list`
  - [ ] `playlists-list`
  - [ ] `search-input`
  - [ ] `virtual-keyboard`
  - [ ] `search-results`
- [ ] Validate Vehicle hooks:
  - [ ] `obd-content`
  - [ ] `obd-disconnected`
  - [ ] `obd-error`
  - [ ] `obd-error-text`
  - [ ] `obd-vehicle-name`
  - [ ] `obd-connection-line`
  - [ ] `obd-fuel-select`
  - [ ] `obd-alerts`
  - [ ] `obd-speed`
  - [ ] `obd-rpm`
  - [ ] `obd-coolant`
  - [ ] `obd-consumption`
  - [ ] `obd-consumption-unit`
  - [ ] `obd-trip-distance`
  - [ ] `obd-trip-fuel`
  - [ ] `obd-trip-average`
  - [ ] `obd-voltage`
  - [ ] `gauges-grid`
- [ ] Validate GPS hooks:
  - [ ] `gps-content`
  - [ ] `gps-disconnected`
  - [ ] `gps-speed`
  - [ ] `gps-sats`
  - [ ] `gps-coords`
- [ ] Validate Radio hooks:
  - [ ] `radio-content`
  - [ ] `radio-disconnected`
  - [ ] `radio-mode`
  - [ ] `radio-freq`
  - [ ] `signal-bars`
  - [ ] `signal-dbm`
  - [ ] `freq-input`
  - [ ] `mode-fm`
  - [ ] `mode-am`
  - [ ] `radio-play-btn`
  - [ ] `radio-play-icon`
  - [ ] `radio-vol`
  - [ ] `spectrogram`
  - [ ] `spectrum-mode-indicator`
  - [ ] `spectrum-start`
  - [ ] `spectrum-center`
  - [ ] `spectrum-end`
  - [ ] `spectrum-freq-display`
  - [ ] `spectrum-update-interval`
  - [ ] `spectrum-integration-time`
  - [ ] `spectrum-max-rows`
  - [ ] `spectrum-db-smoothing`
  - [ ] `spectrum-db-margin`
  - [ ] `spectrum-min-range`
  - [ ] `fm-presets`
  - [ ] `airport-presets-sbsj`
  - [ ] `airport-presets-sbgr`
  - [ ] `favorites-list`

## 3. Shell Migration

- [ ] Port topbar into production template.
- [ ] Port sidebar/navigation into production template.
- [ ] Preserve main panel ids:
  - [ ] `panel-music`
  - [ ] `panel-vehicle`
  - [ ] `panel-gps`
  - [ ] `panel-radio`
- [ ] Confirm panel switching still works.
- [ ] Confirm clock still updates.
- [ ] Confirm no hidden panel remains focusable/clickable.

## 4. Music Migration

- [ ] Port `music-tabs`, `music-tab`, `music-panel` structure.
- [ ] Port `Now Playing` layout.
- [ ] Port `Queue` browser layout.
- [ ] Port `Artists` browser layout.
- [ ] Port `Playlists` browser layout.
- [ ] Port `Search` layout.
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

- [ ] Port GPS panel layout.
- [ ] Confirm connected state renders.
- [ ] Confirm disconnected state renders.
- [ ] Confirm speed updates.
- [ ] Confirm satellites update.
- [ ] Confirm coordinates update.
- [ ] Confirm GPS panel fits in `800x480`.

## 6. Vehicle Migration

### Drive

- [ ] Port `Drive` tab as default.
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

- [ ] Populate/validate:
  - [ ] `0104` load
  - [ ] `010B` MAP
  - [ ] `010E` timing advance
  - [ ] `010F` intake air temp
  - [ ] `0111` throttle position
  - [ ] `0103` fuel system status

### Fuel & O2

- [ ] Populate/validate:
  - [ ] `0106` STFT
  - [ ] `0107` LTFT
  - [ ] `0114` O2 B1S1
  - [ ] `0115` O2 B1S2
  - [ ] `0113` O2 sensors present
- [ ] Explicitly label inferred consumption as estimated.

### Diagnostics

- [ ] Validate:
  - [ ] `0101` MIL / monitors
  - [ ] `03` active DTCs
  - [ ] `07` pending DTCs
  - [ ] `0121` distance with MIL
  - [ ] `011C` OBD standard
  - [ ] adapter/baud/protocol info

### Vehicle ID

- [ ] Validate:
  - [ ] VIN `0902`
  - [ ] Calibration ID `0904`
  - [ ] CVN `0906`

### Advanced

- [ ] Keep `Mode 06` outside high-frequency realtime loop.
- [ ] Confirm no expensive polling was added accidentally.

## 7. Radio Migration

- [ ] Port `radio-tab` and `radio-panel` structure.
- [ ] Port tuner layout.
- [ ] Port spectrum layout.
- [ ] Port presets layout.
- [ ] Port favorites layout.
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

- [ ] Keep Settings restricted to Themes only.
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
