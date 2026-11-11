"""
nlp.py — Motor de Inteligencia Forense Semántica y Detección de Copypasta Coordinado.

Sprint 3 (Bloque A):
1. Indexación y agrupamiento de textos con MinHash y Locality Sensitive Hashing (LSH).
2. Similitud semántica neuronal con 'paraphrase-multilingual-MiniLM-L12-v2' (sentence-transformers).
3. Carga perezosa (lazy load) con fallback automático a MinHash + TF-IDF si la dependencia no está disponible.
4. Detección de campañas de copypasta y parafraseo coordinado (similitud > 0.85, ventana Delta_t < 15 min).
"""

import re
import unicodedata
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

from datasketch import MinHash, MinHashLSH
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ─── Gestión de Carga Perezosa (Lazy Loading) del Modelo Neuronal ─────────────
_ST_MODEL = None
_ST_TRIED_LOADING = False


def get_sentence_transformer_model(model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
    """
    Carga perezosa del modelo multilingüe de sentence-transformers.
    Retorna None si la librería no está instalada o falla la descarga/carga de pesos,
    habilitando un fallback transparente para que tests y CI no dependan de la red.
    """
    global _ST_MODEL, _ST_TRIED_LOADING
    if _ST_MODEL is not None:
        return _ST_MODEL
    if _ST_TRIED_LOADING:
        return None

    _ST_TRIED_LOADING = True
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        _ST_MODEL = SentenceTransformer(model_name)
        return _ST_MODEL
    except Exception:
        _ST_MODEL = None
        return None


def set_sentence_transformer_model(model_instance: Any):
    """Permite inyectar un modelo o mock en tests unitarios para verificar el flujo neuronal."""
    global _ST_MODEL, _ST_TRIED_LOADING
    _ST_MODEL = model_instance
    _ST_TRIED_LOADING = True


def reset_sentence_transformer_cache():
    """Reinicia el singleton de sentence-transformers (útil para aislar tests de fallback)."""
    global _ST_MODEL, _ST_TRIED_LOADING
    _ST_MODEL = None
    _ST_TRIED_LOADING = False


# ─── Normalización y Tokenización Shingle ────────────────────────────────────

def normalize_text(text: str) -> str:
    """Normaliza texto: remueve URLs, menciones, hashtags, puntuación, mayúsculas y acentos."""
    if not text:
        return ""
    # Quitar URLs
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    # Quitar menciones @ y hashtags # para comparar el contenido semántico base
    text = re.sub(r"[@#]\w+", "", text)
    # Descomposición unicode para neutralizar tildes y diacríticos
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    # Minúsculas y limpieza de caracteres no alfanuméricos
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    # Espacios múltiples
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def create_shingles(text: str, k: int = 3) -> set[str]:
    """Crea shingles de caracteres (n-gramas) para preservar similitud ante typos y variaciones leves."""
    clean = normalize_text(text)
    if len(clean) < k:
        return {clean} if clean else set()
    return {clean[i : i + k] for i in range(len(clean) - k + 1)}


def get_minhash(text: str, num_perm: int = 128) -> MinHash:
    """Calcula el MinHash para un texto dado usando datasketch."""
    m = MinHash(num_perm=num_perm)
    shingles = create_shingles(text)
    for shingle in shingles:
        m.update(shingle.encode("utf8"))
    return m


# ─── Cálculo de Similitud Semántica Neuronal y Fallback ───────────────────────

def compute_semantic_similarity(
    text1: str,
    text2: str,
    model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
) -> Tuple[float, str]:
    """
    Calcula la similitud semántica entre dos textos en rango [0.0, 1.0].
    Retorna una tupla: (score_similitud, metodo_utilizado).

    1. Si sentence-transformers está disponible, usa embeddings densos normalizados L2.
    2. Si no está disponible o falla, recurre a MinHash Jaccard ponderado con TF-IDF n-gramas.
    """
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)

    if not norm1 or not norm2:
        return 0.0, "empty"
    if norm1 == norm2:
        return 1.0, "exact_match"

    # Intento 1: sentence-transformers
    model = get_sentence_transformer_model(model_name)
    if model is not None:
        try:
            import numpy as np  # type: ignore
            embs = model.encode([text1, text2], convert_to_numpy=True, normalize_embeddings=True)
            cos = float(np.dot(embs[0], embs[1]))
            clipped = max(0.0, min(1.0, cos))
            return round(clipped, 4), f"sentence-transformers ({model_name})"
        except Exception:
            pass

    # Intento 2: Fallback determinista (MinHash + TF-IDF char n-grams)
    m1 = get_minhash(text1)
    m2 = get_minhash(text2)
    jaccard = float(m1.jaccard(m2))

    try:
        tfidf = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))
        mat = tfidf.fit_transform([norm1, norm2])
        cos_sim = float(cosine_similarity(mat[0:1], mat[1:2])[0][0])
        # Ponderación híbrida: captura similitud léxica y n-gramas
        combined = 0.45 * jaccard + 0.55 * cos_sim
    except Exception:
        combined = jaccard

    return round(max(0.0, min(1.0, combined)), 4), "minhash-tfidf-fallback"


# ─── Detección de Clústeres de Copypasta y Parafraseo Coordinado ──────────────

def detect_copypasta_clusters(
    messages: List[Dict[str, Any]],
    jaccard_threshold: float = 0.80,
    semantic_threshold: float = 0.85,
    time_window_seconds: int = 900,  # 15 minutos (Delta_t < 15 min)
    num_perm: int = 128,
    model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
) -> Dict[str, Any]:
    """
    Detecta campañas coordinadas de copypasta y parafraseo semántico.

    Combina indexación rápida MinHash LSH con verificación semántica neuronal
    (o fallback híbrido si no está instalado sentence-transformers).

    Parámetros:
      messages: Lista de diccionarios con 'id', 'handle', 'text', 'timestamp'.
      jaccard_threshold: Umbral MinHash LSH para generación de pares candidatos.
      semantic_threshold: Umbral semántico (> 0.85) para confirmar parafraseo coordinado.
      time_window_seconds: Ventana temporal máxima (default: 900s = 15 minutos).
      num_perm: Permutaciones MinHash (default: 128).
      model_name: Nombre del modelo de sentence-transformers.

    Retorna:
      Dict con total_messages, clusters, coordinated_accounts, copypasta_volume, clusters_count.
    """
    if not messages or len(messages) < 2:
        return {
            "total_messages": len(messages) if messages else 0,
            "clusters": [],
            "coordinated_accounts": [],
            "copypasta_volume": 0,
            "clusters_count": 0,
        }

    # 1. Indexación de candidatos con MinHash LSH
    # Relajamos ligeramente el umbral LSH para captar paráfrasis semánticas
    lsh_candidate_threshold = min(jaccard_threshold, 0.70)
    lsh = MinHashLSH(threshold=lsh_candidate_threshold, num_perm=num_perm)
    minhashes: Dict[str, MinHash] = {}
    msg_map: Dict[str, Dict[str, Any]] = {}

    for idx, msg in enumerate(messages):
        key = str(msg.get("id", idx))
        text = msg.get("text", "")
        if not text or len(normalize_text(text)) < 8:
            continue
        m = get_minhash(text, num_perm=num_perm)
        minhashes[key] = m
        msg_map[key] = {
            "key": key,
            "handle": msg.get("handle", "anon"),
            "text": text,
            "timestamp": float(msg.get("timestamp", 0)),
        }
        try:
            lsh.insert(key, m)
        except Exception:
            pass

    # 2. Generación de pares candidatos mediante LSH
    candidate_pairs = set()
    for key, m in minhashes.items():
        neighbors = lsh.query(m)
        for cand in neighbors:
            if cand != key:
                pair = tuple(sorted([key, cand]))
                candidate_pairs.add(pair)

    # Si hay pocos mensajes (< 40), evaluamos también pares directos dentro de la ventana de tiempo
    if len(msg_map) <= 40:
        keys_list = list(msg_map.keys())
        for i in range(len(keys_list)):
            for j in range(i + 1, len(keys_list)):
                k1, k2 = keys_list[i], keys_list[j]
                dt = abs(msg_map[k1]["timestamp"] - msg_map[k2]["timestamp"])
                if dt <= time_window_seconds:
                    candidate_pairs.add(tuple(sorted([k1, k2])))

    # 3. Verificación Semántica y Temporal
    adjacency = defaultdict(set)
    edge_similarities: Dict[Tuple[str, str], float] = {}
    used_method = "minhash-tfidf-fallback"

    for k1, k2 in candidate_pairs:
        t1 = msg_map[k1]["text"]
        t2 = msg_map[k2]["text"]
        dt = abs(msg_map[k1]["timestamp"] - msg_map[k2]["timestamp"])

        # Restricción temporal: ventana Delta_t < 15 min
        if dt > time_window_seconds:
            continue

        sim, method = compute_semantic_similarity(t1, t2, model_name=model_name)
        used_method = method

        # Aceptamos si supera el umbral semántico (>0.85) o el umbral Jaccard
        if sim >= semantic_threshold or (k1 in minhashes and k2 in minhashes and minhashes[k1].jaccard(minhashes[k2]) >= jaccard_threshold):
            adjacency[k1].add(k2)
            adjacency[k2].add(k1)
            edge_similarities[(k1, k2)] = sim

    # 4. Extracción de Componentes Conexas (Clústeres)
    visited = set()
    raw_clusters = []
    for key in adjacency:
        if key not in visited:
            cluster_keys = []
            queue = [key]
            visited.add(key)
            while queue:
                curr = queue.pop(0)
                cluster_keys.append(curr)
                for neighbor in adjacency[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            if len(cluster_keys) >= 2:
                raw_clusters.append(cluster_keys)

    # 5. Formateo y Métrica de Evidencia
    formatted_clusters = []
    coordinated_handles_set = set()

    for cl_idx, cl_keys in enumerate(raw_clusters):
        items = [msg_map[k] for k in cl_keys]
        texts = [it["text"] for it in items]
        timestamps = [it["timestamp"] for it in items]
        handles = [it["handle"] for it in items]
        unique_handles = list(set(handles))

        min_time = min(timestamps)
        max_time = max(timestamps)
        delta_time = max_time - min_time

        # Similitud promedio dentro del clúster
        cluster_sims = []
        for i in range(len(cl_keys)):
            for j in range(i + 1, len(cl_keys)):
                pair = tuple(sorted([cl_keys[i], cl_keys[j]]))
                if pair in edge_similarities:
                    cluster_sims.append(edge_similarities[pair])
                else:
                    s, _ = compute_semantic_similarity(items[i]["text"], items[j]["text"], model_name=model_name)
                    cluster_sims.append(s)

        avg_sim = float(sum(cluster_sims) / len(cluster_sims)) if cluster_sims else semantic_threshold

        # Consideramos coordinado si participan 2+ handles distintos en la ventana temporal
        is_coordinated = (len(unique_handles) >= 2 and delta_time <= time_window_seconds) or (
            len(unique_handles) >= 3 and delta_time <= time_window_seconds * 2
        )

        if is_coordinated:
            coordinated_handles_set.update(unique_handles)

        # Seleccionar texto canónico (el más representativo por longitud y centralidad)
        canonical = max(texts, key=lambda t: len(t))

        formatted_clusters.append({
            "cluster_id": cl_idx + 1,
            "canonical_text": canonical,
            "message_count": len(items),
            "unique_accounts_count": len(unique_handles),
            "accounts": sorted(unique_handles),
            "timespan_seconds": round(delta_time, 2),
            "avg_similarity": round(avg_sim, 3),
            "similarity_method": used_method,
            "is_coordinated": is_coordinated,
            "messages": [
                {
                    "id": it["key"],
                    "handle": it["handle"],
                    "text": it["text"],
                    "timestamp": it["timestamp"],
                }
                for it in sorted(items, key=lambda x: x["timestamp"])
            ],
        })

    # Ordenar clústeres por criticidad
    formatted_clusters.sort(
        key=lambda c: (1 if c["is_coordinated"] else 0, c["message_count"]),
        reverse=True,
    )

    total_copypasta_vol = sum(c["message_count"] for c in formatted_clusters if c["is_coordinated"])

    return {
        "total_messages": len(messages),
        "clusters": formatted_clusters,
        "coordinated_accounts": sorted(list(coordinated_handles_set)),
        "copypasta_volume": total_copypasta_vol,
        "clusters_count": len(formatted_clusters),
    }


def detect_paraphrase_campaigns(
    messages: List[Dict[str, Any]],
    similarity_threshold: float = 0.85,
    time_window_seconds: int = 900,
    num_perm: int = 128,
    model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
) -> Dict[str, Any]:
    """
    Especialización para detectar campañas de parafraseo coordinado con umbral semántico >= 0.85
    y ventana temporal Delta_t < 15 min (900s).
    Combina MinHash LSH con sentence-transformers (o fallback si no está instalado).
    """
    return detect_copypasta_clusters(
        messages=messages,
        jaccard_threshold=0.75,
        semantic_threshold=similarity_threshold,
        time_window_seconds=time_window_seconds,
        num_perm=num_perm,
        model_name=model_name,
    )
