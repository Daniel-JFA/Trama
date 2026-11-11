"use client";

import VennOverlapChart from "../charts/VennOverlapChart";

export default function ComparisonPanel({
  profiles,
  graph,
  communities,
  onRemove,
  onNodeClick,
}) {
  const commMap = {};
  (communities || []).forEach((c) => {
    commMap[c.id] = c;
  });

  // Calculate Jaccard neighbor overlap
  function buildNeighborSet(nodeId) {
    const s = new Set();
    if (!graph) return s;
    graph.links.forEach((l) => {
      const sid = typeof l.source === "object" ? l.source.id : l.source;
      const tid = typeof l.target === "object" ? l.target.id : l.target;
      if (sid === nodeId) s.add(tid);
      if (tid === nodeId) s.add(sid);
    });
    return s;
  }

  const neighborSets = profiles.map((p) => ({
    id: p.id,
    set: buildNeighborSet(p.id),
  }));

  const pairs = [];
  for (let i = 0; i < profiles.length; i++) {
    for (let j = i + 1; j < profiles.length; j++) {
      const sa = neighborSets[i].set;
      const sb = neighborSets[j].set;
      const common = [...sa].filter((x) => sb.has(x));
      const union = new Set([...sa, ...sb]);
      const jaccard =
        union.size > 0 ? Math.round((common.length / union.size) * 100) : 0;
      const commonNodes = common
        .slice(0, 8)
        .map((id) => graph?.nodes.find((n) => n.id === id))
        .filter(Boolean);
      pairs.push({
        a: profiles[i],
        b: profiles[j],
        jaccard,
        common,
        commonNodes,
      });
    }
  }

  return (
    <div className="panel-content">
      <h3 className="panel-heading">Comparación de Audiencias</h3>
      <p className="panel-note" style={{ marginBottom: "16px" }}>
        Mide el solapamiento estructural y la redundancia de alcance entre perfiles.
      </p>

      {/* Selected profile chips */}
      <div className="comparison-chips">
        {profiles.map((p) => {
          const comm = commMap[p.comm];
          return (
            <div
              key={p.id}
              className="comp-chip"
              style={{
                borderColor: comm?.color || "#666",
                background: `${comm?.color || "#666"}15`,
              }}
            >
              <span
                className="comp-chip-dot"
                style={{ background: comm?.color || "#666" }}
              />
              <span>@{p.handle}</span>
              <button
                className="comp-chip-remove"
                onClick={() => onRemove(p.id)}
                title="Quitar de la comparación"
              >
                ✕
              </button>
            </div>
          );
        })}
        {profiles.length < 3 && (
          <span className="comp-hint">
            Selecciona un nodo y haz clic en &quot;Añadir a comparación&quot; (máx. 3)
          </span>
        )}
      </div>

      {/* Pairwise Comparison Cards */}
      {pairs.length > 0 && (
        <div className="pairs-section">
          {pairs.map((pair, i) => {
            const commA = commMap[pair.a.comm];
            const commB = commMap[pair.b.comm];

            return (
              <div key={i} className="pair-card">
                <div className="pair-header">
                  <span className="pair-name" style={{ color: commA?.color || "#fff" }}>
                    @{pair.a.handle}
                  </span>
                  <span className="pair-sep">vs</span>
                  <span className="pair-name" style={{ color: commB?.color || "#fff" }}>
                    @{pair.b.handle}
                  </span>
                </div>

                {/* Venn diagram representation */}
                <VennOverlapChart pair={pair} commA={commA} commB={commB} />

                <div className="jaccard-row">
                  <span className="jaccard-label">Índice Jaccard de Intersección</span>
                  <span className="jaccard-val" style={{ color: pair.jaccard >= 40 ? "#E060B8" : "#5AD1B3" }}>
                    {pair.jaccard}%
                  </span>
                </div>

                <div className="jaccard-track">
                  <div
                    className="jaccard-fill"
                    style={{
                      width: `${pair.jaccard}%`,
                      background: pair.jaccard >= 40 ? "#E060B8" : "#5AD1B3",
                      boxShadow: `0 0 8px ${pair.jaccard >= 40 ? "#E060B8" : "#5AD1B3"}66`,
                    }}
                  />
                </div>

                <p className="jaccard-note">
                  {pair.jaccard >= 40
                    ? "🔴 Solapamiento alto: Audiencias muy redundantes o coordinadas."
                    : pair.jaccard >= 15
                    ? "🟡 Solapamiento moderado: Audiencias parcialmente compartidas."
                    : "🟢 Solapamiento bajo: Alcance complementario independiente."}
                </p>

                {pair.commonNodes.length > 0 && (
                  <div className="common-nodes">
                    <p className="common-nodes-title">
                      Contactos y enlaces en común ({pair.common.length}):
                    </p>
                    <div className="common-nodes-grid">
                      {pair.commonNodes.map((n) => {
                        const nc = commMap[n.comm];
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
                          </button>
                        );
                      })}
                    </div>
                    {pair.common.length > 8 && (
                      <span className="common-more">
                        +{pair.common.length - 8} conexiones más
                      </span>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {profiles.length === 0 && (
        <div className="empty-comparison-box">
          <div className="empty-comparison-icon">⚖️</div>
          <p className="empty-comparison-text">
            Selecciona hasta 3 perfiles desde el grafo para calcular solapamiento de audiencias (Jaccard) y descubrir conexiones compartidas.
          </p>
        </div>
      )}
    </div>
  );
}
