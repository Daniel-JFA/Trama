"""
political.py — Motor de Inteligencia y Estrategia Política (War Room) para TRAMA.

Módulos analíticos:
1. Echo Chamber Index (ECI) & Diagnóstico de Posicionamiento
2. Strategic Broker Finder (Nodos Puente & Alianzas Clave)
3. Expansion Paths (Rutas Óptimas hacia Indecisos / Comunidades Objetivo)
4. Dirty War Shield (Detección de Guerra Sucia, Ataques Coordinados y Bots Hostiles)
5. Tactical Campaign Recommendations (Plan de Acción Semanal)
"""

from typing import Dict, Any, List, Optional, Set
import networkx as nx


def _extract_id(val: Any) -> Any:
    if isinstance(val, dict):
        return val.get("id")
    return val


def _build_nx_graph(graph_data: dict) -> tuple[nx.Graph, Dict[Any, dict], Dict[int, str]]:
    """
    Construye un grafo NetworkX no dirigido a partir del dict JSON de TRAMA,
    junto con un mapa de nodos {id: dict} y mapa de comunidades {comm_id: name}.
    """
    G = nx.Graph()
    nodes_map: Dict[Any, dict] = {}
    comm_names: Dict[int, str] = {}

    for c in graph_data.get("communities", []):
        comm_names[c["id"]] = c.get("name", f"Comunidad {c['id']}")

    for n in graph_data.get("nodes", []):
        nid = n["id"]
        nodes_map[nid] = n
        G.add_node(
            nid,
            handle=n.get("handle", f"node_{nid}"),
            comm=n.get("comm", 0),
            bot=n.get("bot", 0),
            auth=n.get("auth", 100),
            influence=n.get("influence", 0),
            bridge=n.get("bridge", 0),
            followers=n.get("followers", 0),
        )

    for l in graph_data.get("links", []):
        s = _extract_id(l.get("source"))
        t = _extract_id(l.get("target"))
        if s is not None and t is not None and G.has_node(s) and G.has_node(t):
            G.add_edge(s, t)

    return G, nodes_map, comm_names


def calculate_echo_chamber_index(G: nx.Graph, candidate_id: Any, candidate_comm: int) -> dict:
    """
    Calcula el Echo Chamber Index (ECI) del candidato (0-100%).
    0 = Máxima transversalidad (dialoga ampliamente fuera de su nicho).
    100 = Burbuja absoluta (solo interactúa con su propio núcleo duro).
    """
    if candidate_id not in G:
        return {
            "score": 100,
            "level": "Sin datos",
            "internal_ratio": 1.0,
            "interpretation": "El candidato no tiene conexiones registradas en el grafo.",
        }

    direct_neighbors = list(G.neighbors(candidate_id))
    if not direct_neighbors:
        return {
            "score": 100,
            "level": "Aislado",
            "internal_ratio": 1.0,
            "interpretation": "Perfil sin interacciones en la red analizada.",
        }

    # 1. Ratio directo (1-hop)
    direct_internal = sum(1 for n in direct_neighbors if G.nodes[n].get("comm") == candidate_comm)
    ratio_1hop = direct_internal / len(direct_neighbors)

    # 2. Ratio ampliado (2-hop: vecinos de los vecinos)
    two_hop_nodes: Set[Any] = set()
    for n in direct_neighbors:
        for n2 in G.neighbors(n):
            if n2 != candidate_id and n2 not in direct_neighbors:
                two_hop_nodes.add(n2)

    if two_hop_nodes:
        two_hop_internal = sum(1 for n in two_hop_nodes if G.nodes[n].get("comm") == candidate_comm)
        ratio_2hop = two_hop_internal / len(two_hop_nodes)
    else:
        ratio_2hop = ratio_1hop

    # Ponderación 70% directo + 30% segundo nivel
    combined_ratio = (ratio_1hop * 0.7) + (ratio_2hop * 0.3)
    score = int(round(combined_ratio * 100))

    if score >= 75:
        level = "Burbuja Crítica (Cámara de Eco Extrema)"
        interpretation = (
            f"El {score}% de tu alcance se concentra en tu propio núcleo duro. "
            "Riesgo alto de falso triunfalismo: tus propuestas no están llegando a electores indecisos."
        )
    elif score >= 55:
        level = "Burbuja Alta (Endogamia Significativa)"
        interpretation = (
            f"Con un ECI del {score}%, la mayoría de tu debate ocurre entre convencidos. "
            "Es crucial activar voceros puente para penetrar nuevas comunidades."
        )
    elif score >= 35:
        level = "Alcance Moderado / En Crecimiento"
        interpretation = (
            f"ECI del {score}%. Tienes una conversación saludable que comienza a permear "
            "hacia otros sectores, aunque aún dependes fuertemente de tu comunidad base."
        )
    else:
        level = "Liderazgo Transversal / Alta Penetración"
        interpretation = (
            f"ECI del {score}%. Tu discurso rompió la burbuja y tiene tracción real en comunidades "
            "ajenas e independientes. Alta capacidad de convocar votantes no tradicionales."
        )

    return {
        "score": score,
        "level": level,
        "direct_internal_count": direct_internal,
        "direct_total_count": len(direct_neighbors),
        "two_hop_count": len(two_hop_nodes),
        "internal_ratio": round(combined_ratio, 3),
        "interpretation": interpretation,
    }


def audit_candidate(graph_data: dict, candidate_id: Any) -> dict:
    """
    Diagnóstico 360° del candidato o perfil político seleccionado.
    """
    G, nodes_map, comm_names = _build_nx_graph(graph_data)

    if candidate_id not in nodes_map:
        raise ValueError(f"Candidato con ID '{candidate_id}' no encontrado en el grafo.")

    cand_node = nodes_map[candidate_id]
    cand_comm = cand_node.get("comm", 0)
    comm_name = comm_names.get(cand_comm, f"Comunidad {cand_comm}")

    neighbors = list(G.neighbors(candidate_id))
    eci = calculate_echo_chamber_index(G, candidate_id, cand_comm)

    # Desglose de alcance por comunidad
    comm_counts: Dict[int, int] = {}
    for n in neighbors:
        c = G.nodes[n].get("comm", 0)
        comm_counts[c] = comm_counts.get(c, 0) + 1

    total_neighbors = len(neighbors)
    community_reach = []
    for cid, cname in comm_names.items():
        count = comm_counts.get(cid, 0)
        pct = round((count / total_neighbors * 100), 1) if total_neighbors > 0 else 0.0
        community_reach.append({
            "comm_id": cid,
            "comm_name": cname,
            "connections_count": count,
            "percentage": pct,
            "is_home": (cid == cand_comm),
        })

    community_reach.sort(key=lambda x: x["connections_count"], reverse=True)

    # Análisis de exposición a Guerra Sucia / Cuentas Inauténticas
    bot_neighbors = []
    hostile_count = 0
    for n in neighbors:
        node_info = nodes_map[n]
        bot_score = node_info.get("bot", 0)
        if bot_score >= 50:
            hostile_count += 1
            bot_neighbors.append({
                "id": node_info["id"],
                "handle": node_info["handle"],
                "comm": node_info.get("comm", 0),
                "bot_score": bot_score,
                "reasons": node_info.get("cib_reasons", []),
            })

    dirty_war_pct = round((hostile_count / total_neighbors * 100), 1) if total_neighbors > 0 else 0.0
    if dirty_war_pct >= 25:
        threat_level = "Alto (Ataque Coordinado Activo)"
        threat_msg = f"{dirty_war_pct}% de las cuentas conectadas a tu perfil presentan patrones inauténticos de astroturfing."
    elif dirty_war_pct >= 10:
        threat_level = "Medio (Hostigamiento Focalizado)"
        threat_msg = f"{dirty_war_pct}% de cuentas sospechosas detectadas en tu órbita directa."
    else:
        threat_level = "Bajo (Interacción Mayormente Orgánica)"
        threat_msg = "No se detectan brigadas masivas de desinformación operando directamente sobre tu perfil."

    # Recomendaciones tácticas de campaña
    tactical_actions = []
    if eci["score"] >= 60:
        tactical_actions.append({
            "priority": "Alta",
            "category": "Romper la Burbuja",
            "action": f"Priorizar apariciones e interacción con voceros fuera de '{comm_name}'. Tu mensaje actual se está recirculando entre convencidos.",
        })

    # Buscar la comunidad externa más débil
    external_comms = [c for c in community_reach if not c["is_home"]]
    if external_comms:
        weakest = min(external_comms, key=lambda x: x["connections_count"])
        tactical_actions.append({
            "priority": "Alta",
            "category": "Expansión Electoral",
            "action": f"Activar puentes hacia la comunidad '{weakest['comm_name']}' (actualmente solo representa {weakest['percentage']}% de tu red).",
        })

    if dirty_war_pct >= 15:
        tactical_actions.append({
            "priority": "Media",
            "category": "Blindaje Forense",
            "action": f"Detectadas {hostile_count} cuentas bot interactuando con tu perfil. Evitar responder directamente para no darles relevancia algorítmica; exportar evidencia forense.",
        })
    else:
        tactical_actions.append({
            "priority": "Media",
            "category": "Posicionamiento",
            "action": "Tu índice de autenticidad es sólido. Apalancar a tus seguidores más influyentes para liderar temas de coyuntura.",
        })

    return {
        "candidate": {
            "id": cand_node["id"],
            "handle": cand_node["handle"],
            "comm_id": cand_comm,
            "comm_name": comm_name,
            "followers": cand_node.get("followers", 0),
            "influence": cand_node.get("influence", 0),
            "bridge": cand_node.get("bridge", 0),
            "degree": cand_node.get("degree", 0),
            "bot_score": cand_node.get("bot", 0),
            "auth_score": cand_node.get("auth", 100),
        },
        "echo_chamber": eci,
        "community_reach": community_reach,
        "dirty_war_shield": {
            "threat_level": threat_level,
            "threat_message": threat_msg,
            "hostile_accounts_count": hostile_count,
            "hostile_percentage": dirty_war_pct,
            "flagged_accounts": bot_neighbors[:10],
        },
        "tactical_actions": tactical_actions,
    }


def find_strategic_brokers(
    graph_data: dict,
    candidate_id: Any,
    target_comm_id: Optional[int] = None,
    limit: int = 10,
) -> List[dict]:
    """
    Encuentra los líderes puente (*brokers*) más estratégicos.
    Son nodos que:
    - Poseen alta intermediación (*bridge centrality*).
    - Tienen alta autenticidad orgánica (baja probabilidad de bot, bot < 35).
    - Tienen conexiones efectivas hacia la comunidad objetivo (o comunidades externas).
    """
    G, nodes_map, comm_names = _build_nx_graph(graph_data)

    if candidate_id not in nodes_map:
        raise ValueError(f"Candidato {candidate_id} no existe en el grafo.")

    cand_comm = nodes_map[candidate_id].get("comm", 0)
    brokers = []

    for nid, node in nodes_map.items():
        if nid == candidate_id:
            continue

        bot_score = node.get("bot", 0)
        # Filtrar bots o cuentas altamente sospechosas
        if bot_score >= 35:
            continue

        neighbors = list(G.neighbors(nid))
        if not neighbors:
            continue

        # Evaluar hacia dónde apunta este nodo
        comm_distribution: Dict[int, int] = {}
        for nb in neighbors:
            c = G.nodes[nb].get("comm", 0)
            comm_distribution[c] = comm_distribution.get(c, 0) + 1

        bridge_score = node.get("bridge", 0)
        influence_score = node.get("influence", 0)

        # Si se especificó comunidad objetivo
        if target_comm_id is not None:
            target_links = comm_distribution.get(target_comm_id, 0)
            if target_links == 0 and bridge_score < 10:
                continue
            reach_metric = target_links
        else:
            # Enlaces hacia cualquier comunidad externa a la del candidato
            reach_metric = sum(cnt for cid, cnt in comm_distribution.items() if cid != cand_comm)

        # Distancia topológica al candidato
        try:
            distance = nx.shortest_path_length(G, source=candidate_id, target=nid)
        except nx.NetworkXNoPath:
            distance = 99

        # Score estratégico de alianza (0 a 100)
        # Valora: puente (30%), alcance a objetivo (30%), influencia (25%), cercanía (15%)
        proximity_score = max(0, 100 - (distance - 1) * 35) if distance < 99 else 0
        reach_norm = min(100, reach_metric * 15)
        
        alliance_score = int(round(
            (bridge_score * 0.30) +
            (reach_norm * 0.30) +
            (influence_score * 0.25) +
            (proximity_score * 0.15)
        ))

        node_comm = node.get("comm", 0)
        target_name = comm_names.get(target_comm_id, "comunidades objetivo") if target_comm_id is not None else "comunidades externas"
        
        rationale = (
            f"Conecta con {reach_metric} actores de {target_name}. "
            f"Autenticidad {100 - bot_score}%, influencia {influence_score}/100 a distancia {distance} de ti."
        )

        brokers.append({
            "id": nid,
            "handle": node["handle"],
            "comm_id": node_comm,
            "comm_name": comm_names.get(node_comm, f"Comunidad {node_comm}"),
            "alliance_score": alliance_score,
            "bridge": bridge_score,
            "influence": influence_score,
            "bot_score": bot_score,
            "auth_score": 100 - bot_score,
            "target_reach": reach_metric,
            "distance_to_candidate": distance,
            "followers": node.get("followers", 0),
            "rationale": rationale,
        })

    brokers.sort(key=lambda x: x["alliance_score"], reverse=True)
    return brokers[:limit]


def find_expansion_paths(
    graph_data: dict,
    candidate_id: Any,
    target_comm_id: int,
    max_paths: int = 3,
) -> List[dict]:
    """
    Calcula las rutas óptimas de menor fricción y mayor tracción para llegar
    desde el candidato a líderes influyentes de una comunidad objetivo.
    """
    G, nodes_map, comm_names = _build_nx_graph(graph_data)

    if candidate_id not in nodes_map:
        raise ValueError(f"Candidato {candidate_id} no existe en el grafo.")

    # Identificar los top 3 líderes de la comunidad objetivo por influencia
    target_candidates = [
        nid for nid, n in nodes_map.items()
        if n.get("comm") == target_comm_id and n.get("bot", 0) < 30
    ]
    target_candidates.sort(key=lambda x: nodes_map[x].get("influence", 0), reverse=True)
    top_targets = target_candidates[:5]

    paths_result = []

    for tgt_id in top_targets:
        if tgt_id == candidate_id:
            continue
        try:
            path = nx.shortest_path(G, source=candidate_id, target=tgt_id)
        except nx.NetworkXNoPath:
            continue

        if len(path) < 2:
            continue

        # Evaluar la calidad y fricción de la ruta
        steps = []
        path_friction = 0
        for idx, node_id in enumerate(path):
            n_data = nodes_map[node_id]
            bot = n_data.get("bot", 0)
            if bot > 40:
                path_friction += 30  # Penalización alta por pasar a través de cuentas bot
            steps.append({
                "step_order": idx + 1,
                "id": node_id,
                "handle": n_data["handle"],
                "comm_id": n_data.get("comm", 0),
                "comm_name": comm_names.get(n_data.get("comm", 0), f"Comunidad {n_data.get('comm', 0)}"),
                "influence": n_data.get("influence", 0),
                "auth": 100 - bot,
                "role": "Candidato" if idx == 0 else ("Objetivo Final" if idx == len(path) - 1 else "Conector / Aliado"),
            })

        target_handle = nodes_map[tgt_id]["handle"]
        paths_result.append({
            "target_id": tgt_id,
            "target_handle": target_handle,
            "target_comm_name": comm_names.get(target_comm_id, f"Comunidad {target_comm_id}"),
            "hops": len(path) - 1,
            "viability_score": max(10, 100 - (len(path) - 1) * 15 - path_friction),
            "steps": steps,
            "strategic_summary": f"Ruta en {len(path) - 1} saltos para conectar con @{target_handle} mediante intermediarios orgánicos.",
        })

    paths_result.sort(key=lambda x: x["viability_score"], reverse=True)
    return paths_result[:max_paths]


def list_potential_candidates(graph_data: dict, top_per_comm: int = 3) -> List[dict]:
    """
    Retorna perfiles clave sugeridos del grafo como candidatos para análisis
    (ordenados por influencia en cada comunidad).
    """
    _, nodes_map, comm_names = _build_nx_graph(graph_data)
    by_comm: Dict[int, List[dict]] = {}

    for n in nodes_map.values():
        c = n.get("comm", 0)
        if c not in by_comm:
            by_comm[c] = []
        by_comm[c].append(n)

    results = []
    for c, nlist in by_comm.items():
        nlist.sort(key=lambda x: x.get("influence", 0), reverse=True)
        for n in nlist[:top_per_comm]:
            results.append({
                "id": n["id"],
                "handle": n["handle"],
                "comm_id": c,
                "comm_name": comm_names.get(c, f"Comunidad {c}"),
                "influence": n.get("influence", 0),
                "bridge": n.get("bridge", 0),
                "followers": n.get("followers", 0),
                "bot_score": n.get("bot", 0),
            })

    results.sort(key=lambda x: x["influence"], reverse=True)
    return results


def calculate_random_walk_controversy(
    graph_data: dict,
    comm1_id: int,
    comm2_id: int,
    num_walks: int = 500,
    max_steps: int = 8,
) -> Dict[str, Any]:
    """
    Calcula el índice de controversia y polarización mediante Random Walk Controversy (RWC)
    (Garimella et al.) y conductancia de frontera entre dos comunidades enfrentadas.

    Métricas retornadas:
      - rwc_score: 0 a 100% (100% = máxima controversia/separación, 0% = debate transversal).
      - conductance: conductancia de frontera (flujo de aristas entre ambas facciones).
      - cut_edges_count: número de aristas que cruzan entre ambas comunidades.
      - p_comm1_stay: probabilidad de que un paseo que arranca en Comm1 permanezca en Comm1.
      - p_comm2_stay: probabilidad de que un paseo que arranca en Comm2 permanezca en Comm2.
      - boundary_nodes_count: cantidad de cuentas en la frontera de contacto.
      - diagnosis: evaluación cualitativa de la rigidez de las cámaras de eco.
    """
    import random

    G, nodes_map, comm_names = _build_nx_graph(graph_data)

    nodes_c1 = [nid for nid, n in nodes_map.items() if n.get("comm") == comm1_id and G.has_node(nid)]
    nodes_c2 = [nid for nid, n in nodes_map.items() if n.get("comm") == comm2_id and G.has_node(nid)]

    name_c1 = comm_names.get(comm1_id, f"Comunidad {comm1_id}")
    name_c2 = comm_names.get(comm2_id, f"Comunidad {comm2_id}")

    if len(nodes_c1) < 2 or len(nodes_c2) < 2:
        return {
            "comm1": {"id": comm1_id, "name": name_c1, "size": len(nodes_c1)},
            "comm2": {"id": comm2_id, "name": name_c2, "size": len(nodes_c2)},
            "rwc_score": 0.0,
            "conductance": 0.0,
            "cut_edges_count": 0,
            "boundary_nodes_count": 0,
            "p_comm1_stay": 0.5,
            "p_comm2_stay": 0.5,
            "diagnosis": "Comunidades insuficientes para calcular controversia RWC.",
        }

    # 1. Conteo de aristas de corte (cut edges)
    set_c1 = set(nodes_c1)
    set_c2 = set(nodes_c2)
    cut_edges = 0
    boundary_nodes = set()

    for u in nodes_c1:
        for v in G.neighbors(u):
            if v in set_c2:
                cut_edges += 1
                boundary_nodes.add(u)
                boundary_nodes.add(v)

    vol_c1 = sum(G.degree(n) for n in nodes_c1)
    vol_c2 = sum(G.degree(n) for n in nodes_c2)
    min_vol = min(vol_c1, vol_c2) if min(vol_c1, vol_c2) > 0 else 1
    conductance = cut_edges / min_vol

    # 2. Random walks desde nodos centrales de cada comunidad
    # Seleccionamos el top de nodos por grado como semillas
    top_c1 = sorted(nodes_c1, key=lambda n: G.degree(n), reverse=True)[: min(10, len(nodes_c1))]
    top_c2 = sorted(nodes_c2, key=lambda n: G.degree(n), reverse=True)[: min(10, len(nodes_c2))]

    def simulate_walk(start_node: Any) -> int:
        curr = start_node
        for _ in range(max_steps):
            nbrs = list(G.neighbors(curr))
            if not nbrs:
                break
            curr = random.choice(nbrs)
            c = nodes_map[curr].get("comm")
            if c in (comm1_id, comm2_id):
                return c
        return nodes_map[curr].get("comm", -1)

    c1_stay = 0
    c1_cross = 0
    for _ in range(num_walks):
        start = random.choice(top_c1)
        end_comm = simulate_walk(start)
        if end_comm == comm1_id:
            c1_stay += 1
        elif end_comm == comm2_id:
            c1_cross += 1

    c2_stay = 0
    c2_cross = 0
    for _ in range(num_walks):
        start = random.choice(top_c2)
        end_comm = simulate_walk(start)
        if end_comm == comm2_id:
            c2_stay += 1
        elif end_comm == comm1_id:
            c2_cross += 1

    p_11 = c1_stay / num_walks if num_walks > 0 else 1.0
    p_12 = c1_cross / num_walks if num_walks > 0 else 0.0
    p_22 = c2_stay / num_walks if num_walks > 0 else 1.0
    p_21 = c2_cross / num_walks if num_walks > 0 else 0.0

    # RWC = P11 * P22 - P12 * P21
    raw_rwc = (p_11 * p_22) - (p_12 * p_21)
    normalized_rwc = max(0.0, min(100.0, raw_rwc * 100.0))

    if normalized_rwc >= 75.0:
        diagnosis = "Polarización Extrema: Cámaras de eco herméticas. El debate no cruza fronteras ideológicas."
    elif normalized_rwc >= 50.0:
        diagnosis = "Controversia Alta: Separación marcada con contacto restringido a pocos nodos puente."
    elif normalized_rwc >= 25.0:
        diagnosis = "Controversia Moderada: Diálogo existente entre comunidades con fricción media."
    else:
        diagnosis = "Baja Controversia: Alta transversalidad y flujo abierto de mensajes entre ambas facciones."

    return {
        "comm1": {"id": comm1_id, "name": name_c1, "size": len(nodes_c1)},
        "comm2": {"id": comm2_id, "name": name_c2, "size": len(nodes_c2)},
        "rwc_score": round(normalized_rwc, 2),
        "conductance": round(conductance, 4),
        "cut_edges_count": cut_edges,
        "boundary_nodes_count": len(boundary_nodes),
        "p_comm1_stay": round(p_11, 3),
        "p_comm2_stay": round(p_22, 3),
        "diagnosis": diagnosis,
    }

