/**
 * utils.js — Funciones de utilidad visual y de formato para TRAMA.
 */

export function initials(handle) {
  if (!handle) return "";
  const parts = handle.replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, " ").trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return handle.slice(0, 2).toUpperCase();
}

export function authColor(auth) {
  if (auth >= 70) return "#5AD1B3";
  if (auth >= 40) return "#E8C15A";
  return "#E060B8";
}
