"use client";

import { useState, useEffect } from "react";
import GrowthChart from "../charts/GrowthChart";
import {
  getAccounts,
  createAccount,
  triggerSnapshot,
  getAccountGrowth,
} from "../../lib/growthApi";

export default function GrowthPanel({
  projectId = "demo-reforma-del-agua",
  onClose,
}) {
  const [accounts, setAccounts] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState(null);
  const [growthData, setGrowthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [takingSnapshot, setTakingSnapshot] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [compareIds, setCompareIds] = useState([]);
  const [compareDataMap, setCompareDataMap] = useState({});
  const [errorMsg, setErrorMsg] = useState(null);

  // Formulario nueva cuenta
  const [newPlatform, setNewPlatform] = useState("youtube");
  const [newExternalId, setNewExternalId] = useState("");
  const [newHandle, setNewHandle] = useState("");
  const [newIsOwned, setNewIsOwned] = useState(false);

  // Cargar cuentas iniciales
  useEffect(() => {
    async function load() {
      setLoading(true);
      setErrorMsg(null);
      try {
        const accs = await getAccounts(projectId);
        setAccounts(accs || []);
        if (accs && accs.length > 0) {
          setSelectedAccountId(accs[0].id);
        }
      } catch (err) {
        setErrorMsg("Error cargando cuentas del proyecto.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [projectId]);

  // Cargar métricas al cambiar de cuenta seleccionada
  useEffect(() => {
    if (!selectedAccountId) return;
    async function loadGrowth() {
      try {
        const data = await getAccountGrowth(projectId, selectedAccountId);
        setGrowthData(data);
      } catch (err) {
        console.error("Error al cargar serie de crecimiento:", err);
      }
    }
    loadGrowth();
  }, [projectId, selectedAccountId]);

  // Forzar snapshot manual
  const handleTriggerSnapshot = async () => {
    if (!selectedAccountId || takingSnapshot) return;
    setTakingSnapshot(true);
    try {
      await triggerSnapshot(projectId, selectedAccountId);
      // Recargar serie
      const updated = await getAccountGrowth(projectId, selectedAccountId);
      setGrowthData(updated);
    } catch (err) {
      alert("Error al tomar instantánea. Verifique las credenciales del proveedor.");
    } finally {
      setTakingSnapshot(false);
    }
  };

  // Registrar nueva cuenta
  const handleCreateAccount = async (e) => {
    e.preventDefault();
    if (!newExternalId.trim()) return;

    try {
      const created = await createAccount(projectId, {
        platform: newPlatform,
        external_id: newExternalId.trim(),
        handle: newHandle.trim() || newExternalId.trim(),
        display_name: newHandle.trim() || newExternalId.trim(),
        is_owned: newIsOwned,
      });

      setAccounts((prev) => [created, ...prev]);
      setSelectedAccountId(created.id);
      setShowAddModal(false);
      setNewExternalId("");
      setNewHandle("");
    } catch (err) {
      alert("Error al registrar la cuenta.");
    }
  };

  const selectedAccount = accounts.find((a) => a.id === selectedAccountId);

  return (
    <div className="panel-content flex flex-col h-full bg-neutral-950 text-neutral-100 p-4 overflow-y-auto">
      {/* ─── Encabezado ──────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between pb-4 border-b border-neutral-800">
        <div>
          <h2 className="text-sm font-semibold tracking-wide uppercase text-neutral-200">
            Seguimiento de Creadores y Crecimiento
          </h2>
          <p className="text-xs text-neutral-500 font-mono">
            Proyecto: {projectId}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAddModal(true)}
            className="px-2.5 py-1 text-xs font-medium rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/20 transition"
          >
            + Seguir Cuenta
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="text-neutral-500 hover:text-neutral-300 p-1 text-xs"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* ─── Estado de Carga o Error ─────────────────────────────────────────── */}
      {loading ? (
        <div className="py-12 text-center text-xs text-neutral-500 font-mono">
          Cargando métricas de crecimiento...
        </div>
      ) : accounts.length === 0 ? (
        /* ─── Estado Vacío ─────────────────────────────────────────────────── */
        <div className="py-12 text-center flex flex-col items-center gap-3">
          <p className="text-xs text-neutral-400">
            No hay cuentas registradas en este proyecto todavía.
          </p>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-3 py-1.5 text-xs rounded bg-cyan-600 text-white font-medium hover:bg-cyan-500 transition"
          >
            Registrar Primera Cuenta
          </button>
        </div>
      ) : (
        /* ─── Panel Principal ──────────────────────────────────────────────── */
        <div className="flex flex-col gap-4 mt-4">
          {/* Selector de Cuentas */}
          <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b border-neutral-900">
            {accounts.map((acc) => {
              const active = acc.id === selectedAccountId;
              return (
                <button
                  key={acc.id}
                  onClick={() => setSelectedAccountId(acc.id)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded text-xs font-mono transition whitespace-nowrap ${
                    active
                      ? "bg-neutral-800 text-cyan-400 border border-cyan-500/40"
                      : "bg-neutral-900 text-neutral-400 border border-neutral-800 hover:border-neutral-700"
                  }`}
                >
                  <span
                    className={`w-2 h-2 rounded-full ${
                      acc.platform === "youtube"
                        ? "bg-rose-500"
                        : acc.platform === "instagram"
                        ? "bg-pink-500"
                        : "bg-blue-500"
                    }`}
                  />
                  <span>@{acc.handle}</span>
                  {acc.is_owned && (
                    <span className="text-[9px] px-1 bg-cyan-950 text-cyan-300 rounded border border-cyan-800/40">
                      PROPIA
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Tarjetas KPI de la cuenta activa */}
          {selectedAccount && growthData && (
            <>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold text-neutral-100">
                    {selectedAccount.display_name}
                  </h3>
                  <span className="text-xs font-mono text-neutral-400">
                    ID Externo: {selectedAccount.external_id}
                  </span>
                </div>
                <button
                  onClick={handleTriggerSnapshot}
                  disabled={takingSnapshot}
                  className="px-3 py-1.5 text-xs font-mono rounded bg-neutral-800 hover:bg-neutral-700 text-neutral-200 border border-neutral-700 disabled:opacity-50 transition"
                >
                  {takingSnapshot ? "Recolectando..." : "⚡ Instantánea Ahora"}
                </button>
              </div>

              {/* Grid KPI */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                <div className="bg-neutral-900/60 border border-neutral-800 p-2.5 rounded">
                  <span className="text-[10px] font-mono text-neutral-500 uppercase">
                    Seguidores Actuales
                  </span>
                  <div className="text-lg font-bold text-cyan-400 font-mono mt-0.5">
                    {growthData.series?.length > 0
                      ? growthData.series[growthData.series.length - 1].followers.toLocaleString()
                      : "—"}
                  </div>
                </div>

                <div className="bg-neutral-900/60 border border-neutral-800 p-2.5 rounded">
                  <span className="text-[10px] font-mono text-neutral-500 uppercase">
                    Crecimiento 7 Días
                  </span>
                  <div className="text-lg font-bold font-mono mt-0.5 flex items-center gap-1.5">
                    <span
                      className={
                        (growthData.summary?.growth_7d || 0) >= 0
                          ? "text-emerald-400"
                          : "text-rose-400"
                      }
                    >
                      {growthData.summary?.growth_7d >= 0 ? "+" : ""}
                      {growthData.summary?.growth_7d?.toLocaleString()}
                    </span>
                    <span className="text-[11px] text-neutral-500 font-normal">
                      ({growthData.summary?.growth_7d_pct}%)
                    </span>
                  </div>
                </div>

                <div className="bg-neutral-900/60 border border-neutral-800 p-2.5 rounded">
                  <span className="text-[10px] font-mono text-neutral-500 uppercase">
                    Crecimiento 30 Días
                  </span>
                  <div className="text-lg font-bold font-mono mt-0.5 flex items-center gap-1.5">
                    <span
                      className={
                        (growthData.summary?.growth_30d || 0) >= 0
                          ? "text-emerald-400"
                          : "text-rose-400"
                      }
                    >
                      {growthData.summary?.growth_30d >= 0 ? "+" : ""}
                      {growthData.summary?.growth_30d?.toLocaleString()}
                    </span>
                    <span className="text-[11px] text-neutral-500 font-normal">
                      ({growthData.summary?.growth_30d_pct}%)
                    </span>
                  </div>
                </div>

                <div className="bg-neutral-900/60 border border-neutral-800 p-2.5 rounded">
                  <span className="text-[10px] font-mono text-neutral-500 uppercase">
                    Publicaciones Monitoreadas
                  </span>
                  <div className="text-lg font-bold text-neutral-200 font-mono mt-0.5">
                    {growthData.summary?.top_posts?.length || 0}
                  </div>
                </div>
              </div>

              {/* Gráfica de Crecimiento */}
              <div className="mt-2">
                <GrowthChart series={growthData.series || []} height={220} />
              </div>

              {/* Mejores Publicaciones */}
              {growthData.summary?.top_posts?.length > 0 && (
                <div className="mt-3">
                  <h4 className="text-xs font-mono uppercase text-neutral-400 tracking-wider mb-2">
                    Mejores Publicaciones Recientes
                  </h4>
                  <div className="flex flex-col gap-2">
                    {growthData.summary.top_posts.map((post) => (
                      <div
                        key={post.id}
                        className="p-2.5 bg-neutral-900/40 border border-neutral-800/80 rounded flex items-start justify-between gap-4 text-xs"
                      >
                        <div className="flex-1">
                          <p className="text-neutral-200 line-clamp-2">
                            {post.text || `Publicación ${post.id}`}
                          </p>
                          <div className="flex items-center gap-2 mt-1.5">
                            <span className="font-mono text-[10px] text-neutral-500">
                              {post.published_at?.slice(0, 10)}
                            </span>
                            {post.hashtags?.map((tag) => (
                              <span
                                key={tag}
                                className="text-[10px] text-cyan-400 bg-cyan-950/40 px-1 py-0.2 rounded border border-cyan-800/30 font-mono"
                              >
                                #{tag}
                              </span>
                            ))}
                          </div>
                        </div>
                        <div className="text-right font-mono text-neutral-400 text-xs shrink-0">
                          <div>
                            <b className="text-neutral-100">{post.views?.toLocaleString()}</b>{" "}
                            vistas
                          </div>
                          <div className="text-[10px] text-neutral-500">
                            {post.likes?.toLocaleString()} likes • {post.comments?.toLocaleString()} com.
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ─── Modal Registrar Cuenta ────────────────────────────────────────── */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4">
          <div className="bg-neutral-900 border border-neutral-700 rounded-lg max-w-sm w-full p-5 shadow-2xl">
            <h3 className="text-sm font-bold uppercase tracking-wider text-neutral-100 mb-4">
              Registrar Nueva Cuenta
            </h3>
            <form onSubmit={handleCreateAccount} className="flex flex-col gap-3 text-xs">
              <div>
                <label className="text-neutral-400 block mb-1">Plataforma</label>
                <select
                  value={newPlatform}
                  onChange={(e) => setNewPlatform(e.target.value)}
                  className="w-full bg-neutral-950 border border-neutral-800 rounded px-2.5 py-1.5 text-neutral-200"
                >
                  <option value="youtube">YouTube</option>
                  <option value="instagram">Instagram</option>
                  <option value="facebook">Facebook</option>
                </select>
              </div>

              <div>
                <label className="text-neutral-400 block mb-1">
                  ID Externo (Channel ID / Instagram ID)
                </label>
                <input
                  type="text"
                  placeholder="ej. UC_x5XG1OV2P6uZZ5FSM9Ttw"
                  value={newExternalId}
                  onChange={(e) => setNewExternalId(e.target.value)}
                  className="w-full bg-neutral-950 border border-neutral-800 rounded px-2.5 py-1.5 text-neutral-200 font-mono"
                  required
                />
              </div>

              <div>
                <label className="text-neutral-400 block mb-1">Handle / Nombre</label>
                <input
                  type="text"
                  placeholder="ej. googledevelopers"
                  value={newHandle}
                  onChange={(e) => setNewHandle(e.target.value)}
                  className="w-full bg-neutral-950 border border-neutral-800 rounded px-2.5 py-1.5 text-neutral-200"
                />
              </div>

              <div className="flex items-center gap-2 mt-1">
                <input
                  type="checkbox"
                  id="is_owned_chk"
                  checked={newIsOwned}
                  onChange={(e) => setNewIsOwned(e.target.checked)}
                  className="rounded border-neutral-700"
                />
                <label htmlFor="is_owned_chk" className="text-neutral-300">
                  Es cuenta propia administrada
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 mt-4 pt-3 border-t border-neutral-800">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-1.5 rounded text-neutral-400 hover:text-neutral-200"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-3.5 py-1.5 rounded bg-cyan-600 text-white font-medium hover:bg-cyan-500"
                >
                  Guardar y Seguir
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
