import numpy as np
import toml

from zscan_studio.fit import normalize_transmission


def load_single_fit_file(file_path: str) -> tuple[dict[str, np.ndarray], dict, int]:
    data = np.loadtxt(file_path, delimiter=",", skiprows=1)
    if data.shape[1] < 3:
        raise ValueError(f"Invalid format in {file_path}: expected at least 3 columns")

    fit_input_data = {
        "z(mm)": data[:, 0],
        "ai0": data[:, 1],
        "ai1": data[:, 2],
    }
    fit_num_x_pts = len(data[:, 0])
    sidecar = file_path.replace(".csv", ".toml")
    with open(sidecar, "r") as file_obj:
        fit_config = toml.load(file_obj)
    return fit_input_data, fit_config, fit_num_x_pts


def load_multi_fit_file_entry(file_path: str) -> tuple[np.ndarray, np.ndarray, int, dict, float]:
    data = np.loadtxt(file_path, delimiter=",", skiprows=1)
    if data.shape[1] < 3:
        raise ValueError(f"Invalid format in {file_path}: expected at least 3 columns")

    num_x_pts = len(data[:, 0])
    x_data = data[:, 0]
    y_data = data[:, 2] / data[:, 1]

    sidecar = file_path.replace(".csv", ".toml")
    with open(sidecar, "r") as file_obj:
        config = toml.load(file_obj)

    pulse_energy = config.get("experiment", {}).get("pulse_energy")
    if pulse_energy is None:
        pulse_energy = config.get("laser", {}).get("energy_pulse")
    if pulse_energy is None:
        raise ValueError(f"No pulse energy found in {sidecar}")

    return x_data, y_data, num_x_pts, config, float(pulse_energy)


def configs_match_ignoring_experiment(left: dict, right: dict) -> bool:
    left_copy = {k: v for k, v in left.items() if k != "experiment"}
    right_copy = {k: v for k, v in right.items() if k != "experiment"}
    return left_copy == right_copy


def prepare_fit_inputs(
    mode: str,
    zscan_data: dict[str, np.ndarray] | None,
    fit_input_data: dict[str, np.ndarray] | None,
    fit_input_x: np.ndarray | None,
    fit_input_y: np.ndarray | None,
    fit_config: dict | None,
    fit_pulse_energies: np.ndarray | None,
    fit_num_datasets: int | None,
    fit_num_x_pts: int | None,
    current_parameters: dict,
) -> tuple[np.ndarray, np.ndarray, dict, np.ndarray | None, int, int]:
    if mode == "Current Data":
        if zscan_data is None:
            raise ValueError("Please run experiment first")
        x_data = zscan_data["z(mm)"]
        y_data = normalize_transmission(zscan_data["ai1/ai0"])
        config = current_parameters
        pulse_energies = None
        num_datasets = 1
        num_x_pts = len(x_data)
        return x_data, y_data, config, pulse_energies, num_datasets, num_x_pts

    if mode == "Single File":
        if fit_input_data is None or fit_config is None or fit_num_x_pts is None:
            raise ValueError("Please load a fit data file first")
        x_data = fit_input_data["z(mm)"]
        y_data = normalize_transmission(fit_input_data["ai1"] / fit_input_data["ai0"])
        config = fit_config
        pulse_energies = None
        num_datasets = 1
        num_x_pts = fit_num_x_pts
        return x_data, y_data, config, pulse_energies, num_datasets, num_x_pts

    if fit_input_x is None or fit_input_y is None or fit_config is None:
        raise ValueError("Please load multiple fit files first")

    num_datasets = fit_num_datasets or 0
    if num_datasets <= 0:
        raise ValueError("Invalid number of datasets for multi-file fitting")

    num_x_pts = fit_num_x_pts or len(fit_input_y)
    normalized_y = []
    for i in range(num_datasets):
        start_idx = i * num_x_pts
        end_idx = start_idx + num_x_pts
        dataset_y = fit_input_y[start_idx:end_idx]
        normalized_y.append(normalize_transmission(dataset_y))

    x_data = fit_input_x
    y_data = np.concatenate(normalized_y)
    config = fit_config
    pulse_energies = fit_pulse_energies
    return x_data, y_data, config, pulse_energies, num_datasets, num_x_pts


def prepare_fit_plot_data(
    mode: str,
    zscan_data: dict[str, np.ndarray] | None,
    fit_input_data: dict[str, np.ndarray] | None,
    fit_input_x: np.ndarray | None,
    fit_input_y: np.ndarray | None,
    fit_num_datasets: int | None,
    fit_num_x_pts: int | None,
) -> tuple[np.ndarray, np.ndarray]:
    if mode == "Current Data":
        if zscan_data is None:
            raise ValueError("No current data available for plotting fit results")
        return zscan_data["z(mm)"], normalize_transmission(zscan_data["ai1/ai0"])

    if mode == "Single File":
        if fit_input_data is None:
            raise ValueError("No single-file fit input available for plotting")
        return fit_input_data["z(mm)"], normalize_transmission(fit_input_data["ai1"] / fit_input_data["ai0"])

    if fit_input_x is None or fit_input_y is None:
        raise ValueError("No multi-file fit input available for plotting")

    num_datasets = fit_num_datasets or 0
    if num_datasets <= 0:
        raise ValueError("Invalid number of datasets for multi-file plotting")

    num_x_pts = fit_num_x_pts or (len(fit_input_y) // num_datasets if num_datasets > 0 else len(fit_input_y))
    normalized_y = []
    for i in range(num_datasets):
        start_idx = i * num_x_pts
        end_idx = start_idx + num_x_pts
        normalized_y.append(normalize_transmission(fit_input_y[start_idx:end_idx]))

    return fit_input_x, np.concatenate(normalized_y)


def build_fit_result_rows(fit_params: object, labels: list[str]) -> list[tuple[str, str]]:
    if fit_params is None:
        return []

    rows: list[tuple[str, str]] = []
    for i, value in enumerate(fit_params):
        label = labels[i] if i < len(labels) else f"Param {i}"
        value_text = f"{float(value):.6e}" if isinstance(value, (int, float, np.floating)) else str(value)
        rows.append((label, value_text))
    return rows
