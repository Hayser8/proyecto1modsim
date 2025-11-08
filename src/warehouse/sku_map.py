from dataclasses import dataclass
from typing import Dict, Tuple, List
from .grid import Coord, WarehouseGrid

@dataclass
class SKUPlacement:
    """Asignación simple de SKUs a coordenadas de intersecciones cercanas a estantes."""
    sku_to_coord: Dict[str, Coord]

    def coord_of(self, sku: str) -> Coord:
        if sku not in self.sku_to_coord:
            raise KeyError(f"SKU no encontrado: {sku}")
        return self.sku_to_coord[sku]

def generate_hotspot_map(grid: WarehouseGrid, popular_skus: List[str], other_skus: List[str]) -> SKUPlacement:
    """
    Distribuye SKUs populares cerca de la estación de empaque y el resto hacia el fondo.
    Heurística simple: barrido por columnas desde packing_station hacia afuera.
    """
    ps = grid.spec.packing_station
    all_coords = sorted(list(grid.nodes()), key=lambda rc: abs(rc[0]-ps[0]) + abs(rc[1]-ps[1]))
    mapping: Dict[str, Coord] = {}

    # Primero asignar populares a los más cercanos
    idx = 0
    for sku in popular_skus:
        mapping[sku] = all_coords[idx]
        idx += 1

    # Luego asignar el resto
    for sku in other_skus:
        mapping[sku] = all_coords[idx]
        idx += 1

    return SKUPlacement(mapping)
