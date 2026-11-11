"use client";

import { useEffect, useState, useCallback } from "react";

export default function ProjectsModal({
  isOpen,
  onClose,
  activeProjectId,
  onSelectProject,
}) {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [topic, setTopic] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState(null);

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/projects`);
      if (!res.ok) throw new Error("No se pudieron cargar los proyectos");
      const data = await res.json();
      setProjects(data);
    } catch {
      setError("Requiere backend activo para gestionar proyectos");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      fetchProjects();
    }
  }, [isOpen, fetchProjects]);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!name.trim() || !topic.trim()) return;
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, topic, description }),
      });
      if (!res.ok) throw new Error("Error al crear la investigación");
      const newProj = await res.json();
      setName("");
      setTopic("");
      setDescription("");
      setCreating(false);
      await fetchProjects();
      onSelectProject(newProj.id);
      onClose();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    if (id === "demo-reforma-del-agua") return;
    if (!confirm("¿Deseas eliminar esta investigación?")) return;
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/projects/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("No se pudo eliminar");
      await fetchProjects();
    } catch (err) {
      setError(err.message);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Gestión de Investigaciones</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        {error && <div className="modal-error">{error}</div>}

        {!creating ? (
          <div className="modal-body">
            <div className="modal-actions-top">
              <span className="projects-count">{projects.length} investigaciones guardadas</span>
              <button className="btn-primary" onClick={() => setCreating(true)}>
                + Nueva Investigación
              </button>
            </div>

            {loading ? (
              <div className="modal-loading">Cargando proyectos…</div>
            ) : (
              <div className="projects-list">
                {projects.map((p) => {
                  const isActive = p.id === activeProjectId;
                  return (
                    <div
                      key={p.id}
                      className={`project-item ${isActive ? "project-item-active" : ""}`}
                      onClick={() => {
                        onSelectProject(p.id);
                        onClose();
                      }}
                    >
                      <div className="project-item-main">
                        <div className="project-item-title-row">
                          <span className="project-item-name">{p.name}</span>
                          <span className="project-item-topic">{p.topic}</span>
                          {isActive && <span className="project-active-badge">Activo</span>}
                        </div>
                        {p.description && (
                          <p className="project-item-desc">{p.description}</p>
                        )}
                        <div className="project-item-stats">
                          <span>{p.node_count} nodos</span>
                          <span>•</span>
                          <span>{p.link_count} aristas</span>
                          <span>•</span>
                          <span>{p.community_count} comunidades</span>
                          <span>•</span>
                          <span className="project-date">
                            {new Date(p.updated_at).toLocaleDateString()}
                          </span>
                        </div>
                      </div>

                      {p.id !== "demo-reforma-del-agua" && (
                        <button
                          className="project-btn-delete"
                          title="Eliminar investigación"
                          onClick={(e) => handleDelete(e, p.id)}
                        >
                          🗑️
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ) : (
          <form className="modal-body modal-form" onSubmit={handleCreate}>
            <div className="form-group">
              <label>Nombre de la Investigación</label>
              <input
                type="text"
                placeholder="Ej. Análisis Elecciones 2026"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label>Tema o Hashtag (#)</label>
              <input
                type="text"
                placeholder="Ej. #Elecciones2026"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label>Descripción / Hipótesis</label>
              <textarea
                rows={3}
                placeholder="Detalla los objetivos del análisis o las fuentes observadas…"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
            <div className="form-actions">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setCreating(false)}
              >
                Cancelar
              </button>
              <button type="submit" className="btn-primary">
                Guardar e Iniciar
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
