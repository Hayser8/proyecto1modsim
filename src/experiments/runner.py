from pathlib import Path
from typing import List, Dict, Any, Iterable
import csv

from src.warehouse.grid import WarehouseGrid
from src.warehouse.sku_map import generate_hotspot_map
from src.demand.rng import RNG
from src.demand.arrivals import PoissonArrivals
from src.demand.orders import Catalog, Popularity, OrderSpec, OrderGenerator
from src.sim.engine import Simulator, SimConfig
from src.experiments.kpis import to_row

def _env(seed:int, n_skus:int, lam:float, horizon:int, pop_mode:str):
    grid = WarehouseGrid(WarehouseGrid.default_spec())
    catalog = Catalog(n_skus=n_skus)
    popular = catalog.ids()[: max(1, n_skus//5)]
    others  = catalog.ids()[len(popular):]
    placement = generate_hotspot_map(grid, popular, others)

    rng = RNG(seed=seed)
    arrivals = PoissonArrivals(lam_per_min=lam, horizon_min=horizon, rng=rng)
    t = arrivals.sample_times()
    pop = Popularity.make(catalog, mode=pop_mode, alpha=1.2 if pop_mode=="concentrada" else 1.0)
    gen = OrderGenerator(catalog, pop, OrderSpec(1,5,True), rng)
    orders = [gen.make_order(tt) for tt in t]
    return grid, placement, orders

def run_grid(
    out_csv: Path,
    # dominio de escenarios
    policies: List[str] = ("Secuencial_FCFS", "Batching_Size", "Batching_Time"),
    n_pickers_list: List[int] = (1,2,3),
    speeds: List[float] = (60.0,),                # m/min (1 m/s ≈ 60 m/min)
    congestion_modes: List[str] = ("off","light"),
    batch_sizes: List[int] = (5,10,15),
    time_thresholds: List[float] = (1.0,2.0,5.0),
    popularity_modes: List[str] = ("uniforme","concentrada"),
    seeds: List[int] = (7,11,23),
    # parámetros comunes del entorno
    horizon_min: int = 240,
    lam_per_min: float = 0.8,
    n_skus: int = 120
) -> Path:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "policy","n_pickers","speed_m_per_min","congestion",
            "batch_size","time_threshold_min","sku_popularity","seed",
            "orders_total","makespan_min","throughput_per_hour",
            "avg_wait_min","util_avg","util_max"
        ])
        w.writeheader()

        for seed in seeds:
            for pop_mode in popularity_modes:
                grid, placement, orders = _env(seed, n_skus, lam_per_min, horizon_min, pop_mode)

                for policy in policies:
                    for n_pickers in n_pickers_list:
                        for speed in speeds:
                            for congest in congestion_modes:
                                # elegir params según policy
                                if policy == "Secuencial_FCFS":
                                    cfg = SimConfig(policy=policy, n_pickers=n_pickers,
                                                    speed_m_per_min=speed, congestion=congest,
                                                    horizon_min=horizon_min)
                                    sim = Simulator(grid, placement, orders, cfg)
                                    res = sim.run()
                                    row = to_row(policy, n_pickers, speed, congest, 0, 0.0, pop_mode, seed, res)
                                    w.writerow(row.to_dict())
                                elif policy == "Batching_Size":
                                    for bsz in batch_sizes:
                                        cfg = SimConfig(policy=policy, n_pickers=n_pickers,
                                                        speed_m_per_min=speed, congestion=congest,
                                                        batch_size=bsz, horizon_min=horizon_min)
                                        sim = Simulator(grid, placement, orders, cfg)
                                        res = sim.run()
                                        row = to_row(policy, n_pickers, speed, congest, bsz, 0.0, pop_mode, seed, res)
                                        w.writerow(row.to_dict())
                                elif policy == "Batching_Time":
                                    for thr in time_thresholds:
                                        cfg = SimConfig(policy=policy, n_pickers=n_pickers,
                                                        speed_m_per_min=speed, congestion=congest,
                                                        time_threshold_min=thr, horizon_min=horizon_min)
                                        sim = Simulator(grid, placement, orders, cfg)
                                        res = sim.run()
                                        row = to_row(policy, n_pickers, speed, congest, 0, thr, pop_mode, seed, res)
                                        w.writerow(row.to_dict())
    return out_csv
