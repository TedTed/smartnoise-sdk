import numpy as np

class Laplace:
    def __init__(self, epsilon, tau):
        self.epsilon = epsilon
        self.tau = tau

    def count(self, vals):
        noise = np.random.normal(0.0, self.tau / self.epsilon, len(vals) )
        new_vals = noise + vals
        return new_vals

    def sum_int(self, vals, sensitivity):
        noise = np.random.laplace(0.0, sensitivity / self.epsilon, len(vals))
        return np.array(noise).astype(int) + vals

    def sum_float(self, vals, sensitivity):
        noise = np.random.normal(0.0, sensitivity / self.epsilon, len(vals))
        return noise + vals
