# Windows Packaging

This project ships two separate Windows installers:

- Standard: no NI hardware dependency (`nidaqmx` excluded)
- Lab: hardware-capable build (`nidaqmx` included)

## Prerequisites

- Windows machine
- Python and `uv`
- PyInstaller available in environment
- Inno Setup 6 installed (`ISCC.exe`)

If PyInstaller is not installed yet:

```bash
uv add --dev pyinstaller
```

## Build executables (onedir)

From repository root:

```bat
scripts\build_pyinstaller_standard.bat
scripts\build_pyinstaller_lab.bat
```

Expected outputs:

- `dist/ZScanStudio-Standard/ZScanStudio-Standard.exe`
- `dist/ZScanStudio-Lab/ZScanStudio-Lab.exe`

## Build installer EXEs

Compile both installers:

```bat
scripts\build_installers.bat
```

Expected outputs:

- `dist/installers/ZScanStudio-Standard-Setup.exe`
- `dist/installers/ZScanStudio-Lab-Setup.exe`

## Installer behavior

- Per-machine install (admin required)
- Start Menu shortcut always created
- Desktop shortcut offered as optional unchecked checkbox

## Validation checklist

Before publishing installers:

```bash
uv run ruff check .
uv run black --check .
uv run pytest
```

Runtime checks:

- Launch both EXEs from `dist/` before installer packaging
- Install and uninstall both setup EXEs on a clean user profile
- Confirm Standard flow works without hardware dependencies
- Confirm Lab flow works on hardware-ready environment
