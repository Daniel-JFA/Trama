/**
 * db.js — Persistencia local IndexedDB mediante Dexie (Sprint 4 / Bloque B).
 * Permite almacenar y cargar grafos, datasets e investigaciones sin conexión a internet.
 */

import Dexie from "dexie";

export const db = new Dexie("TramaOfflineDB");

db.version(1).stores({
  projects: "id, name, topic, updatedAt",
  graphs: "id, projectId, nodeCount, linkCount",
  rawDatasets: "id, name, importedAt",
});

export async function saveOfflineProject(project) {
  await db.projects.put({
    id: project.id,
    name: project.name,
    topic: project.topic,
    description: project.description || "",
    updatedAt: new Date().toISOString(),
  });

  if (project.graph) {
    await db.graphs.put({
      id: project.id,
      projectId: project.id,
      graph: project.graph,
      nodeCount: project.graph.nodes?.length || 0,
      linkCount: project.graph.links?.length || 0,
    });
  }
}

export async function getOfflineProjects() {
  return await db.projects.toArray();
}

export async function getOfflineGraph(projectId) {
  const record = await db.graphs.get(projectId);
  return record ? record.graph : null;
}
