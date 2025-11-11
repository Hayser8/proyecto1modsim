# src/visual/frames.py
from __future__ import annotations
from typing import Dict, Any, List, Tuple, Iterable
from collections import defaultdict

# ---------- Helpers robustos para el layout ----------

def _station(grid) -> Tuple[int, int]:
    # grid.spec.packing_station → grid.packing_xy → (0,0)
    if hasattr(grid, "spec") and hasattr(grid.spec, "packing_station"):
        ps = grid.spec.packing_station
        if ps is not None:
            return (int(ps[0]), int(ps[1]))
    if hasattr(grid, "packing_xy") and getattr(grid, "packing_xy") is not None:
        px = getattr(grid, "packing_xy")
        return (int(px[0]), int(px[1]))
    return (0, 0)

def _size(grid) -> Tuple[int, int]:
    # grid.spec.width/height → grid.width/height → fallback 30x30
    w = None
    h = None
    if hasattr(grid, "spec"):
        if hasattr(grid.spec, "width"):  w = getattr(grid.spec, "width")
        if hasattr(grid.spec, "height"): h = getattr(grid.spec, "height")
    if w is None and hasattr(grid, "width"):  w = getattr(grid, "width")
    if h is None and hasattr(grid, "height"): h = getattr(grid, "height")
    return (int(w) if w is not None else 30, int(h) if h is not None else 30)

def _obstacles_from_placement(placement, station=None):
    cells = set()
    if hasattr(placement, "sku_to_coord") and isinstance(placement.sku_to_coord, dict):
        for xy in placement.sku_to_coord.values():
            c = (int(xy[0]), int(xy[1]))
            cells.add(c)
    # si mandan station, se excluye explícitamente
    if station is not None and station in cells:
        cells.discard(station)
    return sorted(cells)

# ---------- Compactación de frames ----------

def _round_time(t: float, dt: float) -> float:
    if dt is None or dt <= 0:
        return t
    k = round(t / dt)
    return round(k * dt, 6)

def pack_frames(frames: List[dict], round_dt: float = 0.25) -> List[Dict[str, Any]]:
    """
    Agrupa por tiempo (redondeado) y consolida por picker_id:
      - si hay varios registros del mismo picker en el mismo t, se queda el último.
      - elimina consecutivos sin cambio (misma x,y) por picker entre t's contiguos.
    """
    # 1) bucket por t redondeado
    raw: Dict[float, Dict[int, dict]] = defaultdict(dict)  # t -> {picker_id: frame}
    for fr in frames:
        t = _round_time(fr["t"], round_dt)
        pid = int(fr["picker_id"])
        raw[t][pid] = {
            "picker_id": pid,
            "x": int(fr["x"]),
            "y": int(fr["y"]),
            "state": fr.get("state", "moving"),
            "job_id": int(fr.get("job_id", -1)),
        }

    # 2) ordenar tiempos y construir timeline preliminar
    times_sorted = sorted(raw.keys())
    prelim = []
    for t in times_sorted:
        pickers = [raw[t][pid] for pid in sorted(raw[t].keys())]
        prelim.append({"t": float(t), "pickers": pickers})

    # 3) eliminar consecutivos sin cambio por picker comparando con el último emitido
    last_pos: Dict[int, Tuple[int,int]] = {}
    cleaned: List[Dict[str, Any]] = []
    for slot in prelim:
        t = slot["t"]
        out_pickers = []
        for p in slot["pickers"]:
            pid = p["picker_id"]
            pos = (p["x"], p["y"])
            if last_pos.get(pid) != pos:
                out_pickers.append(p)
                last_pos[pid] = pos
        if out_pickers:
            cleaned.append({"t": t, "pickers": out_pickers})

    return cleaned

# ---------- Orquestador: meta + timeline ----------

def compose_trace(grid, placement, frames: List[dict], round_dt: float = 0.25):
    width, height = _size(grid)
    station = _station(grid)
    obstacles = _obstacles_from_placement(placement, station=station)
    timeline = pack_frames(frames, round_dt=round_dt)
    return {
        "meta": {
            "width": width,
            "height": height,
            "station": {"x": station[0], "y": station[1]},
            "obstacles": obstacles
        },
        "timeline": timeline
    }