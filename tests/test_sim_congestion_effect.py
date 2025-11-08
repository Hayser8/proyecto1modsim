from src.warehouse.grid import WarehouseGrid
from src.warehouse.sku_map import generate_hotspot_map
from src.demand.rng import RNG
from src.demand.arrivals import PoissonArrivals
from src.demand.orders import Catalog, Popularity, OrderSpec, OrderGenerator
from src.sim.engine import Simulator, SimConfig

def setup_env(seed=22):
    grid = WarehouseGrid(WarehouseGrid.default_spec())
    catalog = Catalog(n_skus=80)
    popular = catalog.ids()[:16]
    others = catalog.ids()[16:]
    placement = generate_hotspot_map(grid, popular, others)

    rng = RNG(seed=seed)
    arrivals = PoissonArrivals(lam_per_min=0.8, horizon_min=180, rng=rng)
    t = arrivals.sample_times()
    pop = Popularity.make(catalog, mode="concentrada", alpha=1.2)
    gen = OrderGenerator(catalog, pop, OrderSpec(1,5,True), rng)
    orders = [gen.make_order(tt) for tt in t]
    return grid, placement, orders

def test_congestion_light_reduces_gain():
    grid, placement, orders = setup_env()
    cfg_off = SimConfig(policy="Batching_Size", n_pickers=2, speed_m_per_min=60.0, batch_size=8, congestion="off")
    cfg_light = SimConfig(policy="Batching_Size", n_pickers=2, speed_m_per_min=60.0, batch_size=8, congestion="light")
    res_off = Simulator(grid, placement, orders, cfg_off).run()
    res_light = Simulator(grid, placement, orders, cfg_light).run()
    assert res_off.throughput_per_hour >= res_light.throughput_per_hour  # la congestión no ayuda
