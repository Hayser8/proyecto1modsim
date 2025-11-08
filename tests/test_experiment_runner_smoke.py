from pathlib import Path
import pandas as pd
from src.experiments.runner import run_grid

def test_run_grid_smoke(tmp_path: Path):
    csv_path = tmp_path / "grid.csv"
    run_grid(
        out_csv=csv_path,
        policies=["Secuencial_FCFS","Batching_Size"],
        n_pickers_list=[1,2],
        speeds=[60.0],
        congestion_modes=["off"],
        batch_sizes=[5],
        time_thresholds=[2.0],
        popularity_modes=["uniforme"],
        seeds=[3],
        horizon_min=60,
        lam_per_min=0.6,
        n_skus=40
    )
    assert csv_path.exists()
    df = pd.read_csv(csv_path)
    required_cols = {
        "policy","n_pickers","speed_m_per_min","congestion","batch_size","time_threshold_min",
        "sku_popularity","seed","orders_total","makespan_min","throughput_per_hour","avg_wait_min",
        "util_avg","util_max"
    }
    assert required_cols.issubset(set(df.columns))
    assert len(df) >= 3
