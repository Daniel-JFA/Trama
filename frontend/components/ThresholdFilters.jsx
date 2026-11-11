"use client";

import React, { useMemo } from "react";

export default function ThresholdFilters({
  nodes = [],
  communities = [],
  filters = { minInfluence: 0, maxBot: 100, activeCommunities: [] },
  onChange,
}) {
  const { minInfluence = 0, maxBot = 100, activeCommunities = [] } = filters;

  // Calcular histogramas de 10 contenedores (bins)
  const { influenceBins, botBins, matchingCount } = useMemo(() => {
    const infBins = new Array(10).fill(0);
    const bBins = new Array(10).fill(0);
    let match = 0;

    const commSet = new Set(
      activeCommunities.length > 0 ? activeCommunities : communities.map((c) => c.id)
    );

    nodes.forEach((n) => {
      const inf = n.influence || 0;
      const bot = n.bot || 0;
      const infIdx = Math.min(9, Math.floor(inf / 10));
      const botIdx = Math.min(9, Math.floor(bot / 10));
      infBins[infIdx]++;
      bBins[botIdx]++;

      const passInf = inf >= minInfluence;
      const passBot = bot <= maxBot;
      const passComm = commSet.has(n.comm);
      if (passInf && passBot && passComm) {
        match++;
      }
    });

    return { influenceBins: infBins, botBins: bBins, matchingCount: match };
  }, [nodes, communities, minInfluence, maxBot, activeCommunities]);

  const maxInfFreq = Math.max(1, ...influenceBins);
  const maxBotFreq = Math.max(1, ...botBins);

  const handleInfluenceChange = (e) => {
    onChange({
      ...filters,
      minInfluence: Number(e.target.value),
    });
  };

  const handleBotChange = (e) => {
    onChange({
      ...filters,
      maxBot: Number(e.target.value),
    });
  };

  const toggleCommunity = (commId) => {
    const allIds = communities.map((c) => c.id);
    let next;
    if (activeCommunities.length === 0) {
      // Si todos estaban activos implícitamente, desactivar solo este
      next = allIds.filter((id) => id !== commId);
    } else if (activeCommunities.includes(commId)) {
      next = activeCommunities.filter((id) => id !== commId);
    } else {
      next = [...activeCommunities, commId];
    }
    onChange({
      ...filters,
      activeCommunities: next,
    });
  };

  const resetFilters = () => {
    onChange({
      minInfluence: 0,
      maxBot: 100,
      activeCommunities: [],
    });
  };

  const pctVisible = nodes.length > 0 ? Math.round((matchingCount / nodes.length) * 100) : 100;

  return (
    <div className="threshold-filters-container" style={{
      background: "#0c111d",
      border: "1px solid #1f293d",
      borderRadius: "10px",
      padding: "14px 16px",
      margin: "10px 0",
      color: "#e2e8f0",
      fontSize: "12px",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.5px", color: "#60A5FA" }}>
            Filtros Multicriterio en Tiempo Real
          </span>
          <span style={{
            background: "#1e293b",
            padding: "2px 8px",
            borderRadius: "12px",
            fontSize: "11px",
            color: "#94a3b8"
          }}>
            {matchingCount} / {nodes.length} perfiles ({pctVisible}%)
          </span>
        </div>
        {(minInfluence > 0 || maxBot < 100 || activeCommunities.length > 0) && (
          <button
            onClick={resetFilters}
            style={{
              background: "transparent",
              border: "1px solid #334155",
              color: "#94a3b8",
              padding: "2px 8px",
              borderRadius: "4px",
              cursor: "pointer",
              fontSize: "11px",
            }}
          >
            ↺ Restablecer
          </button>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "18px" }}>
        {/* Slider 1: Percentil de Influencia */}
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
            <span style={{ color: "#94a3b8" }}>Mínimo PageRank / Influencia:</span>
            <span style={{ fontWeight: "700", color: "#60A5FA" }}>{minInfluence}%</span>
          </div>

          {/* Histograma de Influencia */}
          <div style={{ height: "30px", display: "flex", alignItems: "flex-end", gap: "2px", marginBottom: "4px" }}>
            {influenceBins.map((freq, idx) => {
              const h = Math.round((freq / maxInfFreq) * 26) + 2;
              const isSelected = idx * 10 >= minInfluence;
              return (
                <div
                  key={idx}
                  title={`Rango ${idx * 10}-${(idx + 1) * 10}%: ${freq} nodos`}
                  style={{
                    flex: 1,
                    height: `${h}px`,
                    background: isSelected ? "#3B82F6" : "#1e293b",
                    borderRadius: "2px 2px 0 0",
                    transition: "all 0.15s ease",
                  }}
                />
              );
            })}
          </div>

          <input
            type="range"
            min="0"
            max="100"
            step="5"
            value={minInfluence}
            onChange={handleInfluenceChange}
            style={{ width: "100%", accentColor: "#3B82F6", cursor: "pointer" }}
          />
        </div>

        {/* Slider 2: Índice CIB / Bot Score */}
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
            <span style={{ color: "#94a3b8" }}>Máximo Umbral Bot (CIB):</span>
            <span style={{ fontWeight: "700", color: maxBot < 50 ? "#10B981" : "#EF4444" }}>
              ≤ {maxBot}/100
            </span>
          </div>

          {/* Histograma de Bot Score */}
          <div style={{ height: "30px", display: "flex", alignItems: "flex-end", gap: "2px", marginBottom: "4px" }}>
            {botBins.map((freq, idx) => {
              const h = Math.round((freq / maxBotFreq) * 26) + 2;
              const isSelected = idx * 10 <= maxBot;
              const barColor = idx < 3 ? "#10B981" : idx < 6 ? "#F59E0B" : "#EF4444";
              return (
                <div
                  key={idx}
                  title={`Score ${idx * 10}-${(idx + 1) * 10}: ${freq} cuentas`}
                  style={{
                    flex: 1,
                    height: `${h}px`,
                    background: isSelected ? barColor : "#1e293b",
                    borderRadius: "2px 2px 0 0",
                    transition: "all 0.15s ease",
                  }}
                />
              );
            })}
          </div>

          <input
            type="range"
            min="0"
            max="100"
            step="5"
            value={maxBot}
            onChange={handleBotChange}
            style={{ width: "100%", accentColor: maxBot < 50 ? "#10B981" : "#EF4444", cursor: "pointer" }}
          />
        </div>
      </div>

      {/* Selector de Comunidades Activas */}
      {communities.length > 0 && (
        <div style={{ marginTop: "12px", borderTop: "1px solid #1a2333", paddingTop: "8px" }}>
          <span style={{ fontSize: "11px", color: "#64748b", display: "block", marginBottom: "6px" }}>
            Comunidades Visibles:
          </span>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
            {communities.map((comm) => {
              const isActive = activeCommunities.length === 0 || activeCommunities.includes(comm.id);
              return (
                <button
                  key={comm.id}
                  onClick={() => toggleCommunity(comm.id)}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "5px",
                    background: isActive ? "rgba(255,255,255,0.06)" : "transparent",
                    border: `1px solid ${isActive ? comm.color : "#26334d"}`,
                    color: isActive ? "#f8fafc" : "#64748b",
                    padding: "3px 8px",
                    borderRadius: "14px",
                    cursor: "pointer",
                    fontSize: "11px",
                    transition: "all 0.15s ease",
                  }}
                >
                  <span
                    style={{
                      width: "7px",
                      height: "7px",
                      borderRadius: "50%",
                      backgroundColor: comm.color,
                      opacity: isActive ? 1 : 0.3,
                    }}
                  />
                  {comm.name} ({comm.percentage}%)
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
