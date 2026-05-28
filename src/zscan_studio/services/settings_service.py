from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import toml

DEFAULT_GLOBAL_SETTINGS: dict[str, dict[str, Any]] = {
    "acquisition": {
        "pretrigger_samples": 10,
        "posttrigger_samples": 140,
        "sample_rate_hz": 1_000_000.0,
        "trigger_source": "/Dev1/PFI0",
        "windows_per_position": 4,
        "read_timeout_s": 5.0,
        "max_retries_per_window": 4,
    }
}


def global_settings_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "ZScanStudio" / "settings.toml"
    return Path.home() / ".zscan_studio" / "settings.toml"


def load_global_settings() -> dict[str, dict[str, Any]]:
    path = global_settings_path()
    settings = _clone_defaults()
    if not path.exists():
        return settings

    try:
        loaded = toml.load(path)
    except Exception:
        return settings

    acquisition = loaded.get("acquisition", {}) if isinstance(loaded, dict) else {}
    if isinstance(acquisition, dict):
        settings["acquisition"].update(_sanitize_acquisition(acquisition))
    return settings


def save_global_settings(settings: dict[str, dict[str, Any]]) -> None:
    path = global_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    to_save = _clone_defaults()
    acquisition = settings.get("acquisition", {}) if isinstance(settings, dict) else {}
    if isinstance(acquisition, dict):
        to_save["acquisition"].update(_sanitize_acquisition(acquisition))
    with path.open("w", encoding="utf-8") as file_obj:
        toml.dump(to_save, file_obj)


def _sanitize_acquisition(acq: dict[str, Any]) -> dict[str, Any]:
    defaults = DEFAULT_GLOBAL_SETTINGS["acquisition"]
    sanitized: dict[str, Any] = {}
    sanitized["pretrigger_samples"] = _coerce_int(acq.get("pretrigger_samples"), int(defaults["pretrigger_samples"]), 0)
    sanitized["posttrigger_samples"] = _coerce_int(acq.get("posttrigger_samples"), int(defaults["posttrigger_samples"]), 1)
    sanitized["sample_rate_hz"] = _coerce_float(acq.get("sample_rate_hz"), float(defaults["sample_rate_hz"]), 1.0)
    trigger_source = acq.get("trigger_source")
    sanitized["trigger_source"] = (
        trigger_source.strip() if isinstance(trigger_source, str) and trigger_source.strip() else defaults["trigger_source"]
    )
    sanitized["windows_per_position"] = _coerce_int(acq.get("windows_per_position"), int(defaults["windows_per_position"]), 1)
    sanitized["read_timeout_s"] = _coerce_float(acq.get("read_timeout_s"), float(defaults["read_timeout_s"]), 0.1)
    sanitized["max_retries_per_window"] = _coerce_int(
        acq.get("max_retries_per_window"),
        int(defaults["max_retries_per_window"]),
        0,
    )
    return sanitized


def _coerce_int(value: Any, default: int, minimum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= minimum else default


def _coerce_float(value: Any, default: float, minimum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= minimum else default


def _clone_defaults() -> dict[str, dict[str, Any]]:
    return {"acquisition": dict(DEFAULT_GLOBAL_SETTINGS["acquisition"])}
