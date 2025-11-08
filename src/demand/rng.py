from dataclasses import dataclass
from typing import Optional
import numpy as np

@dataclass
class RNG:
    """RNG centralizado para reproducibilidad entre módulos."""
    seed: Optional[int] = None

    def __post_init__(self):
        self._rs = np.random.default_rng(self.seed)

    def integers(self, *args, **kwargs):
        return self._rs.integers(*args, **kwargs)

    def random(self, *args, **kwargs):
        return self._rs.random(*args, **kwargs)

    def poisson(self, lam, size=None):
        return self._rs.poisson(lam=lam, size=size)

    def exponential(self, scale, size=None):
        return self._rs.exponential(scale=scale, size=size)

    def choice(self, a, size=None, replace=True, p=None):
        return self._rs.choice(a, size=size, replace=replace, p=p)

    def shuffle(self, x):
        return self._rs.shuffle(x)

    def normal(self, *args, **kwargs):
        return self._rs.normal(*args, **kwargs)
