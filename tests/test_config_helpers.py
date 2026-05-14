from pathlib import Path

from scripts.load_toml import parse_value, process_config, read_toml_config
from scripts.write_toml import write_toml_config


def test_parse_value_none_string() -> None:
    assert parse_value("None") is None
    assert parse_value("1e-6") == "1e-6"


def test_process_config_converts_nested_none() -> None:
    config = {"laser": {"lambda_laser": "None", "w_0": 1.0e-6}}
    processed = process_config(config)
    assert processed["laser"]["lambda_laser"] is None
    assert processed["laser"]["w_0"] == 1.0e-6


def test_write_and_read_toml_round_trip(tmp_path: Path) -> None:
    file_path = tmp_path / "test_config.toml"
    config = {"laser": {"lambda_laser": 532e-9}}

    write_toml_config(config, str(file_path))
    loaded = read_toml_config(str(file_path))

    assert loaded is not None
    assert loaded["laser"]["lambda_laser"] == 532e-9
