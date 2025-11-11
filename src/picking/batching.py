from dataclasses import dataclass
from typing import List, Iterable, Optional
from src.demand.orders import Order

@dataclass
class Batch:
    orders: List[Order]
    first_arrival_min: float
    last_arrival_min: float

class SizeThresholdBatching:
    """Libera un batch cuando acumula N pedidos."""
    def __init__(self, batch_size: int):
        assert batch_size >= 1
        self.batch_size = batch_size

    def make_batches(self, orders: Iterable[Order]) -> List[Batch]:
        buf: List[Order] = []
        batches: List[Batch] = []
        for o in orders:
            buf.append(o)
            if len(buf) == self.batch_size:
                batches.append(Batch(
                    orders=buf[:],
                    first_arrival_min=buf[0].arrival_min,
                    last_arrival_min=buf[-1].arrival_min
                ))
                buf.clear()
        if buf:
            batches.append(Batch(
                orders=buf[:],
                first_arrival_min=buf[0].arrival_min,
                last_arrival_min=buf[-1].arrival_min
            ))
        return batches

class TimeThresholdBatching:
    """
    Libera un batch cuando el tiempo transcurrido desde el primer pedido del batch
    supera el umbral (en minutos). Si llega un pedido y el batch 'vence', se libera antes
    de incluirlo; el pedido inicia un nuevo batch.
    """
    def __init__(self, threshold_min: float):
        assert threshold_min > 0.0
        self.threshold_min = threshold_min

    def make_batches(self, orders: Iterable[Order]) -> List[Batch]:
        it = iter(orders)
        batches: List[Batch] = []
        buf: List[Order] = []
        first_time: Optional[float] = None

        for o in it:
            if not buf:
                buf.append(o)
                first_time = o.arrival_min
                continue
            # si al llegar 'o' ya excedimos el umbral con respecto al primero
            if o.arrival_min - first_time >= self.threshold_min:
                batches.append(Batch(
                    orders=buf[:],
                    first_arrival_min=buf[0].arrival_min,
                    last_arrival_min=buf[-1].arrival_min
                ))
                buf = [o]
                first_time = o.arrival_min
            else:
                buf.append(o)

        if buf:
            batches.append(Batch(
                orders=buf[:],
                first_arrival_min=buf[0].arrival_min,
                last_arrival_min=buf[-1].arrival_min
            ))
        return batches
