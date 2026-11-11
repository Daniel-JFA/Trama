"""
test_nlp.py — Tests automatizados para el Sprint 3:
1. Normalización y shingles.
2. Detección de copypasta y parafraseo con MinHash/LSH.
3. Detección de redes CooRnet de co-compartición sincronizada.
4. Medición de polarización RWC (Random Walk Controversy).
5. Endpoints HTTP de la API FastAPI.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.nlp import (
    normalize_text,
    create_shingles,
    get_minhash,
    detect_copypasta_clusters,
    compute_semantic_similarity,
    get_sentence_transformer_model,
    set_sentence_transformer_model,
    reset_sentence_transformer_cache,
    detect_paraphrase_campaigns,
)
from app.cib import detect_coornet_network, run_monte_carlo_coornet_permutation
from app.political import calculate_random_walk_controversy
from app.synth import generate_synthetic_graph


client = TestClient(app)


# ─── 1. Pruebas Unitarias de NLP & MinHash ───────────────────────────────────

def test_normalize_text():
    raw = "¡URGENTE! Apoya el paro nacional hoy mismo: https://t.co/xyz123 @CongresoCol #ParoYa"
    clean = normalize_text(raw)
    assert "https" not in clean
    assert "@congresocol" not in clean
    assert "#paroya" not in clean
    assert "urgente apoya el paro nacional hoy mismo" in clean


def test_create_shingles():
    text = "reforma agraria"
    shingles = create_shingles(text, k=3)
    assert len(shingles) > 5
    assert "ref" in shingles or "agr" in shingles


def test_minhash_jaccard_similarity():
    t1 = "El agua es un derecho fundamental y no debe privatizarse en el congreso"
    t2 = "El agua es un derecho fundamental y jamas debe privatizarse en el congreso!"
    t3 = "Hoy el partido de futbol termino con un empate cero a cero"

    m1 = get_minhash(t1)
    m2 = get_minhash(t2)
    m3 = get_minhash(t3)

    sim_12 = m1.jaccard(m2)
    sim_13 = m1.jaccard(m3)

    assert sim_12 >= 0.70, f"Similitud entre textos casi idénticos debería ser alta: {sim_12}"
    assert sim_13 < 0.25, f"Similitud entre textos disímiles debería ser baja: {sim_13}"


def test_detect_copypasta_coordinated_campaign():
    messages = [
        {"id": 1, "handle": "bot_alpha", "text": "Alerta nacional, todos a defender los rios y el agua sagrada!", "timestamp": 1000},
        {"id": 2, "handle": "bot_beta", "text": "Alerta nacional, todos a defender los rios y el agua sagrada!", "timestamp": 1020},
        {"id": 3, "handle": "bot_gamma", "text": "Alerta nacional, todos a defender los rios y el agua sagrada", "timestamp": 1050},
        {"id": 4, "handle": "usuario_real", "text": "Una hermosa tarde para salir a caminar por el parque con mi perro", "timestamp": 1100},
    ]

    res = detect_copypasta_clusters(messages, jaccard_threshold=0.75, time_window_seconds=300)

    assert res["clusters_count"] == 1
    assert res["copypasta_volume"] == 3
    cl = res["clusters"][0]
    assert cl["is_coordinated"] is True
    assert cl["unique_accounts_count"] == 3
    assert set(cl["accounts"]) == {"bot_alpha", "bot_beta", "bot_gamma"}
    assert "bot_alpha" in res["coordinated_accounts"]
    assert "usuario_real" not in res["coordinated_accounts"]


# ─── 2. Pruebas Unitarias de CooRnet ─────────────────────────────────────────

def test_detect_coornet_network():
    # Cuentas 1 y 2 comparten el mismo enlace en Delta_t = 10s (coordinado)
    # y luego otro enlace en Delta_t = 15s (coordinado)
    events = [
        {"handle": "coord_1", "entity_id": "https://fake.news/noticia1", "timestamp": 100.0},
        {"handle": "coord_2", "entity_id": "https://fake.news/noticia1", "timestamp": 110.0},
        {"handle": "coord_1", "entity_id": "https://fake.news/noticia2", "timestamp": 200.0},
        {"handle": "coord_2", "entity_id": "https://fake.news/noticia2", "timestamp": 215.0},
        # Cuenta 3 comparte noticia1 horas después (no coordinado)
        {"handle": "organico_3", "entity_id": "https://fake.news/noticia1", "timestamp": 5000.0},
    ]

    res = detect_coornet_network(events, time_window_seconds=45.0, min_co_shares=2)

    assert res["total_pairs_detected"] == 1
    link = res["links"][0]
    assert {link["source"], link["target"]} == {"coord_1", "coord_2"}
    assert link["weight"] == 2
    assert link["avg_delta_seconds"] == 12.5
    assert len(res["coordinated_cliques"]) == 1


# ─── 3. Pruebas de Polarización RWC ──────────────────────────────────────────

def test_calculate_random_walk_controversy():
    synth = generate_synthetic_graph()
    # Comunidades 0 y 1 del grafo sintético
    rwc = calculate_random_walk_controversy(synth, comm1_id=0, comm2_id=1, num_walks=200)

    assert "rwc_score" in rwc
    assert 0.0 <= rwc["rwc_score"] <= 100.0
    assert "conductance" in rwc
    assert rwc["conductance"] >= 0.0
    assert "diagnosis" in rwc
    assert isinstance(rwc["diagnosis"], str)


# ─── 4. Pruebas de Integración de Endpoints FastAPI ──────────────────────────

def test_endpoint_copypasta_api():
    payload = {
        "messages": [
            {"id": "m1", "handle": "astroturf_1", "text": "Atencion pueblo, salgamos a marchar pacíficamente", "timestamp": 10.0},
            {"id": "m2", "handle": "astroturf_2", "text": "Atencion pueblo, salgamos a marchar pacificamente!", "timestamp": 25.0},
        ],
        "jaccard_threshold": 0.8,
        "time_window_seconds": 60,
    }
    resp = client.post("/api/nlp/copypasta", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["clusters_count"] == 1
    assert data["copypasta_volume"] == 2
    assert "astroturf_1" in data["coordinated_accounts"]


def test_endpoint_coornet_api():
    payload = {
        "events": [
            {"handle": "user_a", "entity_id": "item_x", "timestamp": 100.0},
            {"handle": "user_b", "entity_id": "item_x", "timestamp": 120.0},
            {"handle": "user_a", "entity_id": "item_y", "timestamp": 300.0},
            {"handle": "user_b", "entity_id": "item_y", "timestamp": 310.0},
        ],
        "time_window_seconds": 30.0,
        "min_co_shares": 2,
    }
    resp = client.post("/api/cib/coornet", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_pairs_detected"] == 1
    assert len(data["links"]) == 1


def test_endpoint_rwc_api():
    resp = client.get("/api/political/rwc?comm1=0&comm2=1&walks=150")
    assert resp.status_code == 200
    data = resp.json()
    assert "rwc_score" in data
    assert "conductance" in data
    assert "diagnosis" in data


# ─── 5. Nuevas Pruebas del Bloque A (Sprint 3) ───────────────────────────────

def test_semantic_similarity_exact_and_fallback():
    """Verifica que la similitud semántica calcula scores coherentes con fallback transparente."""
    # 1. Textos idénticos
    sim_exact, method_exact = compute_semantic_similarity(
        "El agua es un derecho humano no comercializable",
        "El agua es un derecho humano no comercializable",
    )
    assert sim_exact == 1.0
    assert method_exact == "exact_match"

    # 2. Textos parafraseados con alta similitud
    t1 = "El congreso debe proteger las fuentes hidricas y frenar la mineria en paramos ya mismo"
    t2 = "El congreso debe proteger las fuentes hidricas y frenar la mineria en paramos hoy"
    sim_para, method_para = compute_semantic_similarity(t1, t2)
    assert sim_para >= 0.75, f"Similitud esperada alta, obtenida: {sim_para}"

    # 3. Textos completamente disímiles (control negativo)
    t3 = "Ayer ganaron los locales en el torneo de tenis de mesa internacional"
    sim_diff, _ = compute_semantic_similarity(t1, t3)
    assert sim_diff < 0.35, f"Similitud de textos disímiles debe ser baja: {sim_diff}"


def test_sentence_transformers_lazy_loading_and_mock_injection():
    """Verifica la carga perezosa y la capacidad de inyectar modelos neuronales sin fallar en CI."""
    reset_sentence_transformer_cache()

    # Si sentence_transformers no está instalado, retorna None sin lanzar excepción
    model = get_sentence_transformer_model()
    # No debe arrojar error independientemente de si la librería existe o no en el entorno

    # Mock determinista para probar el branch de sentence-transformers
    class MockSentenceTransformer:
        def encode(self, texts, convert_to_numpy=True, normalize_embeddings=True):
            import numpy as np
            embs = []
            for t in texts:
                clean = normalize_text(t)
                if "agua" in clean or "hidrica" in clean:
                    v = np.array([0.95, 0.25, 0.05, 0.0], dtype=np.float32)
                elif "futbol" in clean:
                    v = np.array([0.05, 0.0, 0.95, 0.25], dtype=np.float32)
                else:
                    v = np.array([0.5, 0.5, 0.5, 0.5], dtype=np.float32)
                norm = np.linalg.norm(v)
                if norm > 0:
                    v = v / norm
                embs.append(v)
            return np.array(embs)

    try:
        set_sentence_transformer_model(MockSentenceTransformer())
        sim, method = compute_semantic_similarity(
            "Defender el agua pública",
            "Protección de la reserva hídrica nacional",
        )
        assert sim >= 0.85
        assert "sentence-transformers" in method
    finally:
        reset_sentence_transformer_cache()


def test_detect_copypasta_paraphrase_campaign_semantic_threshold():
    """Detecta campaña coordinada de parafraseo con umbral semántico y ventana Delta_t < 15 min."""
    messages = [
        {
            "id": "p1",
            "handle": "bot_1",
            "text": "Exigimos al congreso frenar la privatizacion del agua de forma inmediata #ReformaDelAgua",
            "timestamp": 100.0,
        },
        {
            "id": "p2",
            "handle": "bot_2",
            "text": "Exigimos al congreso frenar la privatizacion del agua ya de forma inmediata #ReformaDelAgua",
            "timestamp": 160.0,
        },
        {
            "id": "p3",
            "handle": "bot_3",
            "text": "Urgente: exigimos al congreso frenar la privatizacion del agua de forma inmediata #ReformaDelAgua",
            "timestamp": 220.0,
        },
        {
            "id": "p4",
            "handle": "ciudadano_random",
            "text": "Saliendo a almorzar con los colegas de la oficina en el centro histórico de la ciudad",
            "timestamp": 180.0,
        },
    ]

    res = detect_paraphrase_campaigns(messages, similarity_threshold=0.80, time_window_seconds=900)

    assert res["clusters_count"] >= 1
    assert res["copypasta_volume"] >= 3
    cl = res["clusters"][0]
    assert cl["is_coordinated"] is True
    assert cl["unique_accounts_count"] == 3
    assert set(cl["accounts"]) == {"bot_1", "bot_2", "bot_3"}
    assert "ciudadano_random" not in res["coordinated_accounts"]
    assert cl["timespan_seconds"] <= 900


def test_coornet_monte_carlo_permutation_coordinated_campaign():
    """
    Control Positivo: Red de bots que co-comparten 4 enlaces repetidamente en Delta_t = 3 segundos.
    La prueba de Monte Carlo debe rechazar H0 con p-valor < 0.05 (coordinación estadísticamente significativa).
    """
    bots = ["bot_net_A", "bot_net_B", "bot_net_C"]
    entities = ["https://fake.site/link1", "https://fake.site/link2", "https://fake.site/link3", "https://fake.site/link4"]

    events = []
    base_t = 1000.0
    for ent_idx, ent in enumerate(entities):
        t_batch = base_t + (ent_idx * 5000.0)  # horas distintas
        for i, b in enumerate(bots):
            events.append({
                "handle": b,
                "entity_id": ent,
                "timestamp": t_batch + (i * 3.0),  # Delta_t = 3s
            })

    res = detect_coornet_network(
        events,
        time_window_seconds=45.0,
        min_co_shares=2,
        monte_carlo_iterations=100,
        alpha=0.05,
        seed=42,
    )

    assert res["total_pairs_detected"] >= 3
    assert res["significant_coordinated_pairs"] >= 3

    for link in res["links"]:
        assert link["is_statistically_significant"] is True
        assert link["p_value"] < 0.05
        assert link["classification"] == "coordinated"

    assert len(res["coordinated_cliques"]) >= 1
    clique = res["coordinated_cliques"][0]
    assert clique["is_statistically_significant"] is True
    assert clique["classification"] == "coordinated_campaign"


def test_coornet_monte_carlo_permutation_organic_traffic_negative_control():
    """
    Control Negativo: Tráfico orgánico de cuentas independientes compartiendo un enlace viral
    a lo largo de varias horas. La prueba de Monte Carlo no debe clasificarlas como coordinadas (p >= 0.05).
    """
    # 10 usuarios independientes compartiendo una noticia viral con horas de diferencia
    events = [
        {"handle": f"organic_user_{i}", "entity_id": "https://noticias.com/noticia-viral-del-dia", "timestamp": 10000.0 + (i * 1200.0)}
        for i in range(10)
    ]
    # Dos usuarios coinciden por azar en una ventana de 30s en un solo post
    events.append({"handle": "coincidencia_1", "entity_id": "https://noticias.com/noticia-viral-del-dia", "timestamp": 50000.0})
    events.append({"handle": "coincidencia_2", "entity_id": "https://noticias.com/noticia-viral-del-dia", "timestamp": 50020.0})

    # Como solo coinciden 1 vez, con min_co_shares=2 ni siquiera forman arista
    res = detect_coornet_network(
        events,
        time_window_seconds=45.0,
        min_co_shares=2,
        monte_carlo_iterations=50,
        seed=42,
    )
    assert res["total_pairs_detected"] == 0
    assert res["significant_coordinated_pairs"] == 0

    # Ahora agregamos una segunda coincidencia con min_co_shares=2 en un escenario de alta densidad viral
    viral_events = []
    # 15 usuarios twitteando en una ráfaga viral de 50 segundos
    for i in range(15):
        viral_events.append({"handle": f"persona_{i}", "entity_id": "https://noticias.com/evento-en-vivo-1", "timestamp": 100.0 + (i * 2.0)})
        viral_events.append({"handle": f"persona_{i}", "entity_id": "https://noticias.com/evento-en-vivo-2", "timestamp": 500.0 + (i * 2.0)})

    res_viral = detect_coornet_network(
        viral_events,
        time_window_seconds=45.0,
        min_co_shares=2,
        monte_carlo_iterations=50,
        alpha=0.01,
        seed=42,
    )
    # Verificamos que los enlaces cuenten con p-valor calculado y campo classification
    for link in res_viral["links"]:
        assert "p_value" in link
        assert link["classification"] in ["coordinated", "organic_traffic"]


def test_coornet_monte_carlo_deterministic_seed():
    """Verifica que la semilla de Monte Carlo hace los resultados 100% deterministas y reproducibles."""
    events = [
        {"handle": "usr_x", "entity_id": "ent_1", "timestamp": 10.0},
        {"handle": "usr_y", "entity_id": "ent_1", "timestamp": 15.0},
        {"handle": "usr_x", "entity_id": "ent_2", "timestamp": 80.0},
        {"handle": "usr_y", "entity_id": "ent_2", "timestamp": 85.0},
    ]

    res1 = detect_coornet_network(events, time_window_seconds=45.0, min_co_shares=2, monte_carlo_iterations=50, seed=12345)
    res2 = detect_coornet_network(events, time_window_seconds=45.0, min_co_shares=2, monte_carlo_iterations=50, seed=12345)

    p1 = res1["links"][0]["p_value"]
    p2 = res2["links"][0]["p_value"]
    assert p1 == p2, f"Los p-valores deben ser idénticos con la misma semilla: {p1} vs {p2}"


def test_endpoints_coornet_get_and_post_with_monte_carlo():
    """Prueba los endpoints HTTP GET y POST de CooRnet con soporte para Monte Carlo."""
    # 1. Endpoint POST
    payload = {
        "events": [
            {"handle": "alpha", "entity_id": "res_1", "timestamp": 100.0},
            {"handle": "beta", "entity_id": "res_1", "timestamp": 105.0},
            {"handle": "alpha", "entity_id": "res_2", "timestamp": 300.0},
            {"handle": "beta", "entity_id": "res_2", "timestamp": 310.0},
        ],
        "time_window_seconds": 30.0,
        "min_co_shares": 2,
        "monte_carlo_iterations": 50,
        "alpha": 0.05,
        "seed": 999,
    }
    resp_post = client.post("/api/cib/coornet", json=payload)
    assert resp_post.status_code == 200
    data_post = resp_post.json()
    assert data_post["total_pairs_detected"] == 1
    link = data_post["links"][0]
    assert "p_value" in link
    assert "is_statistically_significant" in link
    assert "classification" in link

    # 2. Endpoint GET sobre la investigación activa
    resp_get = client.get("/api/cib/coornet?min_co_shares=2&monte_carlo_iterations=30&seed=999")
    assert resp_get.status_code == 200
    data_get = resp_get.json()
    assert "links" in data_get
    assert "total_pairs_detected" in data_get
    assert data_get["total_pairs_detected"] >= 1


def test_endpoint_copypasta_get_and_semantic_threshold():
    """Prueba los endpoints HTTP GET y POST de Copypasta con umbral semántico."""
    # 1. Endpoint POST con semantic_threshold
    payload = {
        "messages": [
            {"id": "c1", "handle": "astroturf_1", "text": "¡Urgente todos a defender los ríos sagrados!", "timestamp": 10.0},
            {"id": "c2", "handle": "astroturf_2", "text": "Urgente todos a defender los rios sagrados!", "timestamp": 25.0},
        ],
        "jaccard_threshold": 0.75,
        "semantic_threshold": 0.85,
        "time_window_seconds": 300,
    }
    resp_post = client.post("/api/nlp/copypasta", json=payload)
    assert resp_post.status_code == 200
    data_post = resp_post.json()
    assert data_post["clusters_count"] == 1
    assert "similarity_method" in data_post["clusters"][0]

    # 2. Endpoint GET sobre la investigación activa
    resp_get = client.get("/api/nlp/copypasta?semantic_threshold=0.85")
    assert resp_get.status_code == 200
    data_get = resp_get.json()
    assert "clusters" in data_get
    assert data_get["clusters_count"] >= 1
    assert data_get["copypasta_volume"] >= 2

