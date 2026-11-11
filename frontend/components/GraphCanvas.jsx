"use client";

import { useEffect, useRef, useCallback, useState, forwardRef, useImperativeHandle } from "react";
import * as d3 from "d3";

const GraphCanvas = forwardRef(function GraphCanvas(
  {
    graph,
    activeFilter,
    searchValue,
    selectedNode,
    comparison,
    currentWeek = null,
    showCoornetLayer = false,
    onToggleCoornetLayer,
    onNodeSelect,
  },
  ref
) {
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
  const currentWeekRef = useRef(null);
  const animFrameRef = useRef(null);
  const isDraggingRef = useRef(false);
  const quadtreeRef = useRef(null);

  // Visual toggles
  const [showHulls, setShowHulls] = useState(true);
  const [showAllLabels, setShowAllLabels] = useState(false);
  const [showCoornet, setShowCoornet] = useState(showCoornetLayer);
  const showHullsRef = useRef(true);
  const showAllLabelsRef = useRef(false);
  const showCoornetRef = useRef(showCoornetLayer);

  useEffect(() => {
    setShowCoornet(showCoornetLayer);
  }, [showCoornetLayer]);

  useEffect(() => {
    showCoornetRef.current = showCoornet;
    scheduleDraw();
  }, [showCoornet]);

  useEffect(() => {
    showHullsRef.current = showHulls;
  }, [showHulls]);

  useEffect(() => {
    showAllLabelsRef.current = showAllLabels;
  }, [showAllLabels]);

  // Expose canvas methods
  useImperativeHandle(ref, () => ({
    getCanvas: () => canvasRef.current,
    resetZoom: () => handleFitView(),
    zoomIn: () => handleZoomIn(),
    zoomOut: () => handleZoomOut(),
  }));

  useEffect(() => {
    currentWeekRef.current = currentWeek;
  }, [currentWeek]);

  useEffect(() => {
    graphDataRef.current = graph;
  }, [graph]);

  useEffect(() => {
    selectedRef.current = selectedNode;
  }, [selectedNode]);

  useEffect(() => {
    comparisonRef.current = comparison;
  }, [comparison]);

  useEffect(() => {
    filterRef.current = {
      community: activeFilter === "suspicious" ? null : activeFilter,
      onlySuspicious: activeFilter === "suspicious",
    };
  }, [activeFilter]);

  useEffect(() => {
    searchRef.current = searchValue;
  }, [searchValue]);

  // ─── Render loop ──────────────────────────────────────────────────────────
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
    if (!g || !g.nodes || g.nodes.length === 0) {
      ctx.restore();
      return;
    }

    const { k, x, y } = transformRef.current;
    ctx.translate(x, y);
    ctx.scale(k, k);

    const commMap = {};
    (g.communities || []).forEach((c) => {
      commMap[c.id] = c;
    });

    const hovered = hoveredRef.current;
    const selected = selectedRef.current;
    const filter = filterRef.current;
    const search = searchRef.current.toLowerCase();
    const zoom = k;
    const now = Date.now();

    // Node visibility
    function isVisible(n) {
      if (filter.onlySuspicious && n.bot < 60) return false;
      if (filter.community !== null && n.comm !== filter.community) return false;
      return true;
    }

    const visibleNodes = g.nodes.filter(isVisible);
    const visibleIds = new Set(visibleNodes.map((n) => n.id));

    // Focus / ego-network detection
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

    const maxInfluence = Math.max(...g.nodes.map((n) => n.influence || 1), 1);

    // ─── 1. Community Clouds / Hulls ────────────────────────────────────────
    if (showHullsRef.current && (!filter.community && !filter.onlySuspicious)) {
      (g.communities || []).forEach((c) => {
        const cNodes = visibleNodes.filter((n) => n.comm === c.id && n.x != null);
        if (cNodes.length < 3) return;

        const points = cNodes.map((n) => [n.x, n.y]);
        const hull = d3.polygonHull(points);
        if (!hull || hull.length < 3) return;

        // Expanded smoothed hull polygon
        ctx.beginPath();
        const pad = 24 / Math.sqrt(k);
        const centroid = d3.polygonCentroid(hull);

        const expanded = hull.map(([px, py]) => {
          const dx = px - centroid[0];
          const dy = py - centroid[1];
          const len = Math.sqrt(dx * dx + dy * dy) || 1;
          return [px + (dx / len) * pad, py + (dy / len) * pad];
        });

        ctx.moveTo(expanded[0][0], expanded[0][1]);
        for (let i = 1; i < expanded.length; i++) {
          const midX = (expanded[i - 1][0] + expanded[i][0]) / 2;
          const midY = (expanded[i - 1][1] + expanded[i][1]) / 2;
          ctx.quadraticCurveTo(expanded[i - 1][0], expanded[i - 1][1], midX, midY);
        }
        ctx.closePath();

        ctx.fillStyle = c.color;
        ctx.globalAlpha = 0.055;
        ctx.fill();

        ctx.strokeStyle = c.color;
        ctx.lineWidth = 1.2 / k;
        ctx.globalAlpha = 0.18;
        ctx.stroke();
        ctx.globalAlpha = 1;

        // Centroid watermark name label
        if (zoom > 0.4) {
          ctx.font = `600 ${Math.max(10, 13 / Math.sqrt(k))}px 'Space Grotesk', sans-serif`;
          ctx.fillStyle = c.color;
          ctx.globalAlpha = 0.35;
          ctx.textAlign = "center";
          ctx.fillText(c.name.toUpperCase(), centroid[0], centroid[1]);
          ctx.globalAlpha = 1;
        }
      });
    }

    // ─── 2. Links with Gradients & Energy Pulse ────────────────────────────
    g.links.forEach((l) => {
      const sid = typeof l.source === "object" ? l.source.id : l.source;
      const tid = typeof l.target === "object" ? l.target.id : l.target;
      if (!visibleIds.has(sid) || !visibleIds.has(tid)) return;

      const sn = typeof l.source === "object" ? l.source : g.nodes.find((n) => n.id === l.source);
      const tn = typeof l.target === "object" ? l.target : g.nodes.find((n) => n.id === l.target);
      if (!sn || !tn || sn.x == null || tn.x == null) return;

      const commS = commMap[sn.comm];
      const commT = commMap[tn.comm];

      let alpha = 0.14;
      let strokeWidth = 0.85 / k;
      const isEgoEdge = focusNode && (sn.id === focusNode.id || tn.id === focusNode.id);
      const isNeighborEdge = egoNeighbors && egoNeighbors.has(sn.id) && egoNeighbors.has(tn.id);

      if (egoNeighbors) {
        if (isEgoEdge) {
          alpha = 0.75;
          strokeWidth = 1.8 / k;
        } else if (isNeighborEdge) {
          alpha = 0.1;
          strokeWidth = 0.8 / k;
        } else {
          alpha = 0.02;
        }
      }

      ctx.beginPath();
      ctx.moveTo(sn.x, sn.y);
      ctx.lineTo(tn.x, tn.y);

      // Gradient linking source and target community colors
      if (commS?.color && commT?.color && commS.color !== commT.color && zoom > 0.6) {
        const grad = ctx.createLinearGradient(sn.x, sn.y, tn.x, tn.y);
        grad.addColorStop(0, commS.color);
        grad.addColorStop(1, commT.color);
        ctx.strokeStyle = grad;
      } else {
        ctx.strokeStyle = commS?.color || "#ffffff";
      }

      ctx.globalAlpha = alpha;
      ctx.lineWidth = strokeWidth;
      ctx.stroke();

      // Traveling energy pulse particle on ego edges
      if (isEgoEdge) {
        const speed = 0.0012;
        const progress = (now * speed + (sn.id * 0.17)) % 1;
        const px = sn.x + (tn.x - sn.x) * progress;
        const py = sn.y + (tn.y - sn.y) * progress;
        ctx.beginPath();
        ctx.arc(px, py, 2.5 / k, 0, Math.PI * 2);
        ctx.fillStyle = "#ffffff";
        ctx.globalAlpha = 0.9;
        ctx.fill();
      }

      ctx.globalAlpha = 1;
    });

    // ─── 2.1 Capa Visual Secundaria: Co-compartición CooRnet (Sprint 3) ───
    if (showCoornetRef.current) {
      const coornetLinks = g.coornet_links || [];
      const nodeMap = new Map();
      g.nodes.forEach((n) => {
        nodeMap.set(n.id, n);
        if (n.handle) nodeMap.set(n.handle.toLowerCase(), n);
      });

      coornetLinks.forEach((l) => {
        const sKey = typeof l.source === "object" ? l.source.id : l.source;
        const tKey = typeof l.target === "object" ? l.target.id : l.target;
        const sn = typeof l.source === "object" ? l.source : (nodeMap.get(sKey) || nodeMap.get(String(sKey).toLowerCase()));
        const tn = typeof l.target === "object" ? l.target : (nodeMap.get(tKey) || nodeMap.get(String(tKey).toLowerCase()));

        if (!sn || !tn || sn.x == null || tn.x == null) return;
        if (!visibleIds.has(sn.id) || !visibleIds.has(tn.id)) return;

        const weight = l.weight || 2;
        const isSig = l.is_statistically_significant ?? (l.p_value != null ? l.p_value < 0.05 : true);

        ctx.save();
        ctx.beginPath();
        ctx.moveTo(sn.x, sn.y);
        ctx.lineTo(tn.x, tn.y);

        // Estilo característico de CooRnet: línea punteada/discontinua neón
        ctx.setLineDash([7 / k, 4 / k]);
        ctx.lineDashOffset = -(now * 0.02) % 22;

        if (isSig) {
          ctx.strokeStyle = "#EC4899"; // Magenta neón forense
          ctx.lineWidth = Math.max(1.8, Math.min(4.5, 1.4 + weight * 0.5)) / k;
          ctx.globalAlpha = 0.85;
          ctx.shadowColor = "#EC4899";
          ctx.shadowBlur = 10 / k;
        } else {
          ctx.strokeStyle = "#94A3B8";
          ctx.lineWidth = 1.0 / k;
          ctx.globalAlpha = 0.35;
        }

        ctx.stroke();
        ctx.restore();
      });
    }

    // ─── 3. Nodes ──────────────────────────────────────────────────────────
    g.nodes.forEach((n) => {
      if (!visibleIds.has(n.id)) return;
      if (n.x == null) return;

      const comm = commMap[n.comm];
      const infNorm = Math.sqrt((n.influence || 1) / maxInfluence);
      let baseRadius = 4 + infNorm * 14;
      let r = baseRadius;

      // Halo distintivo de CooRnet para cuentas sincronizadas cuando la capa está activa
      if (showCoornetRef.current && (n.bot >= 60 || n.comm === 3)) {
        ctx.save();
        ctx.beginPath();
        ctx.arc(n.x, n.y, r + 5 / k, 0, Math.PI * 2);
        ctx.strokeStyle = "#EC4899";
        ctx.lineWidth = 2 / k;
        ctx.globalAlpha = 0.7 + Math.sin(now * 0.006 + n.id) * 0.25;
        ctx.shadowColor = "#EC4899";
        ctx.shadowBlur = 10 / k;
        ctx.stroke();
        ctx.restore();
      }

      // Temporal scaling during time-travel
      const activeWeek = currentWeekRef.current;
      let isWeekPeak = false;
      if (activeWeek !== null && n.act && n.act.length >= activeWeek) {
        const weekAct = n.act[activeWeek - 1] || 0;
        const factor = Math.min(2.8, Math.max(0.35, weekAct / 14));
        r = baseRadius * (0.55 + factor * 0.45);
        if (weekAct >= 35) {
          isWeekPeak = true;
          // Pulsing activity wave
          const pulse = (Math.sin(now / 150) + 1) * 0.5;
          ctx.beginPath();
          ctx.arc(n.x, n.y, r + (6 + pulse * 6) / k, 0, Math.PI * 2);
          ctx.fillStyle = "rgba(224, 96, 184, 0.35)";
          ctx.fill();
        }
      }

      let nodeAlpha = 1;
      if (egoNeighbors) {
        if (n.id !== focusNode.id && !egoNeighbors.has(n.id)) {
          nodeAlpha = 0.12;
        }
      }

      if (search && !n.handle.toLowerCase().includes(search)) {
        nodeAlpha = Math.min(nodeAlpha, 0.08);
      }

      ctx.globalAlpha = nodeAlpha;

      // Outer glow for high influence hubs
      if (n.influence >= 45 && nodeAlpha > 0.5) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, r + 8 / k, 0, Math.PI * 2);
        ctx.fillStyle = comm?.color || "#8B7CF6";
        ctx.globalAlpha = 0.15;
        ctx.fill();
        ctx.globalAlpha = nodeAlpha;
      }

      // Bridge accounts: Double turquoise radar beacon
      if (n.bridge >= 40) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, r + 4 / k, 0, Math.PI * 2);
        ctx.strokeStyle = "#5AD1B3";
        ctx.lineWidth = 1.6 / k;
        ctx.stroke();
      }

      // Bot / Astroturfing accounts: Pulsing dashed magenta hazard ring
      if (n.bot >= 60) {
        const pulse = (Math.sin(now / 200 + n.id) + 1) * 0.5;
        ctx.beginPath();
        ctx.arc(n.x, n.y, r + (3.5 + pulse * 2.5) / k, 0, Math.PI * 2);
        ctx.strokeStyle = "#E060B8";
        ctx.lineWidth = 1.8 / k;
        ctx.setLineDash([3 / k, 3 / k]);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // Selection / Comparison ring
      const inComparison = comparisonRef.current.some((c) => c.id === n.id);
      const isSelected = n.id === selected?.id;
      if (isSelected || inComparison) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, r + 6 / k, 0, Math.PI * 2);
        ctx.strokeStyle = isSelected ? "#ffffff" : "rgba(255, 255, 255, 0.7)";
        ctx.lineWidth = 2.2 / k;
        ctx.stroke();
      }

      // Spherical 3D Node Body with Radial Lighting
      ctx.beginPath();
      ctx.arc(n.x, n.y, r, 0, Math.PI * 2);

      const radGrad = ctx.createRadialGradient(
        n.x - r * 0.3,
        n.y - r * 0.3,
        r * 0.1,
        n.x,
        n.y,
        r
      );
      radGrad.addColorStop(0, "#ffffff");
      radGrad.addColorStop(0.35, comm?.color || "#888");
      radGrad.addColorStop(1, d3.color(comm?.color || "#888")?.darker(0.8).toString() || "#555");
      ctx.fillStyle = radGrad;
      ctx.fill();

      // Subtle perimeter border
      ctx.strokeStyle = "rgba(255, 255, 255, 0.25)";
      ctx.lineWidth = 0.8 / k;
      ctx.stroke();

      ctx.globalAlpha = 1;

      // ─── Crisp Badge Label ───────────────────────────────────────────────
      const isHighInfluence = n.influence >= 40;
      const isHovered = n.id === hovered?.id;
      const shouldShowLabel =
        showAllLabelsRef.current ||
        isHovered ||
        isSelected ||
        (zoom > 0.65 && isHighInfluence) ||
        (zoom > 1.3 && nodeAlpha > 0.5);

      if (shouldShowLabel && nodeAlpha > 0.3) {
        const labelText = "@" + n.handle;
        const fontSize = Math.max(9, Math.min(13, 11 / Math.sqrt(k)));
        ctx.font = `600 ${fontSize}px 'IBM Plex Mono', monospace`;
        const textWidth = ctx.measureText(labelText).width;
        const pillPadX = 6 / k;
        const pillPadY = 3 / k;
        const pillH = fontSize + pillPadY * 2;
        const pillW = textWidth + pillPadX * 2;
        const pillX = n.x - pillW / 2;
        const pillY = n.y - r - pillH - 4 / k;

        // Pill background
        ctx.beginPath();
        const cr = 4 / k;
        ctx.roundRect(pillX, pillY, pillW, pillH, cr);
        ctx.fillStyle = isHovered || isSelected ? "#101A2E" : "rgba(16, 26, 46, 0.88)";
        ctx.fill();

        ctx.strokeStyle = isHovered || isSelected ? "#ffffff" : comm?.color || "rgba(255, 255, 255, 0.2)";
        ctx.lineWidth = 1 / k;
        ctx.stroke();

        // Label text
        ctx.fillStyle = isHovered || isSelected ? "#ffffff" : "#E8EAF0";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(labelText, n.x, pillY + pillH / 2);
      }
    });

    ctx.restore();
  }, []);

  const scheduleDraw = useCallback(() => {
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    animFrameRef.current = requestAnimationFrame(draw);
  }, [draw]);

  useEffect(() => {
    scheduleDraw();
  }, [activeFilter, searchValue, selectedNode, comparison, currentWeek, showHulls, showAllLabels, scheduleDraw]);

  // Continuous animation loop for particles and hazard pulses
  useEffect(() => {
    let active = true;
    const loop = () => {
      if (!active) return;
      draw();
      animFrameRef.current = requestAnimationFrame(loop);
    };
    animFrameRef.current = requestAnimationFrame(loop);
    return () => {
      active = false;
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [draw]);

  // ─── Force simulation & drag setup ─────────────────────────────────────────
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

    const commCenters = {
      0: { x: 0.28, y: 0.32 },
      1: { x: 0.72, y: 0.32 },
      2: { x: 0.32, y: 0.68 },
      3: { x: 0.68, y: 0.68 },
    };

    const getW = () => canvas.width / dpr;
    const getH = () => canvas.height / dpr;

    graph.nodes.forEach((n) => {
      if (n.x == null || n.y == null) {
        const center = commCenters[n.comm] || { x: 0.5, y: 0.5 };
        n.x = center.x * getW() + (Math.random() - 0.5) * 100;
        n.y = center.y * getH() + (Math.random() - 0.5) * 100;
      }
    });

    const sim = d3
      .forceSimulation(graph.nodes)
      .force(
        "link",
        d3
          .forceLink(graph.links)
          .id((d) => d.id)
          .distance(42)
          .strength(0.48)
      )
      .force("charge", d3.forceManyBody().strength(-60))
      .force(
        "collide",
        d3.forceCollide().radius((d) => {
          const maxInf = Math.max(...graph.nodes.map((n) => n.influence || 1), 1);
          return 4 + Math.sqrt((d.influence || 1) / maxInf) * 14 + 4;
        })
      )
      .force(
        "x",
        d3
          .forceX((d) => (commCenters[d.comm]?.x || 0.5) * getW())
          .strength(0.09)
      )
      .force(
        "y",
        d3
          .forceY((d) => (commCenters[d.comm]?.y || 0.5) * getH())
          .strength(0.09)
      )
      .alphaDecay(0.02)
      .on("tick", () => {
        updateQuadtree();
        scheduleDraw();
      });

    simRef.current = sim;

    const zoom = d3
      .zoom()
      .scaleExtent([0.2, 6])
      .filter((event) => !event.button) // Ignore right clicks
      .on("zoom", (event) => {
        transformRef.current = event.transform;
        scheduleDraw();
      });

    zoomRef.current = zoom;
    d3.select(canvas).call(zoom);

    // Initial positioning
    const initialTransform = d3.zoomIdentity.translate(0, 0).scale(1);
    d3.select(canvas).call(zoom.transform, initialTransform);

    // ─── Actualización de Quadtree Espacial ──────────────────────────────────
    const updateQuadtree = () => {
      const g = graphDataRef.current;
      if (!g || !g.nodes || g.nodes.length === 0) {
        quadtreeRef.current = null;
        return;
      }
      const filter = filterRef.current;
      const validNodes = [];
      for (let i = 0; i < g.nodes.length; i++) {
        const n = g.nodes[i];
        if (n.x == null || n.y == null) continue;
        if (filter.onlySuspicious && n.bot < 60) continue;
        if (filter.community !== null && n.comm !== filter.community) continue;
        validNodes.push(n);
      }
      quadtreeRef.current = d3
        .quadtree()
        .x((d) => d.x)
        .y((d) => d.y)
        .addAll(validNodes);
    };

    // ─── Indexación espacial Quadtree O(log N) para detección bajo cursor ────
    const getNodeAt = (mx, my) => {
      const g = graphDataRef.current;
      if (!g || !g.nodes || !quadtreeRef.current) return null;
      const { k, x, y } = transformRef.current;
      const wx = (mx - x) / k;
      const wy = (my - y) / k;
      const maxInf = Math.max(...g.nodes.map((n) => n.influence || 1), 1);
      const maxHitRadius = 26; // Radio máximo de nodo con holgura

      let best = null;
      let bestDist = Infinity;

      quadtreeRef.current.visit((treeNode, x0, y0, x1, y1) => {
        // Podar ramas del Quadtree que están fuera de la caja envolvente (O(log N))
        if (
          x0 > wx + maxHitRadius ||
          x1 < wx - maxHitRadius ||
          y0 > wy + maxHitRadius ||
          y1 < wy - maxHitRadius
        ) {
          return true;
        }

        if (!treeNode.length) {
          let d = treeNode.data;
          while (d) {
            const r = 4 + Math.sqrt((d.influence || 1) / maxInf) * 14 + 6;
            const dx = wx - d.x;
            const dy = wy - d.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist <= r && dist < bestDist) {
              best = d;
              bestDist = dist;
            }
            d = d.next;
          }
        }
        return false;
      });

      return best;
    };

    const drag = d3
      .drag()
      .container(canvas)
      .subject((event) => {
        const node = getNodeAt(event.x, event.y);
        return node;
      })
      .on("start", (event) => {
        if (!event.subject) return;
        isDraggingRef.current = true;
        if (!event.active) sim.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
      })
      .on("drag", (event) => {
        if (!event.subject) return;
        const { k, x, y } = transformRef.current;
        event.subject.fx = (event.x - x) / k;
        event.subject.fy = (event.y - y) / k;
      })
      .on("end", (event) => {
        if (!event.subject) return;
        isDraggingRef.current = false;
        if (!event.active) sim.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
      });

    d3.select(canvas).call(drag);

    // ─── Tooltip & Hover ────────────────────────────────────────────────────
    let tooltipEl = document.getElementById("trama-tooltip");
    if (!tooltipEl) {
      tooltipEl = document.createElement("div");
      tooltipEl.id = "trama-tooltip";
      tooltipEl.style.cssText = `
        position:fixed;pointer-events:none;background:#101A2E;border:1px solid rgba(255,255,255,0.18);
        border-radius:10px;padding:12px 16px;font-family:'IBM Plex Mono',monospace;font-size:12px;
        color:#fff;z-index:1000;opacity:0;transition:opacity 0.15s, transform 0.1s;max-width:230px;
        box-shadow:0 12px 32px rgba(0,0,0,0.5);backdrop-filter:blur(10px);
      `;
      document.body.appendChild(tooltipEl);
    }

    const onMove = (e) => {
      if (isDraggingRef.current) return;
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
          <div style="font-weight:700;font-size:13px;margin-bottom:4px;color:${comm?.color || "#fff"}">@${node.handle}</div>
          <div style="opacity:0.75;font-size:11px;margin-bottom:6px">${comm?.name || ""}</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:11px;border-top:1px solid rgba(255,255,255,0.1);padding-top:6px;">
            <span>Influencia: <b style="color:#8B7CF6">${node.influence}</b></span>
            <span>Puente: <b style="color:#5AD1B3">${node.bridge}</b></span>
            <span>Conexiones: <b>${node.degree}</b></span>
            <span>Autenticidad: <b style="color:${node.auth >= 70 ? "#5AD1B3" : node.auth >= 40 ? "#E8C15A" : "#E060B8"}">${node.auth}%</b></span>
          </div>
          ${
            node.bot >= 60
              ? '<div style="color:#E060B8;margin-top:6px;font-size:11px;font-weight:600;display:flex;align-items:center;gap:4px">⚠️ Posible amplificación CIB</div>'
              : ""
          }
        `;
        tooltipEl.style.left = e.clientX + 16 + "px";
        tooltipEl.style.top = e.clientY - 12 + "px";
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
        onNodeSelect(node);

        const W = getW(),
          H = getH();
        const targetK = Math.max(transformRef.current.k, 1.4);
        const targetX = W / 2 - node.x * targetK;
        const targetY = H / 2 - node.y * targetK;
        d3.select(canvas)
          .transition()
          .duration(500)
          .call(
            zoom.transform,
            d3.zoomIdentity.translate(targetX, targetY).scale(targetK)
          );

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
  }, [graph, scheduleDraw, onNodeSelect]);

  // ─── HUD Control Handlers ─────────────────────────────────────────────────
  const handleZoomIn = () => {
    if (!zoomRef.current || !canvasRef.current) return;
    d3.select(canvasRef.current).transition().duration(300).call(zoomRef.current.scaleBy, 1.35);
  };

  const handleZoomOut = () => {
    if (!zoomRef.current || !canvasRef.current) return;
    d3.select(canvasRef.current).transition().duration(300).call(zoomRef.current.scaleBy, 0.74);
  };

  const handleFitView = () => {
    if (!zoomRef.current || !canvasRef.current || !graph?.nodes?.length) return;
    const canvas = canvasRef.current;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const W = canvas.width / dpr;
    const H = canvas.height / dpr;

    const xs = graph.nodes.map((n) => n.x).filter((x) => x != null);
    const ys = graph.nodes.map((n) => n.y).filter((y) => y != null);
    if (xs.length === 0) return;

    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);

    const pad = 60;
    const dx = maxX - minX || 1;
    const dy = maxY - minY || 1;
    const k = Math.min(3, Math.max(0.4, Math.min((W - pad * 2) / dx, (H - pad * 2) / dy)));
    const tx = W / 2 - ((minX + maxX) / 2) * k;
    const ty = H / 2 - ((minY + maxY) / 2) * k;

    d3.select(canvas)
      .transition()
      .duration(600)
      .call(zoomRef.current.transform, d3.zoomIdentity.translate(tx, ty).scale(k));
  };

  const handleReheatSim = () => {
    if (simRef.current) {
      simRef.current.alpha(0.6).restart();
    }
  };

  const handleToggleCoornet = () => {
    const next = !showCoornet;
    setShowCoornet(next);
    if (onToggleCoornetLayer) onToggleCoornetLayer(next);
  };

  return (
    <div className="graph-canvas-container" ref={containerRef} style={{ width: "100%", height: "100%", position: "relative" }}>
      <canvas ref={canvasRef} className="graph-canvas" />

      {/* Floating Canvas HUD Controls Island */}
      <div className="canvas-hud-island">
        <button className="hud-btn" onClick={handleZoomIn} title="Acercar (+)">
          +
        </button>
        <button className="hud-btn" onClick={handleZoomOut} title="Alejar (-)">
          −
        </button>
        <button className="hud-btn" onClick={handleFitView} title="Ajustar y centrar grafo (⛶)">
          ⛶
        </button>
        <div className="hud-sep" />
        <button
          className={`hud-btn ${showHulls ? "hud-btn-active" : ""}`}
          onClick={() => setShowHulls(!showHulls)}
          title={showHulls ? "Ocultar nubes de comunidad" : "Mostrar nubes de comunidad"}
        >
          ☁
        </button>
        <button
          className={`hud-btn ${showAllLabels ? "hud-btn-active" : ""}`}
          onClick={() => setShowAllLabels(!showAllLabels)}
          title={showAllLabels ? "Ocultar todas las etiquetas" : "Mostrar todas las etiquetas"}
        >
          🏷️
        </button>
        <button
          className={`hud-btn ${showCoornet ? "hud-btn-active" : ""}`}
          onClick={handleToggleCoornet}
          title={showCoornet ? "Ocultar capa de co-compartición CooRnet" : "Mostrar capa secundaria CooRnet (Co-compartición rápida Δt ≤ 45s, p < 0.05)"}
          style={{
            borderColor: showCoornet ? "#EC4899" : undefined,
            color: showCoornet ? "#EC4899" : undefined,
            background: showCoornet ? "rgba(236, 72, 153, 0.25)" : undefined,
          }}
        >
          🔗
        </button>
        <button className="hud-btn" onClick={handleReheatSim} title="Re-organizar física del grafo (⚡)">
          ⚡
        </button>
      </div>

      {/* Banner flotante informativo cuando la capa CooRnet está activa */}
      {showCoornet && (
        <div
          className="coornet-hud-banner"
          style={{
            position: "absolute",
            top: "16px",
            left: "16px",
            background: "rgba(16, 26, 46, 0.92)",
            border: "1px solid rgba(236, 72, 153, 0.5)",
            borderRadius: "20px",
            padding: "6px 14px",
            display: "flex",
            alignItems: "center",
            gap: "10px",
            fontSize: "11px",
            color: "#fff",
            backdropFilter: "blur(10px)",
            boxShadow: "0 6px 20px rgba(236, 72, 153, 0.25)",
            zIndex: 5,
          }}
        >
          <span style={{ color: "#EC4899", fontSize: "14px" }}>🔗</span>
          <span style={{ fontWeight: "700", color: "#EC4899" }}>Capa CooRnet Activa:</span>
          <span style={{ color: "var(--text-secondary)" }}>
            {graph?.coornet_links?.length || 0} aristas sincronizadas (Δt ≤ 45s, Monte Carlo p &lt; 0.05)
          </span>
          <button
            onClick={handleToggleCoornet}
            style={{
              background: "none",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              padding: "0 4px",
              fontSize: "12px",
              marginLeft: "4px",
            }}
            title="Ocultar capa CooRnet"
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
});

export default GraphCanvas;
