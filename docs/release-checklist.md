# Release Checklist

Use this checklist for each tagged Windows release.

## 1) Pre-release verification

- Confirm version is updated in `pyproject.toml`.
- Run local checks:

```bash
uv run ruff check .
uv run black --check .
uv run pytest
```

- Build and test both app variants locally:

```bat
scripts\build_pyinstaller_standard.bat
scripts\build_pyinstaller_lab.bat
scripts\build_installers.bat
```

- Smoke test both installers:
  - install and launch Standard
  - install and launch Lab
  - verify uninstall works

## 2) Tag and push

- Create a semantic version tag (example: `v0.1.0`):

```bash
git tag v0.1.0
git push origin v0.1.0
```

- Pushing the tag triggers `.github/workflows/release-installers.yml`.

## 3) Verify GitHub release assets

- Confirm release page contains:
  - `ZScanStudio-Standard-Setup.exe`
  - `ZScanStudio-Lab-Setup.exe`
  - `SHA256SUMS.txt`
- Verify checksums file is present and matches the uploaded EXEs.
- Edit release notes to include install guidance:
  - Standard: for non-hardware users
  - Lab: for NI-DAQ/lab hardware users

## 4) Post-release sanity checks

- Download both installers from the release page.
- Validate each installer runs on a clean Windows profile.
- Share release URL with users.
