from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

def plot_throughput_by_policy(csv_path: Path, out_png: Path):
    df = pd.read_csv(csv_path)
    agg = (df
        .groupby(["policy","n_pickers"], as_index=False)["throughput_per_hour"]
        .mean())
    plt.figure()
    for pol in agg["policy"].unique():
        sub = agg[agg["policy"]==pol]
        plt.plot(sub["n_pickers"], sub["throughput_per_hour"], marker="o", label=pol)
    plt.xlabel("Pickers")
    plt.ylabel("Throughput (orders/h)")
    plt.title("Throughput promedio por política y N pickers")
    plt.legend()
    plt.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png)
    plt.close()

def plot_wait_box_by_policy(csv_path: Path, out_png: Path):
    df = pd.read_csv(csv_path)
    plt.figure()
    # boxplot por política (todas las combinaciones promediadas en la muestra)
    data = [df[df["policy"]==p]["avg_wait_min"].values for p in df["policy"].unique()]
    plt.boxplot(data, labels=df["policy"].unique())
    plt.ylabel("Espera promedio (min)")
    plt.title("Distribución de espera por política")
    plt.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png)
    plt.close()
