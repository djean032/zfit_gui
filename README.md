# ZScan Studio

ZScan Studio is a GUI application for Z-scan data collection and fitting workflows.

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)

## Setup

Install core dependencies:

```bash
uv sync
```

Install with hardware support (NI-DAQ):

```bash
uv sync --extra hardware
```

## Run

Preferred CLI entrypoint:

```bash
uv run zscan-studio
```

If your shell exports a custom `LD_LIBRARY_PATH`, prefer the command above. It uses
the package launcher, which bootstraps Qt library paths to avoid system Qt/PySide6
version conflicts.

Compatibility launcher:

```bash
uv run python app.py
```

## Repository Layout

- `src/zscan_studio/`: application package
- `scripts/`: utility conversion/config scripts
- `data/examples/`: example input files
- `tests/`: automated tests

## Development

### Qt resources

Splash/assets are bundled via Qt resources. If you change files referenced by
`src/zscan_studio/resources.qrc`, regenerate the Python resource module:

```bash
uv run pyside6-rcc src/zscan_studio/resources.qrc -o src/zscan_studio/resources_rc.py
```

Run linting:

```bash
uv run ruff check .
```

Run formatting check:

```bash
uv run black --check .
```

Run tests:

```bash
uv run pytest
```

## Windows Packaging

For PyInstaller + Inno Setup release steps, see `docs/packaging-windows.md`.

For release process steps, see `docs/release-checklist.md`.
