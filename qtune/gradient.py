from typing import Optional, Union

import numpy as np
import pandas as pd

from qtune.kalman_gradient import KalmanGradient
from qtune.storage import HDF5Serializable
from qtune.util import get_orthogonal_vector, calculate_gradient_non_orthogonal

__all__ = ["GradientEstimator", "FiniteDifferencesGradientEstimator", "KalmanGradientEstimator"]


class GradientEstimator(metaclass=HDF5Serializable):
    """Estimate the gradient of a scalar function"""

    def change_position(self, new_position: pd.Series):
        raise NotImplementedError()

    def estimate(self) -> pd.Series:
        raise NotImplementedError()

    def require_measurement(self) -> Optional[pd.Series]:
        raise NotImplementedError()

    def update(self, voltages: pd.Series, value: float, covariance: float, is_new_position=False):
        raise NotImplementedError()

    def to_hdf5(self):
        raise NotImplementedError()


class FiniteDifferencesGradientEstimator(GradientEstimator):
    def __init__(self,
                 current_position: pd.Series,
                 epsilon: Union[pd.Series, float],
                 symmetric: bool=False,
                 current_estimate=None,
                 covariance=None,
                 stored_measurements=None,
                 requested_measurements=None):
        """Estimate the gradient based on finite differences. Requires 2*dim(current_position) measurements if symmetric
        is true and dim(current_position)+1 otherwise.

        :param current_position: Position to base the requirements of measurements around. Also determines the order of
        the gradient entries.
        :param epsilon:
        :param symmetric:
        :param current_estimate:
        :param covariance:
        :param stored_measurements:
        :param requested_measurements:
        """
        self._current_position = current_position

        if not isinstance(epsilon, pd.Series):
            epsilon = pd.Series(epsilon, index=current_position.index)
        self._epsilon = epsilon[self._current_position.index]

        self._current_estimate = current_estimate
        self._covariance = covariance

        self._stored_measurements = stored_measurements or []

        # only for debugging purposes
        self._requested_measurements = requested_measurements or []

        self._symmetric_calculation = symmetric

    @property
    def epsilon(self) -> pd.Series:
        return self._epsilon

    def change_position(self, new_position: pd.Series):
        self._current_position[new_position.index] = new_position

    def estimate(self) -> pd.Series:
        return self._current_estimate

    def covariance(self) -> pd.DataFrame:
        return self._covariance

    def require_measurement(self) -> pd.Series:
        if self._current_estimate is None:
            measured_points = [v for v, *_ in self._stored_measurements]

            if len(measured_points) == 0:
                #  start with arbitrary position
                first_step = np.zeros_like(self._current_position)
                first_step[0] += 1
                self._requested_measurements.append(self._current_position + first_step * self._epsilon)

            elif self._symmetric_calculation:
                if len(measured_points) % 2 == 1:
                    self._requested_measurements.append(2*self._current_position - measured_points[-1][0])
                else:
                    measured_point_diffs = [v2 - v1 for v2, v1 in zip(measured_points[1::2],
                                                                      measured_points[::2])]
                    self._requested_measurements.append(
                        self._current_position + get_orthogonal_vector(measured_point_diffs) * self._epsilon)

            else:
                if len(measured_points) < self._current_position.size:
                    #  request arbitrary orthogonal vector
                    ov = get_orthogonal_vector(measured_points)
                    self._requested_measurements.append(self._current_position + ov)
                else:
                    #  Add the current position as last point
                    self._requested_measurements.append(self._current_position)
            return self._requested_measurements[-1]

    def update(self, voltages: pd.Series, value: float, variance: float, is_new_position=False):
        if self._current_estimate is None:
            self._stored_measurements.append((voltages[self._current_position.index], value, variance))

            positions, values, variances = zip(*self._stored_measurements)

            if self._symmetric_calculation and len(self._stored_measurements) == 2*self._current_position.size:
                gradient, covariance = calculate_gradient_non_orthogonal(positions=positions,
                                                                         values=values,
                                                                         variances=variances)

            elif not self._symmetric_calculation and len(self._stored_measurements) == self._current_position.size + 1:
                #  reverse the order as the "base point" is expected to be the first
                gradient, covariance = calculate_gradient_non_orthogonal(positions=positions[::-1],
                                                                         values=values[::1],
                                                                         variances=variances[::-1])

            else:
                return

            gradient = pd.Series(gradient, index=self._current_position.index)
            covariance = pd.DataFrame(covariance,
                                      index=self._current_position.index,
                                      columns=self._current_position.index)
            self._current_estimate = gradient
            self._covariance = covariance

    def to_hdf5(self):
        return dict(current_position=self._current_position,
                    epsilon=self._epsilon,
                    current_estimate=self._current_estimate,
                    covariance=self._covariance,
                    stored_measurements=self._stored_measurements,
                    symmetric=self._symmetric_calculation,
                    requested_measurements=self._requested_measurements)


class KalmanGradientEstimator(GradientEstimator):
    def __init__(self,
                 kalman_gradient: KalmanGradient,
                 current_position: pd.Series,
                 current_value: float,
                 maximum_covariance: Union[pd.Series, float],
                 epsilon: Union[pd.Series, float]):
        self._kalman_gradient = kalman_gradient
        self._current_position = pd.Series(current_position)
        self._current_value = current_value

        if not isinstance(maximum_covariance, pd.Series):
            maximum_covariance = pd.Series(maximum_covariance, index=self._current_position.index)
        self._maximum_covariance = maximum_covariance[current_position.index]

        if not isinstance(epsilon, pd.Series):
            epsilon = pd.Series(epsilon, index=current_position.index)
        self._epsilon = epsilon[current_position.index]

    def to_hdf5(self):
        return dict(kalman_gradient=self._kalman_gradient,
                    current_position=self._current_position,
                    current_value=self._current_value,
                    maximum_covariance=self._maximum_covariance,
                    epsilon=self._epsilon)

    def change_position(self, new_position: pd.Series):
        """
        :param new_position:
        :return:
        """
        self._current_position = new_position[self._current_position.index]

    def estimate(self) -> pd.Series:
        return pd.Series(np.squeeze(self._kalman_gradient.grad), index=self._current_position.index)

    def require_measurement(self):
        eigenvalues, eigenvectors = np.linalg.eigh(self._kalman_gradient.cov)

        # scale the eigenvectors with their eigenvalues (vector-wise)
        scaled_eigenvectors = eigenvalues[np.newaxis, :] * eigenvectors

        # divide them by the maximum covariance (dimension-wise)
        rescaled_eigenvectors = scaled_eigenvectors / self._maximum_covariance.values[:, np.newaxis]

        # check whether the rescaled vectors are longer than one
        lengths = np.linalg.norm(rescaled_eigenvectors, axis=0)
        if np.any(lengths > 1):
            # if so, pick the longest and scale it with epsilon
            return self._current_position + self._epsilon * eigenvectors[:, np.argmax(lengths)]

    def update(self,
               voltages: pd.Series,
               value: float,
               covariance: float,
               is_new_position=False):
        diff_volts = (voltages - self._current_position)
        diff_param = (value - self._current_value)

        self._kalman_gradient.update(diff_volts=diff_volts,
                                     diff_params=[diff_param],
                                     measurement_covariance=covariance)

        if is_new_position:
            self._current_value = value
            self._current_position = voltages[self._current_position.index]


class SelfInitializingKalmanEstimator(GradientEstimator):
    """A kalman gradient estimator that initializes itself with finite differences"""
    def __init__(self,
                 finite_difference_estimator: FiniteDifferencesGradientEstimator,
                 kalman_estimator: Optional[KalmanGradientEstimator]=None,
                 kalman_arguments: Optional[dict]=None):
        self._finite_difference_estimator = finite_difference_estimator
        self._kalman_estimator = kalman_estimator
        self._kalman_arguments = kalman_arguments

    @classmethod
    def from_scratch(cls,
                     current_position: pd.Series,
                     epsilon: pd.Series,
                     maximum_covariance: float,
                     symmetric: bool=False):
        finite_differences_estimator = FiniteDifferencesGradientEstimator(current_position=current_position,
                                                                          epsilon=epsilon,
                                                                          symmetric=symmetric)
        kalman_arguments = dict(maximum_covariance=maximum_covariance)

        return cls(finite_difference_estimator=finite_differences_estimator,
                   kalman_arguments=kalman_arguments)

    @property
    def kalman_estimator(self) -> Optional[KalmanGradientEstimator]:
        return self._kalman_estimator

    @property
    def finite_difference_estimator(self) -> FiniteDifferencesGradientEstimator:
        return self._finite_difference_estimator

    @property
    def active_estimator(self) -> GradientEstimator:
        return self._kalman_estimator or self._finite_difference_estimator

    def estimate(self):
        return self.active_estimator.estimate()

    def change_position(self, new_position: pd.Series):
        self._finite_difference_estimator.change_position(new_position)
        if self.kalman_estimator:
            self.kalman_estimator.change_position(new_position)

    def require_measurement(self):
        return self.active_estimator.require_measurement()

    def update(self, voltages: pd.Series, value: float, covariance: float, is_new_position=False):
        self.finite_difference_estimator.update(voltages, value, covariance, is_new_position)

        if self.kalman_estimator:
            self.kalman_estimator.update(voltages, value, covariance, is_new_position)

        elif self.finite_difference_estimator.estimate():
            # we collected enough values to initialize the kalman
            initial_estimate = self.finite_difference_estimator.estimate()
            kalman_gradient = KalmanGradient(n_gates=initial_estimate.size, n_params=1,
                                             initial_gradient=initial_estimate,
                                             initial_covariance_matrix=self.finite_difference_estimator.covariance())
            self._kalman_estimator = KalmanGradientEstimator(kalman_gradient=kalman_gradient,
                                                             current_position=voltages[initial_estimate.index],
                                                             current_value=value,
                                                             epsilon=self._finite_difference_estimator.epsilon,
                                                             **self._kalman_arguments)

    def to_hdf5(self):
        return dict(finite_difference_estimator=self._finite_difference_estimator,
                    kalman_estimator=self._kalman_estimator,
                    kalman_arguments=self._kalman_arguments)
