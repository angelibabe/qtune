from qtune.sm import ChargeDiagram
import numpy as np
import pickle


def initialcovarianceandnoise(ch_diag: ChargeDiagram, n_noise=30, n_cov=30, savetofile=True,
                              filename=r'Y:\GaAs\Autotune\Data\UsingPython\heuristics_kalman\NoiseCov.pickle'):
    position_histo = np.zeros((n_noise, 2))
    grad_histo = np.zeros((n_cov, 2, 2))

    for i in range(0, n_noise):
        position_histo[i] = ch_diag.measure_positions()

    for i in range(0, n_cov):
        grad_histo[i] = ch_diag.calculate_gradient()

    std_position = np.std(position_histo, 0)
    std_grad = np.std(grad_histo, 0)

    if savetofile:
        data = {'position_histo': position_histo, 'grad_histo': grad_histo, 'std_position': std_position,
                'std_grad': std_grad}

        with open(filename, 'wb') as handle:
            pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)

    return std_position, std_grad


def load_covandnoise(filename=r'Y:\GaAs\Autotune\Data\UsingPython\heuristics_kalman\NoiseCov.pickle'):
    with open(filename, 'rb') as handle:
        data = pickle.load(handle)
    initP = np.zeros((4, 4))
    std_grad = data["std_grad"]
    initP[0, 0] = 2. * std_grad[0, 0]
    initP[1, 1] = 2. * std_grad[0, 1]
    initP[2, 2] = 2. * std_grad[1, 0]
    initP[3, 3] = 2. * std_grad[1, 1]
    initR = np.zeros((2, 2))
    std_position = data["std_position"]
    initR[0, 0] = (2. * std_position[0]) * (2. * std_position[0])
    initR[1, 1] = (2. * std_position[1]) * (2. * std_position[1])
    return initP, initR