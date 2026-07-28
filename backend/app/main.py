"""
main.py — API FastAPI para TRAMA.

Endpoints:
  GET  /api/health          → {"status":"ok"}
  GET  /api/graph           → grafo activo completo
  GET  /api/overlap?ids=... → solapamiento Jaccard entre vecindades
  POST /api/import          → importar CSV (source,target)
  POST /api/reset           → volver al dataset sintético
"""

import io
import csv
import re
from typing import Optional

import networkx as nx
from fastapi import FastAPI, Query, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .synth import generate_synthetic_graph
from .metrics import compute_metrics, bot_heuristic

app = FastAPI(title="TRAMA API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Grafo activo en memoria ─────────────────────────────────────────────────
_active_graph: dict = {}


def _load_synthetic():
    global _active_graph
    _active_graph = generate_synthetic_graph()


# Inicializar al arrancar
_load_synthetic()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _build_neighbor_sets() -> dict[int, set[int]]:
    """Devuelve un dict id → set de ids vecinos a partir del grafo activo."""
    neighbors: dict[int, set[int]] = {n["id"]: set() for n in _active_graph["nodes"]}
    for link in _active_graph["links"]:
        s, t = link["source"], link["target"]
        if s in neighbors:
            neighbors[s].add(t)
        if t in neighbors:
            neighbors[t].add(s)
    return neighbors


def _node_ids() -> set[int]:
    return {n["id"] for n in _active_graph["nodes"]}


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/graph")
def get_graph():
    return _active_graph


@app.get("/api/overlap")
def overlap(ids: str = Query(..., description="IDs separados por coma, mínimo 2")):
    # Parsear ids
    try:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=422, detail="Los ids deben ser enteros separados por coma.")

    if len(id_list) < 2:
        raise HTTPException(status_code=422, detail="Se necesitan al menos 2 ids para calcular solapamiento.")

    valid_ids = _node_ids()
    invalid = [i for i in id_list if i not in valid_ids]
    if invalid:
        raise HTTPException(status_code=404, detail=f"Nodos no encontrados: {invalid}")

    neighbors = _build_neighbor_sets()
    results = []

    for i in range(len(id_list)):
        for j in range(i + 1, len(id_list)):
            a, b = id_list[i], id_list[j]
            set_a = neighbors[a]
            set_b = neighbors[b]
            common = set_a & set_b
            union = set_a | set_b
            jaccard = round(len(common) / len(union) * 100) if union else 0
            results.append({
                "a": a,
                "b": b,
                "jaccard": jaccard,
                "common": list(common),
            })

    return {"pairs": results}


@app.post("/api/import")
async def import_csv(file: UploadFile = File(...)):
    global _active_graph

    # Leer contenido
    content_bytes = await file.read()
    try:
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="El archivo debe estar en codificación UTF-8.")

    # Parsear CSV
    reader = csv.DictReader(io.StringIO(content))
    if reader.fieldnames is None or not {"source", "target"}.issubset(
        {f.strip().lower() for f in reader.fieldnames}
    ):
        raise HTTPException(
            status_code=422,
            detail="El CSV debe tener columnas 'source' y 'target'.",
        )

    # Normalizar nombres de columnas (por si tienen espacios)
    fieldnames_map = {f.strip().lower(): f for f in (reader.fieldnames or [])}

    edges = []
    for row in reader:
        norm = {k.strip().lower(): v.strip() for k, v in row.items()}
        src = norm.get("source", "").lstrip("@")
        tgt = norm.get("target", "").lstrip("@")
        if src and tgt and src != tgt:
            edges.append((src, tgt))

    if not edges:
        raise HTTPException(status_code=422, detail="No se encontraron aristas válidas en el CSV.")

    # Construir grafo
    G = nx.Graph()
    G.add_edges_from(edges)

    unique_handles = list(G.nodes())
    if len(unique_handles) < 3:
        raise HTTPException(status_code=422, detail="Se necesitan al menos 3 nodos distintos.")

    # Detectar comunidades con Louvain (seed fija para determinismo)
    import networkx.algorithms.community as nx_comm
    communities_sets = list(nx_comm.louvain_communities(G, seed=LOUVAIN_SEED))

    handle_to_comm: dict[str, int] = {}
    for cid, comm_set in enumerate(communities_sets):
        for h in comm_set:
            handle_to_comm[h] = cid

    PALETTE = ["#E8C15A", "#5AD1B3", "#8B7CF6", "#E060B8", "#60A5FA", "#F97316", "#A3E635", "#E879F9"]

    communities_meta = [
        {"id": i, "name": f"Comunidad {i + 1}", "color": PALETTE[i % len(PALETTE)]}
        for i in range(len(communities_sets))
    ]

    # Calcular métricas
    metrics = compute_metrics(G)

    # Construir nodos
    nodes = []
    for idx, handle in enumerate(unique_handles):
        cid = handle_to_comm.get(handle, 0)
        bot = bot_heuristic(handle, posts=50, followers=500)  # placeholder sin datos reales
        m = metrics.get(handle, {"influence": 0, "bridge": 0, "degree": 0})
        nodes.append({
            "id": idx,
            "handle": handle,
            "comm": cid,
            "org": False,
            "bot": bot,
            "auth": max(0, 100 - bot),
            "act": [0] * 12,
            "followers": 0,
            "posts": 0,
            "degree": m["degree"],
            "influence": m["influence"],
            "bridge": m["bridge"],
        })

    handle_to_id = {h: i for i, h in enumerate(unique_handles)}
    links = [{"source": handle_to_id[u], "target": handle_to_id[v]} for u, v in G.edges()]

    _active_graph = {
        "meta": {
            "topic": "CSV importado",
            "weeks": 0,
            "synthetic": False,
            "interactions": len(edges),
        },
        "communities": communities_meta,
        "nodes": nodes,
        "links": links,
    }

    return {
        "imported": len(edges),
        "nodes": len(nodes),
        "links": len(links),
        "communities": len(communities_meta),
    }


@app.post("/api/reset")
def reset():
    _load_synthetic()
    return {"status": "ok", "message": "Grafo sintético restaurado."}


LOUVAIN_SEED = 42
