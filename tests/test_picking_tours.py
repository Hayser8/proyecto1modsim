from src.warehouse.grid import WarehouseGrid
from src.warehouse.sku_map import SKUPlacement
from src.picking.tours import order_tour, batch_tour
from src.demand.orders import Order

def test_order_tour_nonnegative_and_returns_zero_when_empty():
    grid = WarehouseGrid(WarehouseGrid.default_spec())
    placement = SKUPlacement(sku_to_coord={"A": (0,0)})

    # pedido sin items → distancia 0
    o_empty = Order(arrival_min=0.0, items=[], item_counts={})
    tr0 = order_tour(grid, placement, o_empty)
    assert tr0.steps == 0 and tr0.meters == 0.0

    # pedido con item en (0,0) → NN = 0 pasos
    o0 = Order(arrival_min=0.0, items=["A"], item_counts={"A": 1})
    tr = order_tour(grid, placement, o0)
    assert tr.steps == 0

def test_batch_tour_not_worse_than_sum_of_orders_with_returns():
    grid = WarehouseGrid(WarehouseGrid.default_spec())
    placement = SKUPlacement(sku_to_coord={
        "A": (0,5), "B": (2,5), "C": (2,0), "D": (5,0)
    })

    o1 = Order(0.0, ["A","B"], {"A":1,"B":1})
    o2 = Order(1.0, ["C"], {"C":1})
    o3 = Order(2.0, ["D"], {"D":1})

    # Tours individuales REGRESANDO a estación (caso justo para comparar contra un batch único)
    tr1 = order_tour(grid, placement, o1, return_to_station=True)
    tr2 = order_tour(grid, placement, o2, return_to_station=True)
    tr3 = order_tour(grid, placement, o3, return_to_station=True)

    # Un solo tour del batch (sin regreso o con regreso; probamos ambas para ser robustos)
    batch_no_rt = batch_tour(grid, placement, [o1, o2, o3], return_to_station=False)
    batch_rt    = batch_tour(grid, placement, [o1, o2, o3], return_to_station=True)

    # El batch no debería ser peor que hacer 3 viajes separados con regreso
    separate_with_returns = tr1.steps + tr2.steps + tr3.steps
    assert batch_no_rt.steps <= separate_with_returns
    assert batch_rt.steps <= separate_with_returns

def test_order_tour_return_to_station_adds_distance():
    grid = WarehouseGrid(WarehouseGrid.default_spec())
    placement = SKUPlacement(sku_to_coord={"A": (0,5)})
    o = Order(0.0, ["A"], {"A":1})
    tr1 = order_tour(grid, placement, o, return_to_station=False)
    tr2 = order_tour(grid, placement, o, return_to_station=True)
    assert tr2.steps > tr1.steps
