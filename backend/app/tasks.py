"""
tasks.py — Gestor de tareas asíncronas y emisor de Server-Sent Events (SSE) para TRAMA.
Desacopla datasets pesados con progreso granular (0% -> 35% -> 60% -> 80% -> 90% -> 100%).
"""

import io
import csv
import json
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, AsyncGenerator

import networkx as nx

from .metrics import compute_metrics, bot_heuristic, compute_communities_leiden
from .storage import create_project, set_active_project_id
from .database import SessionLocal, get_db
from .models import TaskModel

# Canales en memoria para streaming reactivo SSE hacia clientes conectados
_task_listeners: Dict[str, list[asyncio.Queue]] = {}


def _update_task_db(
    task_id: str,
    status: str,
    progress: int,
    stage: str,
    message: str = "",
    result_data: Optional[Dict[str, Any]] = None,
    error_msg: Optional[str] = None,
):
    """Actualiza el estado de la tarea en la base de datos de forma segura."""
    now = datetime.now(timezone.utc).isoformat()
    try:
        with SessionLocal() as session:
            task = session.query(TaskModel).filter(TaskModel.id == task_id).first()
            if not task:
                task = TaskModel(
                    id=task_id,
                    status=status,
                    progress=progress,
                    stage=stage,
                    message=message,
                    result_json=json.dumps(result_data, ensure_ascii=False) if result_data else None,
                    error=error_msg,
                    created_at=now,
                    updated_at=now,
                )
                session.add(task)
            else:
                task.status = status
                task.progress = progress
                task.stage = stage
                task.message = message
                task.updated_at = now
                if result_data:
                    task.result_json = json.dumps(result_data, ensure_ascii=False)
                if error_msg:
                    task.error = error_msg
            session.commit()
    except Exception as e:
        print(f"[tasks.py] Error persistiendo estado de tarea {task_id}: {e}")


async def emit_task_event(
    task_id: str,
    status: str,
    progress: int,
    stage: str,
    message: str = "",
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
):
    """Emite evento de progreso a la base de datos y a todos los clientes SSE conectados."""
    _update_task_db(task_id, status, progress, stage, message, result, error)

    payload = {
        "task_id": task_id,
        "status": status,
        "progress": progress,
        "stage": stage,
        "message": message,
        "result": result,
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    listeners = _task_listeners.get(task_id, [])
    for q in listeners:
        await q.put(payload)


def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Consulta el estado actual de una tarea desde base de datos."""
    with SessionLocal() as session:
        t = session.query(TaskModel).filter(TaskModel.id == task_id).first()
        if not t:
            return None
        res_data = json.loads(t.result_json) if t.result_json else None
        return {
            "task_id": t.id,
            "status": t.status,
            "progress": t.progress,
            "stage": t.stage,
            "message": t.message,
            "result": res_data,
            "error": t.error,
            "created_at": t.created_at,
            "updated_at": t.updated_at,
        }


async def subscribe_task_events(task_id: str) -> AsyncGenerator[str, None]:
    """Generador asíncrono para Server-Sent Events (SSE)."""
    q = asyncio.Queue()
    if task_id not in _task_listeners:
        _task_listeners[task_id] = []
    _task_listeners[task_id].append(q)

    # Emitir el estado inicial si la tarea ya existe
    current = get_task_status(task_id)
    if current:
        yield f"event: progress\ndata: {json.dumps(current, ensure_ascii=False)}\n\n"
        if current["status"] in ("completed", "failed"):
            _task_listeners[task_id].remove(q)
            return

    try:
        while True:
            try:
                # Esperar siguiente evento con timeout para mantener viva la conexión SSE (keep-alive)
                data = await asyncio.wait_for(q.get(), timeout=15.0)
                event_type = "complete" if data["status"] == "completed" else "error" if data["status"] == "failed" else "progress"
                yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

                if data["status"] in ("completed", "failed"):
                    break
            except asyncio.TimeoutError:
                # Comentario ping para mantener viva la conexión HTTP sin cerrar
                yield ": keep-alive\n\n"
    finally:
        if task_id in _task_listeners and q in _task_listeners[task_id]:
            _task_listeners[task_id].remove(q)
            if not _task_listeners[task_id]:
                del _task_listeners[task_id]


async def process_csv_import_task(
    task_id: str,
    content: str,
    filename: str,
    topic_name: Optional[str] = None,
    project_name: Optional[str] = None,
):
    """Ejecuta el pipeline completo de procesamiento en segundo plano con estados granulares."""
    try:
        # Etapa 1: Sanitización y validación (20%)
        await emit_task_event(task_id, "processing", 15, "Sanitización y normalización CSV")
        await asyncio.sleep(0.05)  # Yield cooperativo al loop de eventos

        from .main import sanitize_csv_cell

        reader = csv.DictReader(io.StringIO(content))
        if reader.fieldnames is None or not {"source", "target"}.issubset(
            {f.strip().lower() for f in reader.fieldnames}
        ):
            await emit_task_event(task_id, "failed", 0, "Error de validación", error="El CSV debe tener columnas 'source' y 'target'.")
            return

        edges = []
        for row in reader:
            norm = {k.strip().lower(): v.strip() for k, v in row.items()}
            src = sanitize_csv_cell(norm.get("source", ""), is_handle=True)
            tgt = sanitize_csv_cell(norm.get("target", ""), is_handle=True)
            if src and tgt and src != tgt:
                edges.append((src, tgt))

        if not edges:
            await emit_task_event(task_id, "failed", 0, "Error de validación", error="No se encontraron aristas válidas en el CSV.")
            return

        # Etapa 2: Construcción topológica del grafo (40%)
        await emit_task_event(task_id, "processing", 40, "Construcción topológica del grafo")
        await asyncio.sleep(0.05)

        G = nx.Graph()
        G.add_edges_from(edges)
        unique_handles = list(G.nodes())
        if len(unique_handles) < 3:
            await emit_task_event(task_id, "failed", 0, "Error topológico", error="Se necesitan al menos 3 nodos distintos.")
            return

        # Etapa 3: Particionamiento comunitario Leiden (65%)
        await emit_task_event(task_id, "processing", 65, "Particionamiento comunitario Leiden (C-core)")
        await asyncio.sleep(0.05)

        communities_sets = compute_communities_leiden(G)
        handle_to_comm = {}
        for cid, comm_set in enumerate(communities_sets):
            for h in comm_set:
                handle_to_comm[h] = cid

        PALETTE = ["#E8C15A", "#5AD1B3", "#8B7CF6", "#E060B8", "#60A5FA", "#F97316", "#A3E635", "#E879F9"]
        communities_meta = [
            {"id": i, "name": f"Comunidad {i + 1}", "color": PALETTE[i % len(PALETTE)]}
            for i in range(len(communities_sets))
        ]

        # Etapa 4: Centralidades aceleradas en C (80%)
        await emit_task_event(task_id, "processing", 80, "Cálculo de métricas de red (PageRank & Centralidad)")
        await asyncio.sleep(0.05)

        metrics = compute_metrics(G)

        # Etapa 5: Análisis forense CIB (90%)
        await emit_task_event(task_id, "processing", 90, "Análisis forense CIB y cálculo de autenticidad")
        await asyncio.sleep(0.05)

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

        raw_topic = topic_name or (filename.replace(".csv", "").replace("_", " ") if filename else "CSV importado")
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

        # Etapa 6: Persistencia relacional (100%)
        await emit_task_event(task_id, "processing", 96, "Persistiendo investigación en base de datos")
        proj_title = sanitize_csv_cell(project_name or f"Investigación: {effective_topic}", is_handle=False)
        new_proj = create_project(proj_title, effective_topic, f"Importado desde {filename}", imported_graph)
        set_active_project_id(new_proj["id"])

        result_payload = {
            "project_id": new_proj["id"],
            "project_name": proj_title,
            "graph": imported_graph,
        }

        await emit_task_event(
            task_id,
            "completed",
            100,
            "Completado exitosamente",
            message="Dataset procesado y persistido con éxito",
            result=result_payload,
        )

    except Exception as exc:
        import traceback
        traceback.print_exc()
        await emit_task_event(
            task_id,
            "failed",
            0,
            "Error inesperado",
            error=str(exc),
        )


def enqueue_import_task(
    content: str,
    filename: str,
    topic_name: Optional[str] = None,
    project_name: Optional[str] = None,
) -> str:
    """Crea y despacha una tarea en segundo plano retornando su task_id."""
    task_id = str(uuid.uuid4())
    _update_task_db(task_id, "pending", 0, "Encolada", message="Esperando worker de procesamiento")

    # Iniciar la corrutina en segundo plano en el loop de asyncio activo
    asyncio.create_task(
        process_csv_import_task(
            task_id=task_id,
            content=content,
            filename=filename,
            topic_name=topic_name,
            project_name=project_name,
        )
    )
    return task_id
