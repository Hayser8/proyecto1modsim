# src/cli/dump_trace.py
import json
from pathlib import Path

from src.warehouse.grid import WarehouseGrid
from src.warehouse.sku_map import generate_hotspot_map
from src.demand.rng import RNG
from src.demand.arrivals import PoissonArrivals
from src.demand.orders import Catalog, Popularity, OrderSpec, OrderGenerator
from src.sim.engine import SimConfig
from src.api.simtrace import simulate_with_trace

OUT_DIR = Path("outputs/ui_trace")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    # --- layout y placement demo ---
    grid = WarehouseGrid(WarehouseGrid.default_spec())
    catalog = Catalog(n_skus=40)
    popular = catalog.ids()[:8]
    others  = catalog.ids()[8:]
    placement = generate_hotspot_map(grid, popular, others)

    # --- demanda demo ---
    rng = RNG(seed=42)
    arrivals = PoissonArrivals(lam_per_min=0.7, horizon_min=120, rng=rng)
    times = arrivals.sample_times()
    pop = Popularity.make(catalog, mode="concentrada", alpha=1.2)
    gen = OrderGenerator(catalog, pop, OrderSpec(1,3,True), rng)
    orders = [gen.make_order(t) for t in times]

    # --- config con traza ---
    cfg = SimConfig(
        policy="Batching_Size",
        n_pickers=2,
        speed_m_per_min=60.0,
        batch_size=10,
        congestion="light",
        horizon_min=120.0,
        trace_dt=0.25,   # << activar traza
    )

    trace, kpis = simulate_with_trace(grid, placement, orders, cfg, round_dt=0.25)

    # guardar
    json_path = OUT_DIR / "trace.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(trace, f, ensure_ascii=False)
    print(f"[OK] Trace JSON → {json_path}  (timeline frames: {len(trace['timeline'])})")

    csv_path = OUT_DIR / "kpis.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        headers = ["makespan_min","orders_completed","throughput_per_hour","avg_wait_min","picker_utilization"]
        f.write(",".join(headers) + "\n")
        f.write(f"{kpis['makespan_min']},{kpis['orders_completed']},{kpis['throughput_per_hour']},{kpis['avg_wait_min']},{'|'.join(map(str,kpis['picker_utilization']))}\n")
    print(f"[OK] KPIs CSV  → {csv_path}")

if __name__ == "__main__":
    main()
