# src/ui/app.py
# Requisitos: pip install customtkinter matplotlib numpy
# Ejecutar:   python -m src.ui.app

import sys, os, time
from typing import List, Optional

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

import numpy as np
import customtkinter as ctk

# ---- paths del proyecto ----
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.warehouse.grid import WarehouseGrid
from src.warehouse.sku_map import SKUPlacement
from src.demand.generator import make_orders
from src.sim.engine import Simulator, SimConfig

# ----------------- helpers de dibujo -----------------
def _draw_grid(ax, w: int, h: int):
    ax.clear()
    ax.set_xlim(-0.5, w - 0.5)
    ax.set_ylim(-0.5, h - 0.5)
    ax.set_aspect('equal')
    ax.set_xticks(np.arange(-0.5, w, 1))
    ax.set_yticks(np.arange(-0.5, h, 1))
    ax.grid(True, which='both', linewidth=0.6)
    ax.invert_yaxis()
    ax.set_xticklabels([])
    ax.set_yticklabels([])

def _plot_frame(ax, meta: dict, pickers: List[dict]):
    station = (meta["station"]["x"], meta["station"]["y"])
    obstacles = [tuple(o) for o in meta.get("obstacles", []) or []]
    _draw_grid(ax, meta["width"], meta["height"])
    if obstacles:
        ox, oy = zip(*obstacles)
        ax.scatter(ox, oy, marker='s', s=90, alpha=0.25)
    ax.scatter([station[0]], [station[1]], marker='o', s=120, edgecolors='k', linewidths=1.2)
    for p in pickers:
        ax.scatter([p["x"]], [p["y"]], s=80)
        ax.text(p["x"] + 0.15, p["y"] - 0.15, f"P{p['picker_id']}", fontsize=8)

# ----------------- simulación -----------------
def _build_trace_from_config(policy, n_pickers, speed_m, congestion, batch_size, time_thr, seed, horizon):
    grid = WarehouseGrid(WarehouseGrid.default_spec())
    placement = SKUPlacement.random_sample(grid, n_skus=120, seed=seed)
    orders = make_orders(seed=seed, horizon=horizon, lam=1.0, popularity="uniforme")[2]
    cfg = SimConfig(
        policy=policy,
        n_pickers=n_pickers,
        speed_m_per_min=speed_m,
        congestion=congestion,
        batch_size=batch_size,
        time_threshold_min=time_thr,
        horizon_min=horizon,
        round_dt=0.25
    )
    sim = Simulator(grid, placement, orders, cfg)
    res = sim.run()
    # ⬇️ Adjunta analytics al resultado que usa la UI
    if hasattr(sim, "analytics"):
        setattr(res, "analytics", sim.analytics)

    spec = grid.spec
    meta = {
        "width": int(spec["width"]),
        "height": int(spec["height"]),
        "station": {"x": int(spec["station"]["x"]), "y": int(spec["station"]["y"])},
        "obstacles": [list(o) for o in (spec.get("obstacles", []) or [])],
    }
    return res, meta, sim.trace_frames

# ====================== UI ======================
POLICY_HELP = {
    "Secuencial_FCFS": (
        "First-Come, First-Served.\n"
        "Atiende cada orden en el orden de llegada (sin batching)."
    ),
    "Batching_Size": (
        "Agrupa órdenes hasta un tamaño fijo (batch_size) y las recoge en un tour."
    ),
    "Batching_Time": (
        "Agrupa por ventana temporal (time_threshold_min) y lanza el tour."
    ),
}

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.title("🔹 Simulador de Picking en Grilla (CustomTkinter)")
        self.geometry("1380x900")
        self.minsize(1200, 780)

        # --- Estado ---
        self.playing: bool = False
        self.play_idx: int = 0
        self.last_tick: float = 0.0
        self.after_id: Optional[str] = None
        self.max_frames_per_tick: int = 3

        self.res = None
        self.meta = None
        self.timeline: List[dict] = []
        self.max_idx: int = 0

        # --- UI ---
        self._build_layout()
        self._bind_events()
        self._refresh_policy_blocks()

    # ---------- Layout ----------
    def _build_layout(self):
        self.columnconfigure(0, weight=0, minsize=360)  # sidebar
        self.columnconfigure(1, weight=1)               # tabview
        self.rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=360, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(self.sidebar, text="Parámetros",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(padx=16, pady=(14, 10), anchor="w")

        self.policy_var = ctk.StringVar(value="Secuencial_FCFS")
        self._frame_policy, self.policy_cb = self._labeled_combobox(
            parent=self.sidebar,
            label="Modo de simulación",
            values=["Secuencial_FCFS", "Batching_Size", "Batching_Time"],
            variable=self.policy_var,
            command=lambda _: self._on_policy_change()
        )
        self.policy_cb.set("Secuencial_FCFS")

        self.policy_help = ctk.CTkTextbox(self.sidebar, height=90, wrap="word")
        self.policy_help.pack(padx=14, pady=(0, 10), fill="x")
        self._set_help_text(POLICY_HELP[self.policy_var.get()])

        self.frame_npick, self.npick_slider, self.npick_val = self._slider(self.sidebar, "# Pickers", 1, 3, 1, 1)
        self.cong_var = ctk.StringVar(value="off")
        self._frame_cong, self.cong_cb = self._labeled_combobox(self.sidebar, "Congestión", ["off", "light"], self.cong_var)
        self.cong_cb.set("off")
        self.frame_speedm, self.speedm_slider, self.speedm_val = self._slider(self.sidebar, "Velocidad (m/min)", 20, 120, 60, 5)
        self.frame_horizon, self.horizon_slider, self.horizon_val = self._slider(self.sidebar, "Horizonte (min)", 30, 240, 120, 10)
        self.seed_var = ctk.StringVar(value="7")
        self._frame_seed, self.seed_entry = self._labeled_entry(self.sidebar, "Seed", self.seed_var)

        self.frame_batchsize, self.batchsize_slider, self.batchsize_val = self._slider(
            self.sidebar, "Batch size", 2, 30, 10, 1, pack_now=False
        )
        self.frame_timethr, self.timethr_slider, self.timethr_val = self._slider(
            self.sidebar, "Threshold de tiempo (min)", 1.0, 10.0, 2.0, 0.5, decimals=1, pack_now=False
        )

        self._separator(self.sidebar, pady=(12, 8))
        ctk.CTkLabel(self.sidebar, text="Animación",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(padx=16, anchor="w")
        self.frame_anim_spd, self.anim_speed_slider, self.anim_speed_val = self._slider(
            self.sidebar, "Velocidad (x)", 0.25, 5.0, 1.0, 0.25, decimals=2
        )
        self.frame_fps, self.fps_slider, self.fps_val = self._slider(self.sidebar, "FPS", 5, 30, 15, 1)
        self.run_btn = ctk.CTkButton(self.sidebar, text="🔁 Re-simular", command=self._run_simulation)
        self.run_btn.pack(padx=14, pady=(8, 12), fill="x")

        # Tabview (Simulación | Análisis)
        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=0, column=1, sticky="nsew", padx=(6, 8), pady=8)
        self.tab_sim = self.tabs.add("Simulación")
        self.tab_ana = self.tabs.add("Análisis")

        # ====== TAB: SIMULACIÓN ======
        self.tab_sim.rowconfigure(0, weight=1)
        self.tab_sim.rowconfigure(1, weight=0)
        self.tab_sim.rowconfigure(2, weight=0)
        self.tab_sim.rowconfigure(3, weight=0)
        self.tab_sim.columnconfigure(0, weight=1)

        # Canvas principal
        self.fig = Figure(figsize=(6.4, 6.0), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab_sim)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        # Toolbar + caption
        tb_row = ctk.CTkFrame(self.tab_sim)
        tb_row.grid(row=1, column=0, sticky="ew", padx=8)
        self.toolbar = NavigationToolbar2Tk(self.canvas, tb_row, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.pack(side="left")
        self.caption_var = ctk.StringVar(value="t = 0.00 min · frame 0/0")
        ctk.CTkLabel(tb_row, textvariable=self.caption_var).pack(side="right", padx=8)

        # KPIs (los 7)
        self.kpi_row = ctk.CTkFrame(self.tab_sim)
        self.kpi_row.grid(row=2, column=0, sticky="ew", padx=8, pady=(2, 8))
        for i in range(7):
            self.kpi_row.columnconfigure(i, weight=1)

        self.k_makes  = self._kpi_card(self.kpi_row, 0, "Makespan (min)")
        self.k_thr    = self._kpi_card(self.kpi_row, 1, "Throughput (ped/h)")
        self.k_done   = self._kpi_card(self.kpi_row, 2, "Órdenes completadas")
        self.k_wait   = self._kpi_card(self.kpi_row, 3, "Espera prom. (min)")
        self.k_p95    = self._kpi_card(self.kpi_row, 4, "P95 espera (min)")
        self.k_util   = self._kpi_card(self.kpi_row, 5, "Utilización prom.")
        self.k_distav = self._kpi_card(self.kpi_row, 6, "Recorrido/prom (m/ped)")

        # Playback
        ctr = ctk.CTkFrame(self.tab_sim)
        ctr.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 8))
        for i in range(6):
            ctr.columnconfigure(i, weight=1)

        self.slider_var = ctk.DoubleVar(value=0.0)
        self.frame_slider = ctk.CTkSlider(ctr, from_=0, to=1, number_of_steps=1,
                                          command=self._on_slider_move, variable=self.slider_var)
        self.frame_slider.grid(row=0, column=0, columnspan=6, sticky="ew", padx=8, pady=(6, 6))

        self.btn_start = ctk.CTkButton(ctr, text="⏮ Inicio", command=self._go_start)
        self.btn_prev  = ctk.CTkButton(ctr, text="◀ -1", command=self._step_prev)
        self.btn_play  = ctk.CTkButton(ctr, text="▶ Reproducir", command=self._toggle_play, fg_color="#0ea5e9")
        self.btn_next  = ctk.CTkButton(ctr, text="+1 ▶", command=self._step_next)
        self.btn_end   = ctk.CTkButton(ctr, text="⏭ Fin", command=self._go_end)
        self.btn_resim = ctk.CTkButton(ctr, text="🔁 Re-simular", command=self._run_simulation)

        for j, b in enumerate([self.btn_start, self.btn_prev, self.btn_play, self.btn_next, self.btn_end, self.btn_resim]):
            b.grid(row=1, column=j, padx=6, pady=6, sticky="ew")

        # ====== TAB: ANÁLISIS ======
        self.tab_ana.rowconfigure(0, weight=0)
        self.tab_ana.rowconfigure(1, weight=1)
        self.tab_ana.columnconfigure(0, weight=1)

        # KPIs (mismos 7, por comodidad de lectura)
        self.kpi2 = ctk.CTkFrame(self.tab_ana)
        self.kpi2.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 8))
        for i in range(7):
            self.kpi2.columnconfigure(i, weight=1)
        self.k2 = [self._kpi_card(self.kpi2, i, t) for i, t in enumerate(
            ["Makespan (min)", "Throughput (ped/h)", "Órdenes completadas",
             "Espera prom. (min)", "P95 espera (min)", "Utilización prom.", "Recorrido/prom (m/ped)"]
        )]

        # Panel de gráficas (4)
        charts = ctk.CTkFrame(self.tab_ana)
        charts.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        for i in range(2):
            charts.columnconfigure(i, weight=1)
            charts.rowconfigure(i, weight=1)

        # 1) Cola
        self.fig_q = Figure(figsize=(3.2, 2.2), dpi=100)
        self.ax_q = self.fig_q.add_subplot(111)
        self.can_q = FigureCanvasTkAgg(self.fig_q, master=charts)
        self.can_q.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        # 2) Curva S
        self.fig_c = Figure(figsize=(3.2, 2.2), dpi=100)
        self.ax_c = self.fig_c.add_subplot(111)
        self.can_c = FigureCanvasTkAgg(self.fig_c, master=charts)
        self.can_c.get_tk_widget().grid(row=0, column=1, sticky="nsew", padx=6, pady=6)

        # 3) Gantt
        self.fig_g = Figure(figsize=(3.2, 2.2), dpi=100)
        self.ax_g = self.fig_g.add_subplot(111)
        self.can_g = FigureCanvasTkAgg(self.fig_g, master=charts)
        self.can_g.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=6, pady=6)

        # 4) Histograma de esperas
        self.fig_h = Figure(figsize=(3.2, 2.2), dpi=100)
        self.ax_h = self.fig_h.add_subplot(111)
        self.can_h = FigureCanvasTkAgg(self.fig_h, master=charts)
        self.can_h.get_tk_widget().grid(row=1, column=1, sticky="nsew", padx=6, pady=6)

    # ---- Helpers UI ----
    def _separator(self, parent, pady=10):
        sep = ctk.CTkFrame(parent, height=1)
        color = ("#3a3a3a", "#3a3a3a")
        sep.configure(fg_color=color)
        sep.pack(fill="x", padx=14, pady=pady)

    def _labeled_entry(self, parent, label: str, variable: ctk.StringVar):
        frame = ctk.CTkFrame(parent)
        frame.pack(padx=14, pady=6, fill="x")
        frame.columnconfigure(1, weight=1)
        ctk.CTkLabel(frame, text=label).grid(row=0, column=0, padx=(6, 8), pady=8, sticky="w")
        entry = ctk.CTkEntry(frame, textvariable=variable)
        entry.grid(row=0, column=1, padx=6, pady=8, sticky="ew")
        return frame, entry

    def _labeled_combobox(self, parent, label: str, values: list, variable: ctk.StringVar, command=None):
        frame = ctk.CTkFrame(parent)
        frame.pack(padx=14, pady=6, fill="x")
        frame.columnconfigure(1, weight=1)
        ctk.CTkLabel(frame, text=label).grid(row=0, column=0, padx=(6, 8), pady=8, sticky="w")
        cb = ctk.CTkComboBox(frame, values=values, variable=variable, state="readonly", command=command)
        cb.grid(row=0, column=1, padx=6, pady=8, sticky="ew")
        return frame, cb

    def _slider(self, parent, label, minv, maxv, init, step, decimals=0, pack_now=True):
        frame = ctk.CTkFrame(parent)
        frame.columnconfigure(1, weight=1)
        ctk.CTkLabel(frame, text=label).grid(row=0, column=0, padx=(6, 8), pady=8, sticky="w")

        def fmt(v: float) -> str:
            return f"{v:.{decimals}f}" if decimals > 0 else f"{int(round(v))}"

        val_lbl = ctk.CTkLabel(frame, text=fmt(init))
        steps = max(1, int(round((maxv - minv) / step)))
        slider = ctk.CTkSlider(
            frame, from_=minv, to=maxv, number_of_steps=steps,
            command=lambda v: val_lbl.configure(text=fmt(float(v)))
        )
        slider.set(init)
        slider.grid(row=0, column=1, padx=6, pady=8, sticky="ew")
        val_lbl.grid(row=0, column=2, padx=(6, 8))
        if pack_now:
            frame.pack(padx=14, pady=6, fill="x")
        return frame, slider, val_lbl

    def _kpi_card(self, parent, col, title):
        card = ctk.CTkFrame(parent, corner_radius=10)
        card.grid(row=0, column=col, sticky="ew", padx=6, pady=4)
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12)).pack(anchor="w", padx=10, pady=(8, 2))
        value = ctk.CTkLabel(card, text="-", font=ctk.CTkFont(size=16, weight="bold"))
        value.pack(anchor="w", padx=10, pady=(0, 8))
        return value

    def _bind_events(self):
        self.policy_var.trace_add("write", lambda *_: self._on_policy_change())

    def _on_policy_change(self):
        self._set_help_text(POLICY_HELP.get(self.policy_var.get(), ""))
        self._refresh_policy_blocks()

    def _refresh_policy_blocks(self):
        try: self.frame_batchsize.pack_forget()
        except Exception: pass
        try: self.frame_timethr.pack_forget()
        except Exception: pass

        pol = self.policy_var.get()
        if pol == "Batching_Size":
            self.frame_batchsize.pack(padx=14, pady=6, fill="x")
        elif pol == "Batching_Time":
            self.frame_timethr.pack(padx=14, pady=6, fill="x")

    def _set_help_text(self, text: str):
        self.policy_help.configure(state="normal")
        self.policy_help.delete("1.0", "end")
        self.policy_help.insert("1.0", text)
        self.policy_help.configure(state="disabled")

    # ---------- Simulación ----------
    def _run_simulation(self):
        self._cancel_tick()

        policy = self.policy_var.get()
        n_pickers = int(round(self.npick_slider.get()))
        congestion = self.cong_var.get()
        speed_m = int(round(self.speedm_slider.get()))
        horizon = int(round(self.horizon_slider.get()))
        seed = int(self.seed_var.get())

        if policy == "Batching_Size":
            batch_size = int(round(self.batchsize_slider.get()))
            time_thr = 0.0
        elif policy == "Batching_Time":
            time_thr = float(self.timethr_slider.get())
            batch_size = 0
        else:
            batch_size, time_thr = 0, 0.0

        try:
            self.res, self.meta, self.timeline = _build_trace_from_config(
                policy, n_pickers, speed_m, congestion, batch_size, time_thr, seed, horizon
            )
        except Exception as e:
            self.caption_var.set(f"Error en simulación: {type(e).__name__}: {e}")
            return

        self.max_idx = max(0, len(self.timeline) - 1)
        self.frame_slider.configure(from_=0, to=max(self.max_idx, 1),
                                    number_of_steps=max(self.max_idx, 1))
        self.frame_slider.set(0)

        self.play_idx = 0
        self._update_kpis()
        self._draw_current_frame()
        self._draw_analysis()  
        self._set_play(False)

    # ---------- Animación ----------
    def _set_play(self, should_play: bool):
        self.playing = should_play
        self.btn_play.configure(text="⏸ Pausar" if should_play else "▶ Reproducir",
                                fg_color=("#ef4444" if should_play else "#0ea5e9"))
        if should_play:
            self.last_tick = 0.0
            self._schedule_tick()
        else:
            self._cancel_tick()

    def _toggle_play(self):
        if not self.timeline:
            self.caption_var.set("Ejecuta la simulación primero.")
            return
        self._set_play(not self.playing)

    def _schedule_tick(self):
        delay = max(10, int(1000 / max(1, int(self.fps_slider.get()))))
        self._cancel_tick()
        self.after_id = self.after(delay, self._tick)

    def _cancel_tick(self):
        if self.after_id is not None:
            try:
                self.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None

    def _tick(self):
        if not self.playing or not self.timeline:
            return
        now = time.perf_counter()
        if self.last_tick == 0.0:
            self.last_tick = now
        elapsed = now - self.last_tick
        dt = 1.0 / max(1, int(self.fps_slider.get()))
        frames_to_advance = int(elapsed / dt * max(0.1, float(self.anim_speed_slider.get())))
        frames_to_advance = max(1, min(frames_to_advance, self.max_frames_per_tick))
        new_idx = min(self.play_idx + frames_to_advance, self.max_idx)
        if new_idx != self.play_idx:
            self.play_idx = new_idx
            self.frame_slider.set(self.play_idx)
            self._draw_current_frame()
            self.last_tick = now
        if self.play_idx >= self.max_idx:
            self._set_play(False)
            return
        self._schedule_tick()

    # ---------- Navegación ----------
    def _go_start(self):
        if not self.timeline: return
        self._set_play(False)
        self.play_idx = 0
        self.frame_slider.set(0)
        self._draw_current_frame()

    def _go_end(self):
        if not self.timeline: return
        self._set_play(False)
        self.play_idx = self.max_idx
        self.frame_slider.set(self.play_idx)
        self._draw_current_frame()

    def _step_prev(self):
        if not self.timeline: return
        self._set_play(False)
        self.play_idx = max(0, self.play_idx - 1)
        self.frame_slider.set(self.play_idx)
        self._draw_current_frame()

    def _step_next(self):
        if not self.timeline: return
        self._set_play(False)
        self.play_idx = min(self.max_idx, self.play_idx + 1)
        self.frame_slider.set(self.play_idx)
        self._draw_current_frame()

    def _on_slider_move(self, value):
        if not self.timeline: return
        self._set_play(False)
        self.play_idx = int(round(float(value)))
        self._draw_current_frame()

    # ---------- Render & KPIs ----------
    def _draw_current_frame(self):
        if not self.timeline:
            self.caption_var.set("t = 0.00 min · frame 0/0")
            _draw_grid(self.ax, 10, 10)
            self.canvas.draw_idle()
            return
        idx = int(self.play_idx)
        frame = self.timeline[idx]
        self.caption_var.set(f"t = {frame['t']:.2f} min · frame {idx+1}/{len(self.timeline)}")
        _plot_frame(self.ax, self.meta, frame["pickers"])
        self.canvas.draw_idle()

    def _update_kpis(self):
        if not self.res:
            for k in [self.k_makes, self.k_thr, self.k_done, self.k_wait, self.k_p95, self.k_util, self.k_distav, *self.k2]:
                k.configure(text="-")
            return

        util_avg = float(np.mean(self.res.picker_utilization)) if self.res.picker_utilization else 0.0
        vals = [
            f"{self.res.makespan_min:.1f}",
            f"{self.res.throughput_per_hour:.2f}",
            f"{self.res.orders_completed:d}",
            f"{self.res.avg_wait_min:.2f}",
            f"{self.res.wait_p95_min:.2f}",
            f"{100*util_avg:.1f}%",
            f"{self.res.distance_per_order_avg_m:.2f}",
        ]
        for lbl, v in zip([self.k_makes, self.k_thr, self.k_done, self.k_wait, self.k_p95, self.k_util, self.k_distav], vals):
            lbl.configure(text=v)
        for i, v in enumerate(vals):
            self.k2[i].configure(text=v)
        
    # ======= helpers visuales =======
    def _fmt_ax(self, ax, title=None, xlabel=None, ylabel=None):
        ax.grid(True, linewidth=0.6, alpha=0.35)
        if title:  ax.set_title(title, fontsize=12, pad=8)
        if xlabel: ax.set_xlabel(xlabel, fontsize=10)
        if ylabel: ax.set_ylabel(ylabel, fontsize=10)
        for sp in ax.spines.values():
            sp.set_alpha(0.4)

    def _freedman_diaconis_bins(self, data):
        # Regla FD: 2 * IQR / n^(1/3)
        import numpy as np
        data = np.asarray(list(data), dtype=float)
        data = data[np.isfinite(data)]
        if data.size < 2:
            return 5
        iqr = np.subtract(*np.percentile(data, [75, 25]))
        if iqr <= 0:
            return min(15, max(5, int(np.sqrt(len(data)))))
        bw = 2.0 * iqr / (len(data) ** (1/3))
        rng = data.max() - data.min()
        if bw <= 0 or rng <= 0:
            return min(15, max(5, int(np.sqrt(len(data)))))
        return max(5, int(np.ceil(rng / bw)))

    # ======= dibujar panel de análisis =======
    def _draw_analysis(self):
        """
        Dibuja:
        1) Cola (jobs) vs tiempo [step]
        2) Órdenes acumuladas (curva S)
        3) Gantt por picker (broken_barh)
        4) Histograma de esperas (+ P95)
        Espera que self.res tenga un dict 'analytics' con llaves típicas;
        si alguna falta, el gráfico se omite con mensaje suave.
        """
        import numpy as np

        an = getattr(self.res, "analytics", {}) or {}

        # ---------- 1) Cola (jobs) vs tiempo ----------
        self.ax_q.cla()
        t_q = an.get("queue_t") or an.get("queue", {}).get("t", [])
        q_q = an.get("queue_q") or an.get("queue", {}).get("q", [])
        if t_q and q_q:
            self.ax_q.step(t_q, q_q, where="post")
            ymax = max(1, int(np.nanmax(q_q)))
            self.ax_q.set_ylim(0, ymax + 0.5)
            self._fmt_ax(self.ax_q, "Cola (jobs) vs tiempo", "min", "# en cola")
        else:
            self.ax_q.text(0.5, 0.5, "Sin datos de cola", ha="center", va="center")
            self._fmt_ax(self.ax_q, "Cola (jobs) vs tiempo", "min", "# en cola")
        self.can_q.draw_idle()

        # ---------- 2) Órdenes acumuladas ----------
        self.ax_c.cla()
        t_c = an.get("completed_t") or an.get("completed", {}).get("t", [])
        y_c = an.get("completed_y") or an.get("completed", {}).get("y", [])
        if t_c and y_c:
            self.ax_c.step(t_c, y_c, where="post")
            self._fmt_ax(self.ax_c, "Órdenes acumuladas", "min", "completadas")
        else:
            self.ax_c.text(0.5, 0.5, "Sin datos de completadas", ha="center", va="center")
            self._fmt_ax(self.ax_c, "Órdenes acumuladas", "min", "completadas")
        self.can_c.draw_idle()

        # ---------- 3) Gantt por picker ----------
        self.ax_g.cla()
        # Acepta dos formatos:
        # an["gantt"] = { pid: [(start, dur), ...], ... }
        # o an["gantt"]["per_picker"] / an["gantt_bars"]
        gantt = an.get("gantt", {})
        if isinstance(gantt, dict) and ("per_picker" in gantt or any(isinstance(v, list) for v in gantt.values())):
            # Normaliza a dict {pid: [(start, dur), ...]}
            if "per_picker" in gantt:
                per = gantt["per_picker"]
                if isinstance(per, list):
                    gantt_dict = {i: lst for i, lst in enumerate(per)}
                else:
                    gantt_dict = dict(per)
            else:
                gantt_dict = {int(pid): bars for pid, bars in gantt.items() if isinstance(bars, list)}
            # broken_barh por fila
            y0, h = 10, 8
            yticks, ylabels = [], []
            for row, pid in enumerate(sorted(gantt_dict.keys())):
                bars = [(float(start), float(dur)) for (start, dur) in gantt_dict[pid] if float(dur) > 0]
                if not bars:
                    continue
                ybase = y0 + row * (h + 6)
                self.ax_g.broken_barh(bars, (ybase, h))
                yticks.append(ybase + h/2)
                ylabels.append(f"P{pid}")
            self.ax_g.set_yticks(yticks)
            self.ax_g.set_yticklabels(ylabels)
            self._fmt_ax(self.ax_g, "Gantt por picker", "min", "")
        else:
            self.ax_g.text(0.5, 0.5, "Sin datos de Gantt", ha="center", va="center")
            self._fmt_ax(self.ax_g, "Gantt por picker", "min", "")
        self.can_g.draw_idle()

        # ---------- 4) Histograma de esperas ----------
        self.ax_h.cla()
        waits = an.get("waits") or an.get("wait_times") or []
        waits = [w for w in waits if np.isfinite(w) and w >= 0]
        if len(waits) >= 1:
            nb = self._freedman_diaconis_bins(waits)
            self.ax_h.hist(waits, bins=nb)
            # Línea P95
            p95 = float(np.percentile(waits, 95)) if len(waits) >= 2 else float(waits[0])
            self.ax_h.axvline(p95, linestyle="--")
            self.ax_h.legend([f"P95 = {p95:.2f}"], loc="best", framealpha=0.3)
            self._fmt_ax(self.ax_h, "Histograma de esperas", "min", "# pedidos")
        else:
            self.ax_h.text(0.5, 0.5, "Sin datos de esperas", ha="center", va="center")
            self._fmt_ax(self.ax_h, "Histograma de esperas", "min", "# pedidos")
        self.can_h.draw_idle()


if __name__ == "__main__":
    app = App()
    app.mainloop()
