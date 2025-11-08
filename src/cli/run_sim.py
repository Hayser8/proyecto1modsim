from src.warehouse.grid import WarehouseGrid
from src.warehouse.sku_map import generate_hotspot_map
from src.demand.rng import RNG
from src.demand.arrivals import PoissonArrivals
from src.demand.orders import Catalog, Popularity, OrderSpec, OrderGenerator
from src.sim.engine import Simulator, SimConfig

def main():
    grid = WarehouseGrid(WarehouseGrid.default_spec())

    catalog = Catalog(n_skus=120)
    popular = catalog.ids()[:24]
    others = catalog.ids()[24:]
    placement = generate_hotspot_map(grid, popular, others)

    rng = RNG(seed=123)
    arrivals = PoissonArrivals(lam_per_min=0.5, horizon_min=240, rng=rng)
    t = arrivals.sample_times()
    pop = Popularity.make(catalog, mode="concentrada", alpha=1.2)
    gen = OrderGenerator(catalog, pop, OrderSpec(1,5,True), rng)
    orders = [gen.make_order(tt) for tt in t]

    cfg = SimConfig(policy="Batching_Size", n_pickers=2, speed_m_per_min=60.0, batch_size=10, congestion="light")
    sim = Simulator(grid, placement, orders, cfg)
    res = sim.run()
    print(f"Orders: {len(orders)}  Completed: {res.orders_completed}")
    print(f"Makespan: {res.makespan_min:.1f} min  Throughput: {res.throughput_per_hour:.2f} orders/h")
    print(f"Avg wait: {res.avg_wait_min:.2f} min  Util: {[round(x,2) for x in res.picker_utilization]}")

if __name__ == "__main__":
    main()
