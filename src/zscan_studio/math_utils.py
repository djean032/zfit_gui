import numpy as np


def generate_z_positions(zlim: float, zsamp: int, spacing_type: str) -> np.ndarray:
    """Generate z positions for Z-scan with different spacing options."""
    u = np.linspace(-1, 1, zsamp)

    if spacing_type == "Linear":
        return zlim * u
    if spacing_type == "Power Law":
        return zlim * np.sign(u) * np.abs(u) ** 2
    return zlim * u
