from snsynth.transform.definitions import ColumnType
from .base import CachingColumnTransformer
from .mechanism import approx_bounds
from snsql.sql.privacy import Privacy
import numpy as np

class MinMaxTransformer(CachingColumnTransformer):
    """Transforms a column of values to scale between 0.0 and 1.0.
    If epsilon is not None, then the bounds of the values are approximated.
    If negative is True, then the values are scaled between -1.0 and 1.0.
    If min and max are not None, then the values are scaled between min and max,
    and no privacy budget is spent.

    :param lower: The minimum value to scale to.
    :param upper: The maximum value to scale to.
    :param negative: Whether to scale between -1.0 and 1.0.
    :param epsilon: The privacy budget to use.
    :return: A transformed column of values.
    """
    def __init__(self, *, lower=None, upper=None, negative=False, epsilon=None, nullable=False, odometer=None):
        self.lower = lower
        self.upper = upper
        self.epsilon = epsilon
        self.negative = negative
        self.budget_spent = []
        self.nullable = nullable
        self.odometer = odometer
        super().__init__()
    @property
    def output_type(self):
        return ColumnType.CONTINUOUS
    @property
    def needs_epsilon(self):
        return self.lower is None or self.upper is None
    def allocate_privacy_budget(self, epsilon, odometer):
        self.epsilon = epsilon
        self.odometer = odometer
    def _fit_finish(self):
        if self.epsilon is not None and self.epsilon > 0.0 and (self.lower is None or self.upper is None):
            self._fit_vals = [v for v in self._fit_vals if v is not None and not (isinstance(v, float) and np.isnan(v))]
            if self.odometer is not None:
                self.odometer.spend(Privacy(self.epsilon, 0.0))
            self.fit_lower, self.fit_upper = approx_bounds(self._fit_vals, self.epsilon)
            self.budget_spent.append(self.epsilon)
            if self.fit_lower is None or self.fit_upper is None:
                raise ValueError("MinMaxTransformer could not find bounds.")
        elif self.lower is None or self.upper is None:
            raise ValueError("MinMaxTransformer requires either epsilon or min and max.")
        else:
            self.fit_lower = self.lower
            self.fit_upper = self.upper
        self._fit_complete = True
        if self.nullable:
            self.output_width = 2
        else:
            self.output_width = 1
    def _clear_fit(self):
        self._reset_fit()
        self.fit_lower = None
        self.fit_upper = None
        # if bounds provided, we can immediately use without fitting
        if self.lower and self.upper:
            self._fit_complete = True
            if self.nullable:
                self.output_width = 2
            else:
                self.output_width = 1
            self.fit_lower = self.lower
            self.fit_upper = self.upper
    def _transform(self, val):
        if not self.fit_complete:
            raise ValueError("MinMaxTransformer has not been fit yet.")
        if self.nullable and (val is None or isinstance(val, float) and np.isnan(val)):
            return (None, 1)
        else:
            val = self.fit_lower if val < self.fit_lower else val
            val = self.fit_upper if val > self.fit_upper else val
            val = (val - self.fit_lower) / (self.fit_upper - self.fit_lower)
            if self.negative:
                val = (val * 2) - 1
        if self.nullable:
            return (val, 0)
        else:
            return val
    def _inverse_transform(self, val):
        if not self.fit_complete:
            raise ValueError("MinMaxTransformer has not been fit yet.")
        if self.nullable:
            v, n = val
            val = v
            if n == 1:
                return None
        if self.negative:
            val = (1 + val) / 2
        val = val * (self.fit_upper - self.fit_lower) + self.fit_lower
        return np.clip(val, self.fit_lower, self.fit_upper)
