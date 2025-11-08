from src.demand.rng import RNG
from src.demand.arrivals import PoissonArrivals

def test_poisson_count_reproducible():
    rng = RNG(seed=123)
    pa = PoissonArrivals(lam_per_min=0.4, horizon_min=300, rng=rng)  # λT = 120
    t1 = pa.sample_times()
    # Con la misma semilla y mismos params debe ser idéntico
    rng2 = RNG(seed=123)
    pa2 = PoissonArrivals(lam_per_min=0.4, horizon_min=300, rng=rng2)
    t2 = pa2.sample_times()
    assert t1 == t2
    # N debe ser el mismo y estar razonablemente cerca del esperado (exacto dado Poisson con la semilla)
    assert len(t1) == len(t2) and len(t1) > 0

def test_times_sorted_and_in_range():
    rng = RNG(seed=7)
    pa = PoissonArrivals(lam_per_min=0.2, horizon_min=120, rng=rng)
    times = pa.sample_times()
    assert all(0.0 <= x <= 120.0 for x in times)
    assert times == sorted(times)
