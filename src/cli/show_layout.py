from src.warehouse.grid import WarehouseGrid

def main():
    grid = WarehouseGrid(WarehouseGrid.default_spec())
    nodes = list(grid.nodes())
    edges = list(grid.edges())
    print(f"Nodos: {len(nodes)}  Aristas: {len(edges)}")
    print(f"Packing station: {grid.spec.packing_station}")
    # ejemplo de distancia en pasos
    from src.warehouse.routing import shortest_path_steps
    steps = shortest_path_steps(grid, grid.spec.packing_station, (grid.spec.rows-1, grid.spec.cols-1))
    print(f"Pasos (packing -> esquina opuesta): {steps}  Distancia(m): {grid.meters(steps):.1f}")

if __name__ == "__main__":
    main()
