import nidaqmx
import numpy as np
import numpy.typing as npt
from esp302 import ESP302
import time

from nidaqmx.constants import AcquisitionType, READ_ALL_AVAILABLE


class Experiment:

    def __init__(self, zlim: float, zsamp: int, samp_per_pos: int = 4) -> None:
        self.zlim = zlim
        self.zsamp = zsamp
        self.zpos = np.linspace(-self.zlim, self.zlim, zsamp)
        self.samp_per_pos = samp_per_pos
        self.stage = ESP302()
        self.zaxis = 3

    def collect(self) -> npt.NDArray:
        measurements = np.zeros(shape=(2, self.zsamp))
        # Fill in with expression for collecting values
        with nidaqmx.Task() as task:
            task.ai_channels.add_ai_voltage_chan(
                "Dev1/ai0", min_val=-10.0, max_val=10.0
            )
            for index, position in enumerate(self.zpos):
                self.step(position)
                try:
                    tmp_val = task.read(number_of_samples_per_channel=self.samp_per_pos)
                    # [TODO] insert some validation code to verify tmp_val list is in window
                    measurements[index] = np.array(position, np.mean(tmp_val))
                except Exception as e:
                    print(f"An error with the DAQ measurements has occured: {e}")
        return measurements

    def step(self, pos: float) -> int:

        try:
            self.stage.moveAbsolute(self.zaxis, pos)

        except Exception as e:
            print(f"An error with the stage has occurred: {e}")
            return 1
        return 0

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
