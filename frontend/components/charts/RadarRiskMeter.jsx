"use client";

export default function RadarRiskMeter({ node }) {
  if (!node) return null;

  // Derive individual factor scores (0-100)
  // 1. Temporal Burstiness
  let temporalScore = 10;
  if (node.act && Array.isArray(node.act)) {
    const maxAct = Math.max(...node.act, 0);
    const avgAct = node.act.reduce((a, b) => a + b, 0) / Math.max(1, node.act.length);
    if (maxAct >= 40 || maxAct > avgAct * 3) {
      temporalScore = 90;
    } else if (maxAct >= 25 || maxAct > avgAct * 2) {
      temporalScore = 55;
    }
  }

  // 2. Handle pattern anomaly
  let handleScore = 15;
  const digitsMatch = (node.handle || "").match(/\d/g);
  const digitCount = digitsMatch ? digitsMatch.length : 0;
  if (/\d{4,}$/.test(node.handle || "")) {
    handleScore = 95;
  } else if (digitCount >= 4) {
    handleScore = 75;
  } else if (digitCount >= 2) {
    handleScore = 40;
  }

  // 3. Activity to followers ratio
  let ratioScore = 15;
  if (node.followers > 0 && node.posts > 0) {
    const ratio = node.posts / node.followers;
    if (ratio > 3.0 && node.posts > 200) {
      ratioScore = 85;
    } else if (ratio > 1.5) {
      ratioScore = 50;
    }
  }

  // 4. Amplification Topology
  let topoScore = 10;
  if (node.comm === 3) {
    topoScore = 80;
  } else if (node.bot >= 60) {
    topoScore = 65;
  }

  // If node has backend cib_breakdown, prioritize it
  if (node.cib_breakdown) {
    if (node.cib_breakdown.temporal_burst) temporalScore = Math.min(100, node.cib_breakdown.temporal_burst * 2.8);
    if (node.cib_breakdown.handle_anomaly) handleScore = Math.min(100, node.cib_breakdown.handle_anomaly * 2.8);
    if (node.cib_breakdown.activity_ratio) ratioScore = Math.min(100, node.cib_breakdown.activity_ratio * 4.5);
    if (node.cib_breakdown.fan_in_topology) topoScore = Math.min(100, node.cib_breakdown.fan_in_topology * 4.5);
  }

  const factors = [
    { name: "Sincronización temporal", score: Math.round(temporalScore), icon: "⏱️", desc: "Ráfagas coordinadas en semanas clave" },
    { name: "Anomalía de handle", score: Math.round(handleScore), icon: "🔤", desc: "Sufijos y patrones generados por botnets" },
    { name: "Ratio posts / audiencia", score: Math.round(ratioScore), icon: "📊", desc: "Frecuencia desproporcionada de emisión" },
    { name: "Topología de amplificación", score: Math.round(topoScore), icon: "🕸️", desc: "Conexión en abanico orientada a hubs" },
  ];

  const getColor = (s) => {
    if (s >= 70) return "#E060B8";
    if (s >= 40) return "#E8C15A";
    return "#5AD1B3";
  };

  return (
    <div className="risk-meter-container">
      <div className="risk-meter-header">
        <span className="risk-meter-title">Desglose Forense Multidimensional</span>
        <span className="risk-meter-overall" style={{ color: getColor(node.bot || 0) }}>
          Score CIB: {node.bot || 0}/100
        </span>
      </div>

      <div className="risk-factors-list">
        {factors.map((f, i) => {
          const barColor = getColor(f.score);
          return (
            <div key={i} className="risk-factor-row">
              <div className="risk-factor-info">
                <span className="risk-factor-icon">{f.icon}</span>
                <div className="risk-factor-text">
                  <span className="risk-factor-name">{f.name}</span>
                  <span className="risk-factor-desc">{f.desc}</span>
                </div>
                <span className="risk-factor-val" style={{ color: barColor }}>
                  {f.score}%
                </span>
              </div>
              <div className="risk-factor-bar-track">
                <div
                  className="risk-factor-bar-fill"
                  style={{
                    width: `${f.score}%`,
                    background: barColor,
                    boxShadow: f.score >= 70 ? "0 0 8px rgba(224, 96, 184, 0.4)" : "none",
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
