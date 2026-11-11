"use client";

import { useEffect, useState } from "react";

export default function ReportModal({
  isOpen,
  onClose,
  activeProjectId,
  candidateId,
}) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  const handleDownloadPdf = async () => {
    if (!activeProjectId) return;
    setDownloadingPdf(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      // Intenta capturar el SVG del lienzo de grafo si está presente en el DOM
      const svgEl = document.querySelector("svg");
      const svgString = svgEl ? new XMLSerializer().serializeToString(svgEl) : null;

      const queryParam =
        candidateId !== undefined && candidateId !== null
          ? `?candidate_id=${candidateId}`
          : "";
      const res = await fetch(
        `${apiUrl}/api/projects/${activeProjectId}/report/pdf${queryParam}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ svg: svgString }),
        }
      );

      if (!res.ok) {
        if (res.status === 501) {
          throw new Error("El motor WeasyPrint no está disponible en el servidor.");
        }
        throw new Error(`Error ${res.status} al generar el PDF`);
      }

      const blob = await res.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = `informe-forense-${activeProjectId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      alert("Error al descargar PDF: " + err.message);
    } finally {
      setDownloadingPdf(false);
    }
  };

  useEffect(() => {
    if (isOpen && activeProjectId) {
      setLoading(true);
      setError(null);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const url = candidateId !== undefined && candidateId !== null
        ? `${apiUrl}/api/projects/${activeProjectId}/report?candidate_id=${candidateId}`
        : `${apiUrl}/api/projects/${activeProjectId}/report`;

      fetch(url)
        .then((res) => {
          if (!res.ok) throw new Error("No se pudo obtener el informe ejecutivo");
          return res.json();
        })
        .then((data) => {
          setReport(data);
          setLoading(false);
        })
        .catch((err) => {
          setError(err.message);
          setLoading(false);
        });
    }
  }, [isOpen, activeProjectId]);

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card report-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="report-header-titles">
            <span className="report-badge-top">INTELIGENCIA OSINT</span>
            <h2 className="modal-title">{report?.report_title || "Informe Ejecutivo de Red"}</h2>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="modal-body report-modal-body">
          {loading && <div className="modal-loading">Generando informe forense…</div>}
          {error && <div className="modal-error">{error}</div>}

          {report && !loading && (
            <div className="report-container">
              {/* Resumen Métrico */}
              <div className="report-section">
                <h3 className="report-section-title">1. Resumen Ejecutivo de la Conversación</h3>
                <div className="kpi-grid report-kpi-grid">
                  <div className="kpi-card">
                    <span className="kpi-value">{report.summary.total_profiles}</span>
                    <span className="kpi-label">Perfiles Analizados</span>
                  </div>
                  <div className="kpi-card">
                    <span className="kpi-value">{report.summary.total_interactions}</span>
                    <span className="kpi-label">Interacciones Totales</span>
                  </div>
                  <div className="kpi-card">
                    <span className="kpi-value">{report.summary.total_communities}</span>
                    <span className="kpi-label">Comunidades Detectadas</span>
                  </div>
                  <div className="kpi-card" style={{ borderColor: report.summary.suspicious_percentage > 15 ? "#E060B8" : undefined }}>
                    <span className="kpi-value" style={{ color: report.summary.suspicious_percentage > 15 ? "#E060B8" : undefined }}>
                      {report.summary.suspicious_percentage}%
                    </span>
                    <span className="kpi-label">Nivel de Inautenticidad</span>
                  </div>
                </div>
              </div>

              {/* Estrategia Electoral del Candidato (War Room) */}
              {report.campaign_strategy && (
                <div className="report-section report-campaign-section">
                  <h3 className="report-section-title">
                    🎯 Diagnóstico de Campaña & War Room: @{report.campaign_strategy.candidate.handle}
                  </h3>
                  
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px", marginBottom: "14px" }}>
                    <div style={{ padding: "14px", background: "rgba(245, 158, 11, 0.08)", border: "1px solid rgba(245, 158, 11, 0.3)", borderRadius: "8px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                        <span style={{ fontSize: "12px", fontWeight: "700", color: "#F59E0B" }}>Índice Cámara de Eco (ECI)</span>
                        <span style={{ fontSize: "18px", fontWeight: "700", fontFamily: "var(--font-mono)", color: "#F59E0B" }}>
                          {report.campaign_strategy.echo_chamber.score}%
                        </span>
                      </div>
                      <div style={{ fontSize: "12px", fontWeight: "600", color: "#E8EAF0", marginBottom: "4px" }}>
                        {report.campaign_strategy.echo_chamber.level}
                      </div>
                      <p style={{ fontSize: "11px", color: "rgba(232, 234, 240, 0.75)", lineHeight: "1.4" }}>
                        {report.campaign_strategy.echo_chamber.interpretation}
                      </p>
                    </div>

                    <div style={{ padding: "14px", background: "rgba(139, 124, 246, 0.08)", border: "1px solid rgba(139, 124, 246, 0.3)", borderRadius: "8px" }}>
                      <span style={{ fontSize: "12px", fontWeight: "700", color: "#A78BFA", display: "block", marginBottom: "8px" }}>
                        Aliados Puente Clave Recomendados
                      </span>
                      <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "6px", fontSize: "11px" }}>
                        {report.campaign_strategy.recommended_allies.map((al, idx) => (
                          <li key={idx} style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)" }}>
                            <strong style={{ color: "#fff" }}>{al.handle}</strong>
                            <span>{al.comm_name} (Score {al.alliance_score})</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {report.campaign_strategy.tactical_actions?.length > 0 && (
                    <div style={{ marginTop: "10px" }}>
                      <h4 style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-muted)", marginBottom: "8px" }}>
                        Acciones Tácticas Prioritarias de la Semana:
                      </h4>
                      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                        {report.campaign_strategy.tactical_actions.map((act, idx) => (
                          <div key={idx} style={{ padding: "8px 10px", background: "rgba(255,255,255,0.03)", borderRadius: "6px", fontSize: "11px", display: "flex", gap: "8px", alignItems: "center" }}>
                            <span style={{ padding: "1px 6px", borderRadius: "3px", background: act.priority === "Alta" ? "rgba(239,68,68,0.2)" : "rgba(245,158,11,0.2)", color: act.priority === "Alta" ? "#F87171" : "#FBBF24", fontWeight: "700" }}>
                              {act.priority}
                            </span>
                            <span style={{ color: "#fff" }}><strong>{act.category}:</strong> {act.action}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Hallazgos de Manipulación / Astroturfing */}
              <div className="report-section">
                <h3 className="report-section-title">2. Detección Forense de Astroturfing</h3>
                <div className="report-findings-list">
                  {report.astroturfing_findings.map((f, i) => (
                    <div key={i} className="report-finding-card">
                      <div className="report-finding-header">
                        <span className={`finding-severity-badge severity-${f.severity.toLowerCase()}`}>
                          {f.severity}
                        </span>
                        <h4 className="report-finding-title">{f.title}</h4>
                      </div>
                      <p className="report-finding-desc">{f.description}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Panorama de Comunidades */}
              <div className="report-section">
                <h3 className="report-section-title">3. Estructura de Comunidades (Louvain)</h3>
                <div className="report-table-wrap">
                  <table className="report-table">
                    <thead>
                      <tr>
                        <th>Comunidad</th>
                        <th>Miembros</th>
                        <th>Cuota de Red</th>
                        <th>Cuentas Sospechosas</th>
                        <th>Autenticidad Prom.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.communities.map((c) => (
                        <tr key={c.id}>
                          <td>
                            <span className="table-dot" style={{ background: c.color }} />
                            {c.name}
                          </td>
                          <td>{c.size}</td>
                          <td>{c.percentage}%</td>
                          <td style={{ color: c.suspicious_count > 0 ? "#E060B8" : undefined }}>
                            {c.suspicious_count}
                          </td>
                          <td>{c.avg_authenticity}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Top Actores Clave */}
              <div className="report-section">
                <h3 className="report-section-title">4. Principales Actores Influyentes y Puentes</h3>
                <div className="report-two-cols">
                  <div>
                    <h4 className="report-subheading">Top Influyentes (PageRank)</h4>
                    <ul className="report-ranking-list">
                      {report.top_influencers.slice(0, 5).map((inf, i) => (
                        <li key={i} className="report-ranking-item">
                          <span className="report-pos">{i + 1}</span>
                          <span className="report-handle">{inf.handle}</span>
                          <span className="report-val">{inf.influence} inf.</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h4 className="report-subheading">Top Nodos Puente (Betweenness)</h4>
                    <ul className="report-ranking-list">
                      {report.top_bridges.map((b, i) => (
                        <li key={i} className="report-ranking-item">
                          <span className="report-pos">{i + 1}</span>
                          <span className="report-handle">{b.handle}</span>
                          <span className="report-val">{b.bridge_index} puente</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>

              {/* Metodología */}
              <div className="report-section report-methodology">
                <h3 className="report-section-title">5. Metodología Aplicada</h3>
                <ul className="methodology-list">
                  <li><b>PageRank:</b> Centralidad vectorial de prestigio sobre grafo ponderado ($\alpha=0.85$).</li>
                  <li><b>Comunidades:</b> Optimización de modularidad mediante partición de Louvain.</li>
                  <li><b>CIB & Bot Score:</b> Análisis multidimensional de entropía horaria, picos de ráfaga y topología de amplificación.</li>
                </ul>
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer report-footer">
          <button
            className="btn-primary"
            style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
            onClick={handleDownloadPdf}
            disabled={downloadingPdf}
          >
            {downloadingPdf ? "Generando PDF…" : "📥 Descargar PDF Oficial"}
          </button>
          <button className="btn-secondary" onClick={() => window.print()}>
            🖨️ Imprimir / Vista Previa
          </button>
          <button className="btn-secondary" onClick={onClose}>
            Cerrar Informe
          </button>
        </div>
      </div>
    </div>
  );
}
