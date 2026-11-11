"""
exporters.py — Exportadores de grafos a formatos estándar de la industria (Gephi GEXF, GraphML).
"""

import io
import networkx as nx
from typing import Dict, Any


def export_graph_to_gexf(graph_dict: Dict[str, Any]) -> str:
    """
    Convierte el formato interno de grafo de TRAMA en un archivo XML GEXF válido para Gephi.
    Incluye comunidades, métricas calculadas y atributos de autenticidad.
    """
    G = nx.Graph()
    comm_map = {c["id"]: c.get("name", f"Comunidad {c['id']}") for c in graph_dict.get("communities", [])}

    # Agregar nodos con atributos
    for node in graph_dict.get("nodes", []):
        node_id = str(node["id"])
        G.add_node(
            node_id,
            label=f"@{node.get('handle', node_id)}",
            community=comm_map.get(node.get("comm", 0), "General"),
            influence=float(node.get("influence", 0)),
            bridge=float(node.get("bridge", 0)),
            bot_score=int(node.get("bot", 0)),
            authenticity=int(node.get("auth", 100)),
            followers=int(node.get("followers", 0)),
            posts=int(node.get("posts", 0)),
            is_institutional=bool(node.get("org", False)),
        )

    # Agregar aristas
    for link in graph_dict.get("links", []):
        s = str(link["source"]["id"] if isinstance(link["source"], dict) else link["source"])
        t = str(link["target"]["id"] if isinstance(link["target"], dict) else link["target"])
        if G.has_node(s) and G.has_node(t):
            G.add_edge(s, t)

    # Generar GEXF
    buffer = io.BytesIO()
    nx.write_gexf(G, buffer, encoding="utf-8", version="1.2draft")
    return buffer.getvalue().decode("utf-8")
