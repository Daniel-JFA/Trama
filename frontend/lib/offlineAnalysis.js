/**
 * offlineAnalysis.js — Motor de análisis forense y grafos offline para el navegador (Sprint 4 / Bloque B).
 * Procesa datasets CSV con PapaParse en segundo plano, calcula modularidad de Louvain
 * y PageRank con Graphology, e infiere métricas CIB sin requerir backend.
 */

import Papa from "papaparse";
import Graph from "graphology";
import louvain from "graphology-communities-louvain";
import pagerank from "graphology-metrics/centrality/pagerank";

const COMMUNITY_COLORS = [
  "#3B82F6", // Azul
  "#10B981", // Verde
  "#F59E0B", // Ámbar
  "#8B5CF6", // Púrpura
  "#EC4899", // Rosa
  "#06B6D4", // Cian
  "#F97316", // Naranja
  "#6366F1", // Índigo
];

/**
 * Calcula heurística de comportamiento inauténtico (CIB / Bot Score) en cliente.
 */
function computeClientBotScore(handle, inDegree, outDegree) {
  let score = 5;

  // 1. Sufijo numérico extenso (patrón típico de granjas de bots)
  const numMatch = handle.match(/\d+$/);
  if (numMatch && numMatch[0].length >= 4) {
    score += 35;
  } else if (numMatch && numMatch[0].length >= 2) {
    score += 15;
  }

  // 2. Desproporción extrema de difusión (mucho out-degree, casi nulo in-degree)
  const totalDegree = inDegree + outDegree;
  if (outDegree > 10 && inDegree === 0) {
    score += 30;
  } else if (outDegree > 5 && inDegree <= 1) {
    score += 20;
  }

  // 3. Longitud excesiva con caracteres aleatorios
  if (handle.length > 14 && /^[a-z0-9_]+$/i.test(handle)) {
    score += 15;
  }

  return Math.min(100, Math.max(0, score));
}

/**
 * Parsea un archivo CSV en cliente y computa la topología completa con Graphology.
 */
export function analyzeCsvOffline(fileOrContent) {
  return new Promise((resolve, reject) => {
    Papa.parse(fileOrContent, {
      header: true,
      skipEmptyLines: true,
      dynamicTyping: true,
      complete: (results) => {
        try {
          const rows = results.data;
          if (!rows || rows.length === 0) {
            throw new Error("El archivo CSV está vacío o no contiene filas válidas.");
          }

          // Identificar columnas de origen y destino
          const firstRow = rows[0];
          const keys = Object.keys(firstRow).map((k) => k.toLowerCase().trim());

          const sourceKey = Object.keys(firstRow).find((k) =>
            ["source", "actor", "origen", "from", "user", "author", "cuenta"].includes(k.toLowerCase().trim())
          ) || Object.keys(firstRow)[0];

          const targetKey = Object.keys(firstRow).find((k) =>
            ["target", "destino", "to", "mentioned", "retweeted", "reply_to"].includes(k.toLowerCase().trim())
          ) || Object.keys(firstRow)[1];

          if (!sourceKey || !targetKey || sourceKey === targetKey) {
            throw new Error(`No se detectaron columnas de interacción válidas en el CSV (detectadas: ${sourceKey}, ${targetKey}).`);
          }

          const graph = new Graph({ type: "directed", multi: false });

          // Construir nodos y enlaces ponderados
          rows.forEach((row) => {
            const rawSrc = row[sourceKey];
            const rawTgt = row[targetKey];
            if (rawSrc && rawTgt) {
              const src = String(rawSrc).trim().replace(/^@/, "");
              const tgt = String(rawTgt).trim().replace(/^@/, "");
              if (src && tgt && src !== tgt) {
                if (!graph.hasNode(src)) graph.addNode(src);
                if (!graph.hasNode(tgt)) graph.addNode(tgt);

                if (graph.hasEdge(src, tgt)) {
                  const currentWeight = graph.getEdgeAttribute(src, tgt, "weight") || 1;
                  graph.setEdgeAttribute(src, tgt, "weight", currentWeight + 1);
                } else {
                  graph.addEdge(src, tgt, { weight: 1 });
                }
              }
            }
          });

          if (graph.order === 0) {
            throw new Error("No se pudieron extraer interacciones dirigidas del archivo.");
          }

          // Particionamiento comunitario con Louvain (Graphology)
          louvain.assign(graph);

          // Centralidad PageRank (Graphology)
          const prScores = pagerank(graph, { damping: 0.85, maxIterations: 100 });
          const maxPr = Math.max(...Object.values(prScores), 1e-6);

          // Construir mapa de comunidades
          const commMembers = new Map();
          graph.forEachNode((node, attrs) => {
            const comm = attrs.community != null ? attrs.community : 0;
            if (!commMembers.has(comm)) commMembers.set(comm, []);
            commMembers.get(comm).push(node);
          });

          const communities = Array.from(commMembers.entries()).map(([cid, members], idx) => ({
            id: cid,
            name: `Comunidad ${cid} (Offline)`,
            color: COMMUNITY_COLORS[idx % COMMUNITY_COLORS.length],
            size: members.length,
            percentage: Math.round((members.length / graph.order) * 100),
          }));

          // Normalizar nodos al contrato estándar de TRAMA
          const nodeMap = new Map();
          const nodes = [];
          let nodeIdx = 0;

          graph.forEachNode((node, attrs) => {
            const inDeg = graph.inDegree(node);
            const outDeg = graph.outDegree(node);
            const deg = inDeg + outDeg;
            const normInfluence = Math.round(((prScores[node] || 0) / maxPr) * 100);
            const botScore = computeClientBotScore(node, inDeg, outDeg);
            const commId = attrs.community != null ? attrs.community : 0;

            const nObj = {
              id: nodeIdx,
              handle: node,
              label: node,
              comm: commId,
              org: inDeg > 15 && botScore < 20,
              bot: botScore,
              auth: Math.max(0, 100 - botScore),
              followers: Math.max(10, inDeg * 25),
              posts: Math.max(1, outDeg * 5),
              degree: deg,
              influence: normInfluence,
              bridge: Math.round((outDeg / Math.max(1, inDeg + 1)) * 20),
              x: (Math.random() - 0.5) * 600,
              y: (Math.random() - 0.5) * 600,
            };

            nodeMap.set(node, nodeIdx);
            nodes.push(nObj);
            nodeIdx++;
          });

          // Normalizar enlaces
          const links = [];
          graph.forEachEdge((edge, attrs, source, target) => {
            const sIdx = nodeMap.get(source);
            const tIdx = nodeMap.get(target);
            if (sIdx !== undefined && tIdx !== undefined) {
              links.push({
                source: sIdx,
                target: tIdx,
                weight: attrs.weight || 1,
              });
            }
          });

          const resultGraph = {
            nodes,
            links,
            communities,
            meta: {
              topic: "Análisis Offline (CSV Local)",
              interactions: links.length,
              mode: "offline",
              importedAt: new Date().toISOString(),
            },
          };

          resolve(resultGraph);
        } catch (err) {
          reject(err);
        }
      },
      error: (err) => reject(err),
    });
  });
}
