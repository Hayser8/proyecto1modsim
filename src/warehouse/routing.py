from typing import List, Tuple
from .grid import WarehouseGrid, Coord
from collections import deque

def shortest_path_steps(grid: WarehouseGrid, start: Coord, goal: Coord) -> int:
    """Número de pasos (4-conectado) entre start y goal. Retorna -1 si no hay ruta."""
    if start == goal:
        return 0
    if not grid.in_bounds(start) or not grid.in_bounds(goal):
        return -1
    if not grid.passable(start) or not grid.passable(goal):
        return -1

    q = deque([start])
    dist = {start: 0}
    while q:
        u = q.popleft()
        for v in grid.neighbors(u):
            if v not in dist:
                dist[v] = dist[u] + 1
                if v == goal:
                    return dist[v]
                q.append(v)
    return -1

def path_distance_m(grid: WarehouseGrid, path_steps: int) -> float:
    return grid.meters(path_steps)

def multi_stop_tour_steps(grid: WarehouseGrid, start: Coord, stops: List[Coord]) -> int:
    """
    Heurística NN: desde start visitar stops en orden de vecino más cercano (en pasos),
    acumulando distancia. Sirve como baseline para ruteo de picking.
    """
    remaining = stops[:]
    current = start
    total = 0
    while remaining:
        # elegir el siguiente más cercano por pasos
        best_idx, best_steps = -1, None
        for i, s in enumerate(remaining):
            steps = shortest_path_steps(grid, current, s)
            if steps < 0:
                return -1
            if best_steps is None or steps < best_steps:
                best_steps, best_idx = steps, i
        total += best_steps
        current = remaining.pop(best_idx)
    return total
