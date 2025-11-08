from src.warehouse.grid import WarehouseGrid
from src.warehouse.sku_map import generate_hotspot_map
from src.demand.rng import RNG
from src.demand.arrivals import PoissonArrivals
from src.demand.orders import Catalog, Popularity, OrderSpec, OrderGenerator
from src.picking.tours import order_tour, batch_tour
from src.picking.batching import SizeThresholdBatching, TimeThresholdBatching

def main():
    # Layout
    grid = WarehouseGrid(WarehouseGrid.default_spec())

    # Catálogo y mapa de SKUs
    catalog = Catalog(n_skus=100)
    pop = Popularity.make(catalog, mode="concentrada", alpha=1.2)
    rng = RNG(seed=10)
    popular = catalog.ids()[:20]
    others = catalog.ids()[20:]
    placement = generate_hotspot_map(grid, popular, others)

    # Arribos + pedidos
    arrivals = PoissonArrivals(lam_per_min=0.4, horizon_min=120, rng=rng)
    t = arrivals.sample_times()[:10]  # primeros 10 para demo
    gen = OrderGenerator(catalog, pop, OrderSpec(1, 5, True), rng)
    orders = [gen.make_order(tt) for tt in t]

    # Rutas por pedido
    dists = [order_tour(grid, placement, o) for o in orders]
    print("Distancias por pedido (m):", [round(x.meters,1) for x in dists])

    # Batching por tamaño
    sb = SizeThresholdBatching(batch_size=3)
    batches = sb.make_batches(orders)
    bt = [batch_tour(grid, placement, b.orders) for b in batches]
    print("Batching(size=3) → #batches:", len(batches), "dist(m):", [round(x.meters,1) for x in bt])

    # Batching por tiempo (2 min)
    tb = TimeThresholdBatching(threshold_min=2.0)
    batches2 = tb.make_batches(orders)
    bt2 = [batch_tour(grid, placement, b.orders) for b in batches2]
    print("Batching(time=2) → #batches:", len(batches2), "dist(m):", [round(x.meters,1) for x in bt2])

if __name__ == "__main__":
    main()
