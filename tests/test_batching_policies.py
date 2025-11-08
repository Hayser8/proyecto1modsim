from src.picking.batching import SizeThresholdBatching, TimeThresholdBatching
from src.demand.orders import Order

def make_orders(arrivals):
    # ítems mínimos; acá lo que interesa es la llegada
    return [Order(a, ["X"], {"X": 1}) for a in arrivals]

def test_size_threshold_batches_counts():
    orders = make_orders([0, 0.5, 1.0, 1.2, 1.5, 2.1, 3.0])
    sb = SizeThresholdBatching(batch_size=3)
    batches = sb.make_batches(orders)
    sizes = [len(b.orders) for b in batches]
    assert sizes == [3,3,1]

def test_time_threshold_releases_when_exceeds():
    # Llegadas cada ~1 min; umbral=2 → agrupa de a 2,2,2,1
    orders = make_orders([0.0, 1.0, 2.01, 3.0, 4.01, 5.0, 7.5])
    tb = TimeThresholdBatching(threshold_min=2.0)
    batches = tb.make_batches(orders)
    sizes = [len(b.orders) for b in batches]
    assert sizes == [2,2,2,1]

def test_time_threshold_batch_boundaries_are_coherent():
    orders = make_orders([0.0, 0.5, 1.0, 3.5])  # con umbral=2, el 3.5 debe abrir batch nuevo
    tb = TimeThresholdBatching(2.0)
    batches = tb.make_batches(orders)
    assert batches[0].first_arrival_min == 0.0
    assert batches[0].last_arrival_min == 1.0
    assert batches[1].first_arrival_min == 3.5
