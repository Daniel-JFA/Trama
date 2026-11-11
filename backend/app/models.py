"""
models.py — Modelos ORM normalizados con SQLAlchemy para TRAMA.
Soporta SQLite (desarrollo/local) y PostgreSQL (producción/enterprise con JSONB).
"""

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class ProjectModel(Base):
    __tablename__ = "projects"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    topic = Column(String(128), nullable=False, index=True)
    description = Column(Text, default="")
    created_at = Column(String(64), nullable=False)
    updated_at = Column(String(64), nullable=False, index=True)
    node_count = Column(Integer, default=0)
    link_count = Column(Integer, default=0)
    community_count = Column(Integer, default=0)
    graph_json = Column(Text, nullable=False)

    nodes = relationship("NodeModel", back_populates="project", cascade="all, delete-orphan")
    edges = relationship("EdgeModel", back_populates="project", cascade="all, delete-orphan")
    communities = relationship("CommunityModel", back_populates="project", cascade="all, delete-orphan")
    cib_evidence = relationship("CIBEvidenceModel", back_populates="project", cascade="all, delete-orphan")


class NodeModel(Base):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(64), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    node_id = Column(Integer, nullable=False, index=True)
    handle = Column(String(128), nullable=False, index=True)
    comm = Column(Integer, nullable=False, index=True)
    org = Column(Boolean, default=False)
    bot = Column(Integer, default=0, index=True)
    auth = Column(Integer, default=100)
    followers = Column(Integer, default=0)
    posts = Column(Integer, default=0)
    degree = Column(Integer, default=0)
    influence = Column(Integer, default=0, index=True)
    bridge = Column(Integer, default=0, index=True)
    act_json = Column(Text, default="[]")

    project = relationship("ProjectModel", back_populates="nodes")

    __table_args__ = (
        Index("idx_nodes_project_handle", "project_id", "handle"),
        Index("idx_nodes_project_influence", "project_id", "influence"),
    )


class EdgeModel(Base):
    __tablename__ = "edges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(64), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(Integer, nullable=False, index=True)
    target = Column(Integer, nullable=False, index=True)
    weight = Column(Float, default=1.0)

    project = relationship("ProjectModel", back_populates="edges")

    __table_args__ = (
        Index("idx_edges_project_st", "project_id", "source", "target"),
    )


class CommunityModel(Base):
    __tablename__ = "communities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(64), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    comm_id = Column(Integer, nullable=False)
    name = Column(String(128), nullable=False)
    color = Column(String(32), nullable=False)

    project = relationship("ProjectModel", back_populates="communities")


class CIBEvidenceModel(Base):
    __tablename__ = "cib_evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(64), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    node_id = Column(Integer, nullable=False, index=True)
    rule_triggered = Column(String(64), nullable=False, index=True)
    score = Column(Integer, nullable=False)
    details_json = Column(Text, default="{}")

    project = relationship("ProjectModel", back_populates="cib_evidence")


class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(String(64), primary_key=True)
    project_id = Column(String(64), nullable=True, index=True)
    status = Column(String(32), default="pending", index=True)
    progress = Column(Integer, default=0)
    stage = Column(String(128), default="Iniciando")
    message = Column(Text, default="")
    result_json = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(String(64), nullable=False)
    updated_at = Column(String(64), nullable=False)


class LeadModel(Base):
    __tablename__ = "leads"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    email = Column(String(128), nullable=False, index=True)
    company = Column(String(128), default="")
    role = Column(String(128), default="")
    use_case = Column(Text, default="")
    created_at = Column(String(64), nullable=False)


class SettingModel(Base):
    __tablename__ = "settings"

    key = Column(String(64), primary_key=True)
    value = Column(Text, nullable=False)


# ─── Bloque D: Modelo Canónico de Eventos de Interacción ─────────────────────

class InteractionEventModel(Base):
    __tablename__ = "interaction_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(64), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    actor = Column(String(128), nullable=False, index=True)
    target = Column(String(128), nullable=True, index=True)
    timestamp = Column(String(64), nullable=False, index=True)
    action_type = Column(String(32), nullable=False, index=True)
    platform = Column(String(32), nullable=False, index=True)
    content = Column(Text, default="")
    extra_json = Column(Text, default="{}")

    __table_args__ = (
        Index("idx_events_proj_ts", "project_id", "timestamp"),
        Index("idx_events_actor_target", "actor", "target"),
        Index("idx_events_platform_action", "platform", "action_type"),
    )

