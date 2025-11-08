# tests/test_sim_fcfs_vs_two_pickers.py
from src.warehouse.grid import WarehouseGrid
from src.warehouse.sku_map import generate_hotspot_map
from src.demand.rng import RNG
from src.demand.arrivals import PoissonArrivals
from src.demand.orders import Catalog, Popularity, OrderSpec, OrderGenerator
from src.sim.engine import Simulator, SimConfig

def make_orders(n_skus=60, lam=0.6, horizon=120, seed=7):
    grid = WarehouseGrid(WarehouseGrid.default_spec())
    catalog = Catalog(n_skus=n_skus)
    popular = catalog.ids()[:12]
    others = catalog.ids()[12:]
    placement = generate_hotspot_map(grid, popular, others)

    rng = RNG(seed=seed)
    arrivals = PoissonArrivals(lam_per_min=lam, horizon_min=horizon, rng=rng)
    t = arrivals.sample_times()
    pop = Popularity.make(catalog, mode="concentrada", alpha=1.2)
    gen = OrderGenerator(catalog, pop, OrderSpec(1,5,True), rng)
    orders = [gen.make_order(tt) for tt in t]
    return grid, placement, orders

def test_two_pickers_outperform_or_equal_fcfs_low_load():
    """Baja carga: 2 pickers no deben ser peores; deben reducir espera/utilización."""
    grid, placement, orders = make_orders(seed=10, lam=0.6, horizon=120)
    cfg1 = SimConfig(policy="Secuencial_FCFS", n_pickers=1, speed_m_per_min=60.0, congestion="off", horizon_min=120)
    cfg2 = SimConfig(policy="Secuencial_FCFS", n_pickers=2, speed_m_per_min=60.0, congestion="off", horizon_min=120)
    res1 = Simulator(grid, placement, orders, cfg1).run()
    res2 = Simulator(grid, placement, orders, cfg2).run()
    assert res2.throughput_per_hour >= res1.throughput_per_hour - 1e-9
    assert res2.avg_wait_min <= res1.avg_wait_min + 1e-9
    assert sum(res2.picker_utilization)/2 <= res1.picker_utilization[0] + 1e-6

def test_two_pickers_better_latency_under_load_saturated():
    """
    En carga alta con horizonte fijo, 2 pickers deben mantener (o mejorar) throughput,
    y reducir latencia (espera) y presión por picker (utilización).
    """
    grid, placement, orders = make_orders(seed=11, lam=1.8, horizon=120)

    cfg1 = SimConfig(policy="Secuencial_FCFS", n_pickers=1, speed_m_per_min=40.0,
                     congestion="off", horizon_min=120)
    cfg2 = SimConfig(policy="Secuencial_FCFS", n_pickers=2, speed_m_per_min=40.0,
                     congestion="off", horizon_min=120)

    res1 = Simulator(grid, placement, orders, cfg1).run()
    res2 = Simulator(grid, placement, orders, cfg2).run()

    # Throughput no debe ser menor (mismo horizonte)
    assert res2.throughput_per_hour >= res1.throughput_per_hour - 1e-9
    assert res2.orders_completed >= res1.orders_completed

    # Latencia: 2 pickers deben reducir la espera promedio
    assert res2.avg_wait_min < res1.avg_wait_min

    # Presión por picker: menor utilización promedio y menor pico de utilización
    avg_util_1p = res1.picker_utilization[0]
    avg_util_2p = sum(res2.picker_utilization) / 2
    assert avg_util_2p < avg_util_1p + 1e-9
    assert max(res2.picker_utilization) < avg_util_1p + 1e-9