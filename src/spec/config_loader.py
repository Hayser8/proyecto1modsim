from pathlib import Path
from typing import Dict, Any
import json

def load_config(path: Path) -> Dict[str, Any]:
    if path.suffix.lower() in {".json"}:
        return json.loads(path.read_text(encoding="utf-8"))
    try:
        import yaml  # opcional
        if path.suffix.lower() in {".yml", ".yaml"}:
            return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    raise ValueError(f"Formato no soportado: {path.suffix} (usa .json o .yaml)")
