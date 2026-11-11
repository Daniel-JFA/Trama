"use client";

import { useRef } from "react";

export default function TopBar({
  graph,
  dataSource,
  searchValue,
  onSearchChange,
  onSearchSubmit,
  onImportCSV,
  onResetDemo,
  onExportPNG,
  onExportSVG,
  onExportGEXF,
  onOpenReport,
  comparisonCount,
  onOpenComparison,
  onOpenProjects,
  onOpenWarRoom,
  showCoornetLayer,
  onToggleCoornetLayer,
  importing,
  importError,
}) {
  const fileInputRef = useRef(null);

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      onSearchSubmit();
    }
  };

  return (
    <header className="top-bar">
      <div className="top-bar-left">
        <span className="brand">TRAMA</span>
        <a
          href="/landing"
          className="btn-secondary btn-landing-nav"
          title="Ver página de presentación, precios y casos de uso"
        >
          🚀 Conoce TRAMA
        </a>
        <button
          className="btn-secondary btn-projects-nav"
          onClick={onOpenProjects}
          title="Ver y gestionar investigaciones guardadas"
        >
          📁 Investigaciones
        </button>
        <button
          className="btn-secondary btn-warroom-nav"
          onClick={onOpenWarRoom}
          title="Modo Inteligencia y Estrategia de Campaña"
          style={{
            borderColor: "rgba(245, 158, 11, 0.4)",
            color: "#F59E0B",
            background: "rgba(245, 158, 11, 0.1)",
          }}
        >
          🎯 War Room
        </button>
        {graph && (
          <div className="project-chip">
            <span className="chip-topic">{graph.meta?.topic}</span>
            <span className="chip-sep" />
            {graph.meta?.weeks > 0 && (
              <span className="chip-detail">{graph.meta.weeks} semanas</span>
            )}
            <span className="chip-sep" />
            <span
              className={`chip-source ${
                dataSource === "local"
                  ? "chip-source-local"
                  : dataSource === "imported"
                  ? "chip-source-imported"
                  : "chip-source-live"
              }`}
            >
              {dataSource === "local"
                ? "sin backend (muestra local)"
                : dataSource === "imported"
                ? "datos importados"
                : "backend activo"}
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
          onChange={(e) => onSearchChange(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          style={{ display: "none" }}
          onChange={onImportCSV}
        />
        <button
          className="btn-secondary btn-import"
          onClick={() => fileInputRef.current?.click()}
          disabled={importing || dataSource === "local"}
          title={
            dataSource === "local"
              ? "Requiere backend activo"
              : "Importar CSV con tus interacciones"
          }
        >
          {importing ? "Importando…" : "Importar CSV"}
        </button>
        {dataSource === "imported" && (
          <button
            className="btn-secondary btn-reset"
            onClick={onResetDemo}
            disabled={importing}
          >
            Demo
          </button>
        )}
        <button
          className={`btn-secondary btn-coornet-toggle ${showCoornetLayer ? "btn-coornet-active" : ""}`}
          onClick={onToggleCoornetLayer}
          title={showCoornetLayer ? "Ocultar capa de co-compartición CooRnet" : "Activar capa secundaria CooRnet (Co-compartición sincrónica Δt ≤ 45s)"}
          style={{
            borderColor: showCoornetLayer ? "rgba(236, 72, 153, 0.8)" : "rgba(236, 72, 153, 0.35)",
            color: "#EC4899",
            background: showCoornetLayer ? "rgba(236, 72, 153, 0.22)" : "rgba(236, 72, 153, 0.08)",
            fontWeight: showCoornetLayer ? "700" : "500",
          }}
        >
          🔗 CooRnet
        </button>
        <button className="btn-secondary" onClick={onOpenReport} title="Ver informe ejecutivo de inteligencia">
          📄 Informe
        </button>
        <button className="btn-secondary" onClick={onExportPNG} title="Exportar imagen rasterizada PNG">
          PNG
        </button>
        <button className="btn-secondary" onClick={onExportSVG} title="Exportar grafo vectorial SVG de alta definición">
          SVG
        </button>
        <button className="btn-secondary" onClick={onExportGEXF} title="Exportar red para Gephi (GEXF)">
          Gephi
        </button>
        {comparisonCount > 0 && (
          <button
            className="btn-secondary btn-compare-active"
            onClick={onOpenComparison}
          >
            Comparar ({comparisonCount})
          </button>
        )}
      </div>

      {importError && <div className="import-error">{importError}</div>}
    </header>
  );
}
