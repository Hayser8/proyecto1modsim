from pathlib import Path
from src.experiments.runner import run_grid
from src.experiments.plots import plot_throughput_by_policy, plot_wait_box_by_policy

def main():
    out_csv = Path("outputs/experiments/exp_grid.csv")
    csv_path = run_grid(
        out_csv=out_csv,
        policies=["Secuencial_FCFS","Batching_Size","Batching_Time"],
        n_pickers_list=[1,2,3],
        speeds=[60.0],
        congestion_modes=["off","light"],
        batch_sizes=[5,10],
        time_thresholds=[1.0,2.0],
        popularity_modes=["uniforme","concentrada"],
        seeds=[7,11],       # rápido para demo; puedes ampliarlo
        horizon_min=180,
        lam_per_min=0.8,
        n_skus=120
    )
    print(f"CSV: {csv_path}")

    plot_throughput_by_policy(csv_path, Path("outputs/plots/throughput_by_policy.png"))
    plot_wait_box_by_policy(csv_path, Path("outputs/plots/wait_box_by_policy.png"))
    print("Gráficas en outputs/plots/")

if __name__ == "__main__":
    main()
