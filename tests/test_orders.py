from collections import Counter
from src.demand.rng import RNG
from src.demand.orders import Catalog, Popularity, OrderSpec, OrderGenerator

def make_generators(seed=999, mode="concentrada"):
    rng = RNG(seed=seed)
    catalog = Catalog(n_skus=100)
    pop = Popularity.make(catalog, mode=mode, alpha=1.2)
    gen = OrderGenerator(catalog, pop, OrderSpec(min_items=1, max_items=5, allow_duplicates=True), rng)
    return gen, catalog

def test_order_size_bounds():
    gen, _ = make_generators()
    for _ in range(200):
        o = gen.make_order(arrival_min=0.0)
        assert 1 <= len(o.items) <= 5

def test_popularity_concentrated_has_heavy_head():
    gen, catalog = make_generators(seed=111, mode="concentrada")
    counts = Counter()
    for _ in range(2000):
        o = gen.make_order(0.0)
        counts.update(o.items)

    # SKU1 debe estar entre los más frecuentes y por encima de la mediana de frecuencias
    top_sku = "S0001"
    freqs = sorted(counts.values())
    median = freqs[len(freqs)//2]
    assert counts[top_sku] > median

def test_popularity_uniform_is_flat():
    gen, catalog = make_generators(seed=222, mode="uniforme")
    counts = Counter()
    for _ in range(2000):
        o = gen.make_order(0.0)
        counts.update(o.items)

    # En uniforme, la razón top/median debe ser cercana a 1 y no muy grande
    top = max(counts.values())
    freqs = sorted(counts.values())
    median = freqs[len(freqs)//2]
    assert top / median < 1.5  # margen razonable con 2000 muestras

def test_no_duplicates_when_not_allowed():
    rng = RNG(seed=333)
    catalog = Catalog(n_skus=20)
    pop = Popularity.make(catalog, mode="concentrada", alpha=1.2)
    gen = OrderGenerator(catalog, pop, OrderSpec(min_items=3, max_items=5, allow_duplicates=False), rng)
    for _ in range(200):
        o = gen.make_order(0.0)
        assert len(o.items) == len(set(o.items))  # sin repetidos
