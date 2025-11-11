from dataclasses import dataclass
from typing import List, Iterable, Tuple, Set
from src.warehouse.grid import WarehouseGrid, Coord
from src.warehouse.routing import multi_stop_tour_steps
from src.warehouse.sku_map import SKUPlacement
from src.demand.orders import Order

@dataclass
class TourResult:
    steps: int
    meters: float

# -------------------- Helpers internos --------------------

def _sku_list(order: Order) -> List[str]:
    """
    Devuelve los SKUs de un Order, tolerante a distintos nombres de atributo:
    - order.item_counts  (dict {sku: qty})   ← el tuyo actual
    - order.sku_list     (list)
    - order.skus         (list)
    - order.items        (dict {sku: qty} o list)
    - order.sku_ids      (list)
    """
    if hasattr(order, "item_counts") and isinstance(order.item_counts, dict):
        return list(order.item_counts.keys())
    if hasattr(order, "sku_list") and order.sku_list is not None:
        return list(order.sku_list)
    if hasattr(order, "skus") and order.skus is not None:
        return list(order.skus)
    if hasattr(order, "items") and order.items is not None:
        it = order.items
        if isinstance(it, dict):
            return list(it.keys())
        if isinstance(it, (list, tuple)):
            return list(it)
    if hasattr(order, "sku_ids") and order.sku_ids is not None:
        return list(order.sku_ids)
    raise AttributeError("Order no presenta campos de SKUs conocidos (item_counts/sku_list/skus/items/sku_ids).")

def _station(grid: WarehouseGrid) -> Tuple[int, int]:
    """
    Devuelve coordenada de estación de empaque de forma robusta.
    Prioriza: grid.spec.packing_station → grid.packing_xy → (0,0)
    """
    # 1) layout en spec
    if hasattr(grid, "spec") and hasattr(grid.spec, "packing_station"):
        ps = grid.spec.packing_station
        if ps is not None:
            return (int(ps[0]), int(ps[1]))
    # 2) atributo directo opcional
    if hasattr(grid, "packing_xy") and getattr(grid, "packing_xy") is not None:
        px = getattr(grid, "packing_xy")
        return (int(px[0]), int(px[1]))
    # 3) fallback
    return (0, 0)

# -------------------- Conversión pedido → coords únicas --------------------

def _coords_for_order(placement: SKUPlacement, order: Order) -> List[Coord]:
    """Convierte ítems del pedido a coordenadas (se cuentan ubicaciones únicas para ruteo)."""
    unique_skus: Set[str] = set(_sku_list(order))
    return [placement.coord_of(sku) for sku in unique_skus]

# -------------------- Tours (métricas) --------------------

def order_tour(grid: WarehouseGrid, placement: SKUPlacement, order: Order, return_to_station: bool=False) -> TourResult:
    """Ruta NN desde estación de empaque por todas las ubicaciones del pedido (únicas)."""
    start = _station(grid)  # antes: grid.spec.packing_station
    stops = _coords_for_order(placement, order)
    steps = 0
    if stops:
        steps = multi_stop_tour_steps(grid, start, stops)
        if steps < 0:
            return TourResult(steps=-1, meters=-1.0)
        if return_to_station:
            # volver a empaque desde último punto visitado
            # reconstruimos la última parada con una pasada extra (ligero overhead, aceptable)
            remaining = stops[:]
            current = start
            while remaining:
                # elige más cercano y avanza
                best_idx, best_steps = -1, None
                for i, s in enumerate(remaining):
                    d = multi_stop_tour_steps(grid, current, [s])  # un hop
                    if best_steps is None or d < best_steps:
                        best_steps, best_idx = d, i
                current = remaining.pop(best_idx)
            # sumar regreso
            from src.warehouse.routing import shortest_path_steps
            back = shortest_path_steps(grid, current, start)
            steps += back
    return TourResult(steps=steps, meters=grid.meters(steps))

def batch_tour(grid: WarehouseGrid, placement: SKUPlacement, orders: List[Order], return_to_station: bool=False) -> TourResult:
    """Ruta NN por el conjunto de ubicaciones (únicas) de todos los pedidos del batch."""
    if not orders:
        return TourResult(steps=0, meters=0.0)
    start = _station(grid)  # antes: grid.spec.packing_station
    # conjunto de ubicaciones únicas del batch
    seen: Set[Coord] = set()
    for o in orders:
        seen.update(_coords_for_order(placement, o))
    stops = list(seen)
    steps = 0
    if stops:
        steps = multi_stop_tour_steps(grid, start, stops)
        if steps < 0:
            return TourResult(steps=-1, meters=-1.0)
        if return_to_station:
            # aproximación: encuentra el último punto de la secuencia NN como arriba
            remaining = stops[:]
            current = start
            while remaining:
                best_idx, best_steps = -1, None
                for i, s in enumerate(remaining):
                    d = multi_stop_tour_steps(grid, current, [s])
                    if best_steps is None or d < best_steps:
                        best_steps, best_idx = d, i
                current = remaining.pop(best_idx)
            from src.warehouse.routing import shortest_path_steps
            back = shortest_path_steps(grid, current, start)
            steps += back
    return TourResult(steps=steps, meters=grid.meters(steps))

# -------------------- Paths Manhattan para visualización --------------------

def _manhattan_path(a: Tuple[int,int], b: Tuple[int,int]) -> List[Tuple[int,int]]:
    """Camino Manhattan simple (recto en x, luego en y). 1 celda = 1 m."""
    x0, y0 = a
    x1, y1 = b
    path: List[Tuple[int,int]] = [(x0, y0)]
    # mover en x
    if x1 != x0:
        dx = 1 if x1 > x0 else -1
        for x in range(x0 + dx, x1 + dx, dx):
            path.append((x, y0))
            if x == x1:
                break
    # mover en y
    if y1 != y0:
        dy = 1 if y1 > y0 else -1
        for y in range(y0 + dy, y1 + dy, dy):
            path.append((x1, y))
            if y == y1:
                break
    # garantizar final exacto
    if not path or path[-1] != (x1, y1):
        path.append((x1, y1))
    return path

def _nn_visit_sequence(grid: WarehouseGrid, placement: SKUPlacement, coords: List[Tuple[int,int]]) -> List[Tuple[int,int]]:
    """Secuencia por vecino más cercano (aprox para dibujar)."""
    seq: List[Tuple[int,int]] = []
    cur = _station(grid)
    remaining = set(coords)
    while remaining:
        nxt = min(remaining, key=lambda c: abs(c[0]-cur[0]) + abs(c[1]-cur[1]))
        seq.append(nxt)
        cur = nxt
        remaining.remove(nxt)
    return seq

def order_tour_path(grid: WarehouseGrid, placement: SKUPlacement, order: Order, return_to_station: bool = True) -> List[Tuple[int,int]]:
    """Path Manhattan para visualizar el tour de un pedido."""
    station = _station(grid)
    coords = [placement.coord_of(sku) for sku in _sku_list(order)]
    if not coords:
        return [station]
    visit_seq = _nn_visit_sequence(grid, placement, coords)
    path: List[Tuple[int,int]] = []
    cur = station
    for c in visit_seq:
        path += _manhattan_path(cur, c)
        cur = c
    if return_to_station:
        path += _manhattan_path(cur, station)
    return path or [station]

def batch_tour_path(grid: WarehouseGrid, placement: SKUPlacement, orders: List[Order], return_to_station: bool = True) -> List[Tuple[int,int]]:
    """Path Manhattan para visualizar un batch (concatena SKUs de todos)."""
    station = _station(grid)
    all_coords: List[Tuple[int,int]] = []
    for o in orders:
        for sku in _sku_list(o):
            all_coords.append(placement.coord_of(sku))
    if not all_coords:
        return [station]
    visit_seq = _nn_visit_sequence(grid, placement, all_coords)
    path: List[Tuple[int,int]] = []
    cur = station
    for c in visit_seq:
        path += _manhattan_path(cur, c)
        cur = c
    if return_to_station:
        path += _manhattan_path(cur, station)
    return path or [station]
