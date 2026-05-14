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
