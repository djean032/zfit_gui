from __future__ import annotations

import threading
import time

import numpy as np
from PySide6.QtCore import QThread, Signal


class CalibrationWorker(QThread):
    """Persistent calibration session worker with lazy DAQ task init."""

    finished = Signal(object)
    reading = Signal(object)
    error = Signal(str)
    status = Signal(str)

    def __init__(
        self,
        trigger_source: str,
        ai0_channel: str,
        ai1_channel: str,
        sample_rate_hz: float,
        pretrigger_samples: int,
        posttrigger_samples: int,
        read_timeout_s: float,
        max_retries_per_window: int,
        z_axis: int,
        z_target: float,
        polarizer_axis: int,
        polarizer_position: float | None,
        live_interval_ms: int = 200,
    ) -> None:
        super().__init__()
        self.trigger_source = trigger_source
        self.ai0_channel = ai0_channel
        self.ai1_channel = ai1_channel
        self.sample_rate_hz = sample_rate_hz
        self.pretrigger_samples = pretrigger_samples
        self.posttrigger_samples = posttrigger_samples
        self.read_timeout_s = read_timeout_s
        self.max_retries_per_window = max_retries_per_window
        self.z_axis = z_axis
        self.z_target = z_target
        self.polarizer_axis = polarizer_axis
        self.polarizer_position = polarizer_position
        self.live_interval_ms = live_interval_ms

        self._lock = threading.Lock()
        self._live_requested = False
        self._single_requested = False
        self._shutdown_requested = False
        self._config_dirty = False

        self._task = None
        self._nidaqmx = None
        self._stage_available: bool | None = None
        self._stage_retry_after_s: float = 10.0
        self._last_stage_failure_ts: float = 0.0

    def request_read_once(self) -> None:
        with self._lock:
            self._single_requested = True

    def request_start_live(self) -> None:
        with self._lock:
            self._live_requested = True

    def request_stop_live(self) -> None:
        with self._lock:
            self._live_requested = False

    def request_shutdown(self) -> None:
        with self._lock:
            self._live_requested = False
            self._single_requested = False
            self._shutdown_requested = True

    def update_config(
        self,
        trigger_source: str,
        ai0_channel: str,
        ai1_channel: str,
        sample_rate_hz: float,
        pretrigger_samples: int,
        posttrigger_samples: int,
        read_timeout_s: float,
        max_retries_per_window: int,
        polarizer_position: float | None,
    ) -> None:
        with self._lock:
            self.trigger_source = trigger_source
            self.ai0_channel = ai0_channel
            self.ai1_channel = ai1_channel
            self.sample_rate_hz = sample_rate_hz
            self.pretrigger_samples = pretrigger_samples
            self.posttrigger_samples = posttrigger_samples
            self.read_timeout_s = read_timeout_s
            self.max_retries_per_window = max_retries_per_window
            self.polarizer_position = polarizer_position
            self._config_dirty = True

    def run(self) -> None:
        try:
            import nidaqmx

            self._nidaqmx = nidaqmx
        except ModuleNotFoundError as e:
            if e.name == "nidaqmx":
                self.error.emit(
                    "NI-DAQ library not found. Install hardware dependencies with `uv sync --extra hardware` "
                    "and verify NI-DAQmx is installed on this machine."
                )
                return
            self.error.emit(str(e))
            return

        try:
            while not self.isInterruptionRequested():
                with self._lock:
                    shutdown_requested = self._shutdown_requested
                    live_requested = self._live_requested
                    single_requested = self._single_requested
                    config_dirty = self._config_dirty
                    if single_requested:
                        self._single_requested = False
                    if config_dirty:
                        self._config_dirty = False

                if shutdown_requested:
                    break

                if config_dirty:
                    self._close_task()

                if single_requested:
                    try:
                        payload = self._acquire(windows_per_read=4, retries=self.max_retries_per_window, timeout_s=self.read_timeout_s)
                        self.finished.emit(payload)
                    except Exception as e:
                        self.error.emit(str(e))
                    continue

                if live_requested:
                    try:
                        payload = self._acquire(windows_per_read=1, retries=0, timeout_s=0.3)
                        self.reading.emit(payload)
                    except Exception as e:
                        self.status.emit(f"Live read error: {e}")
                    self.msleep(max(1, self.live_interval_ms))
                    continue

                self.msleep(20)
        finally:
            self._close_task()

    def _ensure_task(self) -> None:
        if self._task is not None:
            return
        if self._nidaqmx is None:
            raise RuntimeError("NI-DAQ session is not initialized.")

        from nidaqmx.constants import AcquisitionType, Edge

        total_samples = self.pretrigger_samples + self.posttrigger_samples
        if total_samples < 1:
            raise ValueError("Total samples must be >= 1.")

        task = self._nidaqmx.Task()
        task.ai_channels.add_ai_voltage_chan(self.ai0_channel, min_val=-10.0, max_val=10.0)
        task.ai_channels.add_ai_voltage_chan(self.ai1_channel, min_val=-10.0, max_val=10.0)
        task.timing.cfg_samp_clk_timing(
            rate=self.sample_rate_hz,
            active_edge=Edge.RISING,
            sample_mode=AcquisitionType.FINITE,
            samps_per_chan=total_samples,
        )
        task.triggers.reference_trigger.cfg_dig_edge_ref_trig(
            trigger_source=self.trigger_source,
            trigger_edge=Edge.RISING,
            pretrigger_samples=self.pretrigger_samples,
        )
        self._task = task

    def _close_task(self) -> None:
        if self._task is not None:
            try:
                self._task.close()
            except Exception:
                pass
            self._task = None

    def _acquire(self, windows_per_read: int, retries: int, timeout_s: float) -> dict:
        self._ensure_task()
        self._move_stage_for_single_read_if_needed(windows_per_read)

        total_samples = self.pretrigger_samples + self.posttrigger_samples
        ai0_windows: list[np.ndarray] = []
        ai1_windows: list[np.ndarray] = []
        ai0_maxes: list[float] = []
        ai1_maxes: list[float] = []
        attempts = 0
        max_attempts = windows_per_read * (1 + retries)

        while len(ai0_windows) < windows_per_read and attempts < max_attempts:
            if self.isInterruptionRequested():
                raise RuntimeError("Calibration read stopped.")

            attempts += 1
            try:
                assert self._task is not None
                self._task.start()
                tmp_val = self._task.read(number_of_samples_per_channel=total_samples, timeout=timeout_s)
                self._task.stop()

                ai0 = np.asarray(tmp_val[0], dtype=float)
                ai1 = np.asarray(tmp_val[1], dtype=float)
                ai0_post = ai0[self.pretrigger_samples :]
                ai1_post = ai1[self.pretrigger_samples :]
                if ai0_post.size == 0 or ai1_post.size == 0:
                    raise ValueError("Post-trigger window is empty.")

                ai0_windows.append(ai0)
                ai1_windows.append(ai1)
                ai0_maxes.append(float(np.max(ai0_post)))
                ai1_maxes.append(float(np.max(ai1_post)))
            except Exception as read_error:
                try:
                    if self._task is not None:
                        self._task.stop()
                except Exception:
                    pass
                self.status.emit(f"Calibration window read failed (attempt {attempts}/{max_attempts}): {read_error}")

        if len(ai0_windows) < windows_per_read or len(ai1_windows) < windows_per_read:
            raise TimeoutError(
                f"Could not collect {windows_per_read} successful calibration windows. Collected {len(ai0_windows)} in {attempts} attempts."
            )

        ai0_mean_trace = np.mean(np.asarray(ai0_windows), axis=0)
        ai1_mean_trace = np.mean(np.asarray(ai1_windows), axis=0)
        return {
            "ai0_trace": ai0_mean_trace,
            "ai1_trace": ai1_mean_trace,
            "ai0_avg_max": float(np.mean(np.asarray(ai0_maxes))),
            "ai1_avg_max": float(np.mean(np.asarray(ai1_maxes))),
        }

    def _move_stage_for_single_read_if_needed(self, windows_per_read: int) -> None:
        if windows_per_read == 1:
            return
        if self._stage_available is False and (time.monotonic() - self._last_stage_failure_ts) < self._stage_retry_after_s:
            return
        try:
            from zscan_studio.esp302 import ESP302

            stage = ESP302()
            try:
                stage.moveAbsolute(self.z_axis, self.z_target)
                while not stage.queryAtPosition(self.z_axis, self.z_target):
                    if self.isInterruptionRequested():
                        break
                    self.msleep(10)

                if self.polarizer_position is not None:
                    stage.moveAbsolute(self.polarizer_axis, self.polarizer_position)
                    while not stage.queryAtPosition(self.polarizer_axis, self.polarizer_position):
                        if self.isInterruptionRequested():
                            break
                        self.msleep(10)
                self._stage_available = True
            finally:
                stage.close()
        except Exception as stage_error:
            self._stage_available = False
            self._last_stage_failure_ts = time.monotonic()
            self.status.emit(
                f"ESP302 unavailable for calibration motion; running DAQ-only read. "
                f"Will retry stage in {self._stage_retry_after_s:.0f}s. Details: {stage_error}"
            )
