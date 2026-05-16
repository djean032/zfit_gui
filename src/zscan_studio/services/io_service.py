from pathlib import Path

import numpy as np
import toml


def load_zscan_csv(file_path: str) -> dict[str, np.ndarray]:
    data = np.loadtxt(file_path, delimiter=",", skiprows=1)
    if data.shape[1] < 3:
        raise ValueError("CSV must contain at least 3 columns (z, ai0, ai1)")
    return {
        "z(mm)": data[:, 0],
        "ai0": data[:, 1],
        "ai1": data[:, 2],
        "ai1/ai0": data[:, 2] / data[:, 1],
    }


def save_zscan_with_metadata(
    csv_data: np.ndarray,
    molecule_name: str,
    energy: float,
    config: dict,
    requested_file_path: str,
) -> tuple[str, str]:
    requested_path = Path(requested_file_path)
    csv_path = requested_path if requested_path.suffix.lower() == ".csv" else requested_path.with_suffix(".csv")
    toml_path = csv_path.with_suffix(".toml")

    np.savetxt(
        str(csv_path),
        csv_data,
        delimiter=",",
        header="z(mm),ai0,ai1",
    )

    metadata = {
        "experiment": {
            "molecule_name": molecule_name,
            "pulse_energy": energy,
        },
        "laser": config.get("laser", {}),
        "sample": config.get("sample", {}),
    }

    with open(toml_path, "w") as file_obj:
        toml.dump(metadata, file_obj)

    return str(csv_path), str(toml_path)


def save_parameters_toml(file_path: str, params: dict) -> None:
    with open(file_path, "w") as file_obj:
        toml.dump(params, file_obj)


def load_parameters_toml(file_path: str) -> dict:
    with open(file_path, "r") as file_obj:
        return toml.load(file_obj)


def save_fit_results_csv(file_path: str, labels: list[str], values: list[str]) -> str:
    with open(file_path, "w") as file_obj:
        file_obj.write("parameter,value\n")
        for label, value in zip(labels, values, strict=False):
            file_obj.write(f'"{label}","{value}"\n')
    return str(Path(file_path))
