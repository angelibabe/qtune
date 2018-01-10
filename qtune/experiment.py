from typing import Tuple, Dict, Any

import numpy as np
import pandas as pd

from qtune.util import time_string

__all__ = ['Experiment', 'Measurement', 'GateIdentifier']

GateIdentifier = str


class Measurement(str):
    def __new__(cls, name, **kwargs):
        return super().__new__(cls, name)

    def __init__(self, name, **kwargs):
        super().__init__()

        self.parameter = kwargs

    def get_file_name(self):
        return time_string()


class Experiment:
    @property
    def measurements(self) -> Tuple[Measurement, ...]:
        raise NotImplementedError()

    @property
    def gate_voltage_names(self) -> Tuple:
        raise NotImplementedError()

    def read_gate_voltages(self):
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


class TestExperiment(Experiment):
    def __init__(self, test_voltages):
        self.test_voltages = test_voltages

    def read_gate_voltages(self):
        return pd.Series(self.test_voltages).sort_index()

    def set_gate_voltages(self, new_gate_voltages: pd.Series) -> pd.Series:
        new_gate_voltages = new_gate_voltages.sort_index()
        self.test_voltages = new_gate_voltages
        return new_gate_voltages
