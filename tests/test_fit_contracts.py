import sys
import types

import numpy as np
import pytest

from zscan_studio.fit import fit_data


@pytest.fixture(autouse=True)
def stub_zfit_wrapper() -> None:
    stub = types.SimpleNamespace(
        fit_zscan=lambda *args, **kwargs: (
            np.zeros_like(args[0]),
            0.0,
            np.zeros(8),
        )
    )
    old = sys.modules.get("zfit_wrapper")
    sys.modules["zfit_wrapper"] = stub
    try:
        yield
    finally:
        if old is None:
            sys.modules.pop("zfit_wrapper", None)
        else:
            sys.modules["zfit_wrapper"] = old


def base_config() -> dict:
    return {
        "laser": {
            "pulse_width": 8e-9,
            "lambda_laser": 532e-9,
            "w_0": 1e-6,
            "m_squared": 1.0,
            "energy_pulse": 100e-9,
        },
        "sample": {
            "concentration": 1e-3,
            "sig_g": 1e-18,
            "sig_s": 1e-18,
            "sig_t": 1e-18,
            "t_10": 1e-12,
            "t_13": 1e-7,
            "t_21": 1e-15,
            "t_30": 1e-7,
            "t_43": 1e-15,
        },
    }


def test_fit_data_rejects_invalid_dataset_count() -> None:
    with pytest.raises(ValueError, match="num_datasets"):
        fit_data(np.array([0.0]), np.array([1.0]), base_config(), None, 3, 0, 1)


def test_fit_data_requires_pulse_energies_for_multi_dataset() -> None:
    with pytest.raises(ValueError, match="pulse_energies"):
        fit_data(np.array([0.0, 1.0]), np.array([1.0, 1.0]), base_config(), None, 3, 2, 1)


def test_fit_data_requires_slice_parameters() -> None:
    with pytest.raises(ValueError, match="t_slices"):
        fit_data(np.array([0.0]), np.array([1.0]), base_config(), None, 3, 1, 1, t_slices=None)
