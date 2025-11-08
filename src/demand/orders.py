from dataclasses import dataclass
from typing import List, Dict, Literal, Tuple
import math
from .rng import RNG

PopularityMode = Literal["uniforme", "concentrada"]

@dataclass
class Catalog:
    """Catálogo simple de SKUs enumerados como S0001, S0002, ..."""
    n_skus: int

    def ids(self) -> List[str]:
        return [f"S{idx:04d}" for idx in range(1, self.n_skus + 1)]

@dataclass
class Popularity:
    """Pesos de probabilidad por SKU según modo de popularidad."""
    weights: List[float]  # deben sumar 1.0

    @staticmethod
    def make(catalog: Catalog, mode: PopularityMode, alpha: float = 1.1) -> "Popularity":
        """
        - uniforme: todos con el mismo peso
        - concentrada: Zipf(α) sobre el ranking (α>1). α≈1.1–1.3 da 80/20 aproximado.
        """
        n = catalog.n_skus
        if mode == "uniforme":
            w = [1.0 / n] * n
        else:
            # Zipf discreto por ranking (1..n)
            ranks = [i for i in range(1, n + 1)]
            w_raw = [1.0 / (r ** alpha) for r in ranks]
            s = sum(w_raw)
            w = [x / s for x in w_raw]
        return Popularity(w)

    def probs(self) -> List[float]:
        return self.weights

@dataclass
class OrderSpec:
    """Reglas para el tamaño del pedido y selección de SKUs."""
    min_items: int = 1
    max_items: int = 5
    allow_duplicates: bool = True  # si False: cada SKU aparece como máximo 1 vez en el pedido

@dataclass
class Order:
    arrival_min: float
    items: List[str]            # lista con posibles repetidos = cantidad por SKU
    item_counts: Dict[str, int] # diccionario SKU -> cantidad

def _count_items(items: List[str]) -> Dict[str, int]:
    d: Dict[str, int] = {}
    for s in items:
        d[s] = d.get(s, 0) + 1
    return d

@dataclass
class OrderGenerator:
    catalog: Catalog
    popularity: Popularity
    spec: OrderSpec
    rng: RNG

    def _draw_size(self) -> int:
        a, b = self.spec.min_items, self.spec.max_items
        assert 1 <= a <= b
        # tamaño uniforme discreto entre a y b
        return int(self.rng.integers(a, b + 1))

    def _sample_items(self, k: int) -> List[str]:
        ids = self.catalog.ids()
        p = self.popularity.probs()
        if self.spec.allow_duplicates:
            picked = self.rng.choice(ids, size=k, replace=True, p=p).tolist()
            return picked
        else:
            # sin repetidos: muestreo ponderado sin reemplazo
            # estrategia: muestreo secuencial con actualización de pesos (naive pero ok para n pequeño)
            avail: List[Tuple[str, float]] = list(zip(ids, p))
            items: List[str] = []
            for _ in range(min(k, len(avail))):
                total = sum(w for _, w in avail)
                # ruleta
                r = self.rng.random() * total
                cum = 0.0
                idx = 0
                for i, (sku, w) in enumerate(avail):
                    cum += w
                    if r <= cum:
                        idx = i
                        break
                items.append(avail[idx][0])
                avail.pop(idx)
            return items

    def make_order(self, arrival_min: float) -> Order:
        k = self._draw_size()
        items = self._sample_items(k)
        return Order(arrival_min=arrival_min, items=items, item_counts=_count_items(items))
