"use client";

import CommunityDonutChart from "../charts/CommunityDonutChart";
import AuthenticityHistogram from "../charts/AuthenticityHistogram";
import NetworkMacroTimeline from "../charts/NetworkMacroTimeline";

export default function SummaryPanel({
  graph,
  communities,
  activeFilter,
  onSelectFilter,
  onNodeClick,
  currentWeek,
  onSelectWeek,
}) {
  if (!graph) return null;
  const nodes = graph.nodes || [];
  const links = graph.links || [];
  const suspicious = nodes.filter((n) => n.bot >= 60).length;
  const pctSusp = nodes.length > 0 ? Math.round((suspicious / nodes.length) * 100) : 0;

  const topInfluence = [...nodes].sort((a, b) => (b.influence || 0) - (a.influence || 0)).slice(0, 8);
  const topBridge = [...nodes].sort((a, b) => (b.bridge || 0) - (a.bridge || 0)).slice(0, 5);

  const commMap = {};
  (communities || []).forEach((c) => {
    commMap[c.id] = c;
  });

  return (
    <div className="panel-content">
      {/* ─── Macro KPI Grid ────────────────────────────────────────────────── */}
      <div className="panel-section" style={{ marginTop: 0 }}>
        <h3 className="panel-heading">Métricas de la Red</h3>
        <div className="kpi-grid">
          <div className="kpi-card">
            <span className="kpi-value">{nodes.length}</span>
            <span className="kpi-label">Perfiles</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-value">
              {graph.meta?.interactions?.toLocaleString() || links.length}
            </span>
            <span className="kpi-label">Interacciones</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-value">{communities?.length || 0}</span>
            <span className="kpi-label">Comunidades</span>
          </div>
          <div
            className="kpi-card"
            style={{
              borderColor: pctSusp > 20 ? "rgba(224, 96, 184, 0.4)" : undefined,
              background: pctSusp > 20 ? "rgba(224, 96, 184, 0.08)" : undefined,
            }}
          >
            <span
              className="kpi-value"
              style={{ color: pctSusp > 20 ? "#E060B8" : undefined }}
            >
              {pctSusp}%
            </span>
            <span className="kpi-label">Sospechosas</span>
          </div>
        </div>
      </div>

      {/* ─── Timeline Global de Actividad ──────────────────────────────────── */}
      <div className="panel-section">
        <NetworkMacroTimeline
          graph={graph}
          currentWeek={currentWeek}
          onSelectWeek={onSelectWeek}
        />
      </div>

      {/* ─── Distribución de Comunidades (Donut Chart) ────────────────────── */}
      <div className="panel-section">
        <h3 className="panel-heading">Distribución de Comunidades</h3>
        <CommunityDonutChart
          graph={graph}
          communities={communities}
          activeFilter={activeFilter}
          onSelectCommunity={onSelectFilter}
        />
      </div>

      {/* ─── Histograma de Autenticidad ────────────────────────────────────── */}
      <div className="panel-section">
        <AuthenticityHistogram
          graph={graph}
          activeFilter={activeFilter}
          onSelectFilter={onSelectFilter}
        />
      </div>

      {/* ─── Top Influyentes ───────────────────────────────────────────────── */}
      <div className="panel-section">
        <h3 className="panel-heading">Top Influyentes (PageRank)</h3>
        <div className="rank-list">
          {topInfluence.map((n, i) => {
            const comm = commMap[n.comm];
            return (
              <button
                key={n.id}
                className="rank-item"
                onClick={() => onNodeClick(n)}
              >
                <span className="rank-pos">{i + 1}</span>
                <span
                  className="rank-dot"
                  style={{ background: comm?.color || "#666" }}
                />
                <span className="rank-handle">@{n.handle}</span>
                <div className="rank-bar-wrap">
                  <div
                    className="rank-bar"
                    style={{
                      width: `${n.influence}%`,
                      background: comm?.color || "#666",
                    }}
                  />
                </div>
                <span className="rank-val">{n.influence}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ─── Cuentas Puente ────────────────────────────────────────────────── */}
      <div className="panel-section">
        <h3 className="panel-heading">Cuentas Puente (Intermediación)</h3>
        <p className="panel-note">
          Nodos estratégicos por donde fluyen las conversaciones inter-comunitarias.
        </p>
        <div className="rank-list">
          {topBridge.map((n) => {
            const comm = commMap[n.comm];
            return (
              <button
                key={n.id}
                className="rank-item"
                onClick={() => onNodeClick(n)}
              >
                <span
                  className="rank-dot"
                  style={{ background: comm?.color || "#666" }}
                />
                <span className="rank-handle">@{n.handle}</span>
                <span className="rank-badge bridge-badge">puente</span>
                <span className="rank-val" style={{ color: "#5AD1B3" }}>
                  {n.bridge}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ─── Guía de Lectura Visual ────────────────────────────────────────── */}
      <div className="panel-section guide-section">
        <h3 className="panel-heading">Guía Forense Visual</h3>
        <ul className="guide-list">
          <li>
            <span className="guide-dot" style={{ background: "#fff" }} /> Tamaño de nodo = Influencia calculada (PageRank)
          </li>
          <li>
            <span className="guide-dot" style={{ background: "#5AD1B3" }} /> Anillo verde azulado = Cuenta puente estratégica
          </li>
          <li>
            <span className="guide-ring" /> Anillo rosa punteado = Sospecha de amplificación CIB (&ge; 60%)
          </li>
          <li>
            <span className="guide-dot" style={{ background: "rgba(139, 124, 246, 0.4)" }} /> Nube de fondo = Agrupación Louvain
          </li>
        </ul>
      </div>
    </div>
  );
}
