/**
 * graph.worker.js — Simulación de fuerzas física en Web Worker dedicado (Sprint 4 / Bloque B).
 * Ejecuta el cálculo topológico fuera del hilo principal de UI.
 * Comunica las coordenadas actualizadas utilizando Float32Array transferibles para alcanzar 60 FPS constantes.
 */

/* eslint-disable no-restricted-globals */

let nodes = [];
let links = [];
let nodeMap = new Map();
let width = 800;
let height = 600;
let alpha = 1.0;
let alphaMin = 0.001;
let alphaDecay = 0.0228;
let alphaTarget = 0;
let velocityDecay = 0.6;
let isRunning = false;
let animTimer = null;

function initialize(data) {
  width = data.width || 800;
  height = data.height || 600;
  alpha = 1.0;
  alphaTarget = 0;

  // Inicializar nodos
  nodes = data.nodes.map((n, i) => ({
    id: n.id,
    index: i,
    x: typeof n.x === "number" && !isNaN(n.x) ? n.x : width / 2 + (Math.random() - 0.5) * 50,
    y: typeof n.y === "number" && !isNaN(n.y) ? n.y : height / 2 + (Math.random() - 0.5) * 50,
    vx: 0,
    vy: 0,
    fx: n.fx != null ? n.fx : null,
    fy: n.fy != null ? n.fy : null,
    radius: Math.max(4, Math.min(16, ((n.influence || 10) / 100) * 12 + 4)),
  }));

  nodeMap.clear();
  nodes.forEach((n, i) => nodeMap.set(n.id, i));

  // Inicializar links
  links = [];
  (data.links || []).forEach((l) => {
    const sId = typeof l.source === "object" ? l.source.id : l.source;
    const tId = typeof l.target === "object" ? l.target.id : l.target;
    const sIdx = nodeMap.get(sId);
    const tIdx = nodeMap.get(tId);
    if (sIdx !== undefined && tIdx !== undefined) {
      links.push({
        source: sIdx,
        target: tIdx,
        distance: 45,
        strength: 0.7,
      });
    }
  });

  isRunning = true;
  stepSimulation();
}

function tick() {
  alpha += (alphaTarget - alpha) * alphaDecay;
  if (alpha < alphaMin) {
    alpha = 0;
    isRunning = false;
    sendPositions("END");
    return;
  }

  const cx = width / 2;
  const cy = height / 2;
  const centerStrength = 0.05 * alpha;
  const n = nodes.length;

  // 1. Fuerza de centrado y decaimiento
  for (let i = 0; i < n; i++) {
    const node = nodes[i];
    node.vx += (cx - node.x) * centerStrength;
    node.vy += (cy - node.y) * centerStrength;
  }

  // 2. Fuerza de atracción por enlaces (Hooke)
  const linkStrengthCoeff = alpha;
  for (let k = 0; k < links.length; k++) {
    const link = links[k];
    const s = nodes[link.source];
    const t = nodes[link.target];
    let dx = t.x + t.vx - (s.x + s.vx);
    let dy = t.y + t.vy - (s.y + s.vy);
    let dist = Math.sqrt(dx * dx + dy * dy) || 1;
    let delta = (dist - link.distance) / dist * linkStrengthCoeff * link.strength;
    dx *= delta;
    dy *= delta;

    t.vx -= dx * 0.5;
    t.vy -= dy * 0.5;
    s.vx += dx * 0.5;
    s.vy += dy * 0.5;
  }

  // 3. Fuerza de repulsión many-body (Coulomb)
  const repulsion = -180 * alpha;
  for (let i = 0; i < n; i++) {
    const n1 = nodes[i];
    for (let j = i + 1; j < n; j++) {
      const n2 = nodes[j];
      let dx = n2.x - n1.x;
      let dy = n2.y - n1.y;
      let distSq = dx * dx + dy * dy;
      if (distSq < 1) distSq = 1;
      if (distSq > 90000) continue; // Corte a 300px

      let dist = Math.sqrt(distSq);
      let force = repulsion / (distSq * dist);
      let fx = dx * force;
      let fy = dy * force;

      n1.vx -= fx;
      n1.vy -= fy;
      n2.vx += fx;
      n2.vy += fy;
    }
  }

  // 4. Integración de velocidades y actualización de posiciones
  for (let i = 0; i < n; i++) {
    const node = nodes[i];
    if (node.fx != null) {
      node.x = node.fx;
      node.vx = 0;
    } else {
      node.vx *= velocityDecay;
      node.x += node.vx;
    }

    if (node.fy != null) {
      node.y = node.fy;
      node.vy = 0;
    } else {
      node.vy *= velocityDecay;
      node.y += node.vy;
    }
  }

  sendPositions("TICK");
}

function sendPositions(type) {
  const n = nodes.length;
  // Crear Float32Array transferible con pares [x, y]
  const positions = new Float32Array(n * 2);
  for (let i = 0; i < n; i++) {
    positions[i * 2] = nodes[i].x;
    positions[i * 2 + 1] = nodes[i].y;
  }

  self.postMessage(
    {
      type,
      positions,
      alpha,
    },
    [positions.buffer] // Zero-copy transfer
  );
}

function stepSimulation() {
  if (!isRunning) return;
  tick();
  if (isRunning) {
    // Programar siguiente paso a 60 FPS
    setTimeout(stepSimulation, 16);
  }
}

self.onmessage = function (e) {
  const { type, payload } = e.data;
  switch (type) {
    case "INIT":
      initialize(payload);
      break;

    case "DRAG_START":
    case "DRAG": {
      const idx = nodeMap.get(payload.id);
      if (idx !== undefined) {
        nodes[idx].fx = payload.x;
        nodes[idx].fy = payload.y;
        alphaTarget = 0.1;
        if (!isRunning) {
          isRunning = true;
          alpha = 0.2;
          stepSimulation();
        }
      }
      break;
    }

    case "DRAG_END": {
      const idx = nodeMap.get(payload.id);
      if (idx !== undefined) {
        nodes[idx].fx = null;
        nodes[idx].fy = null;
        alphaTarget = 0;
      }
      break;
    }

    case "REHEAT":
      alpha = payload?.alpha || 0.3;
      alphaTarget = 0;
      if (!isRunning) {
        isRunning = true;
        stepSimulation();
      }
      break;

    case "STOP":
      isRunning = false;
      break;

    default:
      break;
  }
};
