# src/sim/engine.py
from dataclasses import dataclass
from typing import List, Literal, Optional, Deque, Tuple
from collections import deque
import numpy as np

from src.sim.events import Event, EventQueue, Job
from src.sim.policies import (
    build_jobs_sequential, build_jobs_batch_size, build_jobs_batch_time
)
from src.warehouse.grid import WarehouseGrid
from src.warehouse.sku_map import SKUPlacement
from src.demand.orders import Order
from src.picking.tours import order_tour_path, batch_tour_path

CongestionMode = Literal["off", "light"]


# --------------------------- Estados y resultados ---------------------------

@dataclass
class PickerState:
    busy_until: float = 0.0
    busy_time: float = 0.0
    completed_orders: int = 0


@dataclass
class SimConfig:
    policy: str                      # "Secuencial_FCFS" | "Batching_Size" | "Batching_Time"
    n_pickers: int
    speed_m_per_min: float
    congestion: CongestionMode = "off"
    batch_size: int = 10
    time_threshold_min: float = 2.0
    horizon_min: Optional[float] = None  # si None, corre hasta acabar jobs
    round_dt: float = 0.25               # dt SOLO para traza visual


@dataclass
class SimResult:
    makespan_min: float
    orders_completed: int
    throughput_per_hour: float
    avg_wait_min: float
    picker_utilization: List[float]

    # Imprescindibles extendidos
    wait_p90_min: float
    wait_p95_min: float
    distance_total_m: float
    distance_per_order_avg_m: float

    # Batching (0 si no aplica)
    batches_count: int
    batch_avg_size: float
    batch_pct_ge2: float
    batch_avg_release_min: float    # Batching_Time
    batch_avg_fill_min: float       # Batching_Size

    # Series para pestaña de análisis
    ts_queue: List[Tuple[float, int]]            # (t, jobs en cola)
    ts_completed: List[Tuple[float, int]]        # (t, órdenes acumuladas)
    gantt: List[List[Tuple[float, float, int]]]  # por picker: [(t0,t1,job_id),...]
    waits_raw: List[float]                        # esperas por pedido

    # Diagnóstico por picker
    picker_idle_min: List[float]
    picker_tours: List[int]


# ------------------------------- Simulador ---------------------------------

class Simulator:
    """
    Simulador basado en eventos (ARRIVAL / PICKER_FREE) con traza para UI.
    """

    def __init__(
        self,
        grid: WarehouseGrid,
        placement: SKUPlacement,
        orders: List[Order],
        cfg: SimConfig,
    ):
        self.grid = grid
        self.placement = placement
        self.orders = sorted(orders, key=lambda o: o.arrival_min)
        self.cfg = cfg

        # Construcción de jobs según política
        if cfg.policy == "Secuencial_FCFS":
            self.jobs = build_jobs_sequential(self.orders, grid, placement, cfg.speed_m_per_min)
        elif cfg.policy == "Batching_Size":
            self.jobs = build_jobs_batch_size(self.orders, grid, placement, cfg.speed_m_per_min, cfg.batch_size)
        elif cfg.policy == "Batching_Time":
            self.jobs = build_jobs_batch_time(self.orders, grid, placement, cfg.speed_m_per_min, cfg.time_threshold_min)
        else:
            raise ValueError(f"Política no soportada: {cfg.policy}")

        # Estado de simulación
        self.now: float = 0.0
        self.evq = EventQueue()
        self.waiting: Deque[Job] = deque()
        self.pickers: List[PickerState] = [PickerState() for _ in range(cfg.n_pickers)]
        self.analytics = {
            "queue_t": [0.0],          # tiempos de muestreo de cola
            "queue_q": [0],            # tamaño de cola en cada tiempo
            "completed_t": [0.0],      # tiempos de completadas acumuladas
            "completed_y": [0],        # completadas acumuladas
            "gantt": {},               # pid -> [(start, dur), ...]
            "waits": []                # lista de esperas por pedido (min)
        }
        self.orders_completed: int = 0

        # Métricas agregadas
        self.order_waits: List[float] = []                # lista cruda de esperas por pedido
        self.picker_tours: List[int] = [0] * cfg.n_pickers
        self.distance_total_m: float = 0.0

        # Series para análisis
        self.ts_queue: List[Tuple[float, int]] = [(0.0, 0)]
        self.ts_completed: List[Tuple[float, int]] = [(0.0, 0)]
        self.gantt: List[List[Tuple[float, float, int]]] = [[] for _ in range(cfg.n_pickers)]

        # Métricas de batching
        self.batches_sizes: List[int] = []
        self.batches_release: List[float] = []   # instante de release del lote
        self.batches_fill: List[float] = []      # tiempo de llenado (size)

        # --------- Traza visual ----------
        spec = self.grid.spec
        if not isinstance(spec, dict):
            raise ValueError("WarehouseGrid.spec debe ser dict con keys: width, height, station, obstacles.")
        for k in ("width", "height", "station", "obstacles"):
            if k not in spec:
                raise ValueError(f"WarehouseGrid.spec debe exponer '{k}'")

        stx, sty = int(spec["station"]["x"]), int(spec["station"]["y"])
        self._picker_xy: List[Tuple[int, int]] = [(stx, sty) for _ in range(cfg.n_pickers)]
        self._picker_job: List[Optional[int]] = [None for _ in range(cfg.n_pickers)]
        self._picker_state: List[str] = ["idle" for _ in range(cfg.n_pickers)]

        # Timeline final para la UI (se construye al final con tracks)
        self.trace_frames: List[dict] = []

        # --- Tracks por picker (keyframes) ---
        # Cada item: (t, x, y, state, job_id)
        self._tracks: List[List[Tuple[float, int, int, str, Optional[int]]]] = [[] for _ in range(cfg.n_pickers)]
        for pid in range(cfg.n_pickers):
            self._tracks[pid].append((0.0, stx, sty, "idle", None))

        # Arribos de jobs
        for job in self.jobs:
            self.evq.push(Event(time=job.arrival_min, etype="ARRIVAL", payload=job))

    # ----------------------- Utilidades internas -----------------------

    def _congestion_multiplier(self, active_pickers: int) -> float:
        mode = self.cfg.congestion
        if mode == "off":
            return 1.0
        # activa desde 2 en adelante: 1 + alpha*(active-1)
        alpha = 0.15  # “light”: ~15% por picker extra
        return 1.0 + alpha * max(0, active_pickers -  1)
    
    def _log_queue(self):
        self.analytics["queue_t"].append(float(self.now))
        self.analytics["queue_q"].append(int(len(self.waiting)))

    # (quedó por compatibilidad; ya no se usa para construir timeline)
    def _snapshot(self, t: float):
        self.trace_frames.append({
            "t": float(t),
            "pickers": [
                {"picker_id": i, "x": int(self._picker_xy[i][0]), "y": int(self._picker_xy[i][1]),
                 "state": self._picker_state[i], "job_id": self._picker_job[i]}
                for i in range(len(self._picker_xy))
            ],
        })

    # -------- keyframes & fusión a timeline --------
    def _keyframe(self, pid: int, t: float, xy: Tuple[int, int], state: str, job_id: Optional[int]):
        self._tracks[pid].append((float(t), int(xy[0]), int(xy[1]), state, job_id))

    def _build_timeline_from_tracks(self, end_time: float):
        # 1) tiempos únicos
        times = sorted({t for track in self._tracks for (t, *_ ) in track})
        if not times or times[0] > 0.0:
            times = [0.0] + times
        if not times or times[-1] < end_time:
            times.append(float(end_time))

        # 2) punteros y último estado conocido por picker
        idx = [0] * len(self._tracks)
        last = [self._tracks[i][0] for i in range(len(self._tracks))]

        self.trace_frames = []
        for t in times:
            for pid, track in enumerate(self._tracks):
                while idx[pid] + 1 < len(track) and track[idx[pid] + 1][0] <= t + 1e-12:
                    idx[pid] += 1
                last[pid] = track[idx[pid]]
            self.trace_frames.append({
                "t": float(t),
                "pickers": [
                    {"picker_id": pid, "x": last[pid][1], "y": last[pid][2],
                     "state": last[pid][3], "job_id": last[pid][4]}
                    for pid in range(len(self._tracks))
                ],
            })

    def _build_path_for_job(self, job: Job) -> List[Tuple[float, float]]:
        orders = getattr(job, "orders", None)
        if not orders:
            return []
        if job.n_orders == 1:
            return order_tour_path(self.grid, self.placement, orders[0], return_to_station=True)
        return batch_tour_path(self.grid, self.placement, orders, return_to_station=True)

    def _path_length_m(self, path: List[Tuple[int, int]]) -> float:
        if not path or len(path) < 2:
            return 0.0
        return float(len(path) - 1)  # 1 m por celda

    def _animate_job(self, pid: int, job: Job, start_t: float, duration_min: float, job_path: List[Tuple[int, int]]):
        """Emite keyframes por picker; la fusión a frames completos se hace al final."""
        path = job_path

        # Sin path (o trivial)
        if not path or len(path) < 2:
            # mantén posición actual y crea dos keyframes
            self._picker_job[pid] = job.job_id
            self._picker_state[pid] = "moving"
            self._keyframe(pid, start_t, self._picker_xy[pid], "moving", job.job_id)
            self._picker_state[pid] = "idle"
            self._picker_job[pid] = None
            self._keyframe(pid, start_t + duration_min, self._picker_xy[pid], "idle", None)
            return

        steps = len(path) - 1
        step_total = duration_min / steps if steps > 0 else duration_min
        dt = max(self.cfg.round_dt, 1e-6)

        # estado inicial
        self._picker_job[pid] = job.job_id
        self._picker_state[pid] = "moving"
        self._picker_xy[pid] = (int(path[0][0]), int(path[0][1]))
        t = start_t
        self._keyframe(pid, t, self._picker_xy[pid], "moving", job.job_id)

        # recorrer path
        for i in range(steps):
            next_xy = (int(path[i + 1][0]), int(path[i + 1][1]))
            t_end_seg = t + step_total

            while t + dt < t_end_seg - 1e-9:
                t += dt
                self._keyframe(pid, t, self._picker_xy[pid], "moving", job.job_id)

            t = t_end_seg
            self._picker_xy[pid] = next_xy
            self._keyframe(pid, t, self._picker_xy[pid], "moving", job.job_id)

        self._picker_state[pid] = "idle"
        self._picker_job[pid] = None
        self._keyframe(pid, t, self._picker_xy[pid], "idle", None)

    def _assign_if_possible(self):
        changed_queue = False

        # Asignar en bucle: mientras haya cola y pickers libres al tiempo actual
        while self.waiting:
            free = [(pid, p) for pid, p in enumerate(self.pickers) if p.busy_until <= self.now]
            if not free:
                break

            # toma el picker libre con menor busy_until (el más “disponible”)
            pid, p = min(free, key=lambda x: x[1].busy_until)

            job = self.waiting.popleft()
            changed_queue = True

            # path y distancia
            path = self._build_path_for_job(job)
            self.distance_total_m += self._path_length_m(path)

            # congestión (si está off, _congestion_multiplier() devuelve 1.0)
            active = sum(1 for x in self.pickers if x.busy_until > self.now)
            dur = job.service_min * self._congestion_multiplier(active + 1)

            # Gantt/analytics
            self.analytics.setdefault("gantt", {}).setdefault(pid, []).append((float(self.now), float(dur)))

            # Espera por pedido(s)
            if getattr(job, "orders", None):
                for o in job.orders:
                    wait = max(0.0, float(self.now - o.arrival_min))
                    self.analytics["waits"].append(wait)
                    self.order_waits.append(wait)
            else:
                wait = max(0.0, float(self.now - job.arrival_min))
                self.analytics["waits"].append(wait)
                self.order_waits.append(wait)

            # Gantt por picker (para métricas finales)
            self.gantt[pid].append((self.now, self.now + dur, int(job.job_id)))

            # Animación con keyframes
            try:
                self._animate_job(pid, job, start_t=self.now, duration_min=dur, job_path=path)
            except Exception:
                # Fallback mínimo: dos keyframes
                self._keyframe(pid, self.now, self._picker_xy[pid], "moving", job.job_id)
                self._keyframe(pid, self.now + dur, self._picker_xy[pid], "idle", None)

            # Actualiza estado del picker y agenda su evento de fin
            p.busy_until = self.now + dur
            p.busy_time  += dur
            self.picker_tours[pid] += 1
            self.evq.push(Event(time=p.busy_until, etype="PICKER_FREE",
                                payload={"pid": pid, "job": job}))

        if changed_queue:
            self.ts_queue.append((self.now, len(self.waiting)))

    # ------------------------------- Run --------------------------------

    def run(self) -> SimResult:
        while not self.evq.empty():
            ev = self.evq.pop()

            if self.cfg.horizon_min is not None and ev.time > self.cfg.horizon_min:
                self.now = self.cfg.horizon_min
                break

            self.now = ev.time
            if ev.etype == "ARRIVAL":
                job: Job = ev.payload
                self.waiting.append(job)
                self._log_queue()
                self.ts_queue.append((self.now, len(self.waiting)))
                self._assign_if_possible()

            elif ev.etype == "PICKER_FREE":
                info = ev.payload
                pid = info["pid"]
                job: Job = info["job"]
                self.pickers[pid].completed_orders += job.n_orders
                self.orders_completed += job.n_orders
                self.analytics["completed_t"].append(float(self.now))
                self.analytics["completed_y"].append(int(self.orders_completed))
                self._log_queue()
                self.ts_completed.append((self.now, self.orders_completed))
                self._assign_if_possible()

        # --------- Métricas finales ----------
        makespan = max(self.now, max((p.busy_until for p in self.pickers), default=0.0))
        sim_time = makespan if self.cfg.horizon_min is None else min(makespan, self.cfg.horizon_min)

        throughput_per_hour = (self.orders_completed / sim_time * 60.0) if sim_time > 0 else 0.0
        avg_wait = float(np.mean(self.order_waits)) if self.order_waits else 0.0
        wait_p90 = float(np.percentile(self.order_waits, 90)) if self.order_waits else 0.0
        wait_p95 = float(np.percentile(self.order_waits, 95)) if self.order_waits else 0.0

        # Utilización precisa: sumar barras del Gantt recortadas al sim_time
        eff_busy: List[float] = []
        for segs in self.gantt:
            total = 0.0
            for (t0, t1, _) in segs:
                a0 = max(0.0, min(t1, sim_time) - min(t0, sim_time))
                total += a0
            eff_busy.append(total)

        util = [(b / sim_time) if sim_time > 0 else 0.0 for b in eff_busy]
        idle = [max(0.0, sim_time - b) for b in eff_busy]

        distance_total_m = self.distance_total_m
        distance_per_order_avg_m = (distance_total_m / self.orders_completed) if self.orders_completed > 0 else 0.0

        batches_count = len(self.batches_sizes)
        batch_avg_size = float(np.mean(self.batches_sizes)) if batches_count > 0 else 0.0
        batch_pct_ge2 = (100.0 * np.mean([b >= 2 for b in self.batches_sizes])) if batches_count > 0 else 0.0
        batch_avg_release = float(np.mean(self.batches_release)) if self.batches_release else 0.0
        batch_avg_fill = float(np.mean(self.batches_fill)) if self.batches_fill else 0.0

        self._log_queue()

        # Construye timeline fusionado por tiempo para la UI
        self._build_timeline_from_tracks(sim_time)

        return SimResult(
            makespan_min=sim_time,
            orders_completed=self.orders_completed,
            throughput_per_hour=throughput_per_hour,
            avg_wait_min=avg_wait,
            picker_utilization=util,

            wait_p90_min=wait_p90,
            wait_p95_min=wait_p95,
            distance_total_m=distance_total_m,
            distance_per_order_avg_m=distance_per_order_avg_m,

            batches_count=batches_count,
            batch_avg_size=batch_avg_size,
            batch_pct_ge2=batch_pct_ge2,
            batch_avg_release_min=batch_avg_release,
            batch_avg_fill_min=batch_avg_fill,

            ts_queue=self.ts_queue,
            ts_completed=self.ts_completed,
            gantt=self.gantt,
            waits_raw=self.order_waits,

            picker_idle_min=idle,
            picker_tours=self.picker_tours,
        )
