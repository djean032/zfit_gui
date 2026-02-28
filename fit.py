import numpy as np
import zfit_wrapper
from numpy.typing import NDArray
from scipy.constants import Avogadro
from typing import Dict, Optional


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
    populations = np.array(
        [float(config["sample"]["concentration"]) * Avogadro / 1000, 0, 0, 0, 0]
    )
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
