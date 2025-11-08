from dataclasses import dataclass, asdict
from typing import Dict, Any, List
from statistics import mean
from src.sim.engine import SimResult

@dataclass
class RowKPIs:
    policy: str
    n_pickers: int
    speed_m_per_min: float
    congestion: str
    batch_size: int
    time_threshold_min: float
    sku_popularity: str
    seed: int

    orders_total: int
    makespan_min: float
    throughput_per_hour: float
    avg_wait_min: float
    util_avg: float
    util_max: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

def to_row(policy: str, n_pickers: int, speed: float, congestion: str,
           batch_size: int, time_thr: float, sku_pop: str, seed: int,
           res: SimResult) -> RowKPIs:
    util_avg = mean(res.picker_utilization) if res.picker_utilization else 0.0
    util_max = max(res.picker_utilization) if res.picker_utilization else 0.0
    return RowKPIs(
        policy=policy,
        n_pickers=n_pickers,
        speed_m_per_min=speed,
        congestion=congestion,
        batch_size=batch_size,
        time_threshold_min=time_thr,
        sku_popularity=sku_pop,
        seed=seed,
        orders_total=res.orders_completed,
        makespan_min=res.makespan_min,
        throughput_per_hour=res.throughput_per_hour,
        avg_wait_min=res.avg_wait_min,
        util_avg=util_avg,
        util_max=util_max
    )
