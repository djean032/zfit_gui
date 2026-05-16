# PLANS.md

This document tracks active technical plans for ZScan Studio.

## Current State

- Project migrated to `src/zscan_studio` package layout.
- `uv` + `pyproject.toml` workflow in place.
- Splash image currently launches successfully.
- Baseline tests and lint/format tooling are active.

## Near-Term Plan

### 1) Qt Native Resource Bundling [done]

Goal: stop loading splash/assets by filesystem path and move to Qt resource URIs.

Steps:

1. [done] Move splash asset into package assets, e.g. `src/zscan_studio/assets/images/splash.png`.
2. [done] Create `src/zscan_studio/resources.qrc` with aliases/prefixes.
3. [done] Generate `src/zscan_studio/resources_rc.py` with `pyside6-rcc`.
4. [done] Import `zscan_studio.resources_rc` in startup path.
5. [done] Load splash via `QPixmap(":/images/splash.png")`.
6. [done] Add/update docs for regenerating resources after asset updates.

Validation:

- `uv run zscan-studio`
- `python app.py`
- `uv run ruff check .`
- `uv run pytest`

### 2) UI Module Decomposition (Refactor-Only) [in progress]

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

Status notes:

- [done] Initial extraction exists in `ui_builders.py`, `ui_components.py`, and `workers.py`.
- [done] Split tab builders into `ui/tabs/config_tab.py`, `ui/tabs/data_tab.py`, and `ui/tabs/fitting_tab.py` (with `ui_builders.py` as compatibility facade).
- [done] Split workers into `workers/experiment_worker.py` and `workers/fit_worker.py` (with `workers/__init__.py` export facade).
- [done] Added `ui/main_window.py` and moved `GUI` class from `main.py` in a behavior-preserving pass (with `main.py` retained as a compatibility wrapper).
- [in progress] Introduce `services/io_service.py` and `services/fit_service.py`, then migrate non-UI logic incrementally.
- [done] Added `services/io_service.py` and moved TOML load/save, CSV load, and fit-result CSV export helpers behind service functions.
- [done] Added `services/fit_service.py` and moved fit-input preparation branching out of `ui/main_window.py` into `prepare_fit_inputs`.
- [done] Moved fit-file parsing/validation helpers for single and multi-file modes into `services/fit_service.py`.
- [done] Moved fit-result data preparation and parameter-row formatting into `services/fit_service.py`.
- [done] Migrated fit/file dialog orchestration in `ui/main_window.py` into thin helper adapters.
- [in progress] Continue shrinking `ui/main_window.py` by extracting additional non-UI workflow branches.
- [done] Extracted data-preview/stat/table formatting and measurement-to-dataset shaping into `services/data_service.py`.
- [todo] Continue reducing `main.py` responsibilities while preserving behavior.

### 3) Hardware Boundary Hardening [done]

Goal: keep non-hardware flows stable on machines without NI-DAQ/stage hardware.

Actions:

- [done] Keep hardware imports lazy where possible.
- [done] Improve error messages when hardware not present.
- [done] Add tests that ensure non-hardware modules import and run.

### 4) UI/UX Friendliness Improvements (Behavior-Preserving First Pass) [in progress]

Goal: reduce user error and speed up common workflows without changing core scientific behavior.

Phase 1: Input safety + action gating [done]

- [done] Attach validators to numeric fields (laser/sample/z/fitting params).
- [done] Add inline invalid-state hints (field border + helper text), and avoid modal error spam for basic input mistakes.
- [done] Normalize button enable/disable rules by fitting mode (especially `Run Fit` in `Current Data` mode).

Phase 2: Workflow clarity [todo]

- [done] Fix save/export path handling so user-selected destinations are honored.
- [done] Improve operation feedback with messages that state both outcome and next action.
- [done] Tighten tab helper copy so each tab starts with one clear, task-oriented sentence.

Phase 3: Accessibility + efficiency [done]

- [done] Add keyboard shortcuts for key actions (Run/Stop/Save/Load/Run Fit).
- [done] Ensure focus order and Enter-key behavior are predictable across tabs.

Validation:

- Manual smoke flow: fresh launch -> configure -> preview -> run/stop experiment -> save/load data -> fit in all 3 modes.
- `uv run ruff check .`
- `uv run black --check .`
- `uv run pytest`
- `uv run zscan-studio`
- `python app.py`

## Notes

- Keep this file updated when priorities or sequencing changes.
