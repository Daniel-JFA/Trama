"""
export_sample.py — Exporta el grafo sintético a frontend/public/sample-graph.json

Uso:
  cd /home/djfa/Dev/projects/Propios/trama/backend
  source .venv/bin/activate
  python scripts/export_sample.py
"""

import json
import sys
from pathlib import Path

# Añadir el directorio backend al path para importar app.*
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.synth import generate_synthetic_graph

OUTPUT_PATH = Path(__file__).parent.parent.parent / "frontend" / "public" / "sample-graph.json"


def main():
    print("Generando grafo sintético...")
    graph = generate_synthetic_graph()

    nodes = graph["nodes"]
    links = graph["links"]
    communities = graph["communities"]

    print(f"  Nodos:       {len(nodes)}")
    print(f"  Aristas:     {len(links)}")
    print(f"  Comunidades: {len(communities)}")
    print(f"  Meta:        {graph['meta']}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, separators=(",", ":"))

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"\nExportado a: {OUTPUT_PATH}")
    print(f"Tamaño: {size_kb:.1f} KB")

    # Verificación básica
    assert len(nodes) == 150, f"Se esperaban 150 nodos, se obtuvieron {len(nodes)}"
    assert len(links) >= 100, f"Se esperaban al menos 100 aristas, se obtuvieron {len(links)}"
    print("\nVerificación OK.")


if __name__ == "__main__":
    main()
