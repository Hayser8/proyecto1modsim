from src.warehouse.grid import WarehouseGrid

def test_grid_nodes_and_edges():
    grid = WarehouseGrid(WarehouseGrid.default_spec())
    nodes = list(grid.nodes())
    assert len(nodes) == grid.spec.rows * grid.spec.cols

    # En una grilla rectangular 4-conectada interna cada nodo tiene hasta 4 vecinos
    # Verificar que la packing_station tenga al menos 2 vecinos (salvo que esté en esquina)
    deg = len(list(grid.neighbors(grid.spec.packing_station)))
    assert deg >= 2

def test_blocked_cells():
    spec = WarehouseGrid.default_spec()
    blocked = {(0,1), (1,1)}
    spec = type(spec)(rows=spec.rows, cols=spec.cols, cell_size_m=spec.cell_size_m,
                      packing_station=spec.packing_station, blocked=blocked)
    grid = WarehouseGrid(spec)
    assert (0,1) not in list(grid.nodes())
    # Asegurar que no aparece arista hacia bloqueados
    for u, v in grid.edges():
        assert u not in blocked and v not in blocked
