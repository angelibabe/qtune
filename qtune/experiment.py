from typing import Tuple, Dict, Any

import numpy as np
import pandas as pd

from qtune.util import time_string

__all__ = ['Experiment', 'Measurement', 'GateIdentifier']

GateIdentifier = str


class Measurement(str):
    """
    This class saves all necessary information for a measurement.
    """
    def __new__(cls, name, **kwargs):
        return super().__new__(cls, name)

    def __init__(self, name, **kwargs):
        super().__init__()

        self.parameter = kwargs

    def get_file_name(self):
        return time_string()


class Experiment:
    """
    Basic class implementing the structure of an experiment consisting of gates whose voltages can be set and read.
    Additionally we require the possibility to conduct measurements.
    """
    @property
    def measurements(self) -> Tuple[Measurement, ...]:
        """Return available measurements for the Experiment"""
        raise NotImplementedError()

    @property
    def gate_voltage_names(self) -> Tuple:
        raise NotImplementedError()

    def read_gate_voltages(self) -> pd.Series:
        raise NotImplementedError()

    def set_gate_voltages(self, new_gate_voltages: pd.Series):
        raise NotImplementedError()

    def measure(self,
                measurement: Measurement) -> np.ndarray:
        """Conduct specified measurements with given gate_voltages

        :param gate_voltages:
        :param measurement:
        :return:
        """
        raise NotImplementedError()
