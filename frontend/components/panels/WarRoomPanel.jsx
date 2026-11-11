"use client";

import { useState, useEffect, useCallback } from "react";
import { initials, authColor } from "../../lib/utils";

export default function WarRoomPanel({
  graph,
  communities,
  candidate,
  onSelectCandidate,
  onNodeClick,
  onHighlightPath,
}) {
  const [candidatesList, setCandidatesList] = useState([]);
  const [auditData, setAuditData] = useState(null);
  const [brokers, setBrokers] = useState([]);
  const [expansionPaths, setExpansionPaths] = useState([]);
  const [targetCommunity, setTargetCommunity] = useState(null);
  const [loadingAudit, setLoadingAudit] = useState(false);
  const [activeTab, setActiveTab] = useState("diagnostico"); // "diagnostico" | "aliados" | "rutas" | "escudo" | "polarizacion"
  const [rwcData, setRwcData] = useState(null);
  const [loadingRwc, setLoadingRwc] = useState(false);
  const [rwcRivalComm, setRwcRivalComm] = useState(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const loadRwc = useCallback(async (c1, c2) => {
    if (c1 === undefined || c1 === null || c2 === undefined || c2 === null) return;
    setLoadingRwc(true);
    try {
      const res = await fetch(`${apiUrl}/api/political/rwc?comm1=${c1}&comm2=${c2}&walks=300`);
      if (res.ok) {
        const data = await res.json();
        setRwcData(data);
      }
    } catch (err) {
      console.error("Error al cargar RWC:", err);
    } finally {
      setLoadingRwc(false);
    }
  }, [apiUrl]);

  // Cargar lista de líderes potenciales para el selector
  useEffect(() => {
    async function loadCandidates() {
      try {
        const res = await fetch(`${apiUrl}/api/political/candidates?top_per_comm=3`);
        if (res.ok) {
          const data = await res.json();
          setCandidatesList(data);
          // Si no hay candidato seleccionado, seleccionar el primero por defecto
          if (!candidate && data.length > 0) {
            onSelectCandidate(data[0]);
          }
        }
      } catch (err) {
        console.warn("No se pudieron cargar candidatos de la API:", err);
      }
    }
    loadCandidates();
  }, [apiUrl, candidate, onSelectCandidate]);

  // Cargar auditoría completa del candidato seleccionado
  const loadAudit = useCallback(async (candId) => {
    if (candId === undefined || candId === null) return;
    setLoadingAudit(true);
    try {
      const res = await fetch(`${apiUrl}/api/political/audit?candidate_id=${candId}`);
      if (res.ok) {
        const data = await res.json();
        setAuditData(data);
      }
    } catch (err) {
      console.error("Error al cargar auditoría del candidato:", err);
    } finally {
      setLoadingAudit(false);
    }
  }, [apiUrl]);

  // Cargar brokers / aliados puente
  const loadBrokers = useCallback(async (candId, targetComm) => {
    if (candId === undefined || candId === null) return;
    try {
      let url = `${apiUrl}/api/political/brokers?candidate_id=${candId}&limit=6`;
      if (targetComm !== null && targetComm !== undefined) {
        url += `&target_comm=${targetComm}`;
      }
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setBrokers(data);
      }
    } catch (err) {
      console.error("Error al cargar brokers:", err);
    }
  }, [apiUrl]);

  // Cargar rutas de expansión
  const loadPaths = useCallback(async (candId, targetComm) => {
    if (candId === undefined || candId === null || targetComm === null || targetComm === undefined) return;
    try {
      const res = await fetch(`${apiUrl}/api/political/expansion-paths?candidate_id=${candId}&target_comm=${targetComm}&max_paths=3`);
      if (res.ok) {
        const data = await res.json();
        setExpansionPaths(data);
      }
    } catch (err) {
      console.error("Error al cargar rutas de expansión:", err);
    }
  }, [apiUrl]);

  // Efecto cuando cambia el candidato seleccionado
  useEffect(() => {
    if (candidate?.id !== undefined) {
      loadAudit(candidate.id);
      loadBrokers(candidate.id, targetCommunity);
      if (targetCommunity !== null) {
        loadPaths(candidate.id, targetCommunity);
      }
    }
  }, [candidate, targetCommunity, loadAudit, loadBrokers, loadPaths]);

  useEffect(() => {
    if (candidate && communities && communities.length > 1) {
      const myComm = candidate.comm_id ?? candidate.comm ?? 0;
      const other = communities.find((c) => c.id !== myComm);
      if (other && rwcRivalComm === null) {
        setRwcRivalComm(other.id);
        loadRwc(myComm, other.id);
      } else if (rwcRivalComm !== null) {
        loadRwc(myComm, rwcRivalComm);
      }
    }
  }, [candidate, communities, rwcRivalComm, loadRwc]);

  // Manejar cambio de candidato en el select
  const handleCandidateChange = (e) => {
    const selectedId = parseInt(e.target.value, 10);
    const found = candidatesList.find((c) => c.id === selectedId);
    if (found) {
      onSelectCandidate(found);
    } else if (graph) {
      const node = graph.nodes.find((n) => n.id === selectedId);
      if (node) onSelectCandidate(node);
    }
  };

  const candComm = communities?.find((c) => c.id === (candidate?.comm_id ?? candidate?.comm));
  const eci = auditData?.echo_chamber;
  const shield = auditData?.dirty_war_shield;

  return (
    <div className="panel-content war-room-panel">
      {/* ─── Encabezado War Room & Selector de Candidato ───────────────────── */}
      <div className="war-room-header">
        <div className="war-room-title-row">
          <span className="war-room-badge">WAR ROOM DE CAMPAÑA</span>
          <span className="war-room-live-dot" />
        </div>
        <p className="war-room-subtitle">
          Inteligencia de posicionamiento, expansión electoral y blindaje forense.
        </p>

        <div className="candidate-selector-group">
          <label htmlFor="cand-select" className="candidate-select-label">
            Perfil Analizado:
          </label>
          <select
            id="cand-select"
            className="candidate-select"
            value={candidate?.id ?? ""}
            onChange={handleCandidateChange}
          >
            {candidatesList.map((c) => (
              <option key={c.id} value={c.id}>
                @{c.handle} ({c.comm_name || `Comunidad ${c.comm_id}`})
              </option>
            ))}
            {candidate && !candidatesList.some((c) => c.id === candidate.id) && (
              <option value={candidate.id}>
                @{candidate.handle} (Personalizado)
              </option>
            )}
          </select>
        </div>
      </div>

      {/* ─── Ficha Resumen del Candidato ───────────────────────────────────── */}
      {candidate && (
        <div className="candidate-card">
          <div
            className="avatar candidate-avatar"
            style={{
              background: `radial-gradient(circle at 30% 30%, #ffffff 0%, ${candComm?.color || "#8B7CF6"} 60%, rgba(0,0,0,0.5) 100%)`,
              boxShadow: `0 0 16px ${candComm?.color || "#8B7CF6"}66`,
            }}
          >
            {initials(candidate.handle)}
          </div>
          <div className="candidate-info">
            <div className="candidate-handle-row">
              <span className="candidate-handle">@{candidate.handle}</span>
              {candComm && (
                <span
                  className="badge"
                  style={{
                    background: candComm.color + "22",
                    color: candComm.color,
                    border: `1px solid ${candComm.color}44`,
                  }}
                >
                  {candComm.name}
                </span>
              )}
            </div>
            <div className="candidate-quick-metrics">
              <div className="quick-metric">
                <span className="metric-label">Influencia</span>
                <span className="metric-val">{candidate.influence ?? 0}/100</span>
              </div>
              <div className="quick-metric">
                <span className="metric-label">Puente</span>
                <span className="metric-val">{candidate.bridge ?? 0}/100</span>
              </div>
              <div className="quick-metric">
                <span className="metric-label">Autenticidad</span>
                <span
                  className="metric-val"
                  style={{ color: authColor(100 - (candidate.bot_score ?? candidate.bot ?? 0)) }}
                >
                  {100 - (candidate.bot_score ?? candidate.bot ?? 0)}%
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ─── Sub-Pestañas del War Room ──────────────────────────────────────── */}
      <div className="war-room-subtabs">
        <button
          className={`subtab-btn ${activeTab === "diagnostico" ? "subtab-active" : ""}`}
          onClick={() => setActiveTab("diagnostico")}
        >
          Diagnóstico & ECI
        </button>
        <button
          className={`subtab-btn ${activeTab === "aliados" ? "subtab-active" : ""}`}
          onClick={() => setActiveTab("aliados")}
        >
          Aliados Puente ({brokers.length})
        </button>
        <button
          className={`subtab-btn ${activeTab === "rutas" ? "subtab-active" : ""}`}
          onClick={() => setActiveTab("rutas")}
        >
          Rutas de Expansión
        </button>
        <button
          className={`subtab-btn ${activeTab === "escudo" ? "subtab-active" : ""}`}
          onClick={() => setActiveTab("escudo")}
        >
          Escudo Anti-Guerra
        </button>
        <button
          className={`subtab-btn ${activeTab === "polarizacion" ? "subtab-active" : ""}`}
          onClick={() => setActiveTab("polarizacion")}
        >
          Polarización RWC
        </button>
      </div>

      {loadingAudit && (
        <div className="war-room-loading">
          <div className="loading-spinner-sm" />
          <span>Calculando métricas de campaña...</span>
        </div>
      )}

      {!loadingAudit && (
        <>
          {/* ─── PESTAÑA 1: DIAGNÓSTICO & ECHO CHAMBER INDEX ────────────────── */}
          {activeTab === "diagnostico" && eci && (
            <div className="war-room-section animate-fade-in">
              <div className="eci-container">
                <div className="eci-header-row">
                  <span className="eci-title">Echo Chamber Index (ECI)</span>
                  <span
                    className={`eci-badge ${
                      eci.score >= 70
                        ? "eci-danger"
                        : eci.score >= 45
                        ? "eci-warning"
                        : "eci-success"
                    }`}
                  >
                    {eci.score}%
                  </span>
                </div>

                {/* Barra de progreso de la cámara de eco */}
                <div className="eci-bar-track">
                  <div
                    className="eci-bar-fill"
                    style={{
                      width: `${eci.score}%`,
                      background:
                        eci.score >= 70
                          ? "linear-gradient(90deg, #E060B8, #EF4444)"
                          : eci.score >= 45
                          ? "linear-gradient(90deg, #E8C15A, #F59E0B)"
                          : "linear-gradient(90deg, #5AD1B3, #10B981)",
                    }}
                  />
                </div>

                <div className="eci-status-label">{eci.level}</div>
                <p className="eci-interpretation">{eci.interpretation}</p>
              </div>

              {/* Desglose de alcance comunitario */}
              <div className="section-block">
                <h4 className="section-title">Distribución de tu Audiencia</h4>
                <div className="reach-list">
                  {auditData?.community_reach?.map((cr) => (
                    <div key={cr.comm_id} className="reach-item">
                      <div className="reach-item-header">
                        <span className="reach-comm-name">
                          {cr.is_home ? "★ " : ""}
                          {cr.comm_name}
                        </span>
                        <span className="reach-comm-pct">{cr.percentage}%</span>
                      </div>
                      <div className="reach-bar-track">
                        <div
                          className="reach-bar-fill"
                          style={{
                            width: `${cr.percentage}%`,
                            background:
                              communities?.find((c) => c.id === cr.comm_id)?.color || "#888",
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Plan de Acción Semanal */}
              <div className="section-block">
                <h4 className="section-title">🎯 Acciones de Campaña de la Semana</h4>
                <div className="tactical-actions-list">
                  {auditData?.tactical_actions?.map((act, idx) => (
                    <div key={idx} className="tactical-action-card">
                      <div className="action-header">
                        <span
                          className={`priority-pill ${
                            act.priority === "Alta" ? "priority-high" : "priority-med"
                          }`}
                        >
                          {act.priority}
                        </span>
                        <span className="action-cat">{act.category}</span>
                      </div>
                      <p className="action-desc">{act.action}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ─── PESTAÑA 2: ALIADOS PUENTE (BROKERS) ───────────────────────── */}
          {activeTab === "aliados" && (
            <div className="war-room-section animate-fade-in">
              <div className="target-comm-filter">
                <label className="filter-label">Filtrar por comunidad a penetrar:</label>
                <div className="filter-chips">
                  <button
                    className={`filter-chip ${targetCommunity === null ? "filter-chip-active" : ""}`}
                    onClick={() => setTargetCommunity(null)}
                  >
                    Todas
                  </button>
                  {communities
                    ?.filter((c) => c.id !== (candidate?.comm_id ?? candidate?.comm))
                    .map((c) => (
                      <button
                        key={c.id}
                        className={`filter-chip ${targetCommunity === c.id ? "filter-chip-active" : ""}`}
                        style={{
                          borderColor: targetCommunity === c.id ? c.color : "rgba(255,255,255,0.1)",
                          color: targetCommunity === c.id ? c.color : "inherit",
                        }}
                        onClick={() => setTargetCommunity(c.id)}
                      >
                        {c.name}
                      </button>
                    ))}
                </div>
              </div>

              <div className="brokers-list">
                {brokers.length === 0 && (
                  <p className="empty-hint">No se encontraron nodos puente para este filtro.</p>
                )}
                {brokers.map((b) => (
                  <div key={b.id} className="broker-card">
                    <div className="broker-header">
                      <div
                        className="avatar avatar-sm"
                        style={{
                          background: communities?.find((c) => c.id === b.comm_id)?.color || "#888",
                        }}
                      >
                        {initials(b.handle)}
                      </div>
                      <div className="broker-meta">
                        <span className="broker-handle">@{b.handle}</span>
                        <span className="broker-comm-pill">{b.comm_name}</span>
                      </div>
                      <div className="alliance-score-badge" title="Valor estratégico de alianza">
                        <span className="score-num">{b.alliance_score}</span>
                        <span className="score-label">Aliado</span>
                      </div>
                    </div>
                    <p className="broker-rationale">{b.rationale}</p>
                    <div className="broker-actions">
                      <button
                        className="btn-secondary btn-sm"
                        onClick={() => {
                          const fullNode = graph?.nodes?.find((n) => n.id === b.id);
                          if (fullNode && onNodeClick) onNodeClick(fullNode);
                        }}
                      >
                        🔍 Ver en Grafo
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ─── PESTAÑA 3: RUTAS DE EXPANSIÓN ELECTORAL ────────────────────── */}
          {activeTab === "rutas" && (
            <div className="war-room-section animate-fade-in">
              <div className="target-comm-filter">
                <label className="filter-label">Selecciona la comunidad objetivo a conquistar:</label>
                <div className="filter-chips">
                  {communities
                    ?.filter((c) => c.id !== (candidate?.comm_id ?? candidate?.comm))
                    .map((c) => (
                      <button
                        key={c.id}
                        className={`filter-chip ${(targetCommunity ?? 1) === c.id ? "filter-chip-active" : ""}`}
                        style={{
                          borderColor: (targetCommunity ?? 1) === c.id ? c.color : "rgba(255,255,255,0.1)",
                          color: (targetCommunity ?? 1) === c.id ? c.color : "inherit",
                        }}
                        onClick={() => {
                          setTargetCommunity(c.id);
                          loadPaths(candidate.id, c.id);
                        }}
                      >
                        {c.name}
                      </button>
                    ))}
                </div>
              </div>

              <div className="expansion-paths-list">
                {expansionPaths.length === 0 && (
                  <p className="empty-hint">
                    Calculando rutas óptimas de menor resistencia hacia esta comunidad...
                  </p>
                )}
                {expansionPaths.map((p, idx) => (
                  <div key={idx} className="path-card">
                    <div className="path-header">
                      <div className="path-target-title">
                        <span>Ruta hacia </span>
                        <strong>@{p.target_handle}</strong>
                      </div>
                      <span className="viability-badge">
                        Viabilidad {p.viability_score}%
                      </span>
                    </div>
                    <p className="path-summary">{p.strategic_summary}</p>

                    {/* Pasos de la ruta */}
                    <div className="path-steps">
                      {p.steps?.map((st, sidx) => (
                        <div key={sidx} className="step-row">
                          <div className="step-dot" />
                          <div className="step-content">
                            <span className="step-role">{st.role}:</span>
                            <span
                              className="step-handle-link"
                              onClick={() => {
                                const fullNode = graph?.nodes?.find((n) => n.id === st.id);
                                if (fullNode && onNodeClick) onNodeClick(fullNode);
                              }}
                            >
                              @{st.handle}
                            </span>
                            <span className="step-comm-name">({st.comm_name})</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ─── PESTAÑA 4: ESCUDO ANTI-GUERRA SUCIA ────────────────────────── */}
          {activeTab === "escudo" && shield && (
            <div className="war-room-section animate-fade-in">
              <div
                className={`threat-banner ${
                  shield.threat_level.startsWith("Alto")
                    ? "threat-high"
                    : shield.threat_level.startsWith("Medio")
                    ? "threat-med"
                    : "threat-low"
                }`}
              >
                <div className="threat-header-row">
                  <span className="threat-title">Nivel de Hostigamiento:</span>
                  <span className="threat-pill">{shield.threat_level}</span>
                </div>
                <p className="threat-message">{shield.threat_message}</p>
              </div>

              <div className="shield-metrics-grid">
                <div className="shield-metric-card">
                  <span className="shield-metric-val">{shield.hostile_accounts_count}</span>
                  <span className="shield-metric-label">Cuentas Inauténticas</span>
                </div>
                <div className="shield-metric-card">
                  <span className="shield-metric-val">{shield.hostile_percentage}%</span>
                  <span className="shield-metric-label">Exposición en tu Red</span>
                </div>
              </div>

              <div className="section-block">
                <h4 className="section-title">Cuentas Sospechosas en tu Órbita</h4>
                {shield.flagged_accounts?.length === 0 && (
                  <p className="empty-hint">No hay cuentas bot hostiles detectadas en tus conexiones inmediatas.</p>
                )}
                <div className="flagged-accounts-list">
                  {shield.flagged_accounts?.map((acc) => (
                    <div key={acc.id} className="flagged-card">
                      <div className="flagged-header">
                        <span className="flagged-handle">@{acc.handle}</span>
                        <span className="flagged-score">Bot Score {acc.bot_score}/100</span>
                      </div>
                      <div className="flagged-reasons">
                        {acc.reasons?.map((r, ri) => (
                          <span key={ri} className="reason-tag">
                            {r}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="defense-protocol-card">
                <h4 className="defense-title">🛡️ Protocolo de Contención de Campaña</h4>
                <ul className="defense-list">
                  <li><strong>No responder ni citar:</strong> Dar réplica a bots premia algorítmicamente la campaña opositora en X e Instagram.</li>
                  <li><strong>Preservación de evidencia:</strong> Utiliza el botón <em>📄 Informe</em> de TRAMA para generar la auditoría forense exportable.</li>
                  <li><strong>Contranarrativa orgánica:</strong> Moviliza a los <em>Aliados Puente</em> detectados para posicionar los temas de agenda pública con tracción ciudadana real.</li>
                </ul>
              </div>
            </div>
          )}

          {/* ─── Pestaña 5: Polarización RWC (Sprint 3) ────────────────────── */}
          {activeTab === "polarizacion" && (
            <div className="war-room-tab-content polarizacion-tab">
              <div className="section-block">
                <h4 className="section-title">Controversia & Cámaras de Eco (RWC)</h4>
                <p className="section-desc" style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "12px" }}>
                  Algoritmo <em>Random Walk Controversy</em> de Garimella et al. Cuantifica el aislamiento
                  ideológico simulando cientos de paseos aleatorios entre tu comunidad y facciones rivales.
                </p>

                <div className="rwc-comm-selector" style={{ marginBottom: "14px", display: "flex", alignItems: "center", gap: "8px" }}>
                  <label style={{ fontSize: "12px", color: "var(--text-muted)" }}>Enfrentar con:</label>
                  <select
                    className="candidate-select"
                    style={{ flex: 1, padding: "6px 10px", fontSize: "12px" }}
                    value={rwcRivalComm ?? ""}
                    onChange={(e) => {
                      const val = parseInt(e.target.value, 10);
                      setRwcRivalComm(val);
                      const myComm = candidate.comm_id ?? candidate.comm ?? 0;
                      loadRwc(myComm, val);
                    }}
                  >
                    {communities?.filter((c) => c.id !== (candidate.comm_id ?? candidate.comm)).map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>

                {loadingRwc && (
                  <div className="war-room-loading">
                    <div className="loading-spinner-sm" />
                    <span>Calculando controversia RWC...</span>
                  </div>
                )}

                {rwcData && !loadingRwc && (
                  <div className="rwc-results-card" style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "var(--radius-sm)", padding: "14px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                      <span style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-primary)" }}>Índice de Polarización RWC</span>
                      <span style={{ fontSize: "20px", fontWeight: "700", color: rwcData.rwc_score >= 70 ? "#EC4899" : rwcData.rwc_score >= 40 ? "#F59E0B" : "#10B981" }}>
                        {rwcData.rwc_score}%
                      </span>
                    </div>

                    <div style={{ width: "100%", height: "8px", background: "rgba(255,255,255,0.08)", borderRadius: "4px", overflow: "hidden", marginBottom: "12px" }}>
                      <div
                        style={{
                          width: `${Math.min(100, rwcData.rwc_score)}%`,
                          height: "100%",
                          background: rwcData.rwc_score >= 70 ? "#EC4899" : rwcData.rwc_score >= 40 ? "#F59E0B" : "#10B981",
                          borderRadius: "4px",
                          transition: "width 0.4s ease",
                        }}
                      />
                    </div>

                    <div style={{ padding: "8px 12px", background: "rgba(0,0,0,0.25)", borderRadius: "var(--radius-sm)", borderLeft: `3px solid ${rwcData.rwc_score >= 70 ? "#EC4899" : "#F59E0B"}`, marginBottom: "14px" }}>
                      <span style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: "1.4" }}>
                        {rwcData.diagnosis}
                      </span>
                    </div>

                    <div className="shield-metrics-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                      <div className="shield-metric-card" style={{ padding: "8px" }}>
                        <span className="shield-metric-val" style={{ fontSize: "16px" }}>{rwcData.conductance}</span>
                        <span className="shield-metric-label" style={{ fontSize: "10px" }}>Conductancia Frontera</span>
                      </div>
                      <div className="shield-metric-card" style={{ padding: "8px" }}>
                        <span className="shield-metric-val" style={{ fontSize: "16px" }}>{rwcData.cut_edges_count}</span>
                        <span className="shield-metric-label" style={{ fontSize: "10px" }}>Aristas de Cruce</span>
                      </div>
                      <div className="shield-metric-card" style={{ padding: "8px" }}>
                        <span className="shield-metric-val" style={{ fontSize: "16px" }}>{(rwcData.p_comm1_stay * 100).toFixed(1)}%</span>
                        <span className="shield-metric-label" style={{ fontSize: "10px" }}>Retención Tu Burbuja</span>
                      </div>
                      <div className="shield-metric-card" style={{ padding: "8px" }}>
                        <span className="shield-metric-val" style={{ fontSize: "16px" }}>{(rwcData.p_comm2_stay * 100).toFixed(1)}%</span>
                        <span className="shield-metric-label" style={{ fontSize: "10px" }}>Retención Rival</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
