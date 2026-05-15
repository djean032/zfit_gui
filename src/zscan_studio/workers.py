import numpy as np
from PySide6.QtCore import QThread, Signal


class ExperimentWorker(QThread):
    """Worker thread for running the experiment."""

    progress = Signal(int)
    finished = Signal(object)
    error = Signal(str)

    def __init__(
        self,
        config: dict,
        zlim: float,
        zsamp: int,
        spacing_type: str = "Linear",
        samp_per_pos: int = 4,
    ) -> None:
        super().__init__()
        self.config = config
        self.zlim = zlim
        self.zsamp = zsamp
        self.spacing_type = spacing_type
        self.samp_per_pos = samp_per_pos
        self.exp = None

    def run(self) -> None:
        try:
            from zscan_studio.experiment import Experiment

            self.exp = Experiment(
                self.zlim,
                self.zsamp,
                self.samp_per_pos,
                self.spacing_type,
            )

            def progress_callback(value: int) -> None:
                self.progress.emit(value)

            self.exp.collect(progress_callback=progress_callback)
            self.finished.emit(self.exp.measurements)
        except Exception as e:
            self.error.emit(str(e))


class FitWorker(QThread):
    """Worker thread for running the fit."""

    progress = Signal(int)
    finished = Signal(object)
    error = Signal(str)

    def __init__(
        self,
        x_data: np.ndarray,
        y_data: np.ndarray,
        config: dict,
        pulse_energies: np.ndarray | None,
        num_starts: int,
        num_datasets: int,
        num_x_pts: int,
        t_slices: int = 11,
        z_slices: int = 11,
    ) -> None:
        super().__init__()
        self.x_data = x_data
        self.y_data = y_data
        self.config = config
        self.pulse_energies = pulse_energies
        self.num_starts = num_starts
        self.num_datasets = num_datasets
        self.num_x_pts = num_x_pts
        self.t_slices = t_slices
        self.z_slices = z_slices

    def run(self) -> None:
        try:
            from zscan_studio.fit import fit_data

            self.progress.emit(50)
            result = fit_data(
                self.x_data,
                self.y_data,
                self.config,
                self.pulse_energies,
                self.num_starts,
                self.num_datasets,
                self.num_x_pts,
                self.t_slices,
                self.z_slices,
            )
            self.progress.emit(100)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
