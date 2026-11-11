"""
main.py — API FastAPI desacoplada para TRAMA con persistencia SQLite y soporte multi-worker.

Arquitectura v0.3.0:
- Sin variables de estado globales en memoria (permite uvicorn --workers 4).
- Inyección de dependencias (FastAPI Depends) para resolución atómica de proyectos vía query param o header 'X-Project-Id'.
- Motor de grafos acelerado en C (python-igraph + Leiden community partitioning).
- Cola de tareas asíncronas con streaming en tiempo real vía Server-Sent Events (SSE).
- Contratos de datos tipados estrictos con Pydantic V2 y modelos normalizados en SQLAlchemy.
- Sanitización estricta contra inyección de fórmulas CSV (CWE-1236) y límite de 15MB.
"""

import io
import csv
import re
from typing import Optional, List, Dict, Any, Set

from fastapi import FastAPI, Query, UploadFile, File, HTTPException, Form, Response, Depends, Header
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from .synth import generate_synthetic_graph
from .metrics import compute_metrics, bot_heuristic, compute_communities_leiden
from .exporters import export_graph_to_gexf
from .reports import generate_executive_report
from .schemas import (
    NodeOut,
    LinkOut,
    CommunityOut,
    GraphMetaOut,
    GraphOut,
    CreateProjectPayload,
    ProjectSummaryOut,
    ProjectDetailOut,
    AsyncTaskResponse,
    CreateLeadPayload,
    LeadOut,
    OverlapResponseOut,
    CandidateOut,
    CopypastaPayload,
    CopypastaResponseOut,
    CooRnetPayload,
    CooRnetResponseOut,
    RWCResponseOut,
    InteractionEvent,
    BatchInteractionEventsPayload,
    ColumnarQueryPayload,
)
from .columnar import ColumnarAnalytics, save_events_to_parquet
from .tasks import (
    enqueue_import_task,
    get_task_status,
    subscribe_task_events,
)
from .storage import (
    list_projects,
    get_project,
    create_project,
    update_project_graph,
    delete_project,
    create_lead,
    list_leads,
    get_active_project_id,
    set_active_project_id,
)
from .political import (
    audit_candidate,
    find_strategic_brokers,
    find_expansion_paths,
    list_potential_candidates,
    calculate_random_walk_controversy,
)
from .nlp import detect_copypasta_clusters
from .cib import detect_coornet_network

app = FastAPI(
    title="TRAMA API",
    version="0.3.0",
    description="Motor de Inteligencia de Redes, Análisis CIB y War Room Electoral con Aceleración C y Streaming SSE.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# ─── Inyección de Dependencias: Proyecto y Grafo Activo ──────────────────────
def get_current_project(
    project_id: Optional[str] = Query(None, description="ID del proyecto objetivo"),
    x_project_id: Optional[str] = Header(None, alias="X-Project-Id", description="Cabecera con ID del proyecto"),
) -> Dict[str, Any]:
    """
    Resuelve el proyecto de forma desacoplada y atómica para soportar concurrencia y escalabilidad horizontal.
    Prioridad:
    1. Query param 'project_id' explícito.
    2. Cabecera 'X-Project-Id'.
    3. Proyecto activo configurado en SQLite (fallback persistido).
    """
    target_id = project_id or x_project_id
    if target_id:
        proj = get_project(target_id)
        if not proj:
            raise HTTPException(status_code=404, detail=f"Proyecto '{target_id}' no encontrado.")
        return proj

    # Recuperar el proyecto activo persistido
    active_id = get_active_project_id()
    proj = get_project(active_id)
    if proj:
        return proj

    # Fallback seguro a demo o primer proyecto registrado
    demo = get_project("demo-reforma-del-agua")
    if demo:
        return demo

    all_projs = list_projects()
    if all_projs:
        p = get_project(all_projs[0]["id"])
        if p:
            return p

    # Si la base de datos no tuviese proyectos, crear el demo base
    synth = generate_synthetic_graph()
    created = create_project("Caso #ReformaDelAgua (Demo)", "#ReformaDelAgua", "Demo base", synth)
    set_active_project_id(created["id"])
    return created


# ─── Helpers de Topología y Seguridad ────────────────────────────────────────
def build_neighbor_sets(graph: Dict[str, Any]) -> Dict[int, Set[int]]:
    neighbors: Dict[int, Set[int]] = {n["id"]: set() for n in graph.get("nodes", [])}
    for link in graph.get("links", []):
        s = link["source"]["id"] if isinstance(link["source"], dict) else link["source"]
        t = link["target"]["id"] if isinstance(link["target"], dict) else link["target"]
        if s in neighbors:
            neighbors[s].add(t)
        if t in neighbors:
            neighbors[t].add(s)
    return neighbors


def sanitize_csv_cell(val: str, is_handle: bool = True) -> str:
    """
    Sanitiza celdas de CSV para mitigar inyección de fórmulas en hojas de cálculo (CWE-1236).
    Neutraliza prefijos de comandos ejecutables (=, +, -, @, \\t, \\r).
    """
    if not val:
        return ""
    clean = val.strip()
    dangerous_chars = ("=", "+", "-", "\t", "\r")
    while clean and clean[0] in dangerous_chars:
        clean = clean[1:].strip()
    if is_handle:
        clean = clean.lstrip("@").strip()
    if clean and clean[0] in dangerous_chars:
        clean = clean.lstrip("=+-@\t\r").strip()
    return clean


# ─── Endpoints: Salud, Leads y Proyectos ─────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.3.0"}


@app.post("/api/leads")
def submit_lead(payload: CreateLeadPayload):
    if not payload.email or "@" not in payload.email:
        raise HTTPException(status_code=422, detail="Correo electrónico inválido.")
    if not payload.name or len(payload.name.strip()) < 2:
        raise HTTPException(status_code=422, detail="Nombre inválido.")
    lead = create_lead(
        name=payload.name.strip(),
        email=payload.email.strip().lower(),
        company=payload.company.strip() if payload.company else "",
        role=payload.role.strip() if payload.role else "",
        use_case=payload.use_case.strip() if payload.use_case else "",
    )
    return {"status": "ok", "message": "Solicitud registrada con éxito.", "lead": lead}


@app.get("/api/leads", response_model=List[LeadOut])
def get_all_leads():
    return list_leads()


@app.get("/api/projects", response_model=List[ProjectSummaryOut])
def get_all_projects():
    return list_projects()


@app.post("/api/projects", response_model=ProjectSummaryOut)
def create_new_project(payload: CreateProjectPayload):
    project = create_project(payload.name, payload.topic, payload.description or "")
    set_active_project_id(project["id"])
    return project


@app.get("/api/projects/{project_id}", response_model=ProjectDetailOut)
def load_project_by_id(project_id: str):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado.")
    set_active_project_id(project["id"])
    return project


@app.delete("/api/projects/{project_id}")
def remove_project(project_id: str):
    if project_id == "demo-reforma-del-agua":
        raise HTTPException(status_code=400, detail="No se puede eliminar el proyecto demo base.")
    success = delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado.")
    return {"status": "ok", "message": "Proyecto eliminado."}


@app.get("/api/projects/{project_id}/export/gexf")
def export_project_gexf(project_id: str):
    project = get_project(project_id)
    if not project or "graph" not in project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado.")
    gexf_content = export_graph_to_gexf(project["graph"])
    filename = f"trama-{project.get('topic', 'grafo')}.gexf"
    return Response(
        content=gexf_content,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/projects/{project_id}/report")
def get_project_executive_report(project_id: str, candidate_id: Optional[int] = Query(None)):
    project = get_project(project_id)
    if not project or "graph" not in project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado.")
    return generate_executive_report(project, candidate_id=candidate_id)


# ─── Endpoints: Grafo y Análisis ─────────────────────────────────────────────

@app.get("/api/graph", response_model=GraphOut)
def get_graph(project: Dict[str, Any] = Depends(get_current_project)):
    """Retorna el grafo del proyecto resuelto de forma aislada."""
    return project["graph"]


@app.get("/api/overlap", response_model=OverlapResponseOut)
def overlap(
    ids: str = Query(..., description="IDs separados por coma, mínimo 2"),
    project: Dict[str, Any] = Depends(get_current_project),
):
    graph = project["graph"]
    try:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=422, detail="Los ids deben ser enteros separados por coma.")

    if len(id_list) < 2:
        raise HTTPException(status_code=422, detail="Se necesitan al menos 2 ids para calcular solapamiento.")

    valid_ids = {n["id"] for n in graph.get("nodes", [])}
    invalid = [i for i in id_list if i not in valid_ids]
    if invalid:
        raise HTTPException(status_code=404, detail=f"Nodos no encontrados: {invalid}")

    neighbors = build_neighbor_sets(graph)
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


# ─── Endpoints: Ingesta Asíncrona & Streaming SSE (Sprint 2) ─────────────────

@app.post("/api/import/async", status_code=202, response_model=AsyncTaskResponse)
async def import_csv_async(
    file: UploadFile = File(...),
    topic_name: Optional[str] = Form(None),
    project_name: Optional[str] = Form(None),
):
    """
    Inicia la importación asíncrona de un dataset de interacciones CSV.
    Responde 202 Accepted de inmediato con un task_id para seguimiento reactivo vía SSE.
    """
    MAX_FILE_SIZE = 15 * 1024 * 1024
    content_bytes = await file.read()
    if len(content_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="El archivo excede el tamaño máximo permitido (15MB).")

    try:
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="El archivo debe estar en codificación UTF-8.")

    task_id = enqueue_import_task(
        content=content,
        filename=file.filename or "dataset.csv",
        topic_name=topic_name,
        project_name=project_name,
    )

    return AsyncTaskResponse(
        task_id=task_id,
        status="pending",
        message="Importación de grafo encolada exitosamente",
    )


@app.post("/api/projects/{project_id}/import", status_code=202, response_model=AsyncTaskResponse)
async def import_csv_to_project(
    project_id: str,
    file: UploadFile = File(...),
):
    """Importa interacciones hacia un proyecto específico en segundo plano."""
    target_project = get_project(project_id)
    if not target_project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado.")

    MAX_FILE_SIZE = 15 * 1024 * 1024
    content_bytes = await file.read()
    if len(content_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="El archivo excede el tamaño máximo permitido (15MB).")

    try:
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="El archivo debe estar en codificación UTF-8.")

    task_id = enqueue_import_task(
        content=content,
        filename=file.filename or "dataset.csv",
        topic_name=target_project.get("topic"),
        project_name=target_project.get("name"),
    )

    return AsyncTaskResponse(
        task_id=task_id,
        status="pending",
        message=f"Importación hacia proyecto {project_id} iniciada",
    )


@app.get("/api/tasks/{task_id}")
def get_task_info(task_id: str):
    """Consulta el estado puntual de una tarea asíncrona."""
    status = get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Tarea no encontrada.")
    return status


@app.get("/api/tasks/{task_id}/events")
async def stream_task_events(task_id: str):
    """
    Streaming reactivo Server-Sent Events (SSE) para progreso granular de tareas.
    """
    status = get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Tarea no encontrada.")

    return StreamingResponse(
        subscribe_task_events(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─── Endpoint de Ingesta Síncrona Tradicional ────────────────────────────────

@app.post("/api/import")
async def import_csv(
    file: UploadFile = File(...),
    topic_name: Optional[str] = Form(None),
    project_name: Optional[str] = Form(None),
):
    MAX_FILE_SIZE = 15 * 1024 * 1024
    content_bytes = await file.read()
    if len(content_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="El archivo excede el tamaño máximo permitido (15MB).")

    try:
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="El archivo debe estar en codificación UTF-8.")

    reader = csv.DictReader(io.StringIO(content))
    if reader.fieldnames is None or not {"source", "target"}.issubset(
        {f.strip().lower() for f in reader.fieldnames}
    ):
        raise HTTPException(
            status_code=422,
            detail="El CSV debe tener columnas 'source' y 'target'.",
        )

    edges: List[tuple[str, str]] = []
    for row in reader:
        norm = {k.strip().lower(): v.strip() for k, v in row.items()}
        raw_src = norm.get("source", "")
        raw_tgt = norm.get("target", "")

        src = sanitize_csv_cell(raw_src, is_handle=True)
        tgt = sanitize_csv_cell(raw_tgt, is_handle=True)

        if src and tgt and src != tgt:
            edges.append((src, tgt))

    if not edges:
        raise HTTPException(status_code=422, detail="No se encontraron aristas válidas en el CSV.")

    import networkx as nx
    G = nx.Graph()
    G.add_edges_from(edges)

    unique_handles = list(G.nodes())
    if len(unique_handles) < 3:
        raise HTTPException(status_code=422, detail="Se necesitan al menos 3 nodos distintos.")

    communities_sets = compute_communities_leiden(G)

    handle_to_comm: Dict[str, int] = {}
    for cid, comm_set in enumerate(communities_sets):
        for h in comm_set:
            handle_to_comm[h] = cid

    PALETTE = ["#E8C15A", "#5AD1B3", "#8B7CF6", "#E060B8", "#60A5FA", "#F97316", "#A3E635", "#E879F9"]
    communities_meta = [
        {"id": i, "name": f"Comunidad {i + 1}", "color": PALETTE[i % len(PALETTE)]}
        for i in range(len(communities_sets))
    ]

    metrics = compute_metrics(G)

    nodes = []
    for idx, handle in enumerate(unique_handles):
        cid = handle_to_comm.get(handle, 0)
        bot = bot_heuristic(handle, posts=50, followers=500)
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

    raw_topic = topic_name or (file.filename.replace(".csv", "").replace("_", " ") if file.filename else "CSV importado")
    effective_topic = sanitize_csv_cell(raw_topic, is_handle=False) or "CSV importado"

    imported_graph = {
        "meta": {
            "topic": effective_topic,
            "weeks": 0,
            "synthetic": False,
            "interactions": len(edges),
        },
        "communities": communities_meta,
        "nodes": nodes,
        "links": links,
    }

    proj_title = sanitize_csv_cell(project_name or f"Investigación: {effective_topic}", is_handle=False)
    new_proj = create_project(proj_title, effective_topic, f"Importado desde {file.filename}", imported_graph)
    set_active_project_id(new_proj["id"])

    return imported_graph


@app.post("/api/reset")
def reset(
    project_id: Optional[str] = Query(None),
    x_project_id: Optional[str] = Header(None, alias="X-Project-Id"),
):
    fresh_graph = generate_synthetic_graph()
    target_id = project_id or x_project_id or "demo-reforma-del-agua"

    demo = get_project(target_id)
    if demo:
        update_project_graph(target_id, fresh_graph, topic="#ReformaDelAgua")
    else:
        create_project("Caso #ReformaDelAgua (Demo)", "#ReformaDelAgua", "Demo base", fresh_graph)

    set_active_project_id(target_id)
    return {"status": "ok", "message": "Grafo sintético restaurado.", "project_id": target_id}


# ─── Endpoints: Inteligencia Política & Campaign War Room ────────────────────

@app.get("/api/political/candidates", response_model=List[CandidateOut])
def get_political_candidates(
    top_per_comm: int = Query(3, ge=1, le=10),
    project: Dict[str, Any] = Depends(get_current_project),
):
    """Retorna los perfiles líderes de opinión sugeridos en el grafo del proyecto resuelto."""
    return list_potential_candidates(project["graph"], top_per_comm=top_per_comm)


@app.get("/api/political/audit")
def get_candidate_audit(
    candidate_id: Optional[int] = Query(None, description="ID numérico del nodo candidato"),
    handle: Optional[str] = Query(None, description="Handle del candidato (ej: @AgroFuturoCol)"),
    project: Dict[str, Any] = Depends(get_current_project),
):
    graph = project["graph"]
    target_id = candidate_id
    if target_id is None and handle:
        clean_handle = handle.lstrip("@").lower()
        for n in graph.get("nodes", []):
            if n.get("handle", "").lstrip("@").lower() == clean_handle:
                target_id = n["id"]
                break
        if target_id is None:
            raise HTTPException(status_code=404, detail=f"Candidato con handle '{handle}' no encontrado en el grafo.")

    if target_id is None:
        raise HTTPException(status_code=422, detail="Debe especificar 'candidate_id' o 'handle'.")

    try:
        return audit_candidate(graph, target_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/political/brokers")
def get_strategic_brokers(
    candidate_id: int = Query(..., description="ID del candidato"),
    target_comm: Optional[int] = Query(None, description="Comunidad objetivo opcional"),
    limit: int = Query(10, ge=1, le=50),
    project: Dict[str, Any] = Depends(get_current_project),
):
    try:
        return find_strategic_brokers(project["graph"], candidate_id, target_comm_id=target_comm, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/political/expansion-paths")
def get_expansion_paths(
    candidate_id: int = Query(..., description="ID del candidato"),
    target_comm: int = Query(..., description="ID de la comunidad objetivo a penetrar"),
    max_paths: int = Query(3, ge=1, le=10),
    project: Dict[str, Any] = Depends(get_current_project),
):
    try:
        return find_expansion_paths(project["graph"], candidate_id, target_comm_id=target_comm, max_paths=max_paths)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─── Sprint 3: Inteligencia Forense NLP, CooRnet y Polarización RWC ─────────

@app.post("/api/nlp/copypasta", response_model=CopypastaResponseOut)
def detect_copypasta(payload: CopypastaPayload):
    """
    Detecta clústeres de copypasta textual coordinado mediante MinHash, LSH y similitud semántica.
    Identifica mensajes idénticos o parafraseados emitidos por cuentas distintas en ventanas de tiempo breves.
    """
    messages_dicts = [
        {
            "id": m.id if m.id is not None else idx,
            "handle": m.handle,
            "text": m.text,
            "timestamp": m.timestamp or 0.0,
        }
        for idx, m in enumerate(payload.messages)
    ]
    return detect_copypasta_clusters(
        messages_dicts,
        jaccard_threshold=payload.jaccard_threshold or 0.80,
        semantic_threshold=payload.semantic_threshold or 0.85,
        time_window_seconds=payload.time_window_seconds or 900,
        model_name=payload.model_name or "paraphrase-multilingual-MiniLM-L12-v2",
    )


@app.get("/api/nlp/copypasta", response_model=CopypastaResponseOut)
def get_project_copypasta(
    jaccard_threshold: float = Query(0.75, ge=0.1, le=1.0),
    semantic_threshold: float = Query(0.85, ge=0.1, le=1.0),
    time_window_seconds: int = Query(900, ge=10, le=86400),
    project: Dict[str, Any] = Depends(get_current_project),
):
    """Obtiene los clústeres de copypasta y parafraseo detectados para la investigación activa."""
    graph = project.get("graph", {})
    if "copypasta_clusters" in graph and graph["copypasta_clusters"]:
        clusters = graph["copypasta_clusters"]
        coord_accounts = set()
        vol = 0
        for c in clusters:
            if c.get("is_coordinated"):
                coord_accounts.update(c.get("accounts", []))
                vol += c.get("message_count", 0)
        return {
            "total_messages": sum(c.get("message_count", 0) for c in clusters),
            "clusters": clusters,
            "coordinated_accounts": sorted(list(coord_accounts)),
            "copypasta_volume": vol,
            "clusters_count": len(clusters),
        }

    # Si es el grafo sintético o demo, generar el corpus de muestra
    from .synth import generate_synthetic_copypasta_messages
    sample_msgs = generate_synthetic_copypasta_messages()
    return detect_copypasta_clusters(
        sample_msgs,
        jaccard_threshold=jaccard_threshold,
        semantic_threshold=semantic_threshold,
        time_window_seconds=time_window_seconds,
    )


@app.post("/api/cib/coornet", response_model=CooRnetResponseOut)
def get_coornet_network(payload: CooRnetPayload):
    """
    Construye la red de co-compartición rápida (CooRnet) detectando perfiles que
    amplifican exactamente los mismos recursos/enlaces en una ventana estrecha (<=45s).
    Aplica prueba de permutación Monte Carlo para calcular p-valores por arista.
    """
    events_dicts = [
        {
            "handle": e.handle,
            "entity_id": e.entity_id,
            "timestamp": e.timestamp,
        }
        for e in payload.events
    ]
    return detect_coornet_network(
        events_dicts,
        time_window_seconds=payload.time_window_seconds or 45.0,
        min_co_shares=payload.min_co_shares or 2,
        monte_carlo_iterations=payload.monte_carlo_iterations if payload.monte_carlo_iterations is not None else 100,
        alpha=payload.alpha if payload.alpha is not None else 0.05,
        seed=payload.seed,
    )


@app.get("/api/cib/coornet", response_model=CooRnetResponseOut)
def get_project_coornet(
    time_window_seconds: float = Query(45.0, ge=1.0, le=300.0),
    min_co_shares: int = Query(2, ge=1, le=10),
    monte_carlo_iterations: int = Query(100, ge=0, le=500),
    alpha: float = Query(0.05, ge=0.001, le=0.5),
    seed: Optional[int] = Query(None),
    project: Dict[str, Any] = Depends(get_current_project),
):
    """Obtiene la red CooRnet de co-compartición coordinada con p-valores Monte Carlo para la investigación activa."""
    graph = project.get("graph", {})
    if "coornet_links" in graph and graph["coornet_links"]:
        nodes = []
        node_handles = set()
        for l in graph["coornet_links"]:
            node_handles.add(l["source"])
            node_handles.add(l["target"])
        nodes = [{"id": h, "handle": h, "degree": 1} for h in sorted(node_handles)]
        sig_count = sum(1 for l in graph["coornet_links"] if l.get("is_statistically_significant"))
        return {
            "nodes": nodes,
            "links": graph["coornet_links"],
            "coordinated_cliques": graph.get("coornet_cliques", []),
            "total_pairs_detected": len(graph["coornet_links"]),
            "significant_coordinated_pairs": sig_count,
        }

    from .synth import generate_synthetic_coornet_events
    sample_events = generate_synthetic_coornet_events()
    return detect_coornet_network(
        sample_events,
        time_window_seconds=time_window_seconds,
        min_co_shares=min_co_shares,
        monte_carlo_iterations=monte_carlo_iterations,
        alpha=alpha,
        seed=seed,
    )


@app.get("/api/political/rwc", response_model=RWCResponseOut)
def get_random_walk_controversy(
    comm1: int = Query(..., description="ID de la primera comunidad"),
    comm2: int = Query(..., description="ID de la segunda comunidad enfrentada"),
    walks: int = Query(500, ge=100, le=2000, description="Número de paseos aleatorios a simular"),
    project: Dict[str, Any] = Depends(get_current_project),
):
    """
    Calcula el índice de controversia y polarización Random Walk Controversy (RWC)
    y la conductancia de frontera entre dos comunidades del proyecto.
    """
    return calculate_random_walk_controversy(
        project["graph"],
        comm1_id=comm1,
        comm2_id=comm2,
        num_walks=walks,
    )


# ─── Bloque D: Ingesta Masiva Streaming y Analítica Columnar DuckDB ──────────

@app.post("/api/ingest/events")
def ingest_interaction_events(payload: BatchInteractionEventsPayload):
    """Ingesta masiva de eventos canónicos con persistencia columnar en Parquet."""
    if not payload.events:
        return {"status": "ok", "ingested_count": 0}

    count = save_events_to_parquet(payload.events, default_project_id=payload.project_id or "default")
    return {
        "status": "ok",
        "ingested_count": count,
        "project_id": payload.project_id or "default",
    }


@app.post("/api/analytics/minute")
def query_analytics_by_minute(payload: ColumnarQueryPayload):
    """Consulta agregada por minuto con DuckDB sobre Parquet particionado."""
    pid = payload.project_id or "default"
    analytics = ColumnarAnalytics()
    results = analytics.aggregate_by_minute(
        project_id=pid,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    return {
        "project_id": pid,
        "buckets_count": len(results),
        "data": results,
    }


@app.post("/api/analytics/rolling")
def query_analytics_rolling(payload: ColumnarQueryPayload):
    """Calcula ventanas móviles de volumen para detección de ráfagas con DuckDB."""
    pid = payload.project_id or "default"
    analytics = ColumnarAnalytics()
    results = analytics.rolling_windows(
        project_id=pid,
        window_minutes=payload.window_minutes or 15,
    )
    return {
        "project_id": pid,
        "window_minutes": payload.window_minutes or 15,
        "points_count": len(results),
        "data": results,
    }


@app.post("/api/analytics/top-actors")
def query_analytics_top_actors(payload: ColumnarQueryPayload):
    """Ranking de actores y amplificación calculado sobre DuckDB."""
    pid = payload.project_id or "default"
    analytics = ColumnarAnalytics()
    results = analytics.top_actors(
        project_id=pid,
        limit=payload.limit or 20,
    )
    return {
        "project_id": pid,
        "top_actors": results,
    }

# ─────────────────────────────────────────────────────────────────────────────


