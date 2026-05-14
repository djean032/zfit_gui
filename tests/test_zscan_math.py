import numpy as np

from zscan_studio.experiment import generate_z_positions
from zscan_studio.fit import normalize_transmission


def test_generate_z_positions_linear_is_symmetric() -> None:
    z = generate_z_positions(20.0, 5, "Linear")
    expected = np.array([-20.0, -10.0, 0.0, 10.0, 20.0])
    np.testing.assert_allclose(z, expected)


def test_generate_z_positions_power_law_keeps_range() -> None:
    z = generate_z_positions(20.0, 5, "Power Law")
    expected = np.array([-20.0, -5.0, 0.0, 5.0, 20.0])
    np.testing.assert_allclose(z, expected)


def test_normalize_transmission_uses_first_points() -> None:
    y = np.array([2.0, 2.0, 4.0, 4.0])
    normalized = normalize_transmission(y, num_points=2)
    np.testing.assert_allclose(normalized, np.array([1.0, 1.0, 2.0, 2.0]))
