"""
test_political.py — Pruebas unitarias para el motor de inteligencia política de TRAMA.
"""

import pytest
from app.synth import generate_synthetic_graph
from app.political import (
    calculate_echo_chamber_index,
    audit_candidate,
    find_strategic_brokers,
    find_expansion_paths,
    list_potential_candidates,
)


@pytest.fixture(scope="module")
def synthetic_graph():
    return generate_synthetic_graph()


def test_list_potential_candidates(synthetic_graph):
    candidates = list_potential_candidates(synthetic_graph, top_per_comm=2)
    assert len(candidates) > 0
    # Cada candidato debe tener atributos indispensables
    first = candidates[0]
    assert "id" in first
    assert "handle" in first
    assert "comm_id" in first
    assert "influence" in first
    assert "bridge" in first


def test_audit_candidate_valid(synthetic_graph):
    # Probar con el nodo 0 (prensa / institucional)
    audit = audit_candidate(synthetic_graph, candidate_id=0)
    assert "candidate" in audit
    assert "echo_chamber" in audit
    assert "community_reach" in audit
    assert "dirty_war_shield" in audit
    assert "tactical_actions" in audit

    cand = audit["candidate"]
    assert cand["id"] == 0
    assert cand["handle"] != ""

    eci = audit["echo_chamber"]
    assert 0 <= eci["score"] <= 100
    assert "level" in eci
    assert "interpretation" in eci

    # Verificar alcance de comunidades
    reach = audit["community_reach"]
    assert len(reach) > 0
    total_pct = sum(r["percentage"] for r in reach)
    assert 95 <= total_pct <= 105 or total_pct == 0  # con redondeo

    # Verificar escudo de guerra sucia
    shield = audit["dirty_war_shield"]
    assert "threat_level" in shield
    assert "threat_message" in shield
    assert isinstance(shield["hostile_accounts_count"], int)

    # Verificar acciones tácticas
    assert len(audit["tactical_actions"]) >= 1


def test_audit_candidate_not_found(synthetic_graph):
    with pytest.raises(ValueError):
        audit_candidate(synthetic_graph, candidate_id=999999)


def test_find_strategic_brokers(synthetic_graph):
    brokers = find_strategic_brokers(synthetic_graph, candidate_id=0, limit=5)
    assert isinstance(brokers, list)
    assert len(brokers) <= 5
    if brokers:
        b = brokers[0]
        assert "alliance_score" in b
        assert "handle" in b
        assert "target_reach" in b
        assert "rationale" in b
        assert b["bot_score"] < 35  # Filtrado de cuentas bot


def test_find_strategic_brokers_target_comm(synthetic_graph):
    # Buscar brokers específicamente para la comunidad 1 (Ambientalistas)
    brokers = find_strategic_brokers(synthetic_graph, candidate_id=0, target_comm_id=1, limit=3)
    assert isinstance(brokers, list)
    for b in brokers:
        assert b["alliance_score"] >= 0


def test_find_expansion_paths(synthetic_graph):
    # Buscar rutas desde un nodo del gremio (ej. nodo en comunidad 2) hacia comunidad 1 (Ambientalistas)
    # Encontrar un nodo en comunidad 2
    nodes_comm_2 = [n["id"] for n in synthetic_graph["nodes"] if n["comm"] == 2]
    assert len(nodes_comm_2) > 0
    cand_id = nodes_comm_2[0]

    paths = find_expansion_paths(synthetic_graph, candidate_id=cand_id, target_comm_id=1, max_paths=2)
    assert isinstance(paths, list)
    if paths:
        p = paths[0]
        assert "target_handle" in p
        assert "viability_score" in p
        assert len(p["steps"]) >= 2
        assert p["steps"][0]["id"] == cand_id
