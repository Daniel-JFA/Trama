"use client";

import { useState } from "react";

const PALETTE = ["#00F0FF", "#E060B8", "#FFD700", "#A855F7"];

export default function GrowthChart({
  series = [],
  compareAccounts = [],
  height = 220,
}) {
  const [hoveredIndex, setHoveredIndex] = useState(null);

  if (!series || series.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-xs text-neutral-500 border border-dashed border-neutral-800 rounded p-6"
        style={{ height }}
      >
        Sin datos de instantáneas suficientes para graficar el crecimiento.
      </div>
    );
  }

  const padding = { top: 20, right: 30, bottom: 30, left: 55 };
  const width = 600; // Ancho virtual para viewBox SVG

  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Extraer valores mínimos y máximos para el eje Y
  const followerValues = series.map((s) => s.followers);
  compareAccounts.forEach((acc) => {
    if (acc.series) {
      acc.series.forEach((s) => followerValues.push(s.followers));
    }
  });

  const minVal = Math.min(...followerValues);
  const maxVal = Math.max(...followerValues);
  const range = maxVal - minVal || 1;

  const getX = (idx, total) => {
    if (total <= 1) return padding.left + chartWidth / 2;
    return padding.left + (idx / (total - 1)) * chartWidth;
  };

  const getY = (val) => {
    return padding.top + chartHeight - ((val - minVal) / range) * chartHeight;
  };

  // Generar path SVG para la serie principal
  const mainPoints = series.map((pt, i) => `${getX(i, series.length)},${getY(pt.followers)}`).join(" ");

  const areaPoints = [
    `${padding.left},${padding.top + chartHeight}`,
    ...series.map((pt, i) => `${getX(i, series.length)},${getY(pt.followers)}`),
    `${getX(series.length - 1, series.length)},${padding.top + chartHeight}`,
  ].join(" ");

  const hoveredPoint = hoveredIndex !== null ? series[hoveredIndex] : null;

  return (
    <div className="relative w-full overflow-hidden bg-neutral-900/60 border border-neutral-800 rounded-lg p-3">
      <div className="flex items-center justify-between text-xs mb-2">
        <span className="font-mono text-neutral-400 uppercase tracking-wider text-[11px]">
          Curva de Crecimiento ({series.length} días)
        </span>
        {hoveredPoint ? (
          <div className="font-mono text-xs flex items-center gap-3">
            <span className="text-neutral-400">{hoveredPoint.date}</span>
            <span className="text-cyan-400 font-semibold">{hoveredPoint.followers.toLocaleString()} seguidores</span>
            <span
              className={`text-[10px] px-1.5 py-0.5 rounded ${
                hoveredPoint.delta >= 0 ? "bg-emerald-950 text-emerald-400" : "bg-rose-950 text-rose-400"
              }`}
            >
              {hoveredPoint.delta >= 0 ? `+${hoveredPoint.delta}` : hoveredPoint.delta} ({hoveredPoint.growth_pct}%)
            </span>
          </div>
        ) : (
          <span className="font-mono text-[10px] text-neutral-500">Pasa el cursor para ver detalles</span>
        )}
      </div>

      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full h-auto overflow-visible select-none"
        style={{ maxHeight: height }}
      >
        <defs>
          <linearGradient id="mainGrowthGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#00F0FF" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#00F0FF" stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {/* Líneas de cuadrícula horizontal */}
        {[0, 0.25, 0.5, 0.75, 1].map((pct, i) => {
          const y = padding.top + chartHeight * (1 - pct);
          const val = Math.round(minVal + range * pct);
          return (
            <g key={i}>
              <line
                x1={padding.left}
                y1={y}
                x2={padding.left + chartWidth}
                y2={y}
                stroke="#262626"
                strokeDasharray="3 3"
              />
              <text
                x={padding.left - 8}
                y={y + 3}
                fill="#737373"
                fontSize="9"
                textAnchor="end"
                fontFamily="monospace"
              >
                {val >= 1000000 ? `${(val / 1000000).toFixed(1)}M` : val >= 1000 ? `${(val / 1000).toFixed(0)}k` : val}
              </text>
            </g>
          );
        })}

        {/* Área bajo la curva principal */}
        <polygon points={areaPoints} fill="url(#mainGrowthGradient)" />

        {/* Línea principal */}
        <polyline
          fill="none"
          stroke="#00F0FF"
          strokeWidth="2.5"
          points={mainPoints}
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Líneas de cuentas comparadas (si hay) */}
        {compareAccounts.map((acc, accIdx) => {
          if (!acc.series || acc.series.length === 0) return null;
          const color = PALETTE[(accIdx + 1) % PALETTE.length];
          const pts = acc.series.map((pt, i) => `${getX(i, acc.series.length)},${getY(pt.followers)}`).join(" ");
          return (
            <polyline
              key={acc.id}
              fill="none"
              stroke={color}
              strokeWidth="1.8"
              strokeDasharray="4 2"
              points={pts}
              strokeLinecap="round"
            />
          );
        })}

        {/* Puntos interactivos de la serie principal */}
        {series.map((pt, i) => {
          const cx = getX(i, series.length);
          const cy = getY(pt.followers);
          const isHovered = hoveredIndex === i;

          return (
            <g key={i} className="cursor-pointer" onMouseEnter={() => setHoveredIndex(i)} onMouseLeave={() => setHoveredIndex(null)}>
              {/* Target invisible más grande para hover */}
              <circle cx={cx} cy={cy} r="12" fill="transparent" />
              <circle
                cx={cx}
                cy={cy}
                r={isHovered ? 5 : 3}
                fill={isHovered ? "#FFFFFF" : "#00F0FF"}
                stroke="#0A0A0A"
                strokeWidth="1.5"
              />
              {/* Etiqueta de fecha en el eje X */}
              {i % Math.ceil(series.length / 5) === 0 && (
                <text
                  x={cx}
                  y={padding.top + chartHeight + 16}
                  fill="#737373"
                  fontSize="8"
                  textAnchor="middle"
                  fontFamily="monospace"
                >
                  {pt.date.slice(5)}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
