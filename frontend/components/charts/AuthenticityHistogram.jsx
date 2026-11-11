"use client";

export default function AuthenticityHistogram({ graph, activeFilter, onSelectFilter }) {
  if (!graph || !graph.nodes || graph.nodes.length === 0) return null;

  const total = graph.nodes.length;
  let organic = 0; // auth >= 70
  let moderate = 0; // 40 <= auth < 70
  let suspicious = 0; // auth < 40 (bot >= 60)

  graph.nodes.forEach((n) => {
    const auth = n.auth ?? (100 - (n.bot || 0));
    if (auth >= 70) organic++;
    else if (auth >= 40) moderate++;
    else suspicious++;
  });

  const pctOrganic = Math.round((organic / total) * 100);
  const pctModerate = Math.round((moderate / total) * 100);
  const pctSuspicious = Math.round((suspicious / total) * 100);

  return (
    <div className="auth-histogram-card">
      <div className="auth-hist-header">
        <span className="auth-hist-title">Salud & Autenticidad</span>
        <span className="auth-hist-status" style={{ color: pctSuspicious > 20 ? "#E060B8" : "#5AD1B3" }}>
          {pctSuspicious > 20 ? "Riesgo CIB Detectado" : "Red Mayormente Orgánica"}
        </span>
      </div>

      {/* Segmented bar */}
      <div className="auth-segmented-bar">
        <div
          className="auth-segment"
          style={{ width: `${pctOrganic}%`, background: "#5AD1B3" }}
          title={`Orgánico: ${organic} cuentas (${pctOrganic}%)`}
        />
        <div
          className="auth-segment"
          style={{ width: `${pctModerate}%`, background: "#E8C15A" }}
          title={`Mixto: ${moderate} cuentas (${pctModerate}%)`}
        />
        <div
          className="auth-segment"
          style={{ width: `${pctSuspicious}%`, background: "#E060B8" }}
          title={`Sospechoso: ${suspicious} cuentas (${pctSuspicious}%)`}
        />
      </div>

      {/* Metrics Row */}
      <div className="auth-hist-grid">
        <div className="auth-hist-col">
          <div className="auth-hist-dot" style={{ background: "#5AD1B3" }} />
          <div className="auth-hist-col-info">
            <span className="auth-hist-col-pct">{pctOrganic}%</span>
            <span className="auth-hist-col-lbl">Orgánico</span>
          </div>
        </div>
        <div className="auth-hist-col">
          <div className="auth-hist-dot" style={{ background: "#E8C15A" }} />
          <div className="auth-hist-col-info">
            <span className="auth-hist-col-pct">{pctModerate}%</span>
            <span className="auth-hist-col-lbl">Mixto</span>
          </div>
        </div>
        <button
          className={`auth-hist-col auth-hist-btn-susp ${
            activeFilter === "suspicious" ? "auth-hist-active" : ""
          }`}
          onClick={() => onSelectFilter(activeFilter === "suspicious" ? null : "suspicious")}
          title="Filtrar solo cuentas sospechosas"
        >
          <div className="auth-hist-dot" style={{ background: "#E060B8" }} />
          <div className="auth-hist-col-info">
            <span className="auth-hist-col-pct" style={{ color: "#E060B8" }}>
              {pctSuspicious}%
            </span>
            <span className="auth-hist-col-lbl">Sospechoso</span>
          </div>
        </button>
      </div>
    </div>
  );
}
