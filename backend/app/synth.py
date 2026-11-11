"""
synth.py — Generador de datos sintéticos deterministas para TRAMA.

Tema: #ReformaDelAgua (ficticio, ningún handle corresponde a cuentas reales)
Semilla: random.Random(20260727)

Comunidades:
  0 - Prensa y medios      (#E8C15A, 42 nodos)
  1 - Ambientalistas       (#5AD1B3, 40 nodos)
  2 - Gremio pro-reforma   (#8B7CF6, 36 nodos)
  3 - Red amplificadora    (#E060B8, 32 nodos)

Caso plantado de astroturfing:
  ~72% de la red amplificadora se conecta al hub del gremio (@AgroFuturoCol)
  Bot scores 58-96 en amplificadora, 3-34 en el resto (~6% infiltrados 55-78)
  Pico coordinado de actividad semanas 6-7 en amplificadora
"""

import random
import networkx as nx
from .metrics import compute_metrics

SEED = 20260727

COMMUNITIES = [
    {"id": 0, "name": "Prensa y medios",    "color": "#E8C15A", "size": 42},
    {"id": 1, "name": "Ambientalistas",     "color": "#5AD1B3", "size": 40},
    {"id": 2, "name": "Gremio pro-reforma", "color": "#8B7CF6", "size": 36},
    {"id": 3, "name": "Red amplificadora",  "color": "#E060B8", "size": 32},
]

# Handles institucionales iniciales (no existen en la realidad)
ORG_HANDLES = {
    0: ["ElFaroDigital", "CronicaAmbiental", "SemanaHidrica", "RadioCivica"],
    1: ["GuardianesDelRio", "AguaEsVida", "RioLibreCo", "ColectivoHidrico"],
    2: ["AgroFuturoCol", "CamaraAgricolaNal", "TierraProductiva", "FedAgricultores"],
    3: [],  # amplificadora solo tiene cuentas tipo bot
}

FIRST_NAMES = [
    "Andrea", "Carlos", "María", "Jorge", "Valentina", "Luis", "Diana",
    "Andrés", "Camila", "Felipe", "Sara", "Ricardo", "Paula", "Sebastián",
    "Laura", "Miguel", "Isabel", "Daniel", "Natalia", "Alejandro",
    "Marcela", "Hernando", "Gloria", "Esteban", "Catalina", "Rodrigo",
    "Paola", "Javier", "Claudia", "Mauricio", "Ángela", "Alberto",
    "Sandra", "Gabriel", "Liliana", "Tomás", "Patricia", "Nicolás",
    "Adriana", "Ernesto",
]

LAST_NAMES = [
    "Morales", "Suárez", "Rincón", "Ospina", "Vargas", "Pedraza",
    "Cifuentes", "Bermúdez", "Lozano", "Castaño", "Herrera", "Mendoza",
    "Aguilar", "Palomino", "Vanegas", "Quijano", "Durán", "Salcedo",
    "Guerrero", "Rodríguez", "Fonseca", "Nieto", "Reyes", "Arango",
    "Betancur", "Cárdenas", "Estrada", "Galvis", "Holguín", "Jiménez",
]

BOT_PREFIXES = [
    "Verdad", "InfoLibre", "NoticiasYa", "OpinionReal", "DataHoy",
    "CiudadanoX", "VozDelPueblo", "AlertaYa", "CronicaReal", "TruthNow",
    "LibertadInfo", "RealiDad", "NotaUrgente", "PulsoInfo", "CentinelaCo",
]


def _generate_handles(rng: random.Random) -> dict[int, list[dict]]:
    """Genera todos los nodos organizados por comunidad."""
    nodes = {}
    node_id = 0

    for comm in COMMUNITIES:
        cid = comm["id"]
        size = comm["size"]
        org_list = ORG_HANDLES.get(cid, [])
        comm_nodes = []

        for i in range(size):
            if i < len(org_list):
                # Cuenta institucional
                handle = org_list[i]
                followers = rng.randint(3000, 25000)
                posts = rng.randint(50, 400)
                bot_score = rng.randint(3, 18)
                is_org = True
            elif cid == 3:
                # Red amplificadora: handles con dígitos
                prefix = rng.choice(BOT_PREFIXES)
                suffix = rng.randint(1000, 9999)
                handle = f"{prefix}{suffix}"
                followers = rng.randint(80, 1200)
                posts = rng.randint(500, 4000)
                bot_score = rng.randint(58, 96)
                is_org = False
            else:
                # Personas normales con ~6% de infiltrados bot
                fn = rng.choice(FIRST_NAMES)
                ln = rng.choice(LAST_NAMES)
                handle = fn + ln.replace(" ", "")
                followers = rng.randint(200, 8000)
                posts = rng.randint(20, 800)
                infiltrado = rng.random() < 0.06
                bot_score = rng.randint(55, 78) if infiltrado else rng.randint(3, 34)
                is_org = False

            # Actividad semanal (12 semanas)
            act = []
            for w in range(12):
                base_act = rng.randint(1, 15)
                if cid == 3 and w in (5, 6):  # pico coordinado semanas 6-7 (índice 5-6)
                    base_act = rng.randint(40, 90)
                act.append(base_act)

            comm_nodes.append({
                "id": node_id,
                "handle": handle,
                "comm": cid,
                "org": is_org,
                "bot": bot_score,
                "auth": max(0, 100 - bot_score),
                "act": act,
                "followers": followers,
                "posts": posts,
            })
            node_id += 1

        nodes[cid] = comm_nodes

    return nodes


def _build_graph(nodes_by_comm: dict[int, list[dict]], rng: random.Random) -> nx.Graph:
    G = nx.Graph()

    # Añadir nodos
    for comm_nodes in nodes_by_comm.values():
        for n in comm_nodes:
            G.add_node(n["id"])

    def hub_bias_edge(comm_nodes: list[dict]) -> tuple[int, int]:
        """Escoge dos nodos con sesgo hacia los hubs (índices bajos)."""
        n = len(comm_nodes)
        # Peso decreciente: nodo 0 tiene peso n, nodo n-1 tiene peso 1
        weights = [n - i for i in range(n)]
        a = rng.choices(comm_nodes, weights=weights, k=1)[0]
        b = rng.choices(comm_nodes, weights=weights, k=1)[0]
        return a["id"], b["id"]

    # Aristas intra-comunidad
    intra_density = {0: 0.12, 1: 0.10, 2: 0.11, 3: 0.09}
    for cid, comm_nodes in nodes_by_comm.items():
        n = len(comm_nodes)
        target_edges = int(n * (n - 1) / 2 * intra_density[cid])
        added = 0
        attempts = 0
        while added < target_edges and attempts < target_edges * 20:
            attempts += 1
            a, b = hub_bias_edge(comm_nodes)
            if a != b and not G.has_edge(a, b):
                G.add_edge(a, b)
                added += 1

    # Puentes inter-comunidades
    # Prensa conecta con todos
    prensa = nodes_by_comm[0]
    for cid in [1, 2, 3]:
        other = nodes_by_comm[cid]
        for _ in range(12):
            a = rng.choices(prensa[:8], k=1)[0]
            b = rng.choices(other[:6], k=1)[0]
            if not G.has_edge(a["id"], b["id"]):
                G.add_edge(a["id"], b["id"])

    # Ambientalistas-gremio (pocos puentes)
    amb = nodes_by_comm[1]
    gremio = nodes_by_comm[2]
    for _ in range(5):
        a = rng.choices(amb[:6], k=1)[0]
        b = rng.choices(gremio[:5], k=1)[0]
        if not G.has_edge(a["id"], b["id"]):
            G.add_edge(a["id"], b["id"])

    # Caso plantado: ~72% de amplificadora → hub del gremio (AgroFuturoCol, id=0 del gremio)
    amp = nodes_by_comm[3]
    gremio_hub_id = nodes_by_comm[2][0]["id"]  # AgroFuturoCol
    target_amp = int(len(amp) * 0.72)
    amp_shuffled = amp[:]
    rng.shuffle(amp_shuffled)
    for amp_node in amp_shuffled[:target_amp]:
        if not G.has_edge(amp_node["id"], gremio_hub_id):
            G.add_edge(amp_node["id"], gremio_hub_id)

    # Unos pocos arcos amplificadora → prensa (para que el astroturfing se detecte)
    for amp_node in amp_shuffled[target_amp:target_amp + 5]:
        a = rng.choices(prensa[:4], k=1)[0]
        if not G.has_edge(amp_node["id"], a["id"]):
            G.add_edge(amp_node["id"], a["id"])

    return G


def generate_synthetic_graph() -> dict:
    """Genera el grafo sintético completo y devuelve el JSON serializable."""
    rng = random.Random(SEED)

    nodes_by_comm = _generate_handles(rng)
    G = _build_graph(nodes_by_comm, rng)

    # Calcular métricas
    metrics = compute_metrics(G)

    # Construir lista de nodos enriquecidos con análisis CIB forense
    from .cib import analyze_cib_profile

    all_nodes = []
    for comm_nodes in nodes_by_comm.values():
        for n in comm_nodes:
            m = metrics.get(n["id"], {"influence": 0, "bridge": 0, "degree": 0})
            cib_info = analyze_cib_profile(
                handle=n["handle"],
                act=n["act"],
                posts=n["posts"],
                followers=n["followers"],
                comm_id=n["comm"],
                node_id=n["id"],
                G=G,
            )
            # Para cuentas orgánicas no sospechosas, conservar valores base
            bot_val = n["bot"] if n["org"] or n["bot"] > cib_info["bot_score"] else cib_info["bot_score"]
            all_nodes.append({
                "id": n["id"],
                "handle": n["handle"],
                "comm": n["comm"],
                "org": n["org"],
                "bot": bot_val,
                "auth": max(0, 100 - bot_val),
                "act": n["act"],
                "followers": n["followers"],
                "posts": n["posts"],
                "degree": m["degree"],
                "influence": m["influence"],
                "bridge": m["bridge"],
                "cib_reasons": cib_info["reasons"],
                "breakdown": cib_info["breakdown"],
            })

    # Construir lista de aristas
    links = [{"source": u, "target": v} for u, v in G.edges()]

    total_interactions = len(links) * 3 + 200  # aproximado para la demo

    # Generar eventos y clústeres forenses del Sprint 3 para la demo
    coornet_events = generate_synthetic_coornet_events()
    from .cib import detect_coornet_network
    coornet_res = detect_coornet_network(coornet_events, time_window_seconds=45.0, min_co_shares=2, monte_carlo_iterations=50, seed=SEED)

    copypasta_msgs = generate_synthetic_copypasta_messages()
    from .nlp import detect_copypasta_clusters
    copypasta_res = detect_copypasta_clusters(copypasta_msgs, jaccard_threshold=0.75, semantic_threshold=0.85, time_window_seconds=900)

    return {
        "meta": {
            "topic": "#ReformaDelAgua",
            "weeks": 12,
            "synthetic": True,
            "interactions": total_interactions,
        },
        "communities": COMMUNITIES,
        "nodes": all_nodes,
        "links": links,
        "coornet_links": coornet_res.get("links", []),
        "coornet_cliques": coornet_res.get("coordinated_cliques", []),
        "copypasta_clusters": copypasta_res.get("clusters", []),
    }


def generate_synthetic_coornet_events() -> list[dict]:
    """Genera serie de eventos de co-compartición sincrónica para el caso demo #ReformaDelAgua."""
    # Handles amplificadores coordinados clave (Comunidad 3)
    bots = [
        "InfoLibre8006", "DataHoy4762", "OpinionReal5253", "DataHoy2363",
        "Verdad4063", "CronicaReal9852", "AlertaYa2146", "CentinelaCo1144",
        "LibertadInfo7106", "TruthNow3187", "Verdad8850", "CentinelaCo3128"
    ]
    entities = [
        "https://verdadcolombia.info/apoyo-agro-urgente",
        "https://noticiasya.com/campana-por-el-agro",
        "https://datoslibres.org/comunicado-reforma",
        "#AgroFuturoAvanza",
    ]

    events = []
    base_t = 1718000000.0  # Base timestamp semana 6

    # Campañas coordinadas: ráfagas sincronizadas en Delta_t <= 35s
    for ent_idx, ent in enumerate(entities):
        t_camp = base_t + ent_idx * 14400.0  # cada 4 horas
        for i, b in enumerate(bots):
            # Intervalo entre bots de 2 a 5 segundos
            t_event = t_camp + (i * 2.8)
            events.append({
                "handle": b,
                "entity_id": ent,
                "timestamp": round(t_event, 2),
            })

    # Cuentas orgánicas para control negativo (comparten con horas o días de diferencia)
    organic_handles = ["ElFaroDigital", "RadioCivica", "GuardianesDelRio", "AguaEsVida"]
    for i, h in enumerate(organic_handles):
        events.append({
            "handle": h,
            "entity_id": "https://verdadcolombia.info/apoyo-agro-urgente",
            "timestamp": base_t + 50000.0 + (i * 7200.0),
        })

    return events


def generate_synthetic_copypasta_messages() -> list[dict]:
    """Genera corpus sintético de mensajes con variaciones de paráfrasis para el caso demo."""
    msgs = [
        # Clúster 1: Apoyo urgente gremio soberanía
        {"id": "m_c1_1", "handle": "InfoLibre8006", "text": "¡Urgente colombianos! Apoyemos masivamente a @AgroFuturoCol para impulsar la soberanía agropecuaria nacional #ReformaDelAgua", "timestamp": 1718000100.0},
        {"id": "m_c1_2", "handle": "DataHoy4762", "text": "Urgente colombianos: Apoyemos masivamente a @AgroFuturoCol para impulsar la soberania agropecuaria del pais #ReformaDelAgua", "timestamp": 1718000140.0},
        {"id": "m_c1_3", "handle": "Verdad4063", "text": "Atencion colombianos, apoyemos con fuerza a @AgroFuturoCol para defender la soberania del campo #ReformaDelAgua", "timestamp": 1718000210.0},
        {"id": "m_c1_4", "handle": "OpinionReal5253", "text": "Alerta colombianos, apoyemos a @AgroFuturoCol para garantizar la soberania agropecuaria en el congreso #ReformaDelAgua", "timestamp": 1718000260.0},

        # Clúster 2: Inversión y empleo rural
        {"id": "m_c2_1", "handle": "CronicaReal9852", "text": "La reforma del agua traerá inversión histórica y empleo rural según informe técnico gremial #AgroFuturoAvanza", "timestamp": 1718014500.0},
        {"id": "m_c2_2", "handle": "AlertaYa2146", "text": "La reforma hidrica traera gran inversion y empleo para el campo confirma informe gremial #AgroFuturoAvanza", "timestamp": 1718014580.0},
        {"id": "m_c2_3", "handle": "CentinelaCo1144", "text": "Reforma del agua generara empleo e inversiones rurales confirma el nuevo estudio oficial #AgroFuturoAvanza", "timestamp": 1718014690.0},

        # Mensajes de control orgánicos (no coordinados, temas diversos)
        {"id": "m_org_1", "handle": "ElFaroDigital", "text": "Publicamos nuestra investigación especial sobre las concesiones de cuencas hídricas en Santander", "timestamp": 1718050000.0},
        {"id": "m_org_2", "handle": "GuardianesDelRio", "text": "Convocamos al plantón pacífico en defensa de los páramos este sábado a las 10am en la plaza mayor", "timestamp": 1718060000.0},
        {"id": "m_org_3", "handle": "CarlosSalcedo", "text": "Disfrutando del fin de semana con la familia en la represa del Sisga, excelente clima", "timestamp": 1718070000.0},
    ]
    return msgs
