/**
 * exportSvg.js — Exportador de grafos a formato SVG vectorial estructurado para TRAMA.
 * 
 * Genera un archivo SVG con grupos semánticos <g>:
 * - <g id="links">: aristas con opacidad y grosor adaptativo
 * - <g id="nodes">: círculos de nodos coloreados por comunidad con etiquetas de handle
 * - <g id="legends">: título de investigación y leyendas de color por comunidad
 */

export function exportGraphToSVG(graph) {
  if (!graph || !graph.nodes || graph.nodes.length === 0) return "";

  const nodes = graph.nodes;
  const links = graph.links || [];
  const communities = graph.communities || [];

  // Calcular caja envolvente basada en coordenadas de los nodos
  const xs = nodes.map((n) => n.x).filter((x) => x != null);
  const ys = nodes.map((n) => n.y).filter((y) => y != null);

  const minX = xs.length ? Math.min(...xs) - 100 : 0;
  const maxX = xs.length ? Math.max(...xs) + 100 : 1200;
  const minY = ys.length ? Math.min(...ys) - 100 : 0;
  const maxY = ys.length ? Math.max(...ys) + 100 : 800;

  const width = Math.round(Math.max(800, maxX - minX));
  const height = Math.round(Math.max(600, maxY - minY));

  const commMap = {};
  communities.forEach((c) => {
    commMap[c.id] = c;
  });

  const nodeMap = {};
  nodes.forEach((n) => {
    nodeMap[n.id] = n;
  });

  const maxInf = Math.max(...nodes.map((n) => n.influence || 1), 1);

  const escapeXml = (unsafe) => {
    return String(unsafe || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&apos;");
  };

  let svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="${minX} ${minY} ${width} ${height}" width="${width}" height="${height}">
  <defs>
    <style>
      .bg { fill: #0B1220; }
      .link { stroke: rgba(148, 163, 184, 0.22); stroke-width: 1px; stroke-linecap: round; }
      .node-circle { stroke: #0B1220; stroke-width: 1.5px; }
      .node-label { font-family: 'IBM Plex Mono', Menlo, monospace; font-size: 10px; fill: #F1F5F9; font-weight: 500; }
      .legend-text { font-family: 'IBM Plex Mono', Menlo, monospace; font-size: 11px; fill: #94A3B8; }
      .title-text { font-family: system-ui, -apple-system, sans-serif; font-size: 18px; font-weight: 700; fill: #F8FAFC; letter-spacing: -0.02em; }
      .subtitle-text { font-family: 'IBM Plex Mono', Menlo, monospace; font-size: 11px; fill: #64748B; }
    </style>
  </defs>

  <!-- Fondo estructurado -->
  <rect class="bg" x="${minX}" y="${minY}" width="${width}" height="${height}" />

  <!-- Aristas / Enlaces de red -->
  <g id="links" opacity="0.8">
`;

  links.forEach((link) => {
    const sId = typeof link.source === "object" ? link.source.id : link.source;
    const tId = typeof link.target === "object" ? link.target.id : link.target;
    const sNode = nodeMap[sId];
    const tNode = nodeMap[tId];
    if (sNode && tNode && sNode.x != null && tNode.x != null) {
      svg += `    <line class="link" x1="${sNode.x.toFixed(1)}" y1="${sNode.y.toFixed(1)}" x2="${tNode.x.toFixed(1)}" y2="${tNode.y.toFixed(1)}" />\n`;
    }
  });

  svg += `  </g>\n\n  <!-- Nodos de la red -->\n  <g id="nodes">\n`;

  nodes.forEach((n) => {
    if (n.x == null || n.y == null) return;
    const comm = commMap[n.comm];
    const color = comm ? comm.color : "#60A5FA";
    const r = (4 + Math.sqrt((n.influence || 1) / maxInf) * 14).toFixed(1);

    svg += `    <g id="node-${n.id}" class="node-group">
      <circle class="node-circle" cx="${n.x.toFixed(1)}" cy="${n.y.toFixed(1)}" r="${r}" fill="${color}" fill-opacity="0.9" />
      <text class="node-label" x="${(n.x + parseFloat(r) + 4).toFixed(1)}" y="${(n.y + 3).toFixed(1)}">@${escapeXml(n.handle)}</text>
    </g>\n`;
  });

  svg += `  </g>\n\n  <!-- Leyendas y Metadatos -->\n  <g id="legends">\n`;
  svg += `    <text class="title-text" x="${minX + 32}" y="${minY + 44}">TRAMA</text>\n`;
  svg += `    <text class="subtitle-text" x="${minX + 104}" y="${minY + 43}">Investigación: ${escapeXml(graph.meta?.topic || "Grafo")}</text>\n`;

  let legY = minY + 74;
  communities.forEach((c) => {
    svg += `    <circle cx="${minX + 38}" cy="${legY - 4}" r="5" fill="${c.color}" />\n`;
    svg += `    <text class="legend-text" x="${minX + 52}" y="${legY}">${escapeXml(c.name)}</text>\n`;
    legY += 20;
  });

  svg += `  </g>\n</svg>`;
  return svg;
}

export function downloadSVG(svgContent, filename = "trama-grafo.svg") {
  if (typeof window === "undefined") return;
  const blob = new Blob([svgContent], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
