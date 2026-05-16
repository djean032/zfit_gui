from collections.abc import Mapping

import numpy as np
from matplotlib.figure import Figure
from matplotlib.ticker import AutoMinorLocator


def get_plot_style_tokens(theme: str) -> dict[str, float | str | bool]:
    _ = theme
    base: dict[str, float | str | bool] = {
        "fig_bg": "#141414",
        "axes_bg": "#1B1B1B",
        "text_color": "#EEDFB5",
        "grid_major": "#4B432B",
        "grid_minor": "#352F1E",
        "spine_color": "#7B6A3D",
        "legend_bg": "#1B1B1B",
        "data_color": "#8AC7FF",
        "fit_color": "#FFD166",
        "preview_color": "#9FEA8F",
        "annotation_bg": "#1E1B14",
        "annotation_edge": "#7B6A3D",
    }

    base.update(
        {
            "line_width": 1.8,
            "fit_width": 2.4,
            "marker_size": 5.0,
            "preview_marker_size": 4.0,
            "major_grid_alpha": 0.24,
            "minor_grid_alpha": 0.12,
            "title_size": 12.0,
            "label_size": 11.0,
            "tick_size": 9.0,
            "show_annotations": False,
        }
    )

    return base


def style_plot_axes(fig: Figure, axes, tokens: Mapping[str, float | str | bool]) -> None:
    fig.patch.set_facecolor(str(tokens["fig_bg"]))
    axes.set_facecolor(str(tokens["axes_bg"]))
    axes.xaxis.label.set_color(str(tokens["text_color"]))
    axes.yaxis.label.set_color(str(tokens["text_color"]))
    axes.title.set_color(str(tokens["text_color"]))
    axes.xaxis.label.set_size(float(tokens["label_size"]))
    axes.yaxis.label.set_size(float(tokens["label_size"]))
    axes.title.set_size(float(tokens["title_size"]))
    axes.tick_params(colors=str(tokens["text_color"]), labelsize=float(tokens["tick_size"]))
    axes.minorticks_on()
    axes.xaxis.set_minor_locator(AutoMinorLocator())
    axes.yaxis.set_minor_locator(AutoMinorLocator())
    axes.grid(True, which="major", alpha=float(tokens["major_grid_alpha"]), color=str(tokens["grid_major"]))
    axes.grid(True, which="minor", alpha=float(tokens["minor_grid_alpha"]), color=str(tokens["grid_minor"]))

    for spine in axes.spines.values():
        spine.set_color(str(tokens["spine_color"]))

    legend = axes.get_legend()
    if legend is None:
        return

    legend.get_frame().set_facecolor(str(tokens["legend_bg"]))
    legend.get_frame().set_edgecolor(str(tokens["spine_color"]))
    legend.get_frame().set_alpha(0.9)
    for text in legend.get_texts():
        text.set_color(str(tokens["text_color"]))


def annotate_series(
    axes,
    x_data: np.ndarray,
    y_data: np.ndarray,
    prefix: str,
    tokens: Mapping[str, float | str | bool],
) -> None:
    if not bool(tokens["show_annotations"]) or len(x_data) == 0:
        return

    min_idx = int(np.argmin(y_data))
    max_idx = int(np.argmax(y_data))
    note = f"{prefix}\nmin T: {y_data[min_idx]:.4f} @ z={x_data[min_idx]:.2f} mm\nmax T: {y_data[max_idx]:.4f} @ z={x_data[max_idx]:.2f} mm"
    axes.text(
        0.02,
        0.98,
        note,
        transform=axes.transAxes,
        va="top",
        ha="left",
        fontsize=float(tokens["tick_size"]),
        color=str(tokens["text_color"]),
        bbox={
            "facecolor": str(tokens["annotation_bg"]),
            "edgecolor": str(tokens["annotation_edge"]),
            "boxstyle": "round,pad=0.3",
            "alpha": 0.9,
        },
    )
