from dataclasses import dataclass
from typing import Tuple, Iterable, Dict, Set, List

Coord = Tuple[int, int]  # (fila, columna)

@dataclass(frozen=True)
class GridSpec:
    rows: int                 # intersecciones de pasillo en vertical
    cols: int                 # intersecciones de pasillo en horizontal
    cell_size_m: float = 1.0  # metros entre intersecciones
    packing_station: Coord = (0, 0)  # punto de empaque/entrada
    blocked: Set[Coord] = None        # celdas bloqueadas (p.ej., zonas no transitables)

    def __post_init__(self):
        if self.rows <= 0 or self.cols <= 0:
            raise ValueError("rows y cols deben ser > 0")

@dataclass
class WarehouseGrid:
    spec: GridSpec

    def nodes(self) -> Iterable[Coord]:
        """Todas las intersecciones transitables del grafo."""
        b = self.spec.blocked or set()
        for r in range(self.spec.rows):
            for c in range(self.spec.cols):
                if (r, c) not in b:
                    yield (r, c)

    def in_bounds(self, rc: Coord) -> bool:
        r, c = rc
        return 0 <= r < self.spec.rows and 0 <= c < self.spec.cols

    def passable(self, rc: Coord) -> bool:
        return rc not in (self.spec.blocked or set())

    def neighbors(self, rc: Coord) -> Iterable[Coord]:
        """Vecinos 4-conectados (arriba, abajo, izq, der)."""
        r, c = rc
        candidates = [(r-1, c), (r+1, c), (r, c-1), (r, c+1)]
        for n in candidates:
            if self.in_bounds(n) and self.passable(n):
                yield n

    def edges(self) -> Iterable[Tuple[Coord, Coord]]:
        """Aristas no dirigidas entre intersecciones adyacentes transitables."""
        seen = set()
        for u in self.nodes():
            for v in self.neighbors(u):
                e = tuple(sorted([u, v]))
                if e not in seen:
                    seen.add(e)
                    yield e

    def all_pairs_shortest_path_length(self) -> Dict[Coord, Dict[Coord, int]]:
        """Distancias en pasos (no en metros). BFS por cada nodo (grilla pequeña)."""
        from collections import deque, defaultdict
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

    def meters(self, steps: int) -> float:
        return steps * self.spec.cell_size_m

    @staticmethod
    def default_spec() -> GridSpec:
        # Por defecto: 10 pasillos x 20 intersecciones (como referencia del plan)
        return GridSpec(rows=10, cols=20, cell_size_m=1.0, packing_station=(0, 0), blocked=set())
