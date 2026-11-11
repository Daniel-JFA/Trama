"""
storage.py — Capa de persistencia relacional con SQLAlchemy para TRAMA.
Soporta SQLite y PostgreSQL con transacciones atómicas y modelos normalizados.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from .synth import generate_synthetic_graph
from .database import engine, SessionLocal
from .models import Base, ProjectModel, LeadModel, SettingModel


def init_db():
    """Inicializa las tablas en la base de datos y realiza el seeding inicial si está vacía."""
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        # 1. Configurar proyecto activo por defecto si no existe
        setting = session.query(SettingModel).filter(SettingModel.key == "active_project_id").first()
        if not setting:
            session.add(SettingModel(key="active_project_id", value="demo-reforma-del-agua"))
            session.commit()

        # 2. Seed con el proyecto demo sintético si no hay proyectos
        count = session.query(ProjectModel).count()
        if count == 0:
            demo_graph = generate_synthetic_graph()
            now = datetime.now(timezone.utc).isoformat()
            demo_proj = ProjectModel(
                id="demo-reforma-del-agua",
                name="Caso #ReformaDelAgua (Demo)",
                topic="#ReformaDelAgua",
                description="Investigación de astroturfing y debate coordinado en 4 comunidades ficticias.",
                created_at=now,
                updated_at=now,
                node_count=len(demo_graph["nodes"]),
                link_count=len(demo_graph["links"]),
                community_count=len(demo_graph["communities"]),
                graph_json=json.dumps(demo_graph, ensure_ascii=False),
            )
            session.add(demo_proj)
            session.commit()


# Inicializar base de datos al importar
init_db()


def get_active_project_id() -> str:
    """Devuelve el ID del proyecto actualmente activo o el demo por defecto."""
    with SessionLocal() as session:
        setting = session.query(SettingModel).filter(SettingModel.key == "active_project_id").first()
        return setting.value if setting else "demo-reforma-del-agua"


def set_active_project_id(project_id: str) -> None:
    """Actualiza de forma atómica en base de datos el ID del proyecto activo."""
    with SessionLocal() as session:
        setting = session.query(SettingModel).filter(SettingModel.key == "active_project_id").first()
        if setting:
            setting.value = project_id
        else:
            session.add(SettingModel(key="active_project_id", value=project_id))
        session.commit()


def list_projects() -> List[Dict[str, Any]]:
    """Devuelve la lista resumida de todos los proyectos ordenados por fecha de actualización."""
    with SessionLocal() as session:
        projects = (
            session.query(ProjectModel)
            .order_by(ProjectModel.updated_at.desc())
            .all()
        )
        return [
            {
                "id": p.id,
                "name": p.name,
                "topic": p.topic,
                "description": p.description,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
                "node_count": p.node_count,
                "link_count": p.link_count,
                "community_count": p.community_count,
            }
            for p in projects
        ]


def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    """Devuelve el proyecto completo con su grafo cargado."""
    with SessionLocal() as session:
        p = session.query(ProjectModel).filter(ProjectModel.id == project_id).first()
        if not p:
            return None
        return {
            "id": p.id,
            "name": p.name,
            "topic": p.topic,
            "description": p.description,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
            "node_count": p.node_count,
            "link_count": p.link_count,
            "community_count": p.community_count,
            "graph": json.loads(p.graph_json),
        }


def create_project(name: str, topic: str, description: str = "", graph: Optional[Dict] = None) -> Dict[str, Any]:
    """Crea una nueva investigación con un grafo inicial."""
    if graph is None:
        graph = generate_synthetic_graph()
        if "meta" in graph:
            graph["meta"] = dict(graph["meta"])
            graph["meta"]["topic"] = topic

    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    node_count = len(graph.get("nodes", []))
    link_count = len(graph.get("links", []))
    comm_count = len(graph.get("communities", []))

    with SessionLocal() as session:
        p = ProjectModel(
            id=project_id,
            name=name,
            topic=topic,
            description=description,
            created_at=now,
            updated_at=now,
            node_count=node_count,
            link_count=link_count,
            community_count=comm_count,
            graph_json=json.dumps(graph, ensure_ascii=False),
        )
        session.add(p)
        session.commit()

    return {
        "id": project_id,
        "name": name,
        "topic": topic,
        "description": description,
        "created_at": now,
        "updated_at": now,
        "node_count": node_count,
        "link_count": link_count,
        "community_count": comm_count,
        "graph": graph,
    }


def update_project_graph(project_id: str, graph: Dict[str, Any], topic: Optional[str] = None) -> bool:
    """Actualiza el grafo y los conteos de un proyecto existente."""
    now = datetime.now(timezone.utc).isoformat()
    node_count = len(graph.get("nodes", []))
    link_count = len(graph.get("links", []))
    comm_count = len(graph.get("communities", []))

    with SessionLocal() as session:
        p = session.query(ProjectModel).filter(ProjectModel.id == project_id).first()
        if not p:
            return False
        p.graph_json = json.dumps(graph, ensure_ascii=False)
        p.node_count = node_count
        p.link_count = link_count
        p.community_count = comm_count
        p.updated_at = now
        if topic:
            p.topic = topic
        session.commit()
        return True


def delete_project(project_id: str) -> bool:
    """Elimina un proyecto y restablece el activo a demo si correspondía."""
    with SessionLocal() as session:
        p = session.query(ProjectModel).filter(ProjectModel.id == project_id).first()
        if not p:
            return False
        session.delete(p)
        session.commit()

    if get_active_project_id() == project_id:
        set_active_project_id("demo-reforma-del-agua")
    return True


def create_lead(name: str, email: str, company: str = "", role: str = "", use_case: str = "") -> Dict[str, Any]:
    """Registra un nuevo lead o solicitud de auditoría."""
    lead_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as session:
        lead = LeadModel(
            id=lead_id,
            name=name,
            email=email,
            company=company,
            role=role,
            use_case=use_case,
            created_at=now,
        )
        session.add(lead)
        session.commit()

    return {
        "id": lead_id,
        "name": name,
        "email": email,
        "company": company,
        "role": role,
        "use_case": use_case,
        "created_at": now,
    }


def list_leads() -> List[Dict[str, Any]]:
    """Devuelve la lista de leads registrados."""
    with SessionLocal() as session:
        leads = session.query(LeadModel).order_by(LeadModel.created_at.desc()).all()
        return [
            {
                "id": l.id,
                "name": l.name,
                "email": l.email,
                "company": l.company,
                "role": l.role,
                "use_case": l.use_case,
                "created_at": l.created_at,
            }
            for l in leads
        ]
