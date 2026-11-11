"""
Test suite for TRAMA API and graph processing.
"""

import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.metrics import compute_metrics, bot_heuristic
from app.synth import generate_synthetic_graph
from app.storage import list_projects, get_project
import networkx as nx

client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_get_graph_synthetic():
    client.post("/api/reset")
    res = client.get("/api/graph")
    assert res.status_code == 200
    data = res.json()
    assert "meta" in data
    assert "communities" in data
    assert "nodes" in data
    assert "links" in data
    assert len(data["nodes"]) == 150
    assert data["meta"]["synthetic"] is True


def test_projects_crud():
    # List projects
    res = client.get("/api/projects")
    assert res.status_code == 200
    projects = res.json()
    assert len(projects) >= 1
    assert any(p["id"] == "demo-reforma-del-agua" for p in projects)

    # Create project
    create_res = client.post(
        "/api/projects",
        json={"name": "Operación Botnet", "topic": "#Elecciones2026", "description": "Test investigation"},
    )
    assert create_res.status_code == 200
    new_proj = create_res.json()
    proj_id = new_proj["id"]
    assert new_proj["name"] == "Operación Botnet"

    # Get project by id
    get_res = client.get(f"/api/projects/{proj_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == proj_id

    # Delete project
    del_res = client.delete(f"/api/projects/{proj_id}")
    assert del_res.status_code == 200

    # Ensure deleted
    get_after = client.get(f"/api/projects/{proj_id}")
    assert get_after.status_code == 404


def test_overlap():
    res = client.get("/api/overlap?ids=0,1")
    assert res.status_code == 200
    data = res.json()
    assert "pairs" in data
    assert len(data["pairs"]) == 1
    assert "jaccard" in data["pairs"][0]


def test_overlap_invalid_ids():
    res = client.get("/api/overlap?ids=99999,99998")
    assert res.status_code == 404


def test_overlap_too_few_ids():
    res = client.get("/api/overlap?ids=0")
    assert res.status_code == 422


def test_import_valid_csv():
    csv_content = (
        "source,target\n"
        "@alice,@bob\n"
        "@bob,@charlie\n"
        "@charlie,@alice\n"
        "@david,@alice\n"
    )
    files = {"file": ("test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res = client.post("/api/import", files=files, data={"topic_name": "#CustomTopic"})
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert isinstance(data["nodes"], list)
    assert len(data["nodes"]) == 4
    assert "links" in data
    assert isinstance(data["links"], list)
    assert data["meta"]["synthetic"] is False

    # Verify reset endpoint returns synthetic
    reset_res = client.post("/api/reset")
    assert reset_res.status_code == 200
    graph_res = client.get("/api/graph")
    assert len(graph_res.json()["nodes"]) == 150


def test_import_invalid_csv_no_headers():
    csv_content = "foo,bar\na,b\nb,c\n"
    files = {"file": ("test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res = client.post("/api/import", files=files)
    assert res.status_code == 422


def test_metrics_computation():
    G = nx.Graph()
    G.add_edges_from([(1, 2), (2, 3), (3, 1), (3, 4)])
    metrics = compute_metrics(G)
    assert len(metrics) == 4
    for node_id in [1, 2, 3, 4]:
        assert "influence" in metrics[node_id]
        assert "bridge" in metrics[node_id]
        assert "degree" in metrics[node_id]
        assert 0 <= metrics[node_id]["influence"] <= 100
        assert 0 <= metrics[node_id]["bridge"] <= 100


def test_bot_heuristic():
    score1 = bot_heuristic("mariagonzalez", posts=100, followers=500)
    assert score1 < 50

    score2 = bot_heuristic("TruthNow9823", posts=2500, followers=100)
    assert score2 >= 60


def test_export_gexf():
    res = client.get("/api/projects/demo-reforma-del-agua/export/gexf")
    assert res.status_code == 200
    assert "gexf" in res.text
    assert "<node" in res.text
    assert "<edge" in res.text


def test_executive_report():
    res = client.get("/api/projects/demo-reforma-del-agua/report")
    assert res.status_code == 200
    report = res.json()
    assert "summary" in report
    assert "top_influencers" in report
    assert "astroturfing_findings" in report
    assert "campaign_strategy" in report
    assert len(report["top_influencers"]) > 0
    assert report["summary"]["total_profiles"] == 150
    if report["campaign_strategy"]:
        assert "echo_chamber" in report["campaign_strategy"]
        assert "tactical_actions" in report["campaign_strategy"]


def test_leads_submission():
    payload = {
        "name": "Lucía Morales",
        "email": "lucia@agenciapr.com",
        "company": "Crisis & Comms Latam",
        "role": "Directora de Asuntos Públicos",
        "use_case": "Monitoreo de desinformación electoral",
    }
    res = client.post("/api/leads", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "lead" in data
    assert data["lead"]["email"] == "lucia@agenciapr.com"

    # List leads
    get_res = client.get("/api/leads")
    assert get_res.status_code == 200
    leads = get_res.json()
    assert any(l["email"] == "lucia@agenciapr.com" for l in leads)


def test_political_candidates_endpoint():
    res = client.get("/api/political/candidates")
    assert res.status_code == 200
    candidates = res.json()
    assert len(candidates) > 0
    assert "handle" in candidates[0]
    assert "comm_name" in candidates[0]


def test_political_audit_endpoint_by_id():
    res = client.get("/api/political/audit?candidate_id=0")
    assert res.status_code == 200
    data = res.json()
    assert "candidate" in data
    assert "echo_chamber" in data
    assert "tactical_actions" in data


def test_political_audit_endpoint_by_handle():
    # Obtener el handle del nodo 0
    candidates = client.get("/api/political/candidates").json()
    test_handle = candidates[0]["handle"]
    res = client.get(f"/api/political/audit?handle={test_handle}")
    assert res.status_code == 200
    data = res.json()
    assert data["candidate"]["handle"] == test_handle


def test_political_brokers_endpoint():
    res = client.get("/api/political/brokers?candidate_id=0&limit=5")
    assert res.status_code == 200
    brokers = res.json()
    assert isinstance(brokers, list)


def test_political_expansion_paths_endpoint():
    res = client.get("/api/political/expansion-paths?candidate_id=0&target_comm=1")
    assert res.status_code == 200
    paths = res.json()
    assert isinstance(paths, list)


def test_sprint1_project_isolation_via_header():
    # Crear dos proyectos distintos
    p1 = client.post("/api/projects", json={"name": "Proyecto Alpha", "topic": "#Alpha"}).json()
    p2 = client.post("/api/projects", json={"name": "Proyecto Beta", "topic": "#Beta"}).json()

    # Modificar el grafo de Alpha con un nodo particular
    id1 = p1["id"]
    id2 = p2["id"]

    # Consultar /api/graph con cabecera X-Project-Id
    res1 = client.get("/api/graph", headers={"X-Project-Id": id1})
    res2 = client.get("/api/graph", headers={"X-Project-Id": id2})

    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.json()["meta"]["topic"] == "#Alpha"
    assert res2.json()["meta"]["topic"] == "#Beta"

    # Limpieza
    client.delete(f"/api/projects/{id1}")
    client.delete(f"/api/projects/{id2}")


def test_sprint1_csv_formula_injection_sanitization():
    # CSV con payloads maliciosos de inyección de fórmulas (CWE-1236)
    csv_malicioso = (
        "source,target\n"
        "=cmd|' /C calc'!A0,+attacker123\n"
        "+attacker123,@target_user\n"
        "@target_user,\t-malicious_macro\n"
    )
    files = {"file": ("malicious.csv", io.BytesIO(csv_malicioso.encode("utf-8")), "text/csv")}
    res = client.post("/api/import", files=files, data={"topic_name": "=SUM(A1:A10)"})

    assert res.status_code == 200
    graph = res.json()
    handles = [n["handle"] for n in graph["nodes"]]

    # Ningún handle debe iniciar con =, +, -, \t o @
    for h in handles:
        assert not h.startswith("=")
        assert not h.startswith("+")
        assert not h.startswith("-")
        assert not h.startswith("\t")
        assert not h.startswith("@")

    # El topic debe haber sido sanitizado y no empezar con =
    assert not graph["meta"]["topic"].startswith("=")


def test_sprint1_csv_size_limit():
    # Simular archivo mayor a 15MB
    large_payload = b"source,target\n" + b"a,b\n" * (4 * 1024 * 1024)  # ~16MB
    files = {"file": ("huge.csv", io.BytesIO(large_payload), "text/csv")}
    res = client.post("/api/import", files=files)
    assert res.status_code == 413


def test_sprint1_leiden_communities():
    from app.metrics import compute_communities_leiden
    G = nx.erdos_renyi_graph(150, 0.05, seed=42)
    communities = compute_communities_leiden(G)
    assert len(communities) >= 2
    # La unión de todas las comunidades cubre todos los nodos
    all_assigned = set().union(*communities)
    assert all_assigned == set(G.nodes())


def test_sprint2_async_import_and_task_polling():
    csv_content = (
        "source,target\n"
        "@node_a,@node_b\n"
        "@node_b,@node_c\n"
        "@node_c,@node_a\n"
        "@node_d,@node_c\n"
    )
    files = {"file": ("async_test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res = client.post("/api/import/async", files=files, data={"topic_name": "#AsyncTest"})

    assert res.status_code == 202
    data = res.json()
    assert "task_id" in data
    assert data["status"] == "pending"

    task_id = data["task_id"]

    # Consultar estado de la tarea
    import time
    time.sleep(0.4)  # Permitir que el background worker procese

    status_res = client.get(f"/api/tasks/{task_id}")
    assert status_res.status_code == 200
    task_info = status_res.json()
    assert task_info["task_id"] == task_id
    assert task_info["status"] in ("processing", "completed")
    assert 0 <= task_info["progress"] <= 100


@pytest.mark.anyio
async def test_sprint2_sse_events_streaming():
    from app.tasks import enqueue_import_task, subscribe_task_events
    csv_content = "source,target\n@u1,@u2\n@u2,@u3\n@u3,@u1\n"
    task_id = enqueue_import_task(csv_content, filename="stream.csv", topic_name="#StreamingTest")

    events = []
    async for event_chunk in subscribe_task_events(task_id):
        events.append(event_chunk)
        if "complete" in event_chunk or "100" in event_chunk or "failed" in event_chunk:
            break

    assert len(events) >= 1
    assert any("event: progress" in e or "event: complete" in e for e in events)


def test_sprint2_sqlalchemy_models_persistence():
    from app.database import SessionLocal
    from app.models import ProjectModel, TaskModel, LeadModel
    import uuid

    test_id = str(uuid.uuid4())
    with SessionLocal() as session:
        proj = ProjectModel(
            id=test_id,
            name="SQLAlchemy Model Test",
            topic="#RelationalTest",
            created_at="2026-10-08T00:00:00Z",
            updated_at="2026-10-08T00:00:00Z",
            node_count=10,
            link_count=15,
            community_count=2,
            graph_json="{}",
        )
        session.add(proj)
        session.commit()

        # Consultar
        found = session.query(ProjectModel).filter(ProjectModel.id == test_id).first()
        assert found is not None
        assert found.topic == "#RelationalTest"

        # Limpiar
        session.delete(found)
        session.commit()


