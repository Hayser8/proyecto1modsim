# src/warehouse/sku_map.py
from typing import Dict, Tuple, List, Optional
import numpy as np
from .grid import WarehouseGrid

Coord = Tuple[int, int]

class SKUPlacement:
    def __init__(self, mapping: Dict[str, Coord]):
        self._map = dict(mapping)

    def coord_of(self, sku: str) -> Coord:
        return self._map[sku]

    def skus(self) -> List[str]:
        return list(self._map.keys())

    @staticmethod
    def random_sample(grid: WarehouseGrid, n_skus: int, seed: int = 0) -> "SKUPlacement":
        """
        Crea un mapeo aleatorio de n_skus a celdas libres de la grilla.
        - Infieren width/height de varios nombres posibles (spec.width/height, spec.w/h, grid.width/height, grid.shape, grid.cells).
        - La estación se toma de spec.packing_station o grid.packing_station (atributo o método).
        - Obstáculos: spec.obstacles o grid.obstacles o grid.blocked; si no hay, vacío.
        - Si existe grid.is_blocked((x,y)), se usa como chequeo extra.
        """
        rng = np.random.default_rng(seed)

        # --- Inferir dimensiones ---
        def _infer_dims(g) -> Tuple[int, int]:
            w: Optional[int] = None
            h: Optional[int] = None
            spec = getattr(g, "spec", None)

            # Candidatos en spec
            if spec is not None:
                for name in ("width", "w", "cols", "n_cols", "ncol", "nx"):
                    if hasattr(spec, name):
                        w = int(getattr(spec, name))
                        break
                for name in ("height", "h", "rows", "n_rows", "nrow", "ny"):
                    if hasattr(spec, name):
                        h = int(getattr(spec, name))
                        break

            # Candidatos directos en grid
            if w is None:
                for name in ("width", "w", "cols", "n_cols", "nx"):
                    if hasattr(g, name):
                        w = int(getattr(g, name))
                        break
            if h is None:
                for name in ("height", "h", "rows", "n_rows", "ny"):
                    if hasattr(g, name):
                        h = int(getattr(g, name))
                        break

            # shape estilo numpy: (alto, ancho) o (rows, cols)
            if (w is None or h is None) and hasattr(g, "shape"):
                sh = getattr(g, "shape")
                if isinstance(sh, (tuple, list)) and len(sh) >= 2:
                    h = int(sh[0]) if h is None else h
                    w = int(sh[1]) if w is None else w

            # matriz cells: asume cells[y][x]
            if (w is None or h is None) and hasattr(g, "cells"):
                cells = getattr(g, "cells")
                try:
                    h = int(len(cells)) if h is None else h
                    w = int(len(cells[0])) if w is None else w
                except Exception:
                    pass

            if w is None or h is None:
                raise ValueError(
                    "No se pudieron inferir dimensiones de la grilla. "
                    "Asegúrate de exponer width/height en grid.spec o grid.{width,height}/shape/cells."
                )
            return w, h

        w, h = _infer_dims(grid)

        # --- Estación de empaque ---
        station = (0, 0)
        spec = getattr(grid, "spec", None)
        if spec is not None and hasattr(spec, "packing_station"):
            ps = getattr(spec, "packing_station")
            station = ps() if callable(ps) else tuple(ps)
        elif hasattr(grid, "packing_station"):
            ps = getattr(grid, "packing_station")
            station = ps() if callable(ps) else tuple(ps)

        # --- Obstáculos ---
        obstacles = set()
        # spec.obstacles
        if spec is not None and hasattr(spec, "obstacles"):
            obs = getattr(spec, "obstacles")
            try:
                obstacles |= {tuple(o) for o in obs}
            except Exception:
                pass
        # grid.obstacles / grid.blocked
        for name in ("obstacles", "blocked"):
            if hasattr(grid, name):
                obs = getattr(grid, name)
                try:
                    obstacles |= {tuple(o) for o in obs}
                except Exception:
                    pass

        # --- Celdas libres ---
        free: List[Coord] = []
        has_is_blocked = hasattr(grid, "is_blocked")
        for x in range(w):
            for y in range(h):
                if (x, y) == station:
                    continue
                if (x, y) in obstacles:
                    continue
                if has_is_blocked and grid.is_blocked((x, y)):
                    continue
                free.append((x, y))

        if n_skus > len(free):
            raise ValueError(f"No hay suficientes celdas libres para {n_skus} SKUs (libres={len(free)}).")

        rng.shuffle(free)
        coords = free[:n_skus]
        skus = [f"S{idx:04d}" for idx in range(1, n_skus + 1)]
        mapping = {sku: coords[i] for i, sku in enumerate(skus)}
        return SKUPlacement(mapping)
