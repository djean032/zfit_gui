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
            self._apply_acquisition_config()

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

    def _apply_acquisition_config(self) -> None:
        if self.exp is None:
            return

        acquisition = self.config.get("acquisition", {}) if isinstance(self.config, dict) else {}
        if not isinstance(acquisition, dict):
            return

        self.exp.pretrigger_samples = self._int_or_default(acquisition.get("pretrigger_samples"), self.exp.pretrigger_samples, minimum=0)
        self.exp.posttrigger_samples = self._int_or_default(acquisition.get("posttrigger_samples"), self.exp.posttrigger_samples, minimum=1)
        self.exp.sample_rate_hz = self._float_or_default(acquisition.get("sample_rate_hz"), self.exp.sample_rate_hz, minimum=1.0)
        self.exp.trigger_source = self._str_or_default(acquisition.get("trigger_source"), self.exp.trigger_source)
        self.exp.windows_per_position = self._int_or_default(
            acquisition.get("windows_per_position"),
            self.exp.windows_per_position,
            minimum=1,
        )
        self.exp.read_timeout_s = self._float_or_default(acquisition.get("read_timeout_s"), self.exp.read_timeout_s, minimum=0.1)
        self.exp.max_retries_per_window = self._int_or_default(
            acquisition.get("max_retries_per_window"),
            self.exp.max_retries_per_window,
            minimum=0,
        )

    @staticmethod
    def _int_or_default(value: object, default: int, minimum: int) -> int:
        try:
            parsed = int(value) if value is not None else default
        except (TypeError, ValueError):
            return default
        return parsed if parsed >= minimum else default

    @staticmethod
    def _float_or_default(value: object, default: float, minimum: float) -> float:
        try:
            parsed = float(value) if value is not None else default
        except (TypeError, ValueError):
            return default
        return parsed if parsed >= minimum else default

    @staticmethod
    def _str_or_default(value: object, default: str) -> str:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else default
        return default
