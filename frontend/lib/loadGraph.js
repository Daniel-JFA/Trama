/**
 * loadGraph.js — Carga el grafo desde el backend o desde el archivo local de muestra.
 *
 * 1. Intenta GET {NEXT_PUBLIC_API_URL}/api/graph con timeout de 2.5s.
 * 2. Si falla (backend no disponible), carga /sample-graph.json.
 * Devuelve { graph, source } donde source es "backend" o "local".
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function loadGraph() {
  // Intento de conexión al backend con timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 2500);

  try {
    const res = await fetch(`${API_URL}/api/graph`, {
      signal: controller.signal,
      cache: "no-store",
    });
    clearTimeout(timeoutId);

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const graph = await res.json();
    return { graph, source: "backend" };
  } catch {
    clearTimeout(timeoutId);
    // Fallback al archivo local
    const res = await fetch("/sample-graph.json");
    const graph = await res.json();
    return { graph, source: "local" };
  }
}

export async function fetchOverlap(ids) {
  const res = await fetch(`${API_URL}/api/overlap?ids=${ids.join(",")}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
