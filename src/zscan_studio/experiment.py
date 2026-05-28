from datetime import datetime
from typing import Callable

import numpy as np
import toml

from zscan_studio.esp302 import ESP302
from zscan_studio.math_utils import generate_z_positions


class Experiment:
    def __init__(
        self,
        zlim: float,
        zsamp: int,
        samp_per_pos: int = 4,
        spacing_type: str = "Linear",
    ) -> None:
        self.zlim: float = zlim
        self.zsamp: int = zsamp
        self.spacing_type: str = spacing_type
        self.zpos: np.ndarray = generate_z_positions(zlim, zsamp, spacing_type)
        self.samp_per_pos: int = samp_per_pos
        self.stage: ESP302 | None = None
        self.zaxis: int = 3
        self.polarizer_axis: int = 2
        self.measurements: np.ndarray = np.zeros(shape=(self.zsamp, 3))
        self._should_stop: bool = False
        self.pretrigger_samples: int = 10
        self.posttrigger_samples: int = 140
        self.sample_rate_hz: float = 1_000_000.0
        self.trigger_source: str = "/Dev1/PFI0"
        self.windows_per_position: int = samp_per_pos
        self.read_timeout_s: float = 5.0
        self.max_retries_per_window: int = 4

    def stop(self) -> None:
        """Signal the experiment to stop at the next opportunity."""
        self._should_stop = True

    def collect(self, progress_callback: Callable[[int], None] | None = None) -> None:
        """Collect measurements across the z-axis positions.

        Args:
            progress_callback: Optional callback function that returns progress percentage (0-100)

        Note:
            If stopped early via stop(), partial data may be returned.
        """
        self._should_stop = False
        self.measurements[:] = 0
        import nidaqmx
        from nidaqmx.constants import AcquisitionType, Edge

        self.stage = ESP302()
        try:
            with nidaqmx.Task() as task:
                task.ai_channels.add_ai_voltage_chan("Dev1/ai0", min_val=-10.0, max_val=10.0)
                task.ai_channels.add_ai_voltage_chan("Dev1/ai1", min_val=-10.0, max_val=10.0)
                task.timing.cfg_samp_clk_timing(
                    rate=self.sample_rate_hz,
                    active_edge=Edge.RISING,
                    sample_mode=AcquisitionType.FINITE,
                    samps_per_chan=self.pretrigger_samples + self.posttrigger_samples,
                )
                task.triggers.reference_trigger.cfg_dig_edge_ref_trig(
                    trigger_source=self.trigger_source,
                    trigger_edge=Edge.RISING,
                    pretrigger_samples=self.pretrigger_samples,
                )
                for index, position in enumerate(self.zpos):
                    if self._should_stop:
                        break

                    self.step(position)
                    try:
                        total_samples = self.pretrigger_samples + self.posttrigger_samples
                        ai0_max_values: list[float] = []
                        ai1_max_values: list[float] = []
                        max_attempts = self.windows_per_position * (1 + self.max_retries_per_window)
                        attempts = 0

                        while len(ai0_max_values) < self.windows_per_position and attempts < max_attempts:
                            if self._should_stop:
                                break

                            attempts += 1
                            try:
                                task.start()
                                tmp_val = task.read(
                                    number_of_samples_per_channel=total_samples,
                                    timeout=self.read_timeout_s,
                                )
                                task.stop()

                                if not self.validate_measurements(tmp_val):
                                    print(f"Warning: Out-of-range DAQ samples at z={position} mm (attempt {attempts}/{max_attempts}).")

                                ai0 = np.asarray(tmp_val[0], dtype=float)
                                ai1 = np.asarray(tmp_val[1], dtype=float)
                                ai0_post = ai0[self.pretrigger_samples :]
                                ai1_post = ai1[self.pretrigger_samples :]

                                if ai0_post.size == 0 or ai1_post.size == 0:
                                    raise ValueError("Post-trigger sample window is empty.")

                                ai0_max_values.append(float(np.max(ai0_post)))
                                ai1_max_values.append(float(np.max(ai1_post)))
                            except Exception as window_error:
                                try:
                                    task.stop()
                                except Exception:
                                    pass
                                print(f"Warning: DAQ window failed at z={position} mm (attempt {attempts}/{max_attempts}): {window_error}")

                        if self._should_stop:
                            break

                        if len(ai0_max_values) < self.windows_per_position or len(ai1_max_values) < self.windows_per_position:
                            raise TimeoutError(
                                f"Could not collect {self.windows_per_position} successful windows at z={position} mm. "
                                f"Collected {len(ai0_max_values)} windows in {attempts} attempts."
                            )

                        self.measurements[index, :] = [
                            position,
                            float(np.mean(np.asarray(ai0_max_values, dtype=float))),
                            float(np.mean(np.asarray(ai1_max_values, dtype=float))),
                        ]

                        if progress_callback is not None:
                            progress = int((index + 1) / self.zsamp * 100)
                            progress_callback(progress)
                    except Exception as e:
                        try:
                            task.stop()
                        except Exception:
                            pass
                        print(f"An error with the DAQ measurements has occurred: {e}")
        finally:
            if self.stage is not None:
                self.stage.close()
                self.stage = None

    def step(self, pos: float) -> int:
        """Move the stage to the specified position."""
        if self.stage is None:
            print("Stage is not initialized.")
            return 1

        try:
            self.stage.moveAbsolute(self.zaxis, pos)
        except Exception as e:
            print(f"An error with the stage has occurred: {e}")
            return 1
        while not self.stage.queryAtPosition(self.zaxis, pos):
            continue
        return 0

    def set_polarizer_position(self, pos: float) -> int:
        """Move the polarizer axis (axis 2 by default) to the specified position."""
        if self.stage is None:
            print("Stage is not initialized.")
            return 1

        try:
            self.stage.moveAbsolute(self.polarizer_axis, pos)
        except Exception as e:
            print(f"An error with the polarizer axis has occurred: {e}")
            return 1
        while not self.stage.queryAtPosition(self.polarizer_axis, pos):
            continue
        return 0

    def validate_measurements(self, measurements: list) -> bool:
        """Validate that measurements are within expected range."""
        values = np.asarray(measurements, dtype=float).ravel()
        for value in values:
            if value < -10.0 or value > 10.0:
                return False
        return True

    def save_with_metadata(
        self,
        measurement_data: np.ndarray,
        molecule_name: str,
        energy: float,
        config: dict,
    ) -> tuple[str, str]:
        """Save measurement data to CSV and config to TOML sidecar.

        Args:
            measurement_data: The z-scan measurement data array
            molecule_name: Name of the molecule/sample
            energy: Laser pulse energy
            config: Configuration dictionary with laser and sample params

        Returns:
            Tuple of (csv_path, toml_path)
        """
        energy_str = self._format_energy(energy)
        base_name = f"{molecule_name}_{energy_str}"

        csv_path = base_name + ".csv"
        np.savetxt(
            csv_path,
            measurement_data,
            delimiter=",",
            header="z(mm),ai0,ai1",
        )

        toml_path = base_name + ".toml"
        metadata = {
            "experiment": {
                "molecule_name": molecule_name,
                "pulse_energy": energy,
                "timestamp": datetime.now().isoformat(),
            },
            "laser": config.get("laser", {}),
            "sample": config.get("sample", {}),
        }

        with open(toml_path, "w") as f:
            toml.dump(metadata, f)

        return csv_path, toml_path

    def _format_energy(self, energy: float) -> str:
        """Format energy value for filename."""
        return f"{energy:.0e}"
