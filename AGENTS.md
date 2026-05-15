# AGENTS.md

This repository hosts **ZScan Studio**, a PySide6 desktop app for Z-scan data acquisition and fitting.

## Primary Agent Goals

- Keep the application launchable via both:
  - `uv run zscan-studio`
  - `python app.py`
- Prefer incremental, non-breaking refactors.
- Maintain compatibility with lab and non-lab environments.

## Project Structure

- `src/zscan_studio/`: main package
- `src/zscan_studio/main.py`: GUI app entry logic
- `src/zscan_studio/launcher.py`: environment/bootstrap launcher
- `src/zscan_studio/fit.py`: fitting utilities
- `src/zscan_studio/experiment.py`: acquisition workflow
- `src/zscan_studio/esp302.py`: stage control
- `scripts/`: data/config utility scripts
- `data/examples/`: sample CSV/TOML files
- `tests/`: non-hardware tests

## Environment and Dependencies

- Dependency manager: `uv`
- Project metadata: `pyproject.toml`
- Optional hardware extra: `hardware` (`nidaqmx`)
- Avoid introducing hard dependency on hardware libraries in import-time code paths used by tests.

## Coding Rules for Agents

- Follow existing typing/style patterns.
- Keep GUI behavior stable unless user asks for UX changes.
- For hardware-related code, fail gracefully and preserve non-hardware usability.
- Prefer package imports (`zscan_studio...`) over relative filesystem assumptions.

## Validation Checklist

Run after meaningful code changes:

```bash
uv run ruff check .
uv run black --check .
uv run pytest
```

For launch-sensitive changes, also verify:

```bash
uv run zscan-studio
python app.py
```

## Commit Guidance

- Keep commits scoped and reviewable.
- Use imperative, intent-based messages.
- Do not commit local logs, secrets, or machine-specific artifacts.
