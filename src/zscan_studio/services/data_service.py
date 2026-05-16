import numpy as np

from zscan_studio.math_utils import generate_z_positions


def build_zscan_data(measurements: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "z(mm)": measurements[:, 0],
        "ai0": measurements[:, 1],
        "ai1": measurements[:, 2],
        "ai1/ai0": measurements[:, 2] / measurements[:, 1],
    }


def build_zscan_table_rows(zscan_data: dict[str, np.ndarray]) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    z_data = zscan_data["z(mm)"]
    ai0_data = zscan_data["ai0"]
    ai1_data = zscan_data["ai1"]
    ratio_data = zscan_data["ai1/ai0"]

    for i in range(len(z_data)):
        rows.append(
            (
                f"{z_data[i]:.2f}",
                f"{ai0_data[i]:.4f}",
                f"{ai1_data[i]:.4f}",
                f"{ratio_data[i]:.6f}",
            )
        )
    return rows


def build_zscan_stats_text(zscan_data: dict[str, np.ndarray]) -> str:
    n_points = len(zscan_data["z(mm)"])
    z_min = np.min(zscan_data["z(mm)"])
    z_max = np.max(zscan_data["z(mm)"])
    ratio_min = np.min(zscan_data["ai1/ai0"])
    ratio_max = np.max(zscan_data["ai1/ai0"])
    ratio_mean = np.mean(zscan_data["ai1/ai0"])
    return (
        f"Data points: {n_points} | "
        f"z range: [{z_min:.1f}, {z_max:.1f}] mm | "
        f"ai1/ai0 range: [{ratio_min:.4f}, {ratio_max:.4f}] | "
        f"Mean: {ratio_mean:.4f}"
    )


def build_preview_curve(zlim: float, zsamp: int, spacing_type: str) -> tuple[np.ndarray, np.ndarray, str]:
    z = generate_z_positions(zlim, zsamp, spacing_type)
    depth = 0.3
    width = 5.0
    y = 1 - depth / (1 + (z / width) ** 2)
    title = f"Z-Scan Measurement Preview ({spacing_type}, zlim={zlim}, zsamp={zsamp})"
    return z, y, title
