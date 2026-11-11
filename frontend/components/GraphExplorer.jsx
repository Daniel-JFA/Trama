"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { loadGraph } from "../lib/loadGraph";
import TopBar from "./TopBar";
import GraphCanvas from "./GraphCanvas";
import Legend from "./Legend";
import TimeTravelControls from "./TimeTravelControls";
import SummaryPanel from "./panels/SummaryPanel";
import DossierPanel from "./panels/DossierPanel";
import ComparisonPanel from "./panels/ComparisonPanel";
import WarRoomPanel from "./panels/WarRoomPanel";
import ProjectsModal from "./ProjectsModal";
import ReportModal from "./ReportModal";
import TaskProgressModal from "./TaskProgressModal";
import ThresholdFilters from "./ThresholdFilters";
import { exportGraphToSVG, downloadSVG } from "../lib/exportSvg";
import { analyzeCsvOffline } from "../lib/offlineAnalysis";
import { saveOfflineProject } from "../lib/db";

export default function GraphExplorer() {
  const canvasComponentRef = useRef(null);

  const [graph, setGraph] = useState(null);
  const [dataSource, setDataSource] = useState("backend");
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState(null);
  const [panel, setPanel] = useState("resumen"); // "resumen" | "expediente" | "comparacion" | "warroom"
  const [politicalCandidate, setPoliticalCandidate] = useState(null);
  const [comparison, setComparison] = useState([]);
  const [searchValue, setSearchValue] = useState("");
  const [activeFilter, setActiveFilter] = useState(null); // community id o "suspicious"
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState(null);
  const [activeProjectId, setActiveProjectId] = useState("demo-reforma-del-agua");
  const [isProjectsModalOpen, setIsProjectsModalOpen] = useState(false);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [currentWeek, setCurrentWeek] = useState(null);
  const [showCoornetLayer, setShowCoornetLayer] = useState(false);

  // Estados de Filtros Multicriterio y Modo Offline (Sprint 4 / Bloque B)
  const [thresholdFilters, setThresholdFilters] = useState({
    minInfluence: 0,
    maxBot: 100,
    activeCommunities: [],
  });
  const [showThresholdSliders, setShowThresholdSliders] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [offlineNotice, setOfflineNotice] = useState(null);

  // Handler de arrastrar y soltar CSV offline
  const handleOfflineCsvDrop = useCallback(async (file) => {
    if (!file || !file.name.toLowerCase().endsWith(".csv")) {
      alert("Por favor arrastra un archivo en formato .csv para análisis local.");
      return;
    }
    setLoading(true);
    setImportError(null);
    try {
      const parsedGraph = await analyzeCsvOffline(file);
      const offlineProj = {
        id: `offline-${Date.now()}`,
        name: file.name.replace(/\.csv$/i, ""),
        topic: "Análisis Offline (CSV Local)",
        graph: parsedGraph,
      };
      await saveOfflineProject(offlineProj);
      setGraph(parsedGraph);
      setDataSource("offline-indexeddb");
      setActiveProjectId(offlineProj.id);
      setOfflineNotice(`✓ Modo Offline: Dataset "${file.name}" analizado con Graphology (Louvain y PageRank) y guardado en IndexedDB.`);
      setTimeout(() => setOfflineNotice(null), 8000);
    } catch (err) {
      setImportError(`Error en análisis offline: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  // Estados de streaming reactivo SSE (Sprint 2)
  const [taskProgress, setTaskProgress] = useState(0);
  const [taskStage, setTaskStage] = useState("");
  const [taskStatus, setTaskStatus] = useState("idle");
  const [taskError, setTaskError] = useState(null);
  const [isProgressModalOpen, setIsProgressModalOpen] = useState(false);

  // Carga inicial
  useEffect(() => {
    loadGraph().then(({ graph: g, source }) => {
      setGraph(g);
      setDataSource(source);
      setLoading(false);
    });
  }, []);

  // ─── Cambiar de proyecto ──────────────────────────────────────────────────
  const handleSelectProject = useCallback(async (projectId) => {
    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/projects/${projectId}`);
      if (!res.ok) throw new Error("No se pudo cargar la investigación");
      const project = await res.json();
      setGraph(project.graph);
      setActiveProjectId(project.id);
      setDataSource("backend");
      setSelectedNode(null);
      setComparison([]);
      setPanel("resumen");
      setActiveFilter(null);
    } catch (err) {
      setImportError(err.message);
      setTimeout(() => setImportError(null), 5000);
    } finally {
      setLoading(false);
    }
  }, []);

  // ─── Importar CSV con Streaming SSE Asíncrono (Sprint 2) ───────────────────
  const handleImportCSV = useCallback(async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    setImporting(true);
    setImportError(null);
    setTaskProgress(5);
    setTaskStage("Enviando dataset al servidor...");
    setTaskStatus("processing");
    setTaskError(null);
    setIsProgressModalOpen(true);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const formData = new FormData();
      formData.append("file", file);

      // Intentar primero el endpoint asíncrono con streaming SSE
      const asyncRes = await fetch(`${apiUrl}/api/import/async`, {
        method: "POST",
        body: formData,
      });

      if (asyncRes.ok && asyncRes.status === 202) {
        const { task_id } = await asyncRes.json();

        // Abrir conexión en tiempo real con Server-Sent Events (SSE)
        const eventSource = new EventSource(`${apiUrl}/api/tasks/${task_id}/events`);

        eventSource.addEventListener("progress", (evt) => {
          try {
            const data = JSON.parse(evt.data);
            setTaskProgress(data.progress);
            setTaskStage(data.stage);
          } catch (err) {}
        });

        eventSource.addEventListener("complete", (evt) => {
          try {
            const data = JSON.parse(evt.data);
            setTaskProgress(100);
            setTaskStage("Completado exitosamente");
            setTaskStatus("completed");
            eventSource.close();

            if (data.result && data.result.graph) {
              setGraph(data.result.graph);
              if (data.result.project_id) {
                setActiveProjectId(data.result.project_id);
              }
              setDataSource("imported");
              setSelectedNode(null);
              setComparison([]);
              setPanel("resumen");
              setActiveFilter(null);
            }

            setTimeout(() => {
              setIsProgressModalOpen(false);
              setImporting(false);
            }, 600);
          } catch (err) {
            eventSource.close();
            setImporting(false);
          }
        });

        eventSource.addEventListener("error", (evt) => {
          let msg = "Fallo durante el procesamiento asíncrono";
          try {
            if (evt.data) {
              const data = JSON.parse(evt.data);
              msg = data.error || msg;
            }
          } catch (err) {}
          setTaskStatus("failed");
          setTaskError(msg);
          setImportError(msg);
          eventSource.close();
          setImporting(false);
        });

        return;
      }

      // Fallback síncrono si el endpoint asíncrono no responde 202
      const res = await fetch(`${apiUrl}/api/import`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Error desconocido" }));
        throw new Error(err.detail || `Error ${res.status}`);
      }
      const data = await res.json();
      setGraph(data);
      setDataSource("imported");
      setSelectedNode(null);
      setComparison([]);
      setPanel("resumen");
      setActiveFilter(null);
      setIsProgressModalOpen(false);
      setImporting(false);
    } catch (err) {
      setTaskStatus("failed");
      setTaskError(err.message);
      setImportError(err.message);
      setImporting(false);
    }
  }, []);

  // ─── Restablecer a dataset sintético ─────────────────────────────────────
  const handleReset = useCallback(async () => {
    setImporting(true);
    setImportError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      await fetch(`${apiUrl}/api/reset`, { method: "POST" });
      const { graph: g, source } = await loadGraph();
      setGraph(g);
      setDataSource(source);
      setActiveProjectId("demo-reforma-del-agua");
      setSelectedNode(null);
      setComparison([]);
      setPanel("resumen");
      setActiveFilter(null);
    } catch {
      setImportError("No se pudo restablecer el demo");
      setTimeout(() => setImportError(null), 5000);
    } finally {
      setImporting(false);
    }
  }, []);

  // ─── Exportar PNG ────────────────────────────────────────────────────────
  const handleExportPNG = useCallback(() => {
    const canvas = canvasComponentRef.current?.getCanvas();
    if (!canvas) return;

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

  // ─── Exportar SVG Vectorial ──────────────────────────────────────────────
  const handleExportSVG = useCallback(() => {
    if (!graph) return;
    const svgContent = exportGraphToSVG(graph);
    downloadSVG(svgContent, `trama-${graph?.meta?.topic || "grafo"}.svg`);
  }, [graph]);

  // ─── Atajos de Teclado Globales (Sprint 1) ────────────────────────────────
  useEffect(() => {
    const handleKeyDown = (e) => {
      const activeTag = document.activeElement?.tagName?.toLowerCase();
      const isInput = activeTag === "input" || activeTag === "textarea" || activeTag === "select";

      // Atajo '/' para enfocar la barra de búsqueda
      if (e.key === "/" && !isInput) {
        e.preventDefault();
        const searchInput = document.querySelector(".search-input");
        if (searchInput) searchInput.focus();
        return;
      }

      // Atajo 'Escape' para deseleccionar nodo o desenfocar
      if (e.key === "Escape") {
        if (isInput) {
          document.activeElement?.blur();
        } else {
          setSelectedNode(null);
          if (panel === "expediente") setPanel("resumen");
        }
        return;
      }

      // Si el foco está en un elemento de texto, no interferir con otras teclas
      if (isInput) return;

      if (e.key === "+" || e.key === "=") {
        e.preventDefault();
        canvasComponentRef.current?.zoomIn();
      } else if (e.key === "-" || e.key === "_") {
        e.preventDefault();
        canvasComponentRef.current?.zoomOut();
      } else if (e.key === "f" || e.key === "F") {
        e.preventDefault();
        canvasComponentRef.current?.resetZoom();
      } else if (e.key === " ") {
        // Prevenir salto de scroll en página
        e.preventDefault();
      } else if (e.key === "1") {
        setPanel("resumen");
      } else if (e.key === "2") {
        if (selectedNode) setPanel("expediente");
      } else if (e.key === "3") {
        setPanel("comparacion");
      } else if (e.key === "4") {
        setPanel("warroom");
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [panel, selectedNode]);

  // ─── Exportar Gephi (GEXF) ───────────────────────────────────────────────
  const handleExportGEXF = useCallback(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    window.open(`${apiUrl}/api/projects/${activeProjectId}/export/gexf`, "_blank");
  }, [activeProjectId]);

  // ─── Handlers de Interacción ─────────────────────────────────────────────
  const handleNodeClick = useCallback((node) => {
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

  const handleSetCandidate = useCallback((node) => {
    setPoliticalCandidate(node);
    setPanel("warroom");
  }, []);

  const handleSearchSubmit = useCallback(() => {
    if (searchValue && graph?.nodes) {
      const node = graph.nodes.find((n) =>
        n.handle.toLowerCase().includes(searchValue.toLowerCase())
      );
      if (node) handleNodeClick(node);
    }
  }, [searchValue, graph, handleNodeClick]);

  const communities = graph?.communities || [];

  return (
    <div className="app-root">
      {/* Barra superior modular con navegación de proyectos */}
      <TopBar
        graph={graph}
        dataSource={dataSource}
        searchValue={searchValue}
        onSearchChange={setSearchValue}
        onSearchSubmit={handleSearchSubmit}
        onImportCSV={handleImportCSV}
        onResetDemo={handleReset}
        onExportPNG={handleExportPNG}
        onExportSVG={handleExportSVG}
        onExportGEXF={handleExportGEXF}
        onOpenReport={() => setIsReportModalOpen(true)}
        comparisonCount={comparison.length}
        onOpenComparison={() => setPanel("comparacion")}
        onOpenProjects={() => setIsProjectsModalOpen(true)}
        onOpenWarRoom={() => setPanel("warroom")}
        showCoornetLayer={showCoornetLayer}
        onToggleCoornetLayer={() => setShowCoornetLayer((prev) => !prev)}
        importing={importing}
        importError={importError}
      />

      {/* Cuerpo principal */}
      <main className="main-content">
        {/* Lienzo del grafo con soporte Drag & Drop Offline */}
        <div
          className="graph-area"
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={(e) => {
            if (!e.currentTarget.contains(e.relatedTarget)) {
              setIsDragOver(false);
            }
          }}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragOver(false);
            if (e.dataTransfer.files?.[0]) {
              handleOfflineCsvDrop(e.dataTransfer.files[0]);
            }
          }}
        >
          {loading && (
            <div className="loading-overlay">
              <div className="loading-spinner" />
              <span>Cargando red...</span>
            </div>
          )}

          {/* Overlay de Arrastrar CSV */}
          {isDragOver && (
            <div style={{
              position: "absolute",
              inset: 0,
              background: "rgba(10, 16, 29, 0.9)",
              border: "2px dashed #3B82F6",
              borderRadius: "12px",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 50,
              color: "#60A5FA",
              pointerEvents: "none",
            }}>
              <span style={{ fontSize: "40px", marginBottom: "8px" }}>📂</span>
              <span style={{ fontSize: "16px", fontWeight: "700" }}>Suelta tu archivo CSV para análisis offline</span>
              <span style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>
                Procesamiento local inmediato con Graphology (Louvain + PageRank) y Dexie / IndexedDB
              </span>
            </div>
          )}

          {/* Notificación de Modo Offline */}
          {offlineNotice && (
            <div style={{
              position: "absolute",
              top: "16px",
              left: "50%",
              transform: "translateX(-50%)",
              background: "#064e3b",
              border: "1px solid #059669",
              color: "#a7f3d0",
              padding: "8px 16px",
              borderRadius: "8px",
              fontSize: "12px",
              fontWeight: "600",
              zIndex: 40,
              boxShadow: "0 4px 12px rgba(0,0,0,0.4)",
            }}>
              {offlineNotice}
            </div>
          )}

          {/* Selector flotante de Sliders de Umbral con Histogramas */}
          <div style={{ position: "absolute", top: "14px", left: "14px", zIndex: 30, maxWidth: "440px" }}>
            <button
              onClick={() => setShowThresholdSliders((prev) => !prev)}
              style={{
                background: showThresholdSliders ? "#1e293b" : "rgba(15, 23, 42, 0.85)",
                backdropFilter: "blur(8px)",
                border: "1px solid rgba(255,255,255,0.15)",
                color: "#e2e8f0",
                padding: "6px 12px",
                borderRadius: "8px",
                cursor: "pointer",
                fontSize: "12px",
                fontWeight: "600",
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
              }}
            >
              <span>📊 Filtros Multicriterio</span>
              <span style={{ fontSize: "10px", color: "#94a3b8" }}>{showThresholdSliders ? "▲" : "▼"}</span>
            </button>

            {showThresholdSliders && !loading && graph?.nodes && (
              <ThresholdFilters
                nodes={graph.nodes}
                communities={communities}
                filters={thresholdFilters}
                onChange={setThresholdFilters}
              />
            )}
          </div>

          <GraphCanvas
            ref={canvasComponentRef}
            graph={graph}
            activeFilter={activeFilter}
            thresholdFilters={thresholdFilters}
            searchValue={searchValue}
            selectedNode={selectedNode}
            comparison={comparison}
            currentWeek={currentWeek}
            showCoornetLayer={showCoornetLayer}
            onToggleCoornetLayer={setShowCoornetLayer}
            onNodeSelect={handleNodeClick}
          />

          {/* Leyenda flotante */}
          {!loading && (
            <Legend
              communities={communities}
              activeFilter={activeFilter}
              onSelectFilter={setActiveFilter}
            />
          )}

          {/* Controles de Time-Travel temporal */}
          {!loading && graph?.meta?.weeks > 0 && (
            <TimeTravelControls
              graph={graph}
              maxWeeks={graph.meta.weeks}
              currentWeek={currentWeek}
              onWeekChange={setCurrentWeek}
            />
          )}
        </div>

        {/* Panel lateral modular */}
        <aside className="side-panel">
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
            <button
              className={`panel-tab ${panel === "warroom" ? "panel-tab-active" : ""}`}
              onClick={() => setPanel("warroom")}
              style={{
                color: panel === "warroom" ? "#F59E0B" : undefined,
                fontWeight: panel === "warroom" ? "700" : undefined,
              }}
            >
              🎯 War Room
            </button>
          </div>

          <div className="panel-body">
            {panel === "resumen" && (
              <SummaryPanel
                graph={graph}
                communities={communities}
                activeFilter={activeFilter}
                onSelectFilter={setActiveFilter}
                onNodeClick={handleNodeClick}
                currentWeek={currentWeek}
                onSelectWeek={setCurrentWeek}
              />
            )}
            {panel === "expediente" && (
              <DossierPanel
                node={selectedNode}
                graph={graph}
                communities={communities}
                onAddToComparison={handleAddToComparison}
                onNodeClick={handleNodeClick}
                onSetAsCandidate={handleSetCandidate}
              />
            )}
            {panel === "comparacion" && (
              <ComparisonPanel
                profiles={comparison}
                graph={graph}
                communities={communities}
                onRemove={handleRemoveFromComparison}
                onNodeClick={handleNodeClick}
              />
            )}
            {panel === "warroom" && (
              <WarRoomPanel
                graph={graph}
                communities={communities}
                candidate={politicalCandidate}
                onSelectCandidate={setPoliticalCandidate}
                onNodeClick={handleNodeClick}
              />
            )}
          </div>
        </aside>
      </main>

      {/* Modal de Proyectos */}
      <ProjectsModal
        isOpen={isProjectsModalOpen}
        onClose={() => setIsProjectsModalOpen(false)}
        activeProjectId={activeProjectId}
        onSelectProject={handleSelectProject}
      />

      {/* Modal de Informe Ejecutivo */}
      <ReportModal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        activeProjectId={activeProjectId}
        candidateId={politicalCandidate?.id}
      />

      {/* Modal de Progreso Asíncrono en Streaming SSE (Sprint 2) */}
      <TaskProgressModal
        isOpen={isProgressModalOpen}
        progress={taskProgress}
        stage={taskStage}
        status={taskStatus}
        error={taskError}
        onClose={() => {
          setIsProgressModalOpen(false);
          setImporting(false);
        }}
      />

      {/* Pie de página */}
      <footer className="app-footer">
        {graph?.meta?.synthetic && (
          <span>
            Datos sintéticos — Red ficticia generada para demostración. #ReformaDelAgua no corresponde a ningún evento real.
          </span>
        )}
        {!graph?.meta?.synthetic && (
          <span>
            Datos importados — El índice de autenticidad usa una heurística placeholder, no es un clasificador validado.
          </span>
        )}
      </footer>
    </div>
  );
}
