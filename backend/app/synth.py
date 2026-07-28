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

    # Construir lista de nodos
    all_nodes = []
    for comm_nodes in nodes_by_comm.values():
        for n in comm_nodes:
            m = metrics.get(n["id"], {"influence": 0, "bridge": 0, "degree": 0})
            all_nodes.append({
                "id": n["id"],
                "handle": n["handle"],
                "comm": n["comm"],
                "org": n["org"],
                "bot": n["bot"],
                "auth": n["auth"],
                "act": n["act"],
                "followers": n["followers"],
                "posts": n["posts"],
                "degree": m["degree"],
                "influence": m["influence"],
                "bridge": m["bridge"],
            })

    # Construir lista de aristas
    links = [{"source": u, "target": v} for u, v in G.edges()]

    total_interactions = len(links) * 3 + 200  # aproximado para la demo

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
    }
