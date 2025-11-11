# src/warehouse/grid.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple, Any
from collections import deque, defaultdict

Coord = Tuple[int, int]  # (x, y) en la grilla

@dataclass
class WarehouseGrid:
    """
    Contenedor ligero de la grilla del CD con un 'spec' estilo dict:

    spec = {
        "width": int,
        "height": int,
        "station": {"x": int, "y": int},
        "obstacles": List[List[int] | Tuple[int,int]],   # opcional
        "cell_size_m": float                             # opcional, default 1.0
    }

    Esta forma coincide con lo que esperan la UI (compose_trace) y SKUPlacement.random_sample.
    """
    spec: Dict[str, Any]

    # --------- constructores ---------
    @staticmethod
    def default_spec() -> Dict[str, Any]:
        # Ajusta si quieres otras dimensiones/obstáculos por defecto
        return {
            "width": 30,
            "height": 30,
            "station": {"x": 0, "y": 0},
            "obstacles": [],         # lista de [x,y] o (x,y)
            "cell_size_m": 1.0,
        }

    # --------- helpers básicos ---------
    @property
    def width(self) -> int:
        return int(self.spec.get("width", 0))

    @property
    def height(self) -> int:
        return int(self.spec.get("height", 0))

    @property
    def cell_size_m(self) -> float:
        return float(self.spec.get("cell_size_m", 1.0))

    @property
    def station_xy(self) -> Coord:
        st = self.spec.get("station", None)
        if isinstance(st, dict) and "x" in st and "y" in st:
            return int(st["x"]), int(st["y"])
        # Fallbacks comunes
        if isinstance(st, (tuple, list)) and len(st) == 2:
            return int(st[0]), int(st[1])
        return (0, 0)

    @property
    def obstacles_set(self) -> Set[Coord]:
        raw = self.spec.get("obstacles", []) or []
        out: Set[Coord] = set()
        for p in raw:
            if isinstance(p, (list, tuple)) and len(p) == 2:
                out.add((int(p[0]), int(p[1])))
        return out

    # --------- API de grafo sobre la grilla ---------
    def in_bounds(self, xy: Coord) -> bool:
        x, y = xy
        return 0 <= x < self.width and 0 <= y < self.height

    def passable(self, xy: Coord) -> bool:
        return xy not in self.obstacles_set

    def neighbors(self, xy: Coord) -> Iterable[Coord]:
        x, y = xy
        candidates = [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]
        for n in candidates:
            if self.in_bounds(n) and self.passable(n):
                yield n

    def nodes(self) -> Iterable[Coord]:
        obs = self.obstacles_set
        for x in range(self.width):
            for y in range(self.height):
                if (x, y) not in obs:
                    yield (x, y)

    def edges(self) -> Iterable[Tuple[Coord, Coord]]:
        seen = set()
        for u in self.nodes():
            for v in self.neighbors(u):
                e = tuple(sorted((u, v)))
                if e not in seen:
                    seen.add(e)
                    yield e

    def all_pairs_shortest_path_length(self) -> Dict[Coord, Dict[Coord, int]]:
        """
        Distancias en pasos (Manhattan con obstáculos) por BFS desde cada nodo.
        Útil para precalcular rutas cortas en grillas pequeñas/medianas.
        """
        distances: Dict[Coord, Dict[Coord, int]] = {}
        nods = list(self.nodes())
        for s in nods:
            dist = defaultdict(lambda: -1)
            dist[s] = 0
            q = deque([s])
            while q:
                u = q.popleft()
                for v in self.neighbors(u):
                    if dist[v] == -1:
                        dist[v] = dist[u] + 1
                        q.append(v)
            distances[s] = dict(dist)
        return distances

    # --------- utilidades métricas ---------
    def meters(self, steps: int) -> float:
        return steps * self.cell_size_m
