"""
dependencies.py — Inyección de dependencias compartidas para FastAPI.
"""

from typing import Optional, Dict, Any
from fastapi import Query, Header, HTTPException

from .synth import generate_synthetic_graph
from .storage import (
    list_projects,
    get_project,
    create_project,
    get_active_project_id,
    set_active_project_id,
)


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
