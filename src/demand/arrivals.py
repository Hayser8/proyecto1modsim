from dataclasses import dataclass
from typing import List
from .rng import RNG

@dataclass
class PoissonArrivals:
    """Genera tiempos de llegada (minutos) en [0, horizon_min] para un proceso Poisson(λ)."""
    lam_per_min: float   # λ en llegadas por minuto
    horizon_min: int     # horizonte en minutos
    rng: RNG

    def sample_times(self) -> List[float]:
        """
        Estrategia estable y fácil de testear:
        1) N ~ Poisson(λ * T)
        2) N tiempos ~ Uniform(0, T) y se ordenan
        (equivalente en distribución a proceso Poisson homogéneo).
        """
        assert self.lam_per_min >= 0.0
        assert self.horizon_min > 0
        expected = self.lam_per_min * self.horizon_min
        n = int(self.rng.poisson(expected))
        if n == 0:
            return []
        u = self.rng.random(n) * self.horizon_min
        return sorted(u.tolist())
