# src/api/simtrace.py
from typing import Dict, Any, Tuple
from src.sim.engine import Simulator, SimConfig
from src.visual.frames import compose_trace

def simulate_with_trace(grid, placement, orders, cfg: SimConfig, round_dt: float = 0.25) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Corre la simulación con traza y devuelve:
      - trace: { meta, timeline }
      - kpis:  { makespan_min, orders_completed, throughput_per_hour, avg_wait_min, picker_utilization }
    Requiere cfg.trace_dt no None.
    """
    assert cfg.trace_dt is not None, "cfg.trace_dt debe ser > 0 para generar traza."
    sim = Simulator(grid, placement, orders, cfg)
    res = sim.run()
    trace = compose_trace(grid, placement, res.frames or [], round_dt=round_dt)
    kpis = {
        "makespan_min": res.makespan_min,
        "orders_completed": res.orders_completed,
        "throughput_per_hour": res.throughput_per_hour,
        "avg_wait_min": res.avg_wait_min,
        "picker_utilization": res.picker_utilization
    }
    return trace, kpis
