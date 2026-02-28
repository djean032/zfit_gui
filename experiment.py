import time
from datetime import datetime
from typing import Callable

import numpy as np
import toml

import nidaqmx

from esp302 import ESP302


def generate_z_positions(zlim: float, zsamp: int, spacing_type: str) -> np.ndarray:
    """Generate z positions for Z-scan with different spacing options."""
    u = np.linspace(-1, 1, zsamp)

    if spacing_type == "Linear":
        return zlim * u
    elif spacing_type == "Power Law":
        return zlim * np.sign(u) * np.abs(u) ** 2
    else:
        return zlim * u


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
        self.stage: ESP302 = ESP302()
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
        with nidaqmx.Task() as task:
            task.ai_channels.add_ai_voltage_chan(
                "Dev1/ai0", min_val=-10.0, max_val=10.0
            )
            task.ai_channels.add_ai_voltage_chan(
                "Dev1/ai1", min_val=-10.0, max_val=10.0
            )
            for index, position in enumerate(self.zpos):
                if self._should_stop:
                    break

                self.step(position)
                try:
                    tmp_val = task.read(number_of_samples_per_channel=self.samp_per_pos)
                    if not self.validate_measurements(tmp_val):
                        print(
                            f"Warning: Measurements at position {position} mm are out of expected range."
                        )
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

    def step(self, pos: float) -> int:
        """Move the stage to the specified position."""
        try:
            self.stage.moveAbsolute(self.zaxis, pos)
        except Exception as e:
            print(f"An error with the stage has occurred: {e}")
            return 1
        while not self.stage.queryAtPosition(self.zaxis, pos):
            continue
        return 0

    def save_all_data(self, measurement_data: np.ndarray, name: str) -> None:
        """Save all measurement data to a CSV file."""
        np.savetxt(
            name + ".csv",
            measurement_data,
            delimiter=",",
            header="z(mm),ai0,ai1",
        )

    def save_norm_data(self, measurement_data: np.ndarray, name: str) -> None:
        """Save normalized measurement data to a CSV file."""
        norm_data = self.normalize(measurement_data)
        np.savetxt(name + "_norm.csv", norm_data, delimiter=",", header="z(mm),ai1/ai0")

    def normalize(self, measurement_data: np.ndarray) -> np.ndarray:
        """Normalize the measurement data to calculate transmission."""
        transmission = measurement_data[:, 2] / measurement_data[:, 1]
        norm_factor = np.mean(transmission[0:10])
        transmission /= norm_factor
        return np.column_stack((measurement_data[:, 0], transmission))

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
        if energy >= 1e-3:
            return f"{energy:.0e}"
        elif energy >= 1e-6:
            return f"{energy:.0e}"
        else:
            return f"{energy:.0e}"

    def move_test(self) -> None:
        stage = ESP302()
        z_axis = 3
        start_z = -20
        end_z = 20
        step = 0.4

        try:
            stage.moveAbsolute(z_axis, start_z)
            print(f"Moving to start position: {start_z} mm")
            time.sleep(2)

            current_z = start_z
            while current_z <= end_z:
                print(f"Moving to position: {current_z} mm")
                stage.moveAbsolute(z_axis, current_z)
                current_z += step
                time.sleep(0.5)

            print(f"Scan complete. Final position: {current_z} mm")

        except Exception as e:
            print(f"An error occurred: {e}")

        stage.close()
        print("Staged connection closed")


if __name__ == "__main__":
    exp = Experiment(zlim=20.0, zsamp=101, samp_per_pos=4)
    exp.collect()
    exp.save_all_data(exp.measurements, "experiment_data")
    exp.save_norm_data(exp.measurements, "normalized_data")
