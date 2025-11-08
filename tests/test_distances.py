from src.warehouse.grid import WarehouseGrid
from src.warehouse.routing import shortest_path_steps, path_distance_m, multi_stop_tour_steps

def test_shortest_path_manhattan_on_empty_grid():
    grid = WarehouseGrid(WarehouseGrid.default_spec())
    start = (0,0)
    goal = (3,5)
    steps = shortest_path_steps(grid, start, goal)
    # En grilla 4-conectada sin bloqueos, distancia = Manhattan
    assert steps == abs(3-0) + abs(5-0)
    assert path_distance_m(grid, steps) == steps * grid.spec.cell_size_m

def test_unreachable_when_blocked():
    spec = WarehouseGrid.default_spec()
    # bloquea toda la fila 0 excepto start, separando el grid
    blocked = {(0, c) for c in range(1, spec.cols)}
    spec = type(spec)(rows=spec.rows, cols=spec.cols, cell_size_m=spec.cell_size_m,
                      packing_station=spec.packing_station, blocked=blocked)
    grid = WarehouseGrid(spec)
    steps = shortest_path_steps(grid, (0,0), (0, spec.cols-1))
    assert steps == -1

def test_multi_stop_nn_is_not_worse_than_sum_of_direct_hops():
    grid = WarehouseGrid(WarehouseGrid.default_spec())
    start = (0,0)
    stops = [(0,5), (2,5), (2,0)]
    tour = multi_stop_tour_steps(grid, start, stops)
    # Debe ser finito y como cota superior, la suma de saltos consecutivos en ese orden fijo
    assert tour > 0
    fixed_sum = (5-0) + (2-0) + (5-0) + (2-0)  # 5 + 2 + 5 + 2 = 14
    assert tour <= fixed_sum
