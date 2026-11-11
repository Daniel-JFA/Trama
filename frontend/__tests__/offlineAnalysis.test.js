/**
 * offlineAnalysis.test.js — Tests unitarios para el motor de grafos y análisis offline (Sprint 4 / Bloque B).
 * Ejecutable directamente mediante `node --test __tests__/offlineAnalysis.test.js`.
 */

const test = require("node:test");
const assert = require("node:assert");

const Papa = require("papaparse");
const Graph = require("graphology");
const louvain = require("graphology-communities-louvain");
const pagerank = require("graphology-metrics/centrality/pagerank");

test("PapaParse extrae correctamente pares de interacción dirigidos de un CSV", () => {
  const csvContent = `source,target,type
alice,bob,retweet
bob,carol,reply
carol,alice,mention
bot_98765432,target_victim,retweet
`;

  const parsed = Papa.parse(csvContent, { header: true, skipEmptyLines: true });
  assert.strictEqual(parsed.data.length, 4);
  assert.strictEqual(parsed.data[0].source, "alice");
  assert.strictEqual(parsed.data[0].target, "bob");
});

test("Graphology construye grafo dirigido, asigna comunidades Louvain y calcula PageRank", () => {
  const g = new Graph({ type: "directed" });
  g.mergeEdge("alice", "bob");
  g.mergeEdge("bob", "carol");
  g.mergeEdge("carol", "alice");
  g.mergeEdge("dave", "eve");
  g.mergeEdge("eve", "dave");

  assert.strictEqual(g.order, 5); // 5 nodos
  assert.strictEqual(g.size, 5);  // 5 aristas

  // Louvain
  louvain.assign(g);
  const commA = g.getNodeAttribute("alice", "community");
  const commB = g.getNodeAttribute("bob", "community");
  assert.strictEqual(commA, commB); // Pertenecen al mismo clúster

  // PageRank
  const pr = pagerank(g);
  assert.ok(pr.alice > 0);
  assert.ok(pr.bob > 0);
  assert.ok(pr.carol > 0);
});

test("Heurística CIB identifica correctamente cuentas anómalas por sufijo numérico extenso", () => {
  function computeBotScore(handle, inDeg, outDeg) {
    let score = 5;
    const numMatch = handle.match(/\d+$/);
    if (numMatch && numMatch[0].length >= 4) score += 35;
    if (outDeg > 10 && inDeg === 0) score += 30;
    return score;
  }

  const organicScore = computeBotScore("periodista_investiga", 15, 2);
  const botScore = computeBotScore("usuario98765432", 0, 15);

  assert.ok(organicScore < 30);
  assert.ok(botScore >= 70);
});

test("Histograma de 10 bins clasifica correctamente los rangos 0-100", () => {
  const values = [5, 12, 19, 25, 55, 78, 82, 95, 99];
  const bins = new Array(10).fill(0);
  values.forEach((v) => {
    const idx = Math.min(9, Math.floor(v / 10));
    bins[idx]++;
  });

  assert.strictEqual(bins[0], 1); // 5
  assert.strictEqual(bins[1], 2); // 12, 19
  assert.strictEqual(bins[2], 1); // 25
  assert.strictEqual(bins[5], 1); // 55
  assert.strictEqual(bins[7], 1); // 78
  assert.strictEqual(bins[8], 1); // 82
  assert.strictEqual(bins[9], 2); // 95, 99
  assert.strictEqual(bins.reduce((a, b) => a + b, 0), values.length);
});
