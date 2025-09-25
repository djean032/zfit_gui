import time

import jax
import jax.numpy as jnp
import nidaqmx
import numpy as onp
from jaxtyping import Array

from esp302 import ESP302

jax.config.update("jax_enable_x64", True)


class Experiment:
    def __init__(self, zlim: float, zsamp: int, samp_per_pos: int = 4) -> None:
        self.zlim: float = zlim
        self.zsamp: int = zsamp
        self.zpos: Array = jnp.linspace(-self.zlim, self.zlim, zsamp)
        self.samp_per_pos: int = samp_per_pos
        self.stage: ESP302 = ESP302()
        self.zaxis: int = 3

    def collect(self) -> Array:
        measurements: Array = jnp.zeros(shape=(self.zsamp, 3))
        with nidaqmx.Task() as task:
            task.ai_channels.add_ai_voltage_chan(
                "Dev1/ai0", min_val=-10.0, max_val=10.0
            )
            task.ai_channels.add_ai_voltage_chan(
                "Dev1/ai1", min_val=-10.0, max_val=10.0
            )
            for index, position in enumerate(self.zpos):
                self.step(position)
                try:
                    # Type hinting for this is a nightmare, about a dozen OR statements. Should always be a list in this case...
                    tmp_val = task.read(
                        number_of_samples_per_channel=self.samp_per_pos  # type: ignore
                    )
                    # [TODO] insert some validation code to verify tmp_val list is in window
                    measurements.at[index, :].set(
                        [
                            position,
                            jnp.mean(jnp.array(tmp_val[0])),
                            jnp.mean(jnp.array(tmp_val[1])),
                        ]
                    )
                except Exception as e:
                    print(f"An error with the DAQ measurements has occured: {e}")

        return measurements

    def step(self, pos: float) -> int:
        try:
            self.stage.moveAbsolute(self.zaxis, pos)
        except Exception as e:
            print(f"An error with the stage has occurred: {e}")
            return 1
        while not self.stage.queryAtPosition(self.zaxis, pos):
            continue

        return 0

    def save_all_data(self, measurement_data: Array, name: str):
        onp.savetxt(
            name + ".csv",
            measurement_data,
            delimiter=",",
            header="Position (mm),ai0,ai1",
        )

    def save_norm_data(self, measurement_data: Array, name: str):
        norm_data = self.normalize(measurement_data)
        onp.savetxt(
            name + ".csv", norm_data, delimiter=",", header="Position (mm),Transmission"
        )

    def normalize(self, measurement_data: Array) -> Array:
        transmission = jnp.zeros(self.zsamp)
        transmission = measurement_data[:, 1] / measurement_data[:, 2]
        norm_factor = jnp.mean(transmission[0:10])
        transmission /= norm_factor
        jnp.column_stack([measurement_data[:, 0], transmission])
        return transmission

    def move_test(self) -> None:
        stage = ESP302()

        # set initial positions
        z_axis = 3
        start_z = -20
        end_z = 20
        step = 0.4

        try:
            # Move to starting position
            stage.moveAbsolute(z_axis, start_z)
            print(f"Moving to start position: {start_z} mm")

            # Wait for the stage to reach the starting position
            time.sleep(2)

            # Iterate from z=-20 mm to z=20 mm
            current_z = start_z
            while current_z <= end_z:
                print(f"Moving to position: {current_z} mm")
                stage.moveAbsolute(z_axis, current_z)

                current_z += step
                time.sleep(0.5)

            print(f"Scan complete. Final position: {current_z} mm")

        except Exception as e:
            print(f"An error occurred: {e}")

        # Close the connection to the stage
        stage.close()
        print("Staged connection closed")
