from src.spec.project_spec import ProjectSpec

def test_summary_contains_core_fields():
    spec = ProjectSpec.default()
    txt = spec.summary()
    assert "ESPECIFICACIÓN DEL PROYECTO" in txt
    assert "Políticas:" in txt
    assert "Paralelismo de personas" in txt
    assert "KPIs:" in txt
    assert "Factores experimentales:" in txt
