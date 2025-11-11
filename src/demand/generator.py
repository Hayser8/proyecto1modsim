# src/demand/generator.py
from typing import List, Tuple
from .rng import RNG
from .arrivals import PoissonArrivals
from .orders import Catalog, Popularity, OrderSpec, OrderGenerator, Order

def make_orders(
    seed: int,
    horizon: float,
    lam: float,
    popularity: str = "uniforme",
    n_skus: int = 120,
    min_items: int = 1,
    max_items: int = 5,
    allow_duplicates: bool = True,
) -> Tuple[None, None, List[Order]]:
    """
    Devuelve (None, None, orders) para ser compatible con tu app actual,
    que usa el índice [2] para extraer la lista de órdenes.
    """
    rng = RNG(seed=seed)

    catalog = Catalog(n_skus=n_skus)
    pop = Popularity.make(catalog, mode=popularity)
    spec = OrderSpec(min_items=min_items, max_items=max_items, allow_duplicates=allow_duplicates)
    og = OrderGenerator(catalog=catalog, popularity=pop, spec=spec, rng=rng)

    arrivals = PoissonArrivals(lam_per_min=lam, horizon_min=int(horizon), rng=rng)
    times = arrivals.sample_times()

    orders = [og.make_order(t) for t in times]
    return (None, None, orders)
