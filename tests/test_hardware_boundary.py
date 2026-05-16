import importlib

import numpy as np

from zscan_studio.workers import ExperimentWorker


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
