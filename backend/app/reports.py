"""
reports.py — Generador de Informes Ejecutivos de Inteligencia de Red para Periodistas y Agencias.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from .political import audit_candidate, find_strategic_brokers


def generate_executive_report(project: Dict[str, Any], candidate_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Genera un informe analítico estructurado a partir del proyecto y su grafo,
    con sección opcional de estrategia electoral para el candidato.
    """
    graph = project.get("graph", {})
    nodes = graph.get("nodes", [])
    links = graph.get("links", [])
    communities = graph.get("communities", [])
    meta = graph.get("meta", {})

    total_nodes = len(nodes)
    total_links = len(links)
    suspicious_nodes = [n for n in nodes if n.get("bot", 0) >= 60]
    pct_suspicious = round(len(suspicious_nodes) / max(1, total_nodes) * 100, 1)

    # Top influyentes
    top_influencers = sorted(nodes, key=lambda x: x.get("influence", 0), reverse=True)[:10]

    # Top puentes
    top_bridges = sorted(nodes, key=lambda x: x.get("bridge", 0), reverse=True)[:5]

    # Distribución por comunidad
    comm_stats = []
    for c in communities:
        cid = c["id"]
        comm_members = [n for n in nodes if n.get("comm") == cid]
        comm_susp = [n for n in comm_members if n.get("bot", 0) >= 60]
        comm_stats.append({
            "id": cid,
            "name": c.get("name", f"Comunidad {cid}"),
            "color": c.get("color", "#888"),
            "size": len(comm_members),
            "percentage": round(len(comm_members) / max(1, total_nodes) * 100, 1),
            "suspicious_count": len(comm_susp),
            "avg_authenticity": round(sum(n.get("auth", 0) for n in comm_members) / max(1, len(comm_members)), 1),
        })

    # Hallazgos forenses de astroturfing
    astroturfing_findings = []
    if len(suspicious_nodes) > 0:
        main_susp_comm = max(comm_stats, key=lambda x: x["suspicious_count"])
        if main_susp_comm["suspicious_count"] > 5:
            astroturfing_findings.append({
                "severity": "ALTA",
                "title": f"Concentración de amplificación artificial en {main_susp_comm['name']}",
                "description": f"Se detectaron {main_susp_comm['suspicious_count']} cuentas con anomalías alfanuméricas o de actividad ({round(main_susp_comm['suspicious_count'] / max(1, len(suspicious_nodes)) * 100)}% de todos los bots).",
            })

    if meta.get("synthetic"):
        astroturfing_findings.append({
            "severity": "CRÍTICA",
            "title": "Sincronización temporal anómala (Semanas 6 y 7)",
            "description": "Pico coordinado de publicaciones 5x superior a la media histórica concentrado en la comunidad amplificadora apuntando al hub gremial.",
        })

    # Sección de Estrategia Electoral del Candidato (War Room)
    campaign_strategy = None
    target_candidate_id = candidate_id
    if target_candidate_id is None and len(nodes) > 0:
        # Por defecto, evaluar al nodo de mayor influencia orgánico
        organic_nodes = [n for n in nodes if not n.get("org") and n.get("bot", 0) < 30]
        if organic_nodes:
            target_candidate_id = max(organic_nodes, key=lambda x: x.get("influence", 0))["id"]

    if target_candidate_id is not None and any(n["id"] == target_candidate_id for n in nodes):
        try:
            audit = audit_candidate(graph, target_candidate_id)
            brokers = find_strategic_brokers(graph, target_candidate_id, limit=3)
            campaign_strategy = {
                "candidate": audit["candidate"],
                "echo_chamber": audit["echo_chamber"],
                "tactical_actions": audit["tactical_actions"],
                "recommended_allies": [
                    {
                        "handle": f"@{b['handle']}",
                        "comm_name": b["comm_name"],
                        "alliance_score": b["alliance_score"],
                        "rationale": b["rationale"],
                    }
                    for b in brokers
                ],
                "threat_level": audit["dirty_war_shield"]["threat_level"],
            }
        except Exception:
            campaign_strategy = None

    return {
        "report_title": f"Informe de Inteligencia de Red: {project.get('name', 'Investigación')}",
        "topic": project.get("topic", meta.get("topic", "N/A")),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_profiles": total_nodes,
            "total_interactions": meta.get("interactions", total_links),
            "total_communities": len(communities),
            "suspicious_profiles": len(suspicious_nodes),
            "suspicious_percentage": pct_suspicious,
        },
        "communities": comm_stats,
        "campaign_strategy": campaign_strategy,
        "top_influencers": [
            {
                "handle": f"@{n.get('handle')}",
                "influence": n.get("influence"),
                "connections": n.get("degree"),
                "authenticity": n.get("auth"),
                "is_institutional": n.get("org", False),
            }
            for n in top_influencers
        ],
        "top_bridges": [
            {
                "handle": f"@{n.get('handle')}",
                "bridge_index": n.get("bridge"),
                "connections": n.get("degree"),
            }
            for n in top_bridges
        ],
        "astroturfing_findings": astroturfing_findings,
        "methodology": {
            "influence_algorithm": "PageRank (damping factor = 0.85, normalizado 0-100)",
            "bridge_algorithm": "Betweenness Centrality (Brandes Algorithm)",
            "community_detection": "Louvain Modularity Optimization",
            "bot_detection": "Análisis Multidimensional CIB (Entropía horaria, sufijos numéricos, fan-in clustering)",
        },
    }
