from pathlib import Path

import numpy as np
import toml

from zscan_studio.services.io_service import save_zscan_with_metadata


def test_save_zscan_with_metadata_honors_requested_csv_path(tmp_path: Path) -> None:
    csv_data = np.array([[0.0, 1.0, 2.0], [1.0, 1.1, 2.2]])
    requested = tmp_path / "custom_output.csv"

    csv_path, toml_path = save_zscan_with_metadata(
        csv_data=csv_data,
        molecule_name="sample",
        energy=1.0e-7,
        config={"laser": {"energy_pulse": 1.0e-7}, "sample": {"thickness": 0.1}},
        requested_file_path=str(requested),
    )

    assert Path(csv_path) == requested
    assert Path(toml_path) == requested.with_suffix(".toml")
    assert Path(csv_path).exists()
    assert Path(toml_path).exists()

    metadata = toml.load(toml_path)
    assert metadata["experiment"]["molecule_name"] == "sample"
    assert metadata["experiment"]["pulse_energy"] == 1.0e-7


def test_save_zscan_with_metadata_adds_csv_suffix(tmp_path: Path) -> None:
    csv_data = np.array([[0.0, 1.0, 2.0]])
    requested = tmp_path / "custom_output"

    csv_path, toml_path = save_zscan_with_metadata(
        csv_data=csv_data,
        molecule_name="sample",
        energy=1.0e-7,
        config={"laser": {}, "sample": {}},
        requested_file_path=str(requested),
    )

    assert Path(csv_path) == requested.with_suffix(".csv")
    assert Path(toml_path) == requested.with_suffix(".toml")
