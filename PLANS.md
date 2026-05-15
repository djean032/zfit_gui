# PLANS.md

This document tracks active technical plans for ZScan Studio.

## Current State

- Project migrated to `src/zscan_studio` package layout.
- `uv` + `pyproject.toml` workflow in place.
- Splash image currently launches successfully.
- Baseline tests and lint/format tooling are active.

## Near-Term Plan

### 1) Qt Native Resource Bundling

Goal: stop loading splash/assets by filesystem path and move to Qt resource URIs.

Steps:

1. Move splash asset into package assets, e.g. `src/zscan_studio/assets/images/splash.png`.
2. Create `src/zscan_studio/resources.qrc` with aliases/prefixes.
3. Generate `src/zscan_studio/resources_rc.py` with `pyside6-rcc`.
4. Import `zscan_studio.resources_rc` in startup path.
5. Load splash via `QPixmap(":/images/splash.png")`.
6. Add/update docs for regenerating resources after asset updates.

Validation:

- `uv run zscan-studio`
- `python app.py`
- `uv run ruff check .`
- `uv run pytest`

### 2) UI Module Decomposition (Refactor-Only)

Goal: reduce size/complexity of `main.py` while preserving behavior.

Proposed split:

- `ui/main_window.py`
- `ui/tabs/config_tab.py`
- `ui/tabs/data_tab.py`
- `ui/tabs/fitting_tab.py`
- `workers/experiment_worker.py`
- `workers/fit_worker.py`
- `services/io_service.py`
- `services/fit_service.py`

Constraints:

- No user-facing behavior changes in first pass.
- Keep launch compatibility and existing defaults.

### 3) Hardware Boundary Hardening

Goal: keep non-hardware flows stable on machines without NI-DAQ/stage hardware.

Actions:

- Keep hardware imports lazy where possible.
- Improve error messages when hardware not present.
- Add tests that ensure non-hardware modules import and run.

## Notes

- Keep this file updated when priorities or sequencing changes.
