"""
test_reports.py — Tests para la generación de Informes Ejecutivos PDF con WeasyPrint (Bloque C).
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.reports import generate_pdf_report, WEASYPRINT_AVAILABLE, WeasyPrintUnavailableError

client = TestClient(app)


@pytest.fixture
def sample_project():
    # Obtener el proyecto por defecto cargado en la API
    res = client.get("/api/projects")
    projects = res.json()
    assert len(projects) > 0
    project_id = projects[0]["id"]
    return project_id


@pytest.mark.skipif(not WEASYPRINT_AVAILABLE, reason="WeasyPrint no está disponible en este entorno")
def test_generate_pdf_report_function():
    """Verifica que generate_pdf_report devuelva bytes válidos de un archivo PDF."""
    res = client.get("/api/projects")
    proj_id = res.json()[0]["id"]

    # Obtenemos el grafo del proyecto
    res_graph = client.get("/api/graph", headers={"X-Project-Id": proj_id})
    project_dict = {
        "id": proj_id,
        "name": "Proyecto de Prueba PDF",
        "topic": "Investigación Electoral",
        "graph": res_graph.json(),
    }

    pdf_bytes = generate_pdf_report(project_dict)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")


@pytest.mark.skipif(not WEASYPRINT_AVAILABLE, reason="WeasyPrint no está disponible en este entorno")
def test_endpoint_get_pdf_report_success(sample_project):
    """Verifica el endpoint GET /api/projects/{id}/report/pdf."""
    res = client.get(f"/api/projects/{sample_project}/report/pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in res.headers.get("content-disposition", "")
    assert res.content.startswith(b"%PDF")
    assert len(res.content) > 1000


@pytest.mark.skipif(not WEASYPRINT_AVAILABLE, reason="WeasyPrint no está disponible en este entorno")
def test_endpoint_post_pdf_report_with_svg(sample_project):
    """Verifica el endpoint POST /api/projects/{id}/report/pdf con captura SVG."""
    custom_svg = '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200"><circle cx="200" cy="100" r="50" fill="#3B82F6"/></svg>'
    payload = {"svg": custom_svg}
    res = client.post(f"/api/projects/{sample_project}/report/pdf", json=payload)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF")


def test_endpoint_pdf_report_not_found():
    """Verifica error 404 para un proyecto inexistente."""
    res = client.get("/api/projects/proyecto-inexistente-12345/report/pdf")
    assert res.status_code == 404


def test_endpoint_pdf_report_501_when_weasyprint_missing(sample_project):
    """Verifica que responda 501 claro cuando WeasyPrint no está disponible."""
    with patch("app.main.generate_pdf_report", side_effect=WeasyPrintUnavailableError("WeasyPrint simulado ausente")):
        res = client.get(f"/api/projects/{sample_project}/report/pdf")
        assert res.status_code == 501
        assert "no disponible" in res.json()["detail"].lower()
