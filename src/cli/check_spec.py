import argparse
from pathlib import Path
from src.spec.project_spec import ProjectSpec
from src.spec.config_loader import load_config

def main():
    parser = argparse.ArgumentParser(description="Validar e imprimir la especificación del proyecto.")
    parser.add_argument("--config", type=Path, help="Ruta a JSON/YAML (opcional)")
    args = parser.parse_args()

    spec = ProjectSpec.default() if not args.config else ProjectSpec.from_dict(load_config(args.config))
    spec.validate()
    print(spec.summary())

if __name__ == "__main__":
    main()
