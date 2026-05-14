from typing import Dict, Optional

import numpy as np
from numpy.typing import NDArray
from scipy.constants import Avogadro


def normalize_transmission(y_data: NDArray[np.float64], num_points: int = 10) -> NDArray[np.float64]:
    """Normalize transmission data by dividing by the mean of the first N points.

    This normalizes the baseline (far from focal point) to approximately 1.0,
    which is standard for Z-scan analysis.

    Args:
        y_data: Array of transmission values (ai1/ai0)
        num_points: Number of points at the start to use for normalization (default: 10)

    Returns:
        Normalized transmission array
    """
    if len(y_data) < num_points:
        num_points = len(y_data) // 4

    norm_factor = np.mean(y_data[:num_points])
    if norm_factor == 0:
        raise ValueError("Normalization factor is zero - cannot normalize data")

    return y_data / norm_factor


def fit_data(
    x_data: NDArray[np.float64],
    y_data: NDArray[np.float64],
    config: Dict,
    pulse_energies: Optional[NDArray[np.float64]],
    num_starts: int,
    num_datasets: int,
    num_x_pts: int,
    t_slices: Optional[int] = 11,
    z_slices: Optional[int] = 11,
):
    import zfit_wrapper

    required_laser = ["pulse_width", "lambda_laser", "w_0", "m_squared", "energy_pulse"]
    required_sample = [
        "concentration",
        "sig_g",
        "sig_s",
        "sig_t",
        "t_10",
        "t_13",
        "t_21",
        "t_30",
        "t_43",
    ]

    for key in required_laser:
        if config["laser"].get(key) is None:
            raise ValueError(f"Missing or invalid laser parameter: {key}")
    for key in required_sample:
        if config["sample"].get(key) is None:
            raise ValueError(f"Missing or invalid sample parameter: {key}")

    # Note: y_data should already be normalized by the GUI before calling fit_data

    populations = np.array([float(config["sample"]["concentration"]) * Avogadro / 1000, 0, 0, 0, 0])
    sample_width = 0.1
    tau = float(config["laser"]["pulse_width"])
    wavelength = float(config["laser"]["lambda_laser"])
    w0 = float(config["laser"]["w_0"])
    M2 = float(config["laser"]["m_squared"])
    if num_datasets < 1:
        return
    elif num_datasets == 1:
        pulse_energy = np.array([float(config["laser"]["energy_pulse"])])
    else:
        if pulse_energies is None:
            return
        pulse_energy = pulse_energies

    sig_g = float(config["sample"]["sig_g"])
    sig_s = float(config["sample"]["sig_s"])
    sig_t = float(config["sample"]["sig_t"])
    t10 = float(config["sample"]["t_10"])
    t13 = float(config["sample"]["t_13"])
    t21 = float(config["sample"]["t_21"])
    t30 = float(config["sample"]["t_30"])
    t43 = float(config["sample"]["t_43"])
    spec_pars = np.array([sig_g, sig_s, sig_t, t10, t13, t21, t30, t43])
    if t_slices is None or z_slices is None:
        return

    # Calculate num_x_pts from data - validate all datasets have same number of points
    total_points = len(x_data)
    if num_datasets == 1:
        num_x_pts = total_points
    else:
        # For multiple datasets, validate all have same number of points
        if total_points % num_datasets != 0:
            raise ValueError(
                f"Total data points ({total_points}) is not divisible by number of datasets ({num_datasets}). "
                f"All datasets must have the same number of points."
            )
        calculated_num_x_pts = total_points // num_datasets

        # Validate that explicitly passed num_x_pts matches calculated value
        if num_x_pts != calculated_num_x_pts:
            raise ValueError(
                f"Data points per dataset mismatch: calculated {calculated_num_x_pts}, "
                f"but expected {num_x_pts}. All files must have the same number of data points."
            )
        num_x_pts = calculated_num_x_pts

    # Ensure all arrays passed to zfit_wrapper are C-contiguous
    # Convert x_data from mm to m (zfit_wrapper expects meters)
    x_data = np.ascontiguousarray(x_data, dtype=np.float64)
    y_data = np.ascontiguousarray(y_data, dtype=np.float64)
    populations = np.ascontiguousarray(populations, dtype=np.float64)
    pulse_energy = np.ascontiguousarray(pulse_energy, dtype=np.float64)
    spec_pars = np.ascontiguousarray(spec_pars, dtype=np.float64)

    residuals, error, fit_params = zfit_wrapper.fit_zscan(
        x_data,
        y_data,
        populations,
        t_slices,
        z_slices,
        sample_width,
        tau,
        wavelength,
        w0,
        M2,
        pulse_energy,
        spec_pars,
        num_x_pts,
        num_datasets,
        num_starts,
    )
    return (residuals, error, fit_params)
