"""
schemas.py — Contratos y esquemas de datos tipados estrictos con Pydantic V2 para TRAMA.
Soporta OpenAPI 3.1 y serialización estricta.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr


# ─── Topología y Grafo ───────────────────────────────────────────────────────
class NodeOut(BaseModel):
    id: int = Field(..., description="ID numérico único del nodo en el grafo")
    handle: str = Field(..., description="Nombre de usuario o handle sin @")
    comm: int = Field(..., description="ID de la comunidad asignada (Leiden)")
    org: bool = Field(False, description="Indica si es una cuenta orgánica auténtica")
    bot: int = Field(..., ge=0, le=100, description="Puntuación de sospecha de bot/CIB (0-100)")
    auth: int = Field(..., ge=0, le=100, description="Índice de autenticidad (100 - bot)")
    act: List[int] = Field(default_factory=list, description="Serie temporal de actividad semanal (12 semanas)")
    followers: int = Field(0, ge=0, description="Cantidad estimada de seguidores")
    posts: int = Field(0, ge=0, description="Cantidad estimada de publicaciones")
    degree: int = Field(0, ge=0, description="Grado de conectividad (aristas incidentes)")
    influence: int = Field(0, ge=0, le=100, description="PageRank normalizado (0-100)")
    bridge: int = Field(0, ge=0, le=100, description="Betweenness centrality normalizado (0-100)")


class LinkOut(BaseModel):
    source: Any = Field(..., description="ID del nodo origen o dict del nodo")
    target: Any = Field(..., description="ID del nodo destino o dict del nodo")


class CommunityOut(BaseModel):
    id: int = Field(..., description="ID numérico de la comunidad")
    name: str = Field(..., description="Nombre legible de la comunidad")
    color: str = Field(..., description="Color hexadecimal representativo")


class GraphMetaOut(BaseModel):
    topic: str = Field(..., description="Tema o hashtag de la conversación analizada")
    weeks: int = Field(0, description="Semanas de seguimiento temporal")
    synthetic: bool = Field(False, description="True si corresponde al dataset demo sintético")
    interactions: int = Field(0, description="Número de interacciones o aristas")


class GraphOut(BaseModel):
    meta: GraphMetaOut
    communities: List[CommunityOut]
    nodes: List[NodeOut]
    links: List[LinkOut]
    coornet_links: Optional[List[Dict[str, Any]]] = None
    coornet_cliques: Optional[List[Dict[str, Any]]] = None
    copypasta_clusters: Optional[List[Dict[str, Any]]] = None


# ─── Proyectos e Investigaciones ─────────────────────────────────────────────
class CreateProjectPayload(BaseModel):
    name: str = Field(..., min_length=2, max_length=120, description="Nombre de la investigación")
    topic: str = Field(..., min_length=2, max_length=100, description="Hashtag o tema principal")
    description: Optional[str] = Field("", max_length=500, description="Descripción opcional")


class ProjectSummaryOut(BaseModel):
    id: str = Field(..., description="UUID o identificador único del proyecto")
    name: str
    topic: str
    description: str
    created_at: str
    updated_at: str
    node_count: int
    link_count: int
    community_count: int


class ProjectDetailOut(ProjectSummaryOut):
    graph: GraphOut


# ─── Tareas Asíncronas y Streaming SSE ───────────────────────────────────────
class AsyncTaskResponse(BaseModel):
    task_id: str = Field(..., description="ID único para seguimiento de la tarea")
    status: str = Field("pending", description="pending | processing | completed | failed")
    message: str = Field("Tarea de procesamiento encolada con éxito")


class TaskProgressEventOut(BaseModel):
    task_id: str
    status: str
    progress: int = Field(..., ge=0, le=100, description="Porcentaje de avance (0-100)")
    stage: str = Field(..., description="Etapa actual del procesamiento")
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ─── Solicitudes Comerciales (Leads) ─────────────────────────────────────────
class CreateLeadPayload(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., max_length=120)
    company: Optional[str] = Field("", max_length=100)
    role: Optional[str] = Field("", max_length=100)
    use_case: Optional[str] = Field("", max_length=300)


class LeadOut(CreateLeadPayload):
    id: str
    created_at: str


# ─── Solapamiento de Vecindades ─────────────────────────────────────────────
class OverlapPairOut(BaseModel):
    a: int
    b: int
    jaccard: int
    common: List[int]


class OverlapResponseOut(BaseModel):
    pairs: List[OverlapPairOut]


# ─── War Room e Inteligencia Política ────────────────────────────────────────
class CandidateOut(BaseModel):
    id: int
    handle: str
    comm_id: int
    comm_name: str
    influence: int
    bridge: int
    followers: int
    bot_score: int


# ─── Sprint 3: Inteligencia Forense NLP, CooRnet y Polarización ─────────────
class MessageItem(BaseModel):
    id: Optional[Any] = None
    handle: str
    text: str
    timestamp: Optional[float] = 0.0


class CopypastaPayload(BaseModel):
    messages: List[MessageItem]
    jaccard_threshold: Optional[float] = 0.80
    semantic_threshold: Optional[float] = 0.85
    time_window_seconds: Optional[int] = 900
    model_name: Optional[str] = "paraphrase-multilingual-MiniLM-L12-v2"


class CopypastaClusterOut(BaseModel):
    cluster_id: int
    canonical_text: str
    message_count: int
    unique_accounts_count: int
    accounts: List[str]
    timespan_seconds: float
    avg_similarity: float
    similarity_method: Optional[str] = None
    is_coordinated: bool
    messages: List[Dict[str, Any]]


class CopypastaResponseOut(BaseModel):
    total_messages: int
    clusters: List[CopypastaClusterOut]
    coordinated_accounts: List[str]
    copypasta_volume: int
    clusters_count: int


class CooRnetEventItem(BaseModel):
    handle: str
    entity_id: str
    timestamp: float


class CooRnetPayload(BaseModel):
    events: List[CooRnetEventItem]
    time_window_seconds: Optional[float] = 45.0
    min_co_shares: Optional[int] = 2
    monte_carlo_iterations: Optional[int] = 100
    alpha: Optional[float] = 0.05
    seed: Optional[int] = None


class CooRnetResponseOut(BaseModel):
    nodes: List[Dict[str, Any]]
    links: List[Dict[str, Any]]
    coordinated_cliques: List[Dict[str, Any]]
    total_pairs_detected: int
    significant_coordinated_pairs: Optional[int] = 0


class RWCResponseOut(BaseModel):
    comm1: Dict[str, Any]
    comm2: Dict[str, Any]
    rwc_score: float
    conductance: float
    cut_edges_count: Optional[int] = 0
    boundary_nodes_count: Optional[int] = 0
    p_comm1_stay: float
    p_comm2_stay: float
    diagnosis: str


# ─── Bloque C: Informes PDF ──────────────────────────────────────────────────

class PdfReportPayload(BaseModel):
    svg: Optional[str] = None

# ─── Bloque D: Modelo Canónico de Eventos de Interacción e Ingesta ──────────

class InteractionEvent(BaseModel):
    id: Optional[str] = None
    project_id: Optional[str] = None
    actor: str
    target: Optional[str] = None
    timestamp: str
    action_type: str
    platform: str
    content: Optional[str] = ""
    extra: Optional[Dict[str, Any]] = None


class BatchInteractionEventsPayload(BaseModel):
    events: List[InteractionEvent]
    project_id: Optional[str] = None


class ColumnarQueryPayload(BaseModel):
    project_id: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    window_minutes: Optional[int] = 15
    limit: Optional[int] = 20


# ─── Sprint 5.5: Seguimiento de Creadores, Crecimiento y Nichos ──────────────

class CreateAccountPayload(BaseModel):
    platform: str = Field(..., description="Plataforma: youtube | instagram | facebook")
    external_id: str = Field(..., description="ID externo de la cuenta o canal")
    handle: Optional[str] = Field(None, description="Handle o nombre de usuario")
    display_name: Optional[str] = Field("", description="Nombre legible")
    is_owned: bool = Field(False, description="True si es una cuenta propia del proyecto")


class AccountOut(BaseModel):
    id: int
    project_id: str
    platform: str
    external_id: str
    handle: str
    display_name: str
    is_owned: bool
    created_at: str


class AccountSnapshotOut(BaseModel):
    id: int
    account_id: int
    taken_at: str
    followers: int
    following: int
    posts_count: int
    total_views: int
    engagement_rate: Optional[float] = None
    raw: Optional[Dict[str, Any]] = None


class GrowthPoint(BaseModel):
    date: str
    followers: int
    delta: int
    growth_pct: float


class GrowthSummary(BaseModel):
    growth_7d: int = 0
    growth_7d_pct: float = 0.0
    growth_30d: int = 0
    growth_30d_pct: float = 0.0
    top_posts: List[Dict[str, Any]] = Field(default_factory=list)


class AccountGrowthResponse(BaseModel):
    account_id: int
    series: List[GrowthPoint]
    summary: GrowthSummary


class DiscoverNichePayload(BaseModel):
    seed_account_id: int = Field(..., description="ID de la cuenta semilla")
    depth: int = Field(1, ge=1, le=2, description="Profundidad de expansión (máx 2)")


class TrendItem(BaseModel):
    topic: str
    volume: int
    acceleration: float
    platform: Optional[str] = None
    community_id: Optional[int] = None


class TrendsResponse(BaseModel):
    trends: List[TrendItem]
    time_window: Dict[str, Any] = Field(default_factory=dict)


class NicheResponse(BaseModel):
    id: str
    seed_account_id: int
    accounts: List[Dict[str, Any]] = Field(default_factory=list)
    tagged_topics: List[Dict[str, Any]] = Field(default_factory=list)
    leaders: List[Dict[str, Any]] = Field(default_factory=list)
    seed_position: Dict[str, Any] = Field(default_factory=dict)


