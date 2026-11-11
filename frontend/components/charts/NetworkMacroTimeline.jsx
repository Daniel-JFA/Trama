"use client";

import { useState } from "react";

export default function NetworkMacroTimeline({
  graph,
  currentWeek,
  onSelectWeek,
}) {
  const [hoveredWeek, setHoveredWeek] = useState(null);

  if (!graph || !graph.nodes || graph.nodes.length === 0) return null;

  const maxWeeks = 12;
  const weeklyTotals = Array(maxWeeks).fill(0);
  const weeklyBotTotals = Array(maxWeeks).fill(0);

  graph.nodes.forEach((n) => {
    if (n.act && Array.isArray(n.act)) {
      n.act.slice(0, maxWeeks).forEach((count, i) => {
        weeklyTotals[i] += count;
        if (n.bot >= 60) {
          weeklyBotTotals[i] += count;
        }
      });
    }
  });

  const maxVolume = Math.max(...weeklyTotals, 1);
  const chartHeight = 64;
  const barWidth = 14;
  const gap = 6;
  const totalWidth = maxWeeks * (barWidth + gap);

  return (
    <div className="macro-timeline-card">
      <div className="macro-timeline-header">
        <span className="macro-timeline-title">Volumen de actividad (12 sem.)</span>
        {hoveredWeek !== null ? (
          <span className="macro-timeline-info">
            Sem. {hoveredWeek + 1}: <b>{weeklyTotals[hoveredWeek].toLocaleString()}</b> posts{" "}
            <span style={{ color: "#E060B8", fontSize: "10px" }}>
              ({weeklyBotTotals[hoveredWeek]} bots)
            </span>
          </span>
        ) : currentWeek !== null ? (
          <span className="macro-timeline-info">
            Sem. {currentWeek}: <b>{weeklyTotals[currentWeek - 1].toLocaleString()}</b> posts
          </span>
        ) : (
          <span className="macro-timeline-info" style={{ color: "var(--text-dim)" }}>
            Clic en barra para filtrar
          </span>
        )}
      </div>

      <div className="macro-timeline-svg-wrap">
        <svg
          width="100%"
          height={chartHeight + 18}
          viewBox={`0 0 ${totalWidth} ${chartHeight + 18}`}
          style={{ overflow: "visible" }}
        >
          {/* Average reference line */}
          {(() => {
            const avg = weeklyTotals.reduce((a, b) => a + b, 0) / maxWeeks;
            const avgY = chartHeight - (avg / maxVolume) * chartHeight;
            return (
              <line
                x1={0}
                y1={avgY}
                x2={totalWidth}
                y2={avgY}
                stroke="rgba(255, 255, 255, 0.15)"
                strokeDasharray="3 3"
                strokeWidth={1}
              />
            );
          })()}

          {weeklyTotals.map((tot, idx) => {
            const weekNum = idx + 1;
            const isPeak = weekNum === 6 || weekNum === 7;
            const isSelected = currentWeek === weekNum;
            const isHovered = hoveredWeek === idx;

            const totalH = Math.max(3, (tot / maxVolume) * chartHeight);
            const botH = (weeklyBotTotals[idx] / maxVolume) * chartHeight;
            const organicH = totalH - botH;

            const x = idx * (barWidth + gap);
            const yTotal = chartHeight - totalH;
            const yBot = yTotal;
            const yOrganic = yTotal + botH;

            return (
              <g
                key={idx}
                style={{ cursor: "pointer" }}
                onClick={() => onSelectWeek(isSelected ? null : weekNum)}
                onMouseEnter={() => setHoveredWeek(idx)}
                onMouseLeave={() => setHoveredWeek(null)}
              >
                {/* Background highlight pill for selected/hovered */}
                {(isSelected || isHovered) && (
                  <rect
                    x={x - 2}
                    y={0}
                    width={barWidth + 4}
                    height={chartHeight + 18}
                    fill="rgba(255, 255, 255, 0.06)"
                    rx={4}
                  />
                )}

                {/* Base bar (organic) */}
                <rect
                  x={x}
                  y={yOrganic}
                  width={barWidth}
                  height={Math.max(0, organicH)}
                  fill={isPeak ? "#8B7CF6" : "rgba(139, 124, 246, 0.55)"}
                  rx={2}
                />

                {/* Bot overlay bar */}
                {botH > 0 && (
                  <rect
                    x={x}
                    y={yBot}
                    width={barWidth}
                    height={Math.max(2, botH)}
                    fill="#E060B8"
                    rx={2}
                  />
                )}

                {/* Peak hazard beacon */}
                {isPeak && (
                  <circle
                    cx={x + barWidth / 2}
                    cy={yTotal - 5}
                    r={2.5}
                    fill="#E060B8"
                  />
                )}

                {/* Week label */}
                <text
                  x={x + barWidth / 2}
                  y={chartHeight + 13}
                  textAnchor="middle"
                  fill={isSelected ? "#fff" : isPeak ? "#E060B8" : "var(--text-dim)"}
                  fontSize="9"
                  fontFamily="var(--font-mono)"
                  fontWeight={isSelected || isPeak ? 600 : 400}
                >
                  S{weekNum}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <div className="macro-timeline-legend">
        <span className="macro-leg-item">
          <span className="macro-leg-dot" style={{ background: "rgba(139, 124, 246, 0.6)" }} />
          Orgánico
        </span>
        <span className="macro-leg-item">
          <span className="macro-leg-dot" style={{ background: "#E060B8" }} />
          Amplificación
        </span>
        <span className="macro-leg-item" style={{ marginLeft: "auto", color: "var(--text-dim)" }}>
          --- Promedio
        </span>
      </div>
    </div>
  );
}
