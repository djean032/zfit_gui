import nidaqmx
import numpy as np
import numpy.typing as npt

from nidaqmx.constants import AcquisitionType, READ_ALL_AVAILABLE

class Experiment:

    def __init__(self, zlim: float, zsamp: int) -> None:
        self.zlim = zlim
        self.zsamp = zsamp
        self.zpos = np.linspace(-self.zlim, self.zlim, zsamp)


    def collect(self) -> npt.NDArray:
        measurements = np.zeros(shape=(2, self.zsamp))
        # Fill in with expression for collecting values
        return measurements
