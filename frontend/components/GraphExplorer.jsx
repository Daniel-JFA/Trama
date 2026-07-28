"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import * as d3 from "d3";
import { loadGraph } from "../lib/loadGraph";

// ─── Utilidades ──────────────────────────────────────────────────────────────

function initials(handle) {
  const parts = handle.replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, " ").trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return handle.slice(0, 2).toUpperCase();
}

function authColor(auth) {
  if (auth >= 70) return "#5AD1B3";
  if (auth >= 40) return "#E8C15A";
  return "#E060B8";
}

function Sparkline({ data, color }) {
  if (!data || data.length === 0) return null;
  const w = 220, h = 40, pad = 4;
  const max = Math.max(...data, 1);
  const xScale = (i) => pad + (i / (data.length - 1)) * (w - pad * 2);
  const yScale = (v) => h - pad - (v / max) * (h - pad * 2);
  const line = data.map((v, i) => `${i === 0 ? "M" : "L"}${xScale(i)},${yScale(v)}`).join(" ");
  return (
    <svg width={w} height={h} style={{ display: "block" }}>
      <path d={line} fill="none" stroke={color || "#8B7CF6"} strokeWidth={1.5} strokeLinejoin="round" />
      {data.map((v, i) => (
        <circle key={i} cx={xScale(i)} cy={yScale(v)} r={2} fill={color || "#8B7CF6"} opacity={0.7} />
      ))}
    </svg>
  );
}

// ─── Panel: Resumen ───────────────────────────────────────────────────────────

function PanelResumen({ graph, communities, onNodeClick }) {
  if (!graph) return null;
  const nodes = graph.nodes || [];
  const links = graph.links || [];
  const suspicious = nodes.filter((n) => n.bot >= 60).length;
  const pctSusp = nodes.length > 0 ? Math.round((suspicious / nodes.length) * 100) : 0;

  const topInfluence = [...nodes].sort((a, b) => b.influence - a.influence).slice(0, 8);
  const topBridge = [...nodes].sort((a, b) => b.bridge - a.bridge).slice(0, 5);

  const commMap = {};
  (communities || []).forEach((c) => { commMap[c.id] = c; });

  return (
    <div className="panel-content">
      <div className="panel-section">
        <h3 className="panel-heading">Resumen de la red</h3>
        <div className="kpi-grid">
          <div className="kpi-card">
            <span className="kpi-value">{nodes.length}</span>
            <span className="kpi-label">Perfiles</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-value">{graph.meta?.interactions?.toLocaleString() || links.length}</span>
            <span className="kpi-label">Interacciones</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-value">{communities?.length || 0}</span>
            <span className="kpi-label">Comunidades</span>
          </div>
          <div className="kpi-card" style={{ borderColor: pctSusp > 20 ? "#E060B8" : undefined }}>
            <span className="kpi-value" style={{ color: pctSusp > 20 ? "#E060B8" : undefined }}>{pctSusp}%</span>
            <span className="kpi-label">Sospechosas</span>
          </div>
        </div>
      </div>

      <div className="panel-section">
        <h3 className="panel-heading">Top influyentes</h3>
        <div className="rank-list">
          {topInfluence.map((n, i) => {
            const comm = commMap[n.comm];
            return (
              <button key={n.id} className="rank-item" onClick={() => onNodeClick(n)}>
                <span className="rank-pos">{i + 1}</span>
                <span className="rank-dot" style={{ background: comm?.color || "#666" }} />
                <span className="rank-handle">@{n.handle}</span>
                <div className="rank-bar-wrap">
                  <div className="rank-bar" style={{ width: `${n.influence}%`, background: comm?.color || "#666" }} />
                </div>
                <span className="rank-val">{n.influence}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="panel-section">
        <h3 className="panel-heading">Cuentas puente</h3>
        <p className="panel-note">Por aqui cruzan las narrativas entre comunidades</p>
        <div className="rank-list">
          {topBridge.map((n) => {
            const comm = commMap[n.comm];
            return (
              <button key={n.id} className="rank-item" onClick={() => onNodeClick(n)}>
                <span className="rank-dot" style={{ background: comm?.color || "#666" }} />
                <span className="rank-handle">@{n.handle}</span>
                <span className="rank-badge bridge-badge">puente</span>
                <span className="rank-val">{n.bridge}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="panel-section guide-section">
        <h3 className="panel-heading">Guia de lectura</h3>
        <ul className="guide-list">
          <li><span className="guide-dot" style={{ background: "#fff" }} /> Tamano del nodo = influencia real (PageRank)</li>
          <li><span className="guide-dot" style={{ background: "#E060B8" }} /> Color = comunidad detectada</li>
          <li><span className="guide-ring" /> Anillo rojo punteado = posible bot (indice &ge; 60)</li>
          <li>Haz clic en cualquier nodo para abrir su expediente</li>
        </ul>
      </div>
    </div>
  );
}

// ─── Panel: Expediente ────────────────────────────────────────────────────────

function PanelExpediente({ node, graph, communities, onAddToComparison, onNodeClick }) {
  if (!node) return null;
  const comm = (communities || []).find((c) => c.id === node.comm);

  const neighbors = [];
  if (graph) {
    const nodeLinks = graph.links.filter(
      (l) => l.source === node.id || l.target === node.id || l.source?.id === node.id || l.target?.id === node.id
    );
    const neighborIds = nodeLinks.map((l) => {
      const sid = typeof l.source === "object" ? l.source.id : l.source;
      const tid = typeof l.target === "object" ? l.target.id : l.target;
      return sid === node.id ? tid : sid;
    }).slice(0, 5);
    neighborIds.forEach((nid) => {
      const n = graph.nodes.find((nd) => nd.id === nid);
      if (n) neighbors.push(n);
    });
  }

  return (
    <div className="panel-content">
      <div className="expediente-header">
        <div className="avatar" style={{ background: comm?.color || "#444" }}>
          {initials(node.handle)}
        </div>
        <div className="expediente-info">
          <div className="expediente-handle">@{node.handle}</div>
          <div className="expediente-badges">
            {comm && <span className="badge" style={{ background: comm.color + "33", color: comm.color, border: `1px solid ${comm.color}` }}>{comm.name}</span>}
            {node.org && <span className="badge badge-org">Institucional</span>}
            {node.bot >= 60 && <span className="badge badge-bot">Posible amplificacion</span>}
          </div>
        </div>
        {node.bot >= 75 && (
          <div className="sello-sospechosa">SOSPECHOSA</div>
        )}
      </div>

      <div className="metrics-grid">
        <div className="metric-card">
          <span className="metric-label">Influencia</span>
          <span className="metric-value" style={{ color: "#8B7CF6" }}>{node.influence}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Conexiones</span>
          <span className="metric-value">{node.degree}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Indice puente</span>
          <span className="metric-value" style={{ color: "#5AD1B3" }}>{node.bridge}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Autenticidad</span>
          <span className="metric-value" style={{ color: authColor(node.auth) }}>{node.auth}</span>
        </div>
      </div>

      <div className="auth-bar-wrap">
        <div className="auth-bar-label">Autenticidad</div>
        <div className="auth-bar-track">
          <div
            className="auth-bar-fill"
            style={{ width: `${node.auth}%`, background: authColor(node.auth) }}
          />
        </div>
        <span className="auth-bar-pct">{node.auth}%</span>
      </div>

      <div className="profile-stats">
        <div className="stat">
          <span className="stat-val">{node.followers?.toLocaleString() || "—"}</span>
          <span className="stat-label">Seguidores</span>
        </div>
        <div className="stat">
          <span className="stat-val">{node.posts?.toLocaleString() || "—"}</span>
          <span className="stat-label">Publicaciones</span>
        </div>
      </div>

      {node.act && node.act.length > 0 && (
        <div className="panel-section">
          <h4 className="panel-heading-sm">Actividad semanal (12 semanas)</h4>
          <Sparkline data={node.act} color={comm?.color} />
          {node.comm === 3 && (
            <p className="panel-note highlight-note">
              Pico coordinado visible en semanas 6-7 junto con otros miembros de esta comunidad.
            </p>
          )}
        </div>
      )}

      {neighbors.length > 0 && (
        <div className="panel-section">
          <h4 className="panel-heading-sm">Conexiones destacadas</h4>
          <div className="connections-list">
            {neighbors.map((n) => {
              const nc = (communities || []).find((c) => c.id === n.comm);
              return (
                <button key={n.id} className="connection-item" onClick={() => onNodeClick(n)}>
                  <span className="conn-dot" style={{ background: nc?.color || "#666" }} />
                  <span className="conn-handle">@{n.handle}</span>
                  <span className="conn-infl">{n.influence} inf.</span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      <button className="btn-add-comparison" onClick={() => onAddToComparison(node)}>
        Anadir a comparacion
      </button>
    </div>
  );
}

// ─── Panel: Comparacion ───────────────────────────────────────────────────────

function PanelComparacion({ profiles, graph, communities, onRemove, onNodeClick }) {
  const commMap = {};
  (communities || []).forEach((c) => { commMap[c.id] = c; });

  // Calcular Jaccard en cliente sobre sets de vecinos
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

  const neighborSets = profiles.map((p) => ({ id: p.id, set: buildNeighborSet(p.id) }));

  const pairs = [];
  for (let i = 0; i < profiles.length; i++) {
    for (let j = i + 1; j < profiles.length; j++) {
      const sa = neighborSets[i].set;
      const sb = neighborSets[j].set;
      const common = [...sa].filter((x) => sb.has(x));
      const union = new Set([...sa, ...sb]);
      const jaccard = union.size > 0 ? Math.round((common.length / union.size) * 100) : 0;
      const commonNodes = common
        .slice(0, 8)
        .map((id) => graph?.nodes.find((n) => n.id === id))
        .filter(Boolean);
      pairs.push({ a: profiles[i], b: profiles[j], jaccard, common, commonNodes });
    }
  }

  return (
    <div className="panel-content">
      <h3 className="panel-heading">Comparacion de audiencias</h3>

      <div className="comparison-chips">
        {profiles.map((p) => {
          const comm = commMap[p.comm];
          return (
            <div key={p.id} className="comp-chip" style={{ borderColor: comm?.color || "#666" }}>
              <span className="comp-chip-dot" style={{ background: comm?.color || "#666" }} />
              <span>@{p.handle}</span>
              <button className="comp-chip-remove" onClick={() => onRemove(p.id)}>x</button>
            </div>
          );
        })}
        {profiles.length < 3 && (
          <span className="comp-hint">Haz clic en un nodo y usa "Anadir a comparacion"</span>
        )}
      </div>

      {pairs.length > 0 && (
        <div className="pairs-section">
          {pairs.map((pair, i) => (
            <div key={i} className="pair-card">
              <div className="pair-header">
                <span className="pair-name">@{pair.a.handle}</span>
                <span className="pair-sep">vs</span>
                <span className="pair-name">@{pair.b.handle}</span>
              </div>
              <div className="jaccard-row">
                <span className="jaccard-label">Solapamiento Jaccard</span>
                <span className="jaccard-val">{pair.jaccard}%</span>
              </div>
              <div className="jaccard-track">
                <div className="jaccard-fill" style={{ width: `${pair.jaccard}%` }} />
              </div>
              <p className="jaccard-note">
                {pair.jaccard >= 40
                  ? "Solapamiento alto: audiencias redundantes."
                  : pair.jaccard >= 15
                  ? "Solapamiento moderado: audiencias parcialmente compartidas."
                  : "Solapamiento bajo: alcance complementario."}
              </p>
              <p className="jaccard-common">{pair.common.length} contacto(s) en comun</p>

              {profiles.length === 2 && pair.commonNodes.length > 0 && (
                <div className="common-nodes">
                  <p className="common-nodes-title">Contactos comunes:</p>
                  {pair.commonNodes.map((n) => {
                    const nc = commMap[n.comm];
                    return (
                      <button key={n.id} className="connection-item" onClick={() => onNodeClick(n)}>
                        <span className="conn-dot" style={{ background: nc?.color || "#666" }} />
                        <span className="conn-handle">@{n.handle}</span>
                      </button>
                    );
                  })}
                  {pair.common.length > 8 && (
                    <span className="common-more">+{pair.common.length - 8} mas</span>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {profiles.length === 0 && (
        <p className="panel-note">Anade hasta 3 perfiles desde sus expedientes para comparar sus audiencias.</p>
      )}
    </div>
  );
}

// ─── Componente principal ─────────────────────────────────────────────────────

export default function GraphExplorer() {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const simRef = useRef(null);
  const zoomRef = useRef(null);
  const transformRef = useRef({ k: 1, x: 0, y: 0 });
  const hoveredRef = useRef(null);
  const selectedRef = useRef(null);
  const graphDataRef = useRef(null);
  const filterRef = useRef({ community: null, onlySuspicious: false });
  const searchRef = useRef("");
  const comparisonRef = useRef([]);
  const animFrameRef = useRef(null);

  const [graph, setGraph] = useState(null);
  const [dataSource, setDataSource] = useState("backend");
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState(null);
  const [panel, setPanel] = useState("resumen"); // resumen | expediente | comparacion
  const [comparison, setComparison] = useState([]);
  const [searchValue, setSearchValue] = useState("");
  const [activeFilter, setActiveFilter] = useState(null); // comm id o "suspicious"

  // Carga inicial
  useEffect(() => {
    loadGraph().then(({ graph: g, source }) => {
      setGraph(g);
      setDataSource(source);
      graphDataRef.current = g;
      setLoading(false);
    });
  }, []);

  // Mantener refs sincronizados
  useEffect(() => {
    comparisonRef.current = comparison;
  }, [comparison]);

  // ─── Dibujo en canvas ──────────────────────────────────────────────────────

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const W = canvas.width / dpr;
    const H = canvas.height / dpr;

    ctx.save();
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, W, H);

    const g = graphDataRef.current;
    if (!g || !g.nodes) { ctx.restore(); return; }

    const { k, x, y } = transformRef.current;
    ctx.translate(x, y);
    ctx.scale(k, k);

    const commMap = {};
    (g.communities || []).forEach((c) => { commMap[c.id] = c; });

    const hovered = hoveredRef.current;
    const selected = selectedRef.current;
    const filter = filterRef.current;
    const search = searchRef.current.toLowerCase();
    const zoom = k;

    // Determinar sets para highlight de ego-red
    let egoNeighbors = null;
    const focusNode = hovered || selected;
    if (focusNode) {
      egoNeighbors = new Set();
      g.links.forEach((l) => {
        const sid = typeof l.source === "object" ? l.source.id : l.source;
        const tid = typeof l.target === "object" ? l.target.id : l.target;
        if (sid === focusNode.id) egoNeighbors.add(tid);
        if (tid === focusNode.id) egoNeighbors.add(sid);
      });
    }

    // Nodos a mostrar
    const maxInfluence = Math.max(...g.nodes.map((n) => n.influence), 1);

    function isVisible(n) {
      if (filter.onlySuspicious && n.bot < 60) return false;
      if (filter.community !== null && n.comm !== filter.community) return false;
      return true;
    }

    const visibleIds = new Set(g.nodes.filter(isVisible).map((n) => n.id));

    // ─── Aristas ───────────────────────────────────────────────────────────
    g.links.forEach((l) => {
      const sid = typeof l.source === "object" ? l.source.id : l.source;
      const tid = typeof l.target === "object" ? l.target.id : l.target;
      if (!visibleIds.has(sid) || !visibleIds.has(tid)) return;

      const sn = typeof l.source === "object" ? l.source : g.nodes.find((n) => n.id === l.source);
      const tn = typeof l.target === "object" ? l.target : g.nodes.find((n) => n.id === l.target);
      if (!sn || !tn || sn.x == null || tn.x == null) return;

      let alpha = 0.12;
      let strokeColor = "#ffffff";

      if (egoNeighbors) {
        const isEgoEdge =
          sn.id === focusNode.id || tn.id === focusNode.id;
        const isNeighborEdge =
          egoNeighbors.has(sn.id) && egoNeighbors.has(tn.id);

        if (isEgoEdge) {
          const comm = commMap[focusNode.comm];
          strokeColor = comm?.color || "#ffffff";
          alpha = 0.55;
        } else if (isNeighborEdge) {
          alpha = 0.08;
        } else {
          alpha = 0.03;
        }
      }

      ctx.beginPath();
      ctx.moveTo(sn.x, sn.y);
      ctx.lineTo(tn.x, tn.y);
      ctx.strokeStyle = strokeColor;
      ctx.globalAlpha = alpha;
      ctx.lineWidth = 0.8 / k;
      ctx.stroke();
      ctx.globalAlpha = 1;
    });

    // ─── Nodos ─────────────────────────────────────────────────────────────
    g.nodes.forEach((n) => {
      if (!visibleIds.has(n.id)) return;
      if (n.x == null) return;

      const comm = commMap[n.comm];
      const r = 3.5 + Math.sqrt(n.influence / maxInfluence) * 13;
      let nodeAlpha = 1;

      if (egoNeighbors) {
        if (n.id !== focusNode.id && !egoNeighbors.has(n.id)) {
          nodeAlpha = 0.13;
        }
      }

      if (search && !n.handle.toLowerCase().includes(search)) {
        nodeAlpha = Math.min(nodeAlpha, 0.1);
      }

      ctx.globalAlpha = nodeAlpha;

      // Anillo rojo punteado: bot >= 60
      if (n.bot >= 60) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, r + 4 / k, 0, Math.PI * 2);
        ctx.strokeStyle = "#E060B8";
        ctx.lineWidth = 1.5 / k;
        ctx.setLineDash([3 / k, 3 / k]);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // Anillo blanco: nodo seleccionado o en comparacion
      const inComparison = comparisonRef.current.some((c) => c.id === n.id);
      if (n.id === selected?.id || inComparison) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, r + 5 / k, 0, Math.PI * 2);
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2 / k;
        ctx.stroke();
      }

      // Cuerpo del nodo
      ctx.beginPath();
      ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
      ctx.fillStyle = comm?.color || "#888";
      ctx.fill();

      ctx.globalAlpha = 1;

      // Etiqueta @handle
      const showLabel =
        zoom > 0.55 && (n.influence >= 42 || n.id === hovered?.id || n.id === selected?.id);
      if (showLabel) {
        const label = "@" + n.handle;
        ctx.font = `${Math.max(9, 11 / k)}px 'IBM Plex Mono', monospace`;
        ctx.fillStyle = "#ffffff";
        ctx.globalAlpha = 0.9;
        ctx.textAlign = "center";
        ctx.fillText(label, n.x, n.y - r - 5 / k);
        ctx.globalAlpha = 1;
      }
    });

    ctx.restore();
  }, []);

  const scheduleDraw = useCallback(() => {
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    animFrameRef.current = requestAnimationFrame(draw);
  }, [draw]);

  // ─── Setup simulación + zoom ─────────────────────────────────────────────

  useEffect(() => {
    if (!graph || !canvasRef.current || !containerRef.current) return;

    const canvas = canvasRef.current;
    const container = containerRef.current;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    const resize = () => {
      const rect = container.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      canvas.style.width = rect.width + "px";
      canvas.style.height = rect.height + "px";
      scheduleDraw();
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(container);

    // Centros por comunidad
    const commCenters = {
      0: { x: 0.25, y: 0.3 },
      1: { x: 0.75, y: 0.3 },
      2: { x: 0.35, y: 0.7 },
      3: { x: 0.7,  y: 0.7 },
    };

    const getW = () => canvas.width / dpr;
    const getH = () => canvas.height / dpr;

    // Inicializar posiciones
    graph.nodes.forEach((n) => {
      const center = commCenters[n.comm] || { x: 0.5, y: 0.5 };
      n.x = center.x * getW() + (Math.random() - 0.5) * 80;
      n.y = center.y * getH() + (Math.random() - 0.5) * 80;
    });

    const sim = d3
      .forceSimulation(graph.nodes)
      .force(
        "link",
        d3
          .forceLink(graph.links)
          .id((d) => d.id)
          .distance(38)
          .strength(0.5)
      )
      .force("charge", d3.forceManyBody().strength(-52))
      .force("collide", d3.forceCollide().radius((d) => {
        const maxInf = Math.max(...graph.nodes.map((n) => n.influence), 1);
        return 3.5 + Math.sqrt(d.influence / maxInf) * 13 + 3;
      }))
      .force("x", d3.forceX((d) => (commCenters[d.comm]?.x || 0.5) * getW()).strength(0.08))
      .force("y", d3.forceY((d) => (commCenters[d.comm]?.y || 0.5) * getH()).strength(0.08))
      .alphaDecay(0.02)
      .on("tick", scheduleDraw);

    simRef.current = sim;

    // Zoom
    const zoom = d3
      .zoom()
      .scaleExtent([0.25, 5])
      .on("zoom", (event) => {
        transformRef.current = event.transform;
        scheduleDraw();
      });

    zoomRef.current = zoom;
    d3.select(canvas).call(zoom);

    // Centrar cámara al inicio
    const initialTransform = d3.zoomIdentity.translate(0, 0).scale(1);
    d3.select(canvas).call(zoom.transform, initialTransform);

    // Hover
    const getNodeAt = (mx, my) => {
      const { k, x, y } = transformRef.current;
      const wx = (mx - x) / k;
      const wy = (my - y) / k;
      const maxInf = Math.max(...graph.nodes.map((n) => n.influence), 1);
      let best = null, bestDist = Infinity;
      for (const n of graph.nodes) {
        if (n.x == null) continue;
        const filter = filterRef.current;
        if (filter.onlySuspicious && n.bot < 60) continue;
        if (filter.community !== null && n.comm !== filter.community) continue;
        const r = 3.5 + Math.sqrt(n.influence / maxInf) * 13 + 4;
        const dx = wx - n.x, dy = wy - n.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < r && dist < bestDist) { best = n; bestDist = dist; }
      }
      return best;
    };

    let tooltipEl = document.getElementById("trama-tooltip");
    if (!tooltipEl) {
      tooltipEl = document.createElement("div");
      tooltipEl.id = "trama-tooltip";
      tooltipEl.style.cssText = `
        position:fixed;pointer-events:none;background:#101A2E;border:1px solid rgba(255,255,255,0.15);
        border-radius:8px;padding:10px 14px;font-family:'IBM Plex Mono',monospace;font-size:12px;
        color:#fff;z-index:1000;opacity:0;transition:opacity 0.15s;max-width:200px;
      `;
      document.body.appendChild(tooltipEl);
    }

    const onMove = (e) => {
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const node = getNodeAt(mx, my);

      if (node !== hoveredRef.current) {
        hoveredRef.current = node;
        scheduleDraw();
      }

      if (node) {
        const comm = (graph.communities || []).find((c) => c.id === node.comm);
        tooltipEl.innerHTML = `
          <div style="font-weight:600;margin-bottom:4px;color:${comm?.color || '#fff'}">@${node.handle}</div>
          <div style="opacity:0.7;font-size:11px">${comm?.name || ''}</div>
          <div style="margin-top:6px;display:flex;gap:12px">
            <span>Inf. <b>${node.influence}</b></span>
            <span>Puente <b>${node.bridge}</b></span>
          </div>
          ${node.bot >= 60 ? '<div style="color:#E060B8;margin-top:4px;font-size:11px">Posible amplificacion</div>' : ''}
        `;
        tooltipEl.style.left = (e.clientX + 14) + "px";
        tooltipEl.style.top = (e.clientY - 10) + "px";
        tooltipEl.style.opacity = "1";
        canvas.style.cursor = "pointer";
      } else {
        tooltipEl.style.opacity = "0";
        canvas.style.cursor = "grab";
      }
    };

    const onLeave = () => {
      hoveredRef.current = null;
      tooltipEl.style.opacity = "0";
      scheduleDraw();
    };

    const onClick = (e) => {
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const node = getNodeAt(mx, my);
      if (node) {
        selectedRef.current = node;
        setSelectedNode(node);
        setPanel("expediente");

        // Centrar cámara con transición
        const W = getW(), H = getH();
        const targetK = Math.max(transformRef.current.k, 1.2);
        const targetX = W / 2 - node.x * targetK;
        const targetY = H / 2 - node.y * targetK;
        d3.select(canvas)
          .transition()
          .duration(500)
          .call(zoom.transform, d3.zoomIdentity.translate(targetX, targetY).scale(targetK));

        scheduleDraw();
      }
    };

    canvas.addEventListener("mousemove", onMove);
    canvas.addEventListener("mouseleave", onLeave);
    canvas.addEventListener("click", onClick);

    return () => {
      sim.stop();
      ro.disconnect();
      canvas.removeEventListener("mousemove", onMove);
      canvas.removeEventListener("mouseleave", onLeave);
      canvas.removeEventListener("click", onClick);
      tooltipEl.style.opacity = "0";
    };
  }, [graph, scheduleDraw]);

  // ─── Sincronizar filtros y redraw ────────────────────────────────────────
  useEffect(() => {
    filterRef.current = {
      community: activeFilter === "suspicious" ? null : activeFilter,
      onlySuspicious: activeFilter === "suspicious",
    };
    scheduleDraw();
  }, [activeFilter, scheduleDraw]);

  useEffect(() => {
    searchRef.current = searchValue;
    scheduleDraw();
  }, [searchValue, scheduleDraw]);

  // ─── Exportar PNG ────────────────────────────────────────────────────────
  const exportPNG = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const W = canvas.width / dpr;
    const H = canvas.height / dpr;

    const exportCanvas = document.createElement("canvas");
    exportCanvas.width = canvas.width;
    exportCanvas.height = canvas.height;
    const ectx = exportCanvas.getContext("2d");
    ectx.fillStyle = "#0B1220";
    ectx.fillRect(0, 0, exportCanvas.width, exportCanvas.height);
    ectx.drawImage(canvas, 0, 0);

    const link = document.createElement("a");
    link.download = `trama-${graph?.meta?.topic || "grafo"}.png`;
    link.href = exportCanvas.toDataURL("image/png");
    link.click();
  }, [graph]);

  // ─── Handlers ────────────────────────────────────────────────────────────
  const handleNodeClick = useCallback((node) => {
    selectedRef.current = node;
    setSelectedNode(node);
    setPanel("expediente");
  }, []);

  const handleAddToComparison = useCallback((node) => {
    setComparison((prev) => {
      if (prev.some((p) => p.id === node.id)) return prev;
      if (prev.length >= 3) return prev;
      return [...prev, node];
    });
    setPanel("comparacion");
  }, []);

  const handleRemoveFromComparison = useCallback((id) => {
    setComparison((prev) => prev.filter((p) => p.id !== id));
  }, []);

  const handleSearch = useCallback(
    (e) => {
      if (e.key === "Enter" && searchValue) {
        const node = graph?.nodes.find((n) =>
          n.handle.toLowerCase().includes(searchValue.toLowerCase())
        );
        if (node) handleNodeClick(node);
      }
    },
    [searchValue, graph, handleNodeClick]
  );

  const communities = graph?.communities || [];

  // ─── Render ──────────────────────────────────────────────────────────────
  return (
    <div className="app-root">
      {/* Barra superior */}
      <header className="top-bar">
        <div className="top-bar-left">
          <span className="brand">TRAMA</span>
          {graph && (
            <div className="project-chip">
              <span className="chip-topic">{graph.meta?.topic}</span>
              <span className="chip-sep" />
              {graph.meta?.weeks > 0 && <span className="chip-detail">{graph.meta.weeks} semanas</span>}
              <span className="chip-sep" />
              <span className={`chip-source ${dataSource === "local" ? "chip-source-local" : "chip-source-live"}`}>
                {dataSource === "local" ? "sin backend (muestra local)" : "backend activo"}
              </span>
            </div>
          )}
        </div>
        <div className="top-bar-right">
          <input
            type="text"
            className="search-input"
            placeholder="Buscar por handle..."
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            onKeyDown={handleSearch}
          />
          <button className="btn-secondary" onClick={exportPNG}>Exportar PNG</button>
          {comparison.length > 0 && (
            <button
              className="btn-secondary btn-compare-active"
              onClick={() => setPanel("comparacion")}
            >
              Comparar ({comparison.length})
            </button>
          )}
        </div>
      </header>

      {/* Cuerpo principal */}
      <main className="main-content">
        {/* Lienzo del grafo */}
        <div className="graph-area" ref={containerRef}>
          {loading && (
            <div className="loading-overlay">
              <div className="loading-spinner" />
              <span>Cargando red...</span>
            </div>
          )}
          <canvas ref={canvasRef} className="graph-canvas" />

          {/* Leyenda flotante */}
          {!loading && graph && (
            <div className="legend">
              {communities.map((c) => (
                <button
                  key={c.id}
                  className={`legend-chip ${activeFilter === c.id ? "legend-chip-active" : ""}`}
                  style={{ "--chip-color": c.color }}
                  onClick={() => setActiveFilter(activeFilter === c.id ? null : c.id)}
                >
                  <span className="legend-dot" style={{ background: c.color }} />
                  {c.name}
                </button>
              ))}
              <button
                className={`legend-chip ${activeFilter === "suspicious" ? "legend-chip-active" : ""}`}
                style={{ "--chip-color": "#E060B8" }}
                onClick={() => setActiveFilter(activeFilter === "suspicious" ? null : "suspicious")}
              >
                <span className="legend-dot legend-dot-bot" />
                Solo sospechosas
              </button>
            </div>
          )}
        </div>

        {/* Panel lateral */}
        <aside className="side-panel">
          {/* Tabs del panel */}
          <div className="panel-tabs">
            <button
              className={`panel-tab ${panel === "resumen" ? "panel-tab-active" : ""}`}
              onClick={() => setPanel("resumen")}
            >
              Resumen
            </button>
            <button
              className={`panel-tab ${panel === "expediente" ? "panel-tab-active" : ""}`}
              onClick={() => setPanel("expediente")}
              disabled={!selectedNode}
            >
              Expediente
            </button>
            <button
              className={`panel-tab ${panel === "comparacion" ? "panel-tab-active" : ""}`}
              onClick={() => setPanel("comparacion")}
            >
              Comparar {comparison.length > 0 ? `(${comparison.length})` : ""}
            </button>
          </div>

          <div className="panel-body">
            {panel === "resumen" && (
              <PanelResumen
                graph={graph}
                communities={communities}
                onNodeClick={handleNodeClick}
              />
            )}
            {panel === "expediente" && (
              <PanelExpediente
                node={selectedNode}
                graph={graph}
                communities={communities}
                onAddToComparison={handleAddToComparison}
                onNodeClick={handleNodeClick}
              />
            )}
            {panel === "comparacion" && (
              <PanelComparacion
                profiles={comparison}
                graph={graph}
                communities={communities}
                onRemove={handleRemoveFromComparison}
                onNodeClick={handleNodeClick}
              />
            )}
          </div>
        </aside>
      </main>

      {/* Pie */}
      <footer className="app-footer">
        {graph?.meta?.synthetic && (
          <span>Datos sinteticos — Red ficticia generada para demostracion. #ReformaDelAgua no corresponde a ningun evento real.</span>
        )}
        {!graph?.meta?.synthetic && (
          <span>Datos importados — El indice de autenticidad usa una heuristica placeholder, no es un clasificador validado.</span>
        )}
      </footer>
    </div>
  );
}
