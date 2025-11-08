from src.warehouse.grid import WarehouseGrid
from src.warehouse.sku_map import generate_hotspot_map

def test_popular_skus_are_nearer_to_packing_station():
    grid = WarehouseGrid(WarehouseGrid.default_spec())
    popular = [f"SKU_P{i}" for i in range(5)]
    others = [f"SKU_{i}" for i in range(5, 20)]
    mapping = generate_hotspot_map(grid, popular, others)

    ps = grid.spec.packing_station
    def manhattan(a,b): return abs(a[0]-b[0]) + abs(a[1]-b[1])

    pop_d = sorted([manhattan(mapping.coord_of(s), ps) for s in popular])
    oth_d = sorted([manhattan(mapping.coord_of(s), ps) for s in others])

    # Las distancias de populares deben ser no mayores que las de otros en la mediana
    assert pop_d[len(pop_d)//2] <= oth_d[len(oth_d)//2]
