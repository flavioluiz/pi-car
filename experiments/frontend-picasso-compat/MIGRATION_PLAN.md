# PiCASSO Compat Migration Plan

## Goal

Migrate the current frontend to the `experiments/frontend-picasso-compat/` structure with the lowest possible integration risk, preserving:

- current backend endpoints
- current `frontend/static/js/app.js` data flow
- current Raspberry Pi runtime constraints
- existing working features in Music, GPS, Vehicle and SDR Radio

The objective is not a visual rewrite in isolation. The objective is a controlled replacement of the current frontend shell and markup while keeping the system behavior stable on the first real test.

## Migration Strategy

Use a compatibility-first migration.

Do not start by rewriting backend logic or changing APIs.

Do not start by replacing everything at once in a single unstructured pass.

Instead:

1. Keep the existing backend and polling/update loop intact.
2. Port the `compat` markup into the real frontend in small, testable steps.
3. Preserve existing ids, classes and DOM hooks expected by `frontend/static/js/app.js`.
4. Only after the UI is stable, refactor JS/CSS internals if needed.

This is the safest path to avoid first-test regressions.

## Current Assets

Reference sources:

- Compat prototype:
  - [index.html](/Users/flavioribeiro/github/pi-car/experiments/frontend-picasso-compat/index.html)
  - [styles.css](/Users/flavioribeiro/github/pi-car/experiments/frontend-picasso-compat/styles.css)
  - [app.js](/Users/flavioribeiro/github/pi-car/experiments/frontend-picasso-compat/app.js)
- Current production frontend:
  - [frontend/templates/index.html](/Users/flavioribeiro/github/pi-car/frontend/templates/index.html)
  - [frontend/static/css/style.css](/Users/flavioribeiro/github/pi-car/frontend/static/css/style.css)
  - [frontend/static/js/app.js](/Users/flavioribeiro/github/pi-car/frontend/static/js/app.js)
- OBD reference:
  - [OBSERVACOES_OBD_C3_PICASSO_2013.md](/Users/flavioribeiro/github/pi-car/experiments/obd-macos/OBSERVACOES_OBD_C3_PICASSO_2013.md)

## Migration Principles

### 1. Preserve working hooks

Any element currently consumed by `frontend/static/js/app.js` must continue to exist during the migration unless the JS is updated in the same commit.

Examples:

- `ind-music`
- `ind-gps`
- `ind-obd`
- `ind-radio`
- `music-title`
- `music-artist`
- `progress-fill`
- `btn-play`
- `queue-list`
- `artists-list`
- `playlists-list`
- `search-input`
- `virtual-keyboard`
- `search-results`
- `obd-speed`
- `obd-rpm`
- `obd-coolant`
- `obd-consumption`
- `obd-trip-distance`
- `gps-speed`
- `gps-sats`
- `gps-coords`
- `radio-freq`
- `radio-mode`
- `radio-vol`
- `favorites-list`

### 2. Separate visual migration from behavioral changes

Do not redesign behavior and layout in the same step if it can be avoided.

Examples of behavior changes that should be deferred:

- changing polling intervals
- changing endpoint contracts
- changing OBD derivation logic
- changing SDR spectrum update flow

### 3. Keep one rollback path

At every stage, the frontend must still have a fast rollback path:

- restore previous template
- restore previous CSS include
- restore previous panel shell

### 4. Optimize for Raspberry Pi first

The target is not desktop web.

Primary envelope:

- `800x480`
- no scroll on main views
- low GPU/CPU overhead
- stable rendering under continuous DOM updates

## Recommended Implementation Phases

## Phase 0. Freeze Scope

Before changing production files:

- freeze the target visual scope for the first migration
- decide what is in v1 and what is postponed

Recommended v1:

- new PiCASSO shell
- new top bar
- new sidebar
- compatible panel markup
- Settings reduced to Themes only
- Vehicle with internal tabs
- Music/Radio structure compatible with current JS

Postpone from v1:

- deep JS refactors
- dynamic theme persistence in backend
- large spectrum redesign
- advanced animation
- nonessential micro-interactions

## Phase 1. Compatibility Audit

Create a hard mapping table of current frontend hooks.

For each element used by `frontend/static/js/app.js`, record:

- DOM id/class
- which endpoint or function updates it
- whether the compat markup already contains it
- whether the final production template will preserve it unchanged

Deliverable:

- a checklist file or table inside the migration branch

This prevents silent regressions where one missing id breaks a feature without obvious console feedback on the Pi.

## Post-Review Guardrails

The compatibility migration introduced two classes of issues that must now be treated as hard rules:

1. Brand assets used by the production template must live under `frontend/static/` and be referenced with `url_for('static', ...)`.
2. New dashboard fields must not be added unless the current backend already exposes the corresponding data or the JS patch that fills them ships in the same commit.

Examples of fields that require explicit backend support before appearing in production:

- average speed on Home
- queue length in Music status
- OBD standard, O2 sensor details, calibration ids and CVN

If a value is not available yet, prefer:

- hiding the field
- renaming it to match an available metric
- or rendering a clear `Not available` state instead of stale/static placeholder text

## Phase 2. Shell Replacement

Replace only the top-level shell in the real frontend:

- header/topbar
- sidebar/nav
- panel container structure

Do not yet fully replace internal content of every panel if that adds risk.

Goal:

- preserve `panel-music`, `panel-vehicle`, `panel-gps`, `panel-radio`
- preserve panel activation logic
- preserve music/radio subtab behavior

Acceptance criteria:

- tab switching works
- clock still updates
- status indicators still toggle
- no broken panel visibility

## Phase 3. Music Migration

Port `Music` first because it is the best balance of:

- already structured
- visually important
- behavior easy to validate

Required compatibility areas:

- `music-playing`
- `music-queue`
- `music-artists`
- `music-playlists`
- `music-search`

Required actions to preserve:

- play / pause
- prev / next
- restart
- shuffle
- repeat
- volume
- queue play/remove/clear
- artist play/add
- playlist play/add
- search/add/play
- virtual keyboard hooks

Acceptance criteria:

- all buttons produce the same requests as before
- now playing updates continuously
- queue mutations reflect visually
- search still works with keyboard

## Phase 4. GPS Migration

Port GPS after Music.

Required compatibility:

- `gps-content`
- `gps-disconnected`
- `gps-speed`
- `gps-sats`
- `gps-coords`

Rules:

- keep GPS panel lightweight
- do not prioritize map complexity over readability
- preserve disconnected state behavior

Acceptance criteria:

- connected/disconnected switching works
- coordinates update correctly
- no overflow at `800x480`

## Phase 5. Vehicle Migration

Vehicle is the highest-risk panel after Radio because:

- it mixes direct values and inferred values
- it may expose missing-data situations
- it is likely to receive future growth

Recommended structure already defined in `compat`:

- `Drive`
- `Engine`
- `Fuel & O2`
- `Diagnostics`
- `Vehicle ID`
- `Advanced`

Implementation rule:

Keep `Drive` wired to the existing current ids first.

Only after `Drive` is stable, progressively feed:

- `Engine`
- `Fuel & O2`
- `Diagnostics`
- `Vehicle ID`
- `Advanced`

### Vehicle data mapping

#### Drive

Use current working live values:

- `obd-speed`
- `obd-rpm`
- `obd-coolant`
- `obd-consumption`
- `obd-consumption-unit`
- `obd-trip-distance`
- `obd-trip-fuel`
- `obd-trip-average`
- `obd-voltage`
- `obd-alerts`
- `gauges-grid`

#### Engine

Populate from available documented PIDs:

- `0104` Calculated engine load
- `010B` MAP
- `010E` Timing advance
- `010F` Intake air temperature
- `0111` Throttle position
- `0103` Fuel system status

#### Fuel & O2

Populate from:

- `0106` STFT B1
- `0107` LTFT B1
- `0114` O2 B1S1
- `0115` O2 B1S2
- `0113` O2 sensors present

Display clearly that instant consumption is inferred, not directly read.

#### Diagnostics

Populate from:

- `0101` MIL/monitor status
- `03` active DTCs
- `07` pending DTCs
- `0121` distance with MIL
- `011C` OBD standard
- adapter metadata
- baudrate / protocol / ATRV

#### Vehicle ID

Populate from:

- `0902` VIN
- `0904` Calibration ID
- `0906` CVN

#### Advanced

Keep `Mode 06` out of realtime loop.

Only query on demand.

Never make `Mode 06` part of the high-frequency update path.

Acceptance criteria:

- `Drive` behaves identically to the old vehicle screen for core live data
- missing PIDs fail gracefully
- no blank panel if a subset of data is unavailable

## Phase 6. Radio Migration

Radio is the most sensitive UI after Vehicle because:

- it has tuner, spectrum, presets and favorites
- it includes more stateful actions
- spectrum can be performance-sensitive

Required compatibility:

- `radio-content`
- `radio-disconnected`
- `radio-tuner`
- `radio-spectrum`
- `radio-presets`
- `radio-favorites`
- `radio-freq`
- `radio-mode`
- `signal-bars`
- `signal-dbm`
- `freq-input`
- `mode-fm`
- `mode-am`
- `radio-play-btn`
- `radio-play-icon`
- `radio-vol`
- `favorites-list`

Important rule:

Keep spectrum logic and visual update cost under control.

If performance drops on the Pi, reduce refresh complexity before changing the rest of the radio UI.

Acceptance criteria:

- tuner actions work
- play/stop works
- presets render
- favorites add/remove render
- spectrum does not freeze the UI

## Phase 7. Settings to Themes Only

The current product does not expose real configurable settings yet.

Therefore:

- `Settings` should remain intentionally minimal
- only `Themes` should be shown in v1

Recommended themes:

- `PiCASSO Red`
- `Signal Cyan`
- `Amber Dusk`

Rules:

- theme switching is frontend-only in v1
- persistence can remain local first
- no fake settings beyond themes

This avoids misleading UI and reduces maintenance burden.

## Phase 8. CSS Consolidation

After functional parity is achieved:

- merge compat CSS into the production stylesheet in controlled blocks
- avoid a single monolithic paste if possible

Suggested order:

1. tokens / colors / theme variables
2. shell / nav / topbar
3. shared cards / typography / grids
4. music
5. gps
6. vehicle
7. radio
8. settings/themes

Keep old CSS available until the new panel is verified.

## Phase 9. JS Consolidation

Only after markup is stable:

- compare `experiments/frontend-picasso-compat/app.js` against `frontend/static/js/app.js`
- merge only what is needed for panel navigation and theme switching

Do not copy the compat JS wholesale over production JS.

Reason:

- production JS already contains the real endpoint logic
- replacing it blindly is the fastest way to introduce regressions

Recommended approach:

- keep production `app.js` as the source of truth
- transplant only:
  - shell navigation changes
  - optional theme switching logic
  - panel mapping helpers if needed

## Critical Attention Points

## 1. Missing DOM hooks

Most likely regression class.

Symptom:

- panel renders but one feature silently stops updating

Mitigation:

- maintain a hook checklist
- validate all ids used by JS exist in the final template

## 2. `select` vs `button` mismatches

Example:

- `obd-fuel-select`
- spectrum config controls

If the JS expects `.value`, the DOM element must actually be a `select` or compatible input.

## 3. Scroll appearing in `800x480`

The prototype goal is no-scroll main views.

Mitigation:

- check every panel in `800x480`
- especially `Vehicle`, `Radio`, `Search`, `Presets`, `Favorites`

## 4. Performance regression from spectrum or excessive DOM churn

Mitigation:

- keep complex visual updates localized
- avoid unnecessary re-render of large lists on every polling cycle
- avoid expensive shadows/filters in frequently updated nodes

## 5. Theme collisions

When themes are introduced:

- only theme variables should change
- layout geometry should not depend on theme

Otherwise a theme change may unexpectedly break spacing or contrast.

## 6. OBD missing-data behavior

This ECU does not expose everything.

Do not assume availability of:

- `MAF`
- `Fuel level`
- `Engine fuel rate`
- ethanol percentage

Mitigation:

- label inferred values explicitly
- show unavailable values gracefully
- never leave broken placeholders

## 7. Technical data overload

The new vehicle tabs solve this, but only if `Drive` remains glanceable.

Rule:

- `Drive` should stay operational
- deep data goes to technical tabs

## First-Test Checklist

Run this before testing in the car or on the Raspberry Pi:

### UI structure

- all main tabs open correctly
- all music subtabs open correctly
- all radio subtabs open correctly
- all vehicle subtabs open correctly
- no page scroll in `800x480`

### Music

- title updates
- artist updates
- progress updates
- play/pause button changes state
- prev/next work
- queue tab renders
- artists tab renders with action buttons
- playlists tab renders with action buttons
- search tab renders keyboard/results

### GPS

- connected state visible
- disconnected state visible
- speed/sats/coords update

### Vehicle

- `Drive` live values update
- `Fuel Mode` selector remains functional
- alerts render
- no crash when some PID is absent
- technical tabs open without overflow

### Radio

- connected/disconnected state works
- tuner values update
- mode switch reflects state
- volume updates
- presets render
- favorites render
- spectrum panel opens without layout break

### Themes

- theme switch applies immediately
- theme choice persists locally
- contrast remains acceptable in all themes

## Regression Checklist Against Current Frontend

Before declaring migration ready, confirm that nothing currently working was lost:

- music playback control
- queue manipulation
- artist browsing
- playlist playback
- search and keyboard
- GPS visibility
- OBD core live values
- radio tuning
- radio mode switching
- radio favorites
- disconnected states
- clock
- status indicators

## Recommended Delivery Sequence

If implementing now, I would do it in this exact order:

1. Port compat shell into `frontend/templates/index.html`
2. Preserve current production JS and verify main panel switching
3. Port Music markup and verify all music actions
4. Port GPS markup
5. Port Vehicle `Drive`
6. Port Vehicle technical tabs
7. Port Radio tuner
8. Port Radio spectrum/presets/favorites
9. Port Themes-only Settings
10. Clean CSS and remove dead legacy markup

This sequence minimizes the chance of getting stuck with a half-migrated frontend that looks better but no longer controls the system reliably.

## Suggested Deliverables for the Migration Branch

- updated `frontend/templates/index.html`
- updated `frontend/static/css/style.css`
- minimally changed `frontend/static/js/app.js`
- optional `frontend/static/css/themes.css` if separation helps
- short migration notes in repo docs

## Final Recommendation

Do not treat this migration as a pure redesign.

Treat it as:

- a DOM compatibility exercise
- a layout replacement
- a low-regression embedded UI rollout

If that discipline is maintained, the first real test is much more likely to succeed without breaking Music, OBD, GPS or Radio behavior.
