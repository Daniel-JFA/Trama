"""
models.py — Modelos ORM normalizados con SQLAlchemy para TRAMA.
Soporta SQLite (desarrollo/local) y PostgreSQL (producción/enterprise con JSONB).
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    ForeignKey,
    Index,
    BigInteger,
    DateTime,
    JSON,
    UniqueConstraint,
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
    accounts = relationship("Account", back_populates="project", cascade="all, delete-orphan")


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


# ─── Sprint 5.5: Seguimiento de Creadores, Crecimiento y Nichos ──────────────

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(64), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String(32), nullable=False, index=True)
    external_id = Column(String(128), nullable=False, index=True)
    handle = Column(String(128), nullable=False, index=True)
    display_name = Column(String(128), nullable=False, default="")
    is_owned = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    project = relationship("ProjectModel", back_populates="accounts")
    snapshots = relationship("AccountSnapshot", back_populates="account", cascade="all, delete-orphan")
    post_snapshots = relationship("PostSnapshot", back_populates="account", cascade="all, delete-orphan")
    credentials = relationship("OAuthCredential", back_populates="account", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("platform", "external_id", "project_id", name="uq_accounts_platform_ext_proj"),
        Index("idx_accounts_proj_platform", "project_id", "platform"),
    )


class AccountSnapshot(Base):
    __tablename__ = "account_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    taken_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    followers = Column(Integer, default=0, nullable=False)
    following = Column(Integer, default=0, nullable=False)
    posts_count = Column(Integer, default=0, nullable=False)
    total_views = Column(BigInteger, default=0, nullable=False)
    engagement_rate = Column(Float, nullable=True)
    raw = Column(JSON, default=dict)

    account = relationship("Account", back_populates="snapshots")

    __table_args__ = (
        Index("idx_acc_snapshots_account_taken", "account_id", "taken_at"),
    )


class PostSnapshot(Base):
    __tablename__ = "post_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    external_post_id = Column(String(128), nullable=False, index=True)
    published_at = Column(DateTime(timezone=True), nullable=False, index=True)
    taken_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    views = Column(BigInteger, default=0, nullable=False)
    likes = Column(Integer, default=0, nullable=False)
    comments = Column(Integer, default=0, nullable=False)
    shares = Column(Integer, default=0, nullable=False)
    text = Column(Text, nullable=True)
    hashtags = Column(JSON, default=list)

    account = relationship("Account", back_populates="post_snapshots")

    __table_args__ = (
        Index("idx_post_snapshots_account_pub", "account_id", "published_at"),
        Index("idx_post_snapshots_acc_ext", "account_id", "external_post_id"),
    )


class OAuthCredential(Base):
    __tablename__ = "oauth_credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(32), nullable=False)
    access_token_enc = Column(Text, nullable=False)
    refresh_token_enc = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    scopes = Column(Text, nullable=True)

    account = relationship("Account", back_populates="credentials")


# Aliases para compatibilidad de nomenclatura
AccountModel = Account
AccountSnapshotModel = AccountSnapshot
PostSnapshotModel = PostSnapshot
OAuthCredentialModel = OAuthCredential

