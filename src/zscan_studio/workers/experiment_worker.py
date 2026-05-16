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
        except ModuleNotFoundError as e:
            if e.name == "nidaqmx":
                self.error.emit(
                    "NI-DAQ library not found. Install hardware dependencies with `uv sync --extra hardware` "
                    "and verify NI-DAQmx is installed on this machine."
                )
                return
            self.error.emit(str(e))
        except (ConnectionError, TimeoutError) as e:
            self.error.emit(f"Unable to connect to stage controller. Check ESP302 power/network settings and try again. Details: {e}")
        except OSError as e:
            self.error.emit(f"Hardware communication failed during acquisition. Check NI-DAQ/stage availability and retry. Details: {e}")
        except Exception as e:
            self.error.emit(str(e))
