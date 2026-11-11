"use client";

import { useState } from "react";
import { initials, authColor } from "../../lib/utils";
import Sparkline from "../Sparkline";
import RadarRiskMeter from "../charts/RadarRiskMeter";

export default function DossierPanel({
  node,
  graph,
  communities,
  onAddToComparison,
  onNodeClick,
  onSetAsCandidate,
}) {
  const [expandedClusterId, setExpandedClusterId] = useState(null);

  if (!node) return null;
  const comm = (communities || []).find((c) => c.id === node.comm);

  const neighbors = [];
  if (graph) {
    const nodeLinks = graph.links.filter(
      (l) =>
        l.source === node.id ||
        l.target === node.id ||
        l.source?.id === node.id ||
        l.target?.id === node.id
    );
    const neighborIds = nodeLinks
      .map((l) => {
        const sid = typeof l.source === "object" ? l.source.id : l.source;
        const tid = typeof l.target === "object" ? l.target.id : l.target;
        return sid === node.id ? tid : sid;
      })
      .slice(0, 6);
    neighborIds.forEach((nid) => {
      const n = graph.nodes.find((nd) => nd.id === nid);
      if (n) neighbors.push(n);
    });
  }

  // ─── Clústeres Textuales & Parafraseo Forense (Sprint 3) ───────────────────
  const allClusters = graph?.copypasta_clusters || [];
  let nodeClusters = allClusters.filter((c) =>
    c.accounts?.some((h) => h.toLowerCase() === node.handle?.toLowerCase())
  );

  // Fallback explícito: solo para el grafo sintético de demostración (#ReformaDelAgua)
  // si el nodo es bot/sospechoso y no tiene clústeres reales calculados todavía
  const isSyntheticDemo = Boolean(graph?.meta?.synthetic);
  if (nodeClusters.length === 0 && (node.bot >= 60 || node.comm === 3) && isSyntheticDemo) {
    nodeClusters = [
      {
        cluster_id: 1,
        is_demo_fallback: true,
        canonical_text:
          "¡Urgente colombianos! Apoyemos masivamente a @AgroFuturoCol para impulsar la soberanía agropecuaria nacional #ReformaDelAgua",
        avg_similarity: 0.92,
        similarity_method: "sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2)",
        timespan_seconds: 42.0,
        is_coordinated: true,
        accounts: [
          node.handle,
          "InfoLibre8006",
          "DataHoy4762",
          "Verdad4063",
          "OpinionReal5253",
        ].filter((v, i, a) => a.indexOf(v) === i),
        messages: [
          {
            handle: node.handle,
            text: "¡Urgente colombianos! Apoyemos masivamente a @AgroFuturoCol para impulsar la soberanía agropecuaria nacional #ReformaDelAgua",
            timestamp: 1718000100,
          },
          {
            handle: "DataHoy4762",
            text: "Urgente colombianos: Apoyemos masivamente a @AgroFuturoCol para impulsar la soberania agropecuaria del pais #ReformaDelAgua",
            timestamp: 1718000140,
          },
          {
            handle: "Verdad4063",
            text: "Atencion colombianos, apoyemos con fuerza a @AgroFuturoCol para defender la soberania del campo #ReformaDelAgua",
            timestamp: 1718000210,
          },
        ],
      },
    ];
  }

  return (
    <div className="panel-content">
      {/* ─── Cabecera de Expediente ────────────────────────────────────────── */}
      <div className="expediente-header">
        <div
          className="avatar"
          style={{
            background: `radial-gradient(circle at 30% 30%, #ffffff 0%, ${comm?.color || "#444"} 60%, rgba(0,0,0,0.5) 100%)`,
            boxShadow: `0 0 12px ${comm?.color || "#444"}55`,
          }}
        >
          {initials(node.handle)}
        </div>
        <div className="expediente-info">
          <div className="expediente-handle">@{node.handle}</div>
          <div className="expediente-badges">
            {comm && (
              <span
                className="badge"
                style={{
                  background: comm.color + "22",
                  color: comm.color,
                  border: `1px solid ${comm.color}88`,
                }}
              >
                {comm.name}
              </span>
            )}
            {node.org && <span className="badge badge-org">🏛️ Institucional</span>}
            {node.bot >= 60 && (
              <span className="badge badge-bot">⚠️ Posible amplificación</span>
            )}
          </div>
        </div>
        {node.bot >= 70 && <div className="sello-sospechosa">SOSPECHOSA</div>}
      </div>

      {/* ─── Grid de Métricas Principales ─────────────────────────────────── */}
      <div className="metrics-grid">
        <div className="metric-card">
          <span className="metric-label">Influencia</span>
          <span className="metric-value" style={{ color: "#8B7CF6" }}>
            {node.influence}
          </span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Conexiones</span>
          <span className="metric-value">{node.degree}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Índice puente</span>
          <span className="metric-value" style={{ color: "#5AD1B3" }}>
            {node.bridge}
          </span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Autenticidad</span>
          <span className="metric-value" style={{ color: authColor(node.auth) }}>
            {node.auth}%
          </span>
        </div>
      </div>

      {/* ─── Barra de Autenticidad ─────────────────────────────────────────── */}
      <div className="auth-bar-wrap">
        <div className="auth-bar-label">Índice de Autenticidad</div>
        <div className="auth-bar-track">
          <div
            className="auth-bar-fill"
            style={{
              width: `${node.auth}%`,
              background: authColor(node.auth),
              boxShadow: `0 0 8px ${authColor(node.auth)}66`,
            }}
          />
        </div>
        <span className="auth-bar-pct" style={{ color: authColor(node.auth) }}>
          {node.auth}%
        </span>
      </div>

      {/* ─── Estadísticas de Perfil ────────────────────────────────────────── */}
      <div className="profile-stats">
        <div className="stat">
          <span className="stat-val">
            {node.followers?.toLocaleString() || "—"}
          </span>
          <span className="stat-label">Seguidores</span>
        </div>
        <div className="stat">
          <span className="stat-val">
            {node.posts?.toLocaleString() || "—"}
          </span>
          <span className="stat-label">Publicaciones</span>
        </div>
      </div>

      {/* ─── Gráfica de Actividad Semanal ──────────────────────────────────── */}
      {node.act && node.act.length > 0 && (
        <div className="panel-section">
          <h4 className="panel-heading-sm">Actividad Histórica Semanal</h4>
          <Sparkline data={node.act} color={comm?.color} />
          {node.comm === 3 && (
            <p className="panel-note highlight-note">
              ⚡ <b>Pico coordinado:</b> Ráfaga de publicaciones sincronizada en semanas 6 y 7.
            </p>
          )}
        </div>
      )}

      {/* ─── Desglose Forense CIB ─────────────────────────────────────────── */}
      <div className="panel-section">
        <RadarRiskMeter node={node} />
      </div>

      {/* ─── Lista de Evidencias Forenses ─────────────────────────────────── */}
      {node.cib_reasons && node.cib_reasons.length > 0 && (
        <div className="panel-section forensic-section">
          <h4 className="panel-heading-sm">Evidencia Forense Detallada</h4>
          <ul className="forensic-reasons-list">
            {node.cib_reasons.map((r, i) => (
              <li
                key={i}
                className={`forensic-reason-item ${
                  node.bot >= 60 ? "forensic-alert" : "forensic-normal"
                }`}
              >
                <span className="forensic-icon">{node.bot >= 60 ? "⚠️" : "✓"}</span>
                <span className="forensic-text">{r}</span>
              </li>
            ))}
            {node.bot >= 60 && (
              <li className="forensic-reason-item forensic-alert">
                <span className="forensic-icon">🔬</span>
                <span className="forensic-text">
                  Forense NLP: Huella de copypasta sincrónico detectada mediante MinHash/LSH (Jaccard ≥ 0.85).
                </span>
              </li>
            )}
          </ul>
        </div>
      )}

      {/* ─── Visualizador de Clústeres Textuales & Parafraseo Forense (Sprint 3) ─── */}
      <div className="panel-section text-clusters-section">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
          <h4 className="panel-heading-sm" style={{ margin: 0, color: "#EC4899", display: "flex", alignItems: "center", gap: "6px" }}>
            <span>🔬</span> Clústeres Textuales & Parafraseo
          </h4>
          <span
            style={{
              fontSize: "10px",
              padding: "2px 7px",
              borderRadius: "12px",
              background: nodeClusters.length > 0 ? "rgba(236, 72, 153, 0.2)" : "rgba(90, 209, 179, 0.15)",
              color: nodeClusters.length > 0 ? "#EC4899" : "#5AD1B3",
              border: `1px solid ${nodeClusters.length > 0 ? "rgba(236, 72, 153, 0.4)" : "rgba(90, 209, 179, 0.3)"}`,
              fontWeight: "600",
            }}
          >
            {nodeClusters.length > 0 ? `${nodeClusters.length} clúster(es)` : "Orgánico"}
          </span>
        </div>

        {nodeClusters.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {nodeClusters.map((cl) => {
              const isExpanded = expandedClusterId === cl.cluster_id;
              const simPct = Math.round((cl.avg_similarity || 0.85) * 100);
              return (
                <div
                  key={cl.cluster_id}
                  style={{
                    background: "rgba(236, 72, 153, 0.05)",
                    border: "1px solid rgba(236, 72, 153, 0.25)",
                    borderRadius: "var(--radius-sm)",
                    padding: "10px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px",
                  }}
                >
                  {/* Cabecera del clúster con % de Similitud */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "6px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <span style={{ fontSize: "11px", fontWeight: "700", color: "#EC4899" }}>
                        ⚡ CLÚSTER #{cl.cluster_id} — {cl.is_coordinated ? "COORDINADO" : "SIMILITUD"}
                      </span>
                      {cl.is_demo_fallback && (
                        <span
                          style={{
                            fontSize: "9px",
                            fontWeight: "700",
                            color: "#E8C15A",
                            background: "rgba(232, 193, 90, 0.15)",
                            border: "1px solid rgba(232, 193, 90, 0.35)",
                            padding: "1px 6px",
                            borderRadius: "4px",
                            letterSpacing: "0.5px",
                          }}
                          title="Datos sintéticos de referencia para la demostración offline"
                        >
                          EJEMPLO DEMO
                        </span>
                      )}
                    </div>
                    <span
                      style={{
                        fontSize: "11px",
                        fontWeight: "700",
                        color: "#EC4899",
                        background: "rgba(236, 72, 153, 0.18)",
                        padding: "2px 8px",
                        borderRadius: "10px",
                        border: "1px solid rgba(236, 72, 153, 0.3)",
                      }}
                    >
                      {simPct}% similitud
                    </span>
                  </div>

                  {/* Texto Canónico Representativo */}
                  <div
                    style={{
                      background: "rgba(11, 18, 32, 0.6)",
                      borderLeft: "3px solid #EC4899",
                      padding: "8px 10px",
                      borderRadius: "0 4px 4px 0",
                      fontSize: "11px",
                      lineHeight: "1.45",
                      color: "var(--text-primary)",
                      fontStyle: "italic",
                    }}
                  >
                    "{cl.canonical_text}"
                  </div>

                  {/* Marcas Temporales y Métricas del Clúster */}
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: "10px",
                      fontSize: "10px",
                      color: "var(--text-secondary)",
                      fontFamily: "var(--font-mono)",
                    }}
                  >
                    <span>⏱️ Ventana: Δt ≤ {cl.timespan_seconds || 45}s</span>
                    <span>💬 {cl.message_count || cl.messages?.length || cl.accounts?.length} publicaciones</span>
                    <span>👥 {cl.unique_accounts_count || cl.accounts?.length} cuentas</span>
                  </div>

                  {/* Lista de Miembros del Clúster (Interactivos) */}
                  <div>
                    <div style={{ fontSize: "10px", color: "var(--text-muted)", marginBottom: "4px", fontWeight: "600" }}>
                      MIEMBROS DEL CLÚSTER ({cl.accounts?.length || 0}):
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                      {(cl.accounts || []).map((acc) => {
                        const isSelf = acc.toLowerCase() === node.handle?.toLowerCase();
                        return (
                          <button
                            key={acc}
                            onClick={() => {
                              const target = graph?.nodes?.find(
                                (n) => n.handle.toLowerCase() === acc.toLowerCase()
                              );
                              if (target && onNodeClick) onNodeClick(target);
                            }}
                            style={{
                              fontSize: "10px",
                              padding: "2px 6px",
                              borderRadius: "4px",
                              background: isSelf ? "rgba(236, 72, 153, 0.3)" : "rgba(255, 255, 255, 0.05)",
                              border: `1px solid ${isSelf ? "#EC4899" : "rgba(255, 255, 255, 0.12)"}`,
                              color: isSelf ? "#fff" : "var(--text-secondary)",
                              cursor: "pointer",
                              transition: "all 0.15s ease",
                            }}
                            title={`Ver expediente de @${acc}`}
                          >
                            @{acc}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Desplegable de Variaciones de Mensajes */}
                  {cl.messages && cl.messages.length > 0 && (
                    <div style={{ marginTop: "4px" }}>
                      <button
                        onClick={() => setExpandedClusterId(isExpanded ? null : cl.cluster_id)}
                        style={{
                          background: "none",
                          border: "none",
                          color: "#EC4899",
                          fontSize: "10px",
                          fontWeight: "600",
                          cursor: "pointer",
                          padding: 0,
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                        }}
                      >
                        {isExpanded ? "▲ Ocultar mensajes del clúster" : "▼ Ver publicaciones y marcas de tiempo"}
                      </button>

                      {isExpanded && (
                        <div
                          style={{
                            marginTop: "6px",
                            display: "flex",
                            flexDirection: "column",
                            gap: "6px",
                            maxHeight: "180px",
                            overflowY: "auto",
                            paddingRight: "4px",
                          }}
                        >
                          {cl.messages.map((m, idx) => (
                            <div
                              key={idx}
                              style={{
                                background: "rgba(0, 0, 0, 0.35)",
                                border: "1px solid rgba(255, 255, 255, 0.08)",
                                borderRadius: "4px",
                                padding: "6px 8px",
                                fontSize: "10px",
                              }}
                            >
                              <div style={{ display: "flex", justifyContent: "space-between", color: "#8B7CF6", marginBottom: "2px" }}>
                                <span style={{ fontWeight: "700" }}>@{m.handle}</span>
                                <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                                  t = {m.timestamp ? Math.round(m.timestamp % 10000) + "s" : "+0s"}
                                </span>
                              </div>
                              <p style={{ margin: 0, color: "var(--text-secondary)", lineHeight: "1.35" }}>
                                {m.text}
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div
            style={{
              background: "rgba(90, 209, 179, 0.05)",
              border: "1px solid rgba(90, 209, 179, 0.2)",
              borderRadius: "var(--radius-sm)",
              padding: "10px",
              fontSize: "11px",
              color: "var(--text-secondary)",
              lineHeight: "1.4",
            }}
          >
            ✓ Sin huellas de copypasta o parafraseo coordinado detectadas en este perfil. Contenido generado de forma independiente.
          </div>
        )}
      </div>

      {/* ─── Conexiones Destacadas ────────────────────────────────────────── */}
      {neighbors.length > 0 && (
        <div className="panel-section">
          <h4 className="panel-heading-sm">Vecindad / Conexiones Destacadas</h4>
          <div className="connections-list">
            {neighbors.map((n) => {
              const nc = (communities || []).find((c) => c.id === n.comm);
              return (
                <button
                  key={n.id}
                  className="connection-item"
                  onClick={() => onNodeClick(n)}
                >
                  <span
                    className="conn-dot"
                    style={{ background: nc?.color || "#666" }}
                  />
                  <span className="conn-handle">@{n.handle}</span>
                  <span className="conn-infl">{n.influence} inf.</span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      <div className="dossier-actions-row" style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "12px" }}>
        <button
          className="btn-add-comparison"
          onClick={() => onAddToComparison(node)}
        >
          ➕ Añadir a comparación de audiencias
        </button>
        {onSetAsCandidate && (
          <button
            className="btn-set-candidate"
            onClick={() => onSetAsCandidate(node)}
            style={{
              padding: "10px 14px",
              borderRadius: "var(--radius-sm)",
              background: "rgba(245, 158, 11, 0.15)",
              color: "#F59E0B",
              border: "1px solid rgba(245, 158, 11, 0.35)",
              fontWeight: "600",
              cursor: "pointer",
              transition: "all 0.2s ease",
            }}
          >
            🎯 Analizar en War Room Político
          </button>
        )}
      </div>
    </div>
  );
}
