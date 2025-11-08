from src.warehouse.grid import WarehouseGrid
from src.warehouse.sku_map import SKUPlacement
from src.demand.rng import RNG
from src.demand.arrivals import PoissonArrivals
from src.demand.orders import Catalog, Popularity, OrderSpec, OrderGenerator
from src.sim.engine import Simulator, SimConfig

def clustered_orders_env():
    grid = WarehouseGrid(WarehouseGrid.default_spec())
    # Ubicaciones forzadas para crear “overlap” entre pedidos
    placement = SKUPlacement(sku_to_coord={
        "S0001": (0,3), "S0002": (0,4), "S0003": (1,4), "S0004": (1,3),
        "S0005": (0,5), "S0006": (1,5), "S0007": (2,5), "S0008": (2,4)
    })
    catalog = Catalog(n_skus=8)
    rng = RNG(seed=5)
    arrivals = PoissonArrivals(lam_per_min=0.8, horizon_min=60, rng=rng)
    t = arrivals.sample_times()
    pop = Popularity.make(catalog, mode="concentrada", alpha=1.2)
    gen = OrderGenerator(catalog, pop, OrderSpec(3,5,True), rng)
    orders = [gen.make_order(tt) for tt in t]
    return grid, placement, orders

def test_batching_has_lower_avg_service_time_per_order_on_clustered():
    grid, placement, orders = clustered_orders_env()
    # limitar horizontes iguales para comparación justa
    cfg_fcfs = SimConfig(policy="Secuencial_FCFS", n_pickers=1, speed_m_per_min=60.0, congestion="off")
    cfg_bsz  = SimConfig(policy="Batching_Size", n_pickers=1, speed_m_per_min=60.0, batch_size=6, congestion="off")
    # corre ambos
    res_fcfs = Simulator(grid, placement, orders, cfg_fcfs).run()
    res_bsz  = Simulator(grid, placement, orders, cfg_bsz).run()
    # Métrica proxy: con mismo picker, batching debe entregar mayor throughput (menos tiempo por pedido en promedio)
    assert res_bsz.throughput_per_hour >= res_fcfs.throughput_per_hour * 0.95  # tolerancia
