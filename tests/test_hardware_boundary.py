import importlib

import numpy as np

from zscan_studio.workers import CalibrationWorker, ExperimentWorker


def test_non_hardware_modules_importable() -> None:
    assert importlib.import_module("zscan_studio.ui.main_window") is not None
    assert importlib.import_module("zscan_studio.fit") is not None
    assert importlib.import_module("zscan_studio.math_utils") is not None


def test_experiment_worker_reports_missing_nidaqmx(monkeypatch) -> None:
    from zscan_studio import experiment as experiment_module

    original_collect = experiment_module.Experiment.collect

    def _raise_missing_nidaqmx(self, progress_callback=None):  # type: ignore[no-untyped-def]
        raise ModuleNotFoundError("No module named 'nidaqmx'", name="nidaqmx")

    monkeypatch.setattr(experiment_module.Experiment, "collect", _raise_missing_nidaqmx)

    worker = ExperimentWorker(config={}, zlim=20.0, zsamp=11)
    errors: list[str] = []
    worker.error.connect(errors.append)

    worker.run()

    assert errors
    assert "NI-DAQ library not found" in errors[0]
    assert "uv sync --extra hardware" in errors[0]

    monkeypatch.setattr(experiment_module.Experiment, "collect", original_collect)


def test_experiment_worker_reports_stage_connection_error(monkeypatch) -> None:
    from zscan_studio import experiment as experiment_module

    original_collect = experiment_module.Experiment.collect

    def _raise_stage_error(self, progress_callback=None):  # type: ignore[no-untyped-def]
        raise ConnectionError("stage socket unavailable")

    monkeypatch.setattr(experiment_module.Experiment, "collect", _raise_stage_error)

    worker = ExperimentWorker(config={}, zlim=20.0, zsamp=11)
    errors: list[str] = []
    worker.error.connect(errors.append)

    worker.run()

    assert errors
    assert "Unable to connect to stage controller" in errors[0]

    monkeypatch.setattr(experiment_module.Experiment, "collect", original_collect)


def test_experiment_worker_finished_signal_on_success(monkeypatch) -> None:
    from zscan_studio import experiment as experiment_module

    original_collect = experiment_module.Experiment.collect

    def _fake_collect(self, progress_callback=None):  # type: ignore[no-untyped-def]
        self.measurements = np.array([[0.0, 1.0, 1.0]])

    monkeypatch.setattr(experiment_module.Experiment, "collect", _fake_collect)

    worker = ExperimentWorker(config={}, zlim=20.0, zsamp=11)
    payloads: list[np.ndarray] = []
    worker.finished.connect(payloads.append)

    worker.run()

    assert payloads
    assert payloads[0].shape == (1, 3)

    monkeypatch.setattr(experiment_module.Experiment, "collect", original_collect)


def test_calibration_worker_reports_missing_nidaqmx(monkeypatch) -> None:
    import builtins

    original_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):  # type: ignore[no-untyped-def]
        if name == "nidaqmx":
            raise ModuleNotFoundError("No module named 'nidaqmx'", name="nidaqmx")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    worker = CalibrationWorker(
        trigger_source="/Dev1/PFI0",
        ai0_channel="Dev1/ai0",
        ai1_channel="Dev1/ai1",
        sample_rate_hz=1_000_000.0,
        pretrigger_samples=0,
        posttrigger_samples=140,
        read_timeout_s=5.0,
        max_retries_per_window=4,
        z_axis=3,
        z_target=0.0,
        polarizer_axis=2,
        polarizer_position=0.0,
    )
    errors: list[str] = []
    worker.error.connect(errors.append)

    worker.run()

    assert errors
    assert "NI-DAQ library not found" in errors[0]
