"""
metrics.py — Cálculo optimizado de métricas de red, centralidades y comunidades para TRAMA.

Aceleración en C mediante python-igraph:
- PageRank (alpha=0.85, damping=0.85) normalizado 0-100 → influence
- Betweenness Centrality (C-accelerated Brandes) normalizado 0-100 → bridge
- Degree Centrality → degree
- Particionamiento comunitario Leiden (superior a Louvain, resuelve el problema de comunidades desconectadas)
- Integración con motor CIB para detección forense de astroturfing.
"""

import re
from typing import Dict, Any, Union, List, Set, Optional
import networkx as nx
import igraph as ig

from .cib import analyze_cib_profile


def _count_digits(handle: str) -> int:
    return len(re.findall(r"\d", handle))


def bot_heuristic(handle: str, posts: int, followers: int) -> int:
    """
    Evaluación rápida de probabilidad de bot (0-96) combinando patrones de handle y ratios.
    """
    analysis = analyze_cib_profile(
        handle=handle,
        act=[],
        posts=posts,
        followers=followers,
        comm_id=0,
        node_id=-1,
    )
    return analysis["bot_score"]


def compute_metrics(G: Union[nx.DiGraph, nx.Graph, ig.Graph]) -> Dict[Any, Dict[str, int]]:
    """
    Calcula PageRank, betweenness centrality y degree para todos los nodos mediante python-igraph (C core).
    Devuelve un dict: node_id → {influence, bridge, degree} normalizados (0-100).
    """
    if isinstance(G, ig.Graph):
        g_ig = G
        nodes = list(range(g_ig.vcount()))
        is_directed = g_ig.is_directed()
    else:
        nodes = list(G.nodes())
        N = len(nodes)
        if N == 0:
            return {}
        is_directed = G.is_directed()
        node_to_idx = {n: i for i, n in enumerate(nodes)}
        edges = [(node_to_idx[u], node_to_idx[v]) for u, v in G.edges()]
        g_ig = ig.Graph(n=N, edges=edges, directed=is_directed)

    N = g_ig.vcount()
    if N == 0:
        return {}

    # 1. PageRank en C
    try:
        pr = g_ig.pagerank(damping=0.85, directed=is_directed)
    except Exception:
        pr = [1.0 / N] * N

    # 2. Betweenness Centrality en C
    try:
        g_undir = g_ig if not is_directed else g_ig.as_undirected()
        bc_raw = g_undir.betweenness(directed=False)
        # Normalización matemática: para grafo no dirigido con N nodos, max pares = (N-1)(N-2)/2
        norm_factor = ((N - 1) * (N - 2) / 2.0) if N > 2 else 1.0
        bc = [val / norm_factor for val in bc_raw]
    except Exception:
        bc = [0.0] * N

    # Degree
    degrees = g_ig.degree()

    # 3. Normalizar PageRank a 0-100
    pr_min = min(pr) if pr else 0.0
    pr_max = max(pr) if pr else 1.0
    pr_range = pr_max - pr_min if pr_max != pr_min else 1.0

    result = {}
    for i, node in enumerate(nodes):
        inf = round((pr[i] - pr_min) / pr_range * 100) if pr_max != pr_min else 50
        bridge = round(bc[i] * 100)
        result[node] = {
            "influence": min(100, max(0, inf)),
            "bridge": min(100, max(0, bridge)),
            "degree": degrees[i],
        }

    return result


def compute_communities_leiden(
    G: Union[nx.Graph, nx.DiGraph, ig.Graph],
    resolution: float = 1.0,
) -> List[Set[Any]]:
    """
    Detecta comunidades utilizando el algoritmo Leiden optimizado en C vía python-igraph.
    Garantiza comunidades bien conectadas y mayor modularidad en una fracción del tiempo de Louvain.
    Retorna una lista de conjuntos de nodos: [ {node_a, node_b}, ... ]
    """
    if isinstance(G, ig.Graph):
        g_ig = G
        node_list = list(range(g_ig.vcount()))
    else:
        node_list = list(G.nodes())
        if len(node_list) == 0:
            return []
        node_to_idx = {n: i for i, n in enumerate(node_list)}
        edges = [(node_to_idx[u], node_to_idx[v]) for u, v in G.edges()]
        g_ig = ig.Graph(n=len(node_list), edges=edges, directed=False)

    if g_ig.vcount() == 0:
        return []
    if g_ig.ecount() == 0:
        return [{n} for n in node_list]

    try:
        partition = g_ig.community_leiden(
            objective_function="modularity",
            resolution=resolution,
            n_iterations=2,
        )
        return [{node_list[idx] for idx in cluster} for cluster in partition]
    except Exception:
        # Fallback de seguridad en caso de grafos con singularidades
        return [set(node_list)]
