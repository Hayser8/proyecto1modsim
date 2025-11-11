from dataclasses import dataclass, field
from typing import List, Literal, Tuple
import heapq
from typing import Optional
from src.demand.orders import Order  # nuevo

EventType = Literal["ARRIVAL", "PICKER_FREE"]

@dataclass(order=True)
class Event:
    time: float
    etype: EventType
    payload: object = field(compare=False, default=None)

@dataclass
class Job:
    """Trabajo que un picker ejecuta de una sola vez (pedido o batch)."""
    job_id: int
    arrival_min: float   # primer arribo entre los pedidos que contiene
    service_min: float   # tiempo de servicio (ruta ida y vuelta convertida a tiempo)
    n_orders: int        # cuántos pedidos incluye (1 si pedido individual)
    orders: Optional[List[Order]] = None  

class EventQueue:
    def __init__(self):
        self._h: List[Tuple[float, int, Event]] = []
        self._seq = 0

    def push(self, ev: Event):
        self._seq += 1
        heapq.heappush(self._h, (ev.time, self._seq, ev))

    def pop(self) -> Event:
        _, _, ev = heapq.heappop(self._h)
        return ev

    def empty(self) -> bool:
        return not self._h

    def peek_time(self) -> float:
        return self._h[0][0] if self._h else float("inf")
