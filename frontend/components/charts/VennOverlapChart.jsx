"use client";

export default function VennOverlapChart({ pair, commA, commB }) {
  if (!pair) return null;

  const { a, b, jaccard, common } = pair;
  const setSizeA = (a.degree || a.followers || 20);
  const setSizeB = (b.degree || b.followers || 20);
  const commonCount = common.length;

  const colorA = commA?.color || "#8B7CF6";
  const colorB = commB?.color || "#5AD1B3";

  const width = 260;
  const height = 110;
  const rA = 42;
  const rB = 42;
  const centerY = height / 2;

  // Separation distance inversely proportional to Jaccard index
  // 0% -> separated (dist = 110), 100% -> centered (dist = 0)
  const overlapFactor = Math.min(1, Math.max(0, jaccard / 100));
  const dist = 85 - overlapFactor * 52;
  const cxA = width / 2 - dist / 2;
  const cxB = width / 2 + dist / 2;

  return (
    <div className="venn-chart-container">
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ margin: "0 auto", display: "block" }}>
        <defs>
          <radialGradient id={`gradA-${a.id}`} cx="40%" cy="40%" r="60%">
            <stop offset="0%" stopColor={colorA} stopOpacity="0.45" />
            <stop offset="100%" stopColor={colorA} stopOpacity="0.15" />
          </radialGradient>
          <radialGradient id={`gradB-${b.id}`} cx="60%" cy="40%" r="60%">
            <stop offset="0%" stopColor={colorB} stopOpacity="0.45" />
            <stop offset="100%" stopColor={colorB} stopOpacity="0.15" />
          </radialGradient>
        </defs>

        {/* Circle A */}
        <circle
          cx={cxA}
          cy={centerY}
          r={rA}
          fill={`url(#gradA-${a.id})`}
          stroke={colorA}
          strokeWidth="1.5"
        />

        {/* Circle B */}
        <circle
          cx={cxB}
          cy={centerY}
          r={rB}
          fill={`url(#gradB-${b.id})`}
          stroke={colorB}
          strokeWidth="1.5"
        />

        {/* Overlap Label */}
        <text
          x={width / 2}
          y={centerY - 4}
          textAnchor="middle"
          fill="#ffffff"
          fontSize="14"
          fontWeight="700"
          fontFamily="var(--font-mono)"
        >
          {jaccard}%
        </text>
        <text
          x={width / 2}
          y={centerY + 12}
          textAnchor="middle"
          fill="var(--text-muted)"
          fontSize="9"
          fontFamily="var(--font-mono)"
        >
          {commonCount} común
        </text>

        {/* Handles */}
        <text
          x={cxA - 14}
          y={centerY + 3}
          textAnchor="middle"
          fill={colorA}
          fontSize="10"
          fontWeight="600"
          fontFamily="var(--font-mono)"
        >
          @{a.handle.slice(0, 7)}
        </text>

        <text
          x={cxB + 14}
          y={centerY + 3}
          textAnchor="middle"
          fill={colorB}
          fontSize="10"
          fontWeight="600"
          fontFamily="var(--font-mono)"
        >
          @{b.handle.slice(0, 7)}
        </text>
      </svg>
    </div>
  );
}
