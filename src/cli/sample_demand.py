from dataclasses import dataclass
from typing import Literal
from src.demand.rng import RNG
from src.demand.arrivals import PoissonArrivals
from src.demand.orders import Catalog, Popularity, OrderSpec, OrderGenerator

def main():
    rng = RNG(seed=42)

    # Arribos
    arrivals = PoissonArrivals(lam_per_min=0.5, horizon_min=60*4, rng=rng)  # 0.5/min x 240min ≈ 120 pedidos
    t = arrivals.sample_times()
    print(f"Arribos: {len(t)} en {max(t) if t else 0:.1f} min. Muestra primeros 5:", [round(x,1) for x in t[:5]])

    # Catálogo + popularidad
    catalog = Catalog(n_skus=200)
    pop = Popularity.make(catalog, mode="concentrada", alpha=1.2)
    gen = OrderGenerator(catalog, pop, OrderSpec(min_items=1, max_items=5, allow_duplicates=True), rng)

    # Ejemplo de 3 pedidos
    for i, ti in enumerate(t[:3], 1):
        o = gen.make_order(ti)
        print(f"Pedido {i} @ {ti:.2f} min -> {len(o.items)} ítems, únicos={len(o.item_counts)} | {o.items[:5]}")

if __name__ == "__main__":
    main()
