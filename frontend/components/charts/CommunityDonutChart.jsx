"use client";

import { useState } from "react";
import * as d3 from "d3";

export default function CommunityDonutChart({
  graph,
  communities,
  activeFilter,
  onSelectCommunity,
}) {
  const [hoveredComm, setHoveredComm] = useState(null);

  if (!graph || !graph.nodes || !communities || communities.length === 0) return null;

  const totalNodes = graph.nodes.length;
  const commCounts = {};
  const commBots = {};

  communities.forEach((c) => {
    commCounts[c.id] = 0;
    commBots[c.id] = 0;
  });

  graph.nodes.forEach((n) => {
    if (commCounts[n.comm] !== undefined) {
      commCounts[n.comm]++;
      if (n.bot >= 60) {
        commBots[n.comm]++;
      }
    }
  });

  const data = communities.map((c) => ({
    id: c.id,
    name: c.name,
    color: c.color,
    count: commCounts[c.id] || 0,
    bots: commBots[c.id] || 0,
    percentage: totalNodes > 0 ? Math.round(((commCounts[c.id] || 0) / totalNodes) * 100) : 0,
  }));

  const size = 180;
  const radius = size / 2;
  const innerRadius = radius * 0.62;

  const pie = d3
    .pie()
    .value((d) => d.count)
    .sort(null)
    .padAngle(0.04);

  const arc = d3.arc().innerRadius(innerRadius).outerRadius(radius - 4);
  const arcHover = d3.arc().innerRadius(innerRadius - 2).outerRadius(radius);

  const pieData = pie(data);

  const activeDisplay = hoveredComm !== null
    ? data.find((d) => d.id === hoveredComm)
    : activeFilter !== null && typeof activeFilter === "number"
    ? data.find((d) => d.id === activeFilter)
    : null;

  return (
    <div className="donut-chart-container">
      <div className="donut-svg-wrap" style={{ position: "relative", width: size, height: size, margin: "0 auto" }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          <g transform={`translate(${radius}, ${radius})`}>
            {pieData.map((d) => {
              const isSelected = activeFilter === d.data.id;
              const isHovered = hoveredComm === d.data.id;
              const currentArc = isHovered || isSelected ? arcHover(d) : arc(d);

              return (
                <path
                  key={d.data.id}
                  d={currentArc}
                  fill={d.data.color}
                  opacity={
                    hoveredComm !== null
                      ? isHovered
                        ? 1
                        : 0.35
                      : activeFilter !== null
                      ? isSelected
                        ? 1
                        : 0.35
                      : 0.88
                  }
                  stroke={isSelected ? "#ffffff" : isHovered ? d.data.color : "rgba(16, 26, 46, 0.8)"}
                  strokeWidth={isSelected ? 2 : 1}
                  style={{
                    cursor: "pointer",
                    transition: "all 0.2s ease",
                    filter: isHovered ? "drop-shadow(0 0 6px " + d.data.color + "88)" : "none",
                  }}
                  onMouseEnter={() => setHoveredComm(d.data.id)}
                  onMouseLeave={() => setHoveredComm(null)}
                  onClick={() =>
                    onSelectCommunity(activeFilter === d.data.id ? null : d.data.id)
                  }
                />
              );
            })}
          </g>
        </svg>

        {/* Central HUD info */}
        <div
          className="donut-center-info"
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            pointerEvents: "none",
            textAlign: "center",
            padding: "0 10px",
          }}
        >
          {activeDisplay ? (
            <>
              <span
                style={{
                  fontSize: "10px",
                  fontFamily: "var(--font-mono)",
                  color: activeDisplay.color,
                  fontWeight: 600,
                  maxWidth: "110px",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {activeDisplay.name}
              </span>
              <span style={{ fontSize: "16px", fontWeight: 700, color: "#fff", lineHeight: 1.1 }}>
                {activeDisplay.percentage}%
              </span>
              <span style={{ fontSize: "9px", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                {activeDisplay.count} nodos
              </span>
            </>
          ) : (
            <>
              <span style={{ fontSize: "16px", fontWeight: 700, color: "#fff" }}>
                {communities.length}
              </span>
              <span style={{ fontSize: "9px", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                Comunidades
              </span>
            </>
          )}
        </div>
      </div>

      {/* Mini legend beneath chart */}
      <div className="donut-legend-grid">
        {data.map((c) => {
          const isSelected = activeFilter === c.id;
          return (
            <button
              key={c.id}
              className={`donut-legend-row ${isSelected ? "donut-legend-row-active" : ""}`}
              onClick={() => onSelectCommunity(activeFilter === c.id ? null : c.id)}
              onMouseEnter={() => setHoveredComm(c.id)}
              onMouseLeave={() => setHoveredComm(null)}
            >
              <div className="donut-legend-name-wrap">
                <span className="donut-legend-dot" style={{ background: c.color }} />
                <span className="donut-legend-name">{c.name}</span>
              </div>
              <div className="donut-legend-stats">
                <span className="donut-legend-pct">{c.percentage}%</span>
                {c.bots > 0 && (
                  <span className="donut-legend-bot-badge" title={`${c.bots} cuentas sospechosas`}>
                    ⚠️ {c.bots}
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
