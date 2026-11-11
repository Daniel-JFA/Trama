"use client";

import { useEffect } from "react";

export default function TaskProgressModal({
  isOpen,
  progress = 0,
  stage = "Iniciando procesamiento...",
  status = "processing",
  error = null,
  onClose,
}) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" style={{ zIndex: 1200 }}>
      <div
        className="modal-card"
        style={{
          maxWidth: "480px",
          width: "92%",
          background: "#0E1726",
          border: "1px solid rgba(255, 255, 255, 0.14)",
          borderRadius: "16px",
          padding: "28px",
          boxShadow: "0 20px 50px rgba(0, 0, 0, 0.6)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ fontSize: "20px" }}>
              {status === "failed" ? "❌" : status === "completed" ? "✅" : "⚡"}
            </span>
            <h3 style={{ margin: 0, fontSize: "16px", fontWeight: "700", color: "#F8FAFC" }}>
              {status === "failed"
                ? "Error en Procesamiento"
                : status === "completed"
                ? "Procesamiento Completado"
                : "Procesando Red en Streaming"}
            </h3>
          </div>
          {status === "failed" && (
            <button
              onClick={onClose}
              style={{
                background: "transparent",
                border: "none",
                color: "#94A3B8",
                fontSize: "18px",
                cursor: "pointer",
              }}
            >
              ✕
            </button>
          )}
        </div>

        <p style={{ margin: "0 0 20px 0", fontSize: "13px", color: "#94A3B8", lineHeight: 1.5 }}>
          {status === "failed"
            ? "Ocurrió una inconsistencia durante la ingesta del archivo."
            : status === "completed"
            ? "El grafo se ha construido, analizado y persistido con éxito."
            : "Worker ejecutando pipeline en segundo plano. Progreso recibido vía Server-Sent Events (SSE)."}
        </p>

        {/* Barra de progreso */}
        <div style={{ marginBottom: "12px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px", fontSize: "12px" }}>
            <span style={{ color: "#E2E8F0", fontWeight: "600" }}>{stage}</span>
            <span style={{ color: "#38BDF8", fontWeight: "700", fontFamily: "var(--font-mono, monospace)" }}>
              {progress}%
            </span>
          </div>

          <div
            style={{
              width: "100%",
              height: "10px",
              background: "rgba(255, 255, 255, 0.08)",
              borderRadius: "999px",
              overflow: "hidden",
              position: "relative",
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${Math.min(100, Math.max(progress, 4))}%`,
                background:
                  status === "failed"
                    ? "#EF4444"
                    : status === "completed"
                    ? "#10B981"
                    : "linear-gradient(90deg, #3B82F6 0%, #10B981 100%)",
                borderRadius: "999px",
                transition: "width 0.35s ease, background 0.3s ease",
                boxShadow:
                  status === "failed"
                    ? "0 0 12px rgba(239, 68, 68, 0.5)"
                    : "0 0 12px rgba(56, 189, 248, 0.5)",
              }}
            />
          </div>
        </div>

        {/* Mensaje de error si falla */}
        {error && (
          <div
            style={{
              background: "rgba(239, 68, 68, 0.12)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              borderRadius: "8px",
              padding: "10px 14px",
              marginTop: "16px",
              color: "#FCA5A5",
              fontSize: "12px",
              lineHeight: 1.4,
            }}
          >
            {error}
          </div>
        )}

        {/* Botones de acción */}
        {status === "failed" && (
          <div style={{ marginTop: "20px", display: "flex", justifyContent: "flex-end" }}>
            <button className="btn-secondary" onClick={onClose}>
              Cerrar
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
