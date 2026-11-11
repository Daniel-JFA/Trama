"use client";

import { useState } from "react";

export default function Sparkline({ data, color = "#8B7CF6" }) {
  const [hoveredIdx, setHoveredIdx] = useState(null);

  if (!data || data.length === 0) return null;

  const w = 290;
  const h = 55;
  const padX = 12;
  const padY = 8;
  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);

  const xScale = (i) => padX + (i / (data.length - 1)) * (w - padX * 2);
  const yScale = (v) => h - padY - (v / max) * (h - padY * 2);

  // Generate smooth cubic bezier path
  let pathD = "";
  data.forEach((v, i) => {
    const x = xScale(i);
    const y = yScale(v);
    if (i === 0) {
      pathD += `M ${x},${y}`;
    } else {
      const prevX = xScale(i - 1);
      const prevY = yScale(data[i - 1]);
      const cpX1 = prevX + (x - prevX) / 2;
      const cpX2 = prevX + (x - prevX) / 2;
      pathD += ` C ${cpX1},${prevY} ${cpX2},${y} ${x},${y}`;
    }
  });

  const areaD = `${pathD} L ${xScale(data.length - 1)},${h - padY} L ${xScale(0)},${h - padY} Z`;

  const avg = Math.round(data.reduce((a, b) => a + b, 0) / data.length);
  const avgY = yScale(avg);

  return (
    <div className="sparkline-container" style={{ position: "relative", width: "100%" }}>
      {/* Header with scrub tooltip */}
      <div className="sparkline-header-stats">
        <span className="sparkline-stat-lbl">
          {hoveredIdx !== null ? `Semana ${hoveredIdx + 1}` : "Tendencia 12 sem."}
        </span>
        <span className="sparkline-stat-val" style={{ color: color }}>
          {hoveredIdx !== null ? (
            <>
              <b>{data[hoveredIdx]}</b> posts
              {data[hoveredIdx] >= 35 && (
                <span style={{ color: "#E060B8", marginLeft: "6px", fontSize: "10px" }}>⚡ Pico</span>
              )}
            </>
          ) : (
            `Prom: ${avg} posts/sem.`
          )}
        </span>
      </div>

      <svg
        width="100%"
        height={h}
        viewBox={`0 0 ${w} ${h}`}
        style={{ overflow: "visible", display: "block" }}
        onMouseLeave={() => setHoveredIdx(null)}
      >
        <defs>
          <linearGradient id={`spark-grad-${color.replace("#", "")}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.38" />
            <stop offset="100%" stopColor={color} stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {/* Average line */}
        <line
          x1={padX}
          y1={avgY}
          x2={w - padX}
          y2={avgY}
          stroke="rgba(255, 255, 255, 0.12)"
          strokeDasharray="2 2"
          strokeWidth="1"
        />

        {/* Area fill */}
        <path d={areaD} fill={`url(#spark-grad-${color.replace("#", "")})`} />

        {/* Line stroke */}
        <path
          d={pathD}
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Points & Burst Indicators */}
        {data.map((v, i) => {
          const cx = xScale(i);
          const cy = yScale(v);
          const isPeak = v >= 35 && v >= avg * 2.2;
          const isHovered = hoveredIdx === i;

          return (
            <g key={i}>
              {/* Invisible touch target for hover */}
              <rect
                x={cx - (w / data.length) / 2}
                y={0}
                width={w / data.length}
                height={h}
                fill="transparent"
                style={{ cursor: "crosshair" }}
                onMouseEnter={() => setHoveredIdx(i)}
              />

              {isPeak && (
                <circle
                  cx={cx}
                  cy={cy}
                  r="6"
                  fill="none"
                  stroke="#E060B8"
                  strokeWidth="1.5"
                  opacity="0.8"
                />
              )}

              <circle
                cx={cx}
                cy={cy}
                r={isHovered ? 4.5 : isPeak ? 3 : 2}
                fill={isPeak ? "#E060B8" : color}
                stroke={isHovered ? "#ffffff" : "none"}
                strokeWidth={isHovered ? 1.5 : 0}
              />
            </g>
          );
        })}

        {/* Hover vertical tracking line */}
        {hoveredIdx !== null && (
          <line
            x1={xScale(hoveredIdx)}
            y1={padY}
            x2={xScale(hoveredIdx)}
            y2={h - padY}
            stroke="#ffffff"
            strokeDasharray="2 2"
            strokeWidth="1"
            opacity="0.6"
            pointerEvents="none"
          />
        )}
      </svg>
    </div>
  );
}
