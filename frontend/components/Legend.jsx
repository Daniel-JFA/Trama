"use client";

export default function Legend({ communities, activeFilter, onSelectFilter }) {
  if (!communities || communities.length === 0) return null;

  return (
    <div className="legend">
      {communities.map((c) => (
        <button
          key={c.id}
          className={`legend-chip ${activeFilter === c.id ? "legend-chip-active" : ""}`}
          style={{ "--chip-color": c.color }}
          onClick={() => onSelectFilter(activeFilter === c.id ? null : c.id)}
        >
          <span className="legend-dot" style={{ background: c.color }} />
          {c.name}
        </button>
      ))}
      <button
        className={`legend-chip ${activeFilter === "suspicious" ? "legend-chip-active" : ""}`}
        style={{ "--chip-color": "#E060B8" }}
        onClick={() =>
          onSelectFilter(activeFilter === "suspicious" ? null : "suspicious")
        }
      >
        <span className="legend-dot legend-dot-bot" />
        Solo sospechosas
      </button>
    </div>
  );
}
