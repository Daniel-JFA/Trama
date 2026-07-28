"""
metrics.py — Cálculo de métricas de red para TRAMA.

PageRank (alpha=0.85) normalizado 0-100 → influence
Betweenness centrality normalizado 0-100 → bridge
Degree → degree
auth = 100 - bot

Para grafos importados (sin score de bot), heurística documentada:
  base = 10
  +35 si el handle tiene 4+ dígitos
  +15 si el handle tiene 2-3 dígitos
  +25 si ratio posts/seguidores > 2
  tope = 95
"""

import re
import networkx as nx


def _count_digits(handle: str) -> int:
    return len(re.findall(r"\d", handle))


def bot_heuristic(handle: str, posts: int, followers: int) -> int:
    """
    Heurística PLACEHOLDER para estimar probabilidad de bot (0-95).
    No es un clasificador real. Señales documentadas:
      - Dígitos en el handle: patrón común en cuentas automatizadas.
      - Ratio posts/seguidores alto: actividad desproporcionada.
    """
    score = 10
    digits = _count_digits(handle)
    if digits >= 4:
        score += 35
    elif digits >= 2:
        score += 15

    if followers > 0 and (posts / followers) > 2:
        score += 25

    return min(score, 95)


def compute_metrics(G: nx.DiGraph | nx.Graph) -> dict:
    """
    Calcula PageRank, betweenness centrality y degree para todos los nodos.
    Devuelve un dict: node_id → {influence, bridge, degree}
    """
    # Trabajar siempre con grafo no dirigido para métricas de centralidad
    UG = G.to_undirected() if G.is_directed() else G

    # PageRank sobre grafo (puede ser dirigido si se importa así)
    try:
        pr = nx.pagerank(G if G.is_directed() else UG, alpha=0.85)
    except Exception:
        pr = {n: 1.0 / len(G) for n in G.nodes()}

    # Betweenness
    bc = nx.betweenness_centrality(UG, normalized=True)

    # Normalizar PageRank a 0-100
    pr_values = list(pr.values())
    pr_min, pr_max = min(pr_values), max(pr_values)
    pr_range = pr_max - pr_min if pr_max != pr_min else 1.0

    result = {}
    for node in G.nodes():
        influence = round((pr[node] - pr_min) / pr_range * 100)
        bridge = round(bc.get(node, 0) * 100)
        degree = UG.degree(node)
        result[node] = {"influence": influence, "bridge": bridge, "degree": degree}

    return result
