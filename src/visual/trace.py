# src/visual/trace.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any

Coord = Tuple[int, int]

@dataclass
class TraceRecorder:
    """
    Guarda segmentos de movimiento y holds con el esquema que necesita compose_trace.
    Cada segmento es un dict con:
      - picker_id: int
      - job_id: int
      - start_t: float   (minutos)
      - path: List[Tuple[int,int]]  [(x0,y0),(x1,y1),...]
      - speed_m_per_min: float
    Los 'holds' son opcionales y se agregan como eventos con:
      - picker_id, job_id, start_t, hold_min, x, y, state="hold"
    """
    dt: Optional[float] = None  # no lo usamos aquí; compose_trace aplicará su propio muestreo

    def __post_init__(self):
        self._segments: List[Dict[str, Any]] = []
        self._holds: List[Dict[str, Any]] = []

    # ---- API pública ----
    def add_path_segment(
        self,
        start_t: float,
        picker_id: int,
        job_id: int,
        path: List[Coord],
        speed_m_per_min: float,
    ) -> None:
        if not path or len(path) < 1:
            return
        self._segments.append({
            "picker_id": picker_id,
            "job_id": job_id,
            "start_t": float(start_t),
            "path": [(int(x), int(y)) for (x, y) in path],
            "speed_m_per_min": float(speed_m_per_min),
        })

    def add_hold(
        self,
        start_t: float,
        picker_id: int,
        job_id: int,
        hold_min: float,
        x: int,
        y: int,
        state: str = "hold",
    ) -> None:
        self._holds.append({
            "picker_id": picker_id,
            "job_id": job_id,
            "start_t": float(start_t),
            "hold_min": float(hold_min),
            "x": int(x),
            "y": int(y),
            "state": state,
        })

    # Lo que el simulador debe exponer para compose_trace:
    def get_frames(self) -> List[Dict[str, Any]]:
        # Devolvemos una lista plana; compose_trace ya sabe diferenciar segmentos de holds por llaves.
        # (Si tu compose_trace requiere una sola lista, concatenar está bien.)
        return self._segments + self._holds
