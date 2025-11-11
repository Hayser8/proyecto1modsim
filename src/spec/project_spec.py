from dataclasses import dataclass
from typing import List, Dict, Optional, Literal, Any

Direction = Literal["max", "min", "balanced"]

@dataclass
class KPI:
    target_direction: Direction
    notes: Optional[str] = None

@dataclass
class Scope:
    system: str
    time_horizon_hours: int
    entities: List[str]
    policies_to_compare: List[str]
    parallelism_people_enabled: bool
    notes: Optional[str] = None

@dataclass
class ExperimentalFactors:
    policy: List[str]
    batch_size: List[int]
    batch_time_min: List[int]
    sku_popularity: List[str]
    n_pickers: List[int]
    congestion_model: List[str]

@dataclass
class ProjectSpec:
    scope: Scope
    objectives: List[str]
    key_questions: List[str]
    kpis: Dict[str, KPI]
    assumptions: List[str]
    experimental_factors: ExperimentalFactors

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ProjectSpec":
        scope = Scope(**d["scope"])
        ef = ExperimentalFactors(**d["experimental_factors"])
        kpis = {k: KPI(**v) for k, v in d["kpis"].items()}
        return ProjectSpec(
            scope=scope,
            objectives=d["objectives"],
            key_questions=d["key_questions"],
            kpis=kpis,
            assumptions=d["assumptions"],
            experimental_factors=ef,
        )

    @staticmethod
    def default() -> "ProjectSpec":
        """Configuración por código (no necesitas JSON)."""
        return ProjectSpec.from_dict({
            "scope": {
                "system": "CD con picking y empaque en grilla",
                "time_horizon_hours": 8,
                "entities": ["Pedido", "SKU", "Picker", "Estante", "EstaciónEmpaque", "Almacén"],
                "policies_to_compare": ["Secuencial_FCFS", "Batching"],
                "parallelism_people_enabled": True,
                "notes": "Comparar 1–3 pickers; congestión model opcional"
            },
            "objectives": [
                "Maximizar throughput (pedidos/hora)",
                "Minimizar espera promedio del cliente",
                "Evaluar el efecto del paralelismo humano en productividad y utilización"
            ],
            "key_questions": [
                "¿Batching reduce distancia por pedido vs Secuencial?",
                "¿Cómo afectan tamaño/tiempo de batch la espera?",
                "¿Cuánto sube el throughput con 2–3 pickers?",
                "¿Hay cuellos por congestión con varios pickers?"
            ],
            "kpis": {
                "throughput_pedidos_por_hora": {"target_direction": "max"},
                "tiempo_espera_promedio_min": {"target_direction": "min"},
                "distancia_por_pedido_m": {"target_direction": "min"},
                "utilizacion_picker": {"target_direction": "balanced", "notes": "Ideal 70–90%"},
                "bloqueos_por_congestion": {"target_direction": "min"}
            },
            "assumptions": [
                "Arribos ~ Poisson (λ configurable)",
                "Pedido con 1–5 SKUs; popularidad: uniforme o concentrada (80/20)",
                "Velocidad de desplazamiento constante (1ª aproximación)",
                "Layout fijo en grilla; hotspots de SKUs"
            ],
            "experimental_factors": {
                "policy": ["Secuencial_FCFS", "Batching"],
                "batch_size": [5, 10, 15],
                "batch_time_min": [1, 2, 5],
                "sku_popularity": ["uniforme", "concentrada"],
                "n_pickers": [1, 2, 3],
                "congestion_model": ["off", "ligera"]
            }
        })

    def validate(self) -> None:
        assert self.scope.time_horizon_hours > 0, "time_horizon_hours debe ser > 0"
        assert self.scope.policies_to_compare, "Definir policies_to_compare"
        assert self.objectives, "Faltan objetivos"
        assert self.key_questions, "Faltan preguntas clave"
        assert self.kpis, "Faltan KPIs"
        assert all(isinstance(v, KPI) for v in self.kpis.values()), "KPIs mal definidos"
        assert self.experimental_factors.n_pickers, "Definir niveles de n_pickers"

        if self.scope.parallelism_people_enabled:
            assert max(self.experimental_factors.n_pickers) >= 2, \
                "Con paralelismo ON, incluir al menos n_pickers ≥ 2"

        if "Batching" in self.experimental_factors.policy:
            assert (self.experimental_factors.batch_size or self.experimental_factors.batch_time_min), \
                "Si hay Batching, definir batch_size o batch_time_min"

    def summary(self) -> str:
        s = []
        s.append("=== ESPECIFICACIÓN DEL PROYECTO ===")
        s.append(f"Sistema: {self.scope.system}")
        s.append(f"Horizonte: {self.scope.time_horizon_hours} h")
        s.append(f"Entidades: {', '.join(self.scope.entities)}")
        s.append(f"Políticas: {', '.join(self.scope.policies_to_compare)}")
        s.append(f"Paralelismo de personas: {'ON' if self.scope.parallelism_people_enabled else 'OFF'}")
        if self.scope.notes:
            s.append(f"Notas: {self.scope.notes}")
        s.append("\nObjetivos:")
        s += [f"- {o}" for o in self.objectives]
        s.append("\nPreguntas clave:")
        s += [f"- {q}" for q in self.key_questions]
        s.append("\nKPIs:")
        for n, k in self.kpis.items():
            line = f"- {n} → {k.target_direction}"
            if k.notes:
                line += f" ({k.notes})"
            s.append(line)
        s.append("\nFactores experimentales:")
        ef = self.experimental_factors
        s.append(f"- policy = {ef.policy}")
        s.append(f"- batch_size = {ef.batch_size}")
        s.append(f"- batch_time_min = {ef.batch_time_min}")
        s.append(f"- sku_popularity = {ef.sku_popularity}")
        s.append(f"- n_pickers = {ef.n_pickers}")
        s.append(f"- congestion_model = {ef.congestion_model}")
        return "\n".join(s)
