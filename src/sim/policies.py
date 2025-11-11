from typing import List, Literal
from src.sim.events import Job
from src.warehouse.grid import WarehouseGrid
from src.warehouse.sku_map import SKUPlacement
from src.picking.tours import order_tour, batch_tour
from src.picking.batching import SizeThresholdBatching, TimeThresholdBatching
from src.demand.orders import Order

PolicyName = Literal["Secuencial_FCFS", "Batching_Size", "Batching_Time"]

def build_jobs_sequential(
    orders: List[Order],
    grid: WarehouseGrid,
    placement: SKUPlacement,
    speed_m_per_min: float
) -> List[Job]:
    jobs: List[Job] = []
    jid = 0
    for o in orders:
        tr = order_tour(grid, placement, o, return_to_station=True)
        service = tr.meters / max(speed_m_per_min, 1e-9)
        jobs.append(Job(
            job_id=jid,
            arrival_min=o.arrival_min,          # correcto: la llegada de la orden
            service_min=service,
            n_orders=1,
            orders=[o]
        ))
        jid += 1
    return jobs


def build_jobs_batch_size(
    orders: List[Order],
    grid: WarehouseGrid,
    placement: SKUPlacement,
    speed_m_per_min: float,
    batch_size: int
) -> List[Job]:
    sb = SizeThresholdBatching(batch_size)
    batches = sb.make_batches(orders)

    jobs: List[Job] = []
    jid = 0
    for b in batches:
        tr = batch_tour(grid, placement, b.orders, return_to_station=True)
        service = tr.meters / max(speed_m_per_min, 1e-9)

        # ⬇️ TIEMPO CORRECTO DE ENTRADA DEL LOTE A LA COLA
        last_arrival = max(o.arrival_min for o in b.orders)
        release_min  = last_arrival        # lote se libera al completarse

        jobs.append(Job(
            job_id=jid,
            arrival_min=release_min,       # <-- usar release, NO first_arrival
            service_min=service,
            n_orders=len(b.orders),
            orders=b.orders
        ))
        jid += 1
    return jobs


def build_jobs_batch_time(
    orders: List[Order],
    grid: WarehouseGrid,
    placement: SKUPlacement,
    speed_m_per_min: float,
    threshold_min: float
) -> List[Job]:
    tb = TimeThresholdBatching(threshold_min)
    batches = tb.make_batches(orders)

    jobs: List[Job] = []
    jid = 0
    for b in batches:
        tr = batch_tour(grid, placement, b.orders, return_to_station=True)
        service = tr.meters / max(speed_m_per_min, 1e-9)

        first_arrival = min(o.arrival_min for o in b.orders)
        last_arrival  = max(o.arrival_min for o in b.orders)
        # ventana termina en first + threshold; por robustez, nunca antes de la última llegada
        release_min   = max(first_arrival + float(threshold_min), last_arrival)

        jobs.append(Job(
            job_id=jid,
            arrival_min=release_min,       # <-- usar fin de ventana (release)
            service_min=service,
            n_orders=len(b.orders),
            orders=b.orders
        ))
        jid += 1
    return jobs
