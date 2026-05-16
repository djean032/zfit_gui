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
        self.measurements: np.ndarray = np.zeros(shape=(self.zsamp, 3))
        self._should_stop: bool = False

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

        self.stage = ESP302()
        try:
            with nidaqmx.Task() as task:
                task.ai_channels.add_ai_voltage_chan("Dev1/ai0", min_val=-10.0, max_val=10.0)
                task.ai_channels.add_ai_voltage_chan("Dev1/ai1", min_val=-10.0, max_val=10.0)
                for index, position in enumerate(self.zpos):
                    if self._should_stop:
                        break

                    self.step(position)
                    try:
                        tmp_val = task.read(number_of_samples_per_channel=self.samp_per_pos)
                        if not self.validate_measurements(tmp_val):
                            print(f"Warning: Measurements at position {position} mm are out of expected range.")
                        self.measurements[index, :] = [
                            position,
                            np.mean(np.array(tmp_val[0])),
                            np.mean(np.array(tmp_val[1])),
                        ]

                        if progress_callback is not None:
                            progress = int((index + 1) / self.zsamp * 100)
                            progress_callback(progress)
                    except Exception as e:
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

    def validate_measurements(self, measurements: list) -> bool:
        """Validate that measurements are within expected range."""
        for value in measurements:
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
