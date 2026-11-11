/**
 * growthApi.js — Cliente API para seguimiento de cuentas y crecimiento histórico (Sprint 5.5).
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const MOCK_ACCOUNTS = [
  {
    id: 1,
    project_id: "demo-reforma-del-agua",
    platform: "youtube",
    external_id: "UC_x5XG1OV2P6uZZ5FSM9Ttw",
    handle: "googledevelopers",
    display_name: "Google Developers",
    is_owned: true,
    created_at: "2026-11-01T10:00:00Z",
  },
  {
    id: 2,
    project_id: "demo-reforma-del-agua",
    platform: "instagram",
    external_id: "ig_trama_lab",
    handle: "trama_investigation",
    display_name: "Trama Investigation Lab",
    is_owned: false,
    created_at: "2026-11-03T12:30:00Z",
  },
];

export const MOCK_GROWTH_DATA = {
  1: {
    account_id: 1,
    series: [
      { date: "2026-11-05", followers: 2348500, delta: 0, growth_pct: 0.0 },
      { date: "2026-11-06", followers: 2349100, delta: 600, growth_pct: 0.03 },
      { date: "2026-11-07", followers: 2349550, delta: 450, growth_pct: 0.02 },
      { date: "2026-11-08", followers: 2350200, delta: 650, growth_pct: 0.03 },
      { date: "2026-11-09", followers: 2351100, delta: 900, growth_pct: 0.04 },
      { date: "2026-11-10", followers: 2352050, delta: 950, growth_pct: 0.04 },
      { date: "2026-11-11", followers: 2353200, delta: 1150, growth_pct: 0.05 },
    ],
    summary: {
      growth_7d: 4700,
      growth_7d_pct: 0.2,
      growth_30d: 18500,
      growth_30d_pct: 0.79,
      top_posts: [
        {
          id: "vid_sample_102",
          published_at: "2026-11-05T15:30:00Z",
          views: 32000,
          likes: 2400,
          comments: 190,
          text: "FastAPI and Columnar Analytics with DuckDB #fastapi #duckdb",
          hashtags: ["fastapi", "duckdb"],
        },
        {
          id: "vid_sample_101",
          published_at: "2026-11-01T12:00:00Z",
          views: 15000,
          likes: 1200,
          comments: 85,
          text: "Intro to Graph Analysis in Python #network #graph",
          hashtags: ["network", "graph"],
        },
      ],
    },
  },
};

/**
 * Obtiene la lista de cuentas seguidas en el proyecto.
 */
export async function getAccounts(projectId = "demo-reforma-del-agua") {
  try {
    const res = await fetch(`${API_BASE}/accounts`, {
      headers: {
        "X-Project-Id": projectId,
      },
    });
    if (!res.ok) {
      console.warn("Fallo HTTP en getAccounts, usando datos mock.");
      return MOCK_ACCOUNTS;
    }
    const data = await res.json();
    return data && data.length > 0 ? data : MOCK_ACCOUNTS;
  } catch (err) {
    console.warn("Error de red conectando con backend, usando mock.", err);
    return MOCK_ACCOUNTS;
  }
}

/**
 * Registra una nueva cuenta a seguir.
 */
export async function createAccount(projectId, accountPayload) {
  try {
    const res = await fetch(`${API_BASE}/accounts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Project-Id": projectId,
      },
      body: JSON.stringify(accountPayload),
    });
    if (!res.ok) {
      throw new Error(`Error ${res.status}: ${res.statusText}`);
    }
    return await res.json();
  } catch (err) {
    console.warn("Fallo al crear cuenta en API real, simulando localmente.", err);
    return {
      id: Date.now(),
      project_id: projectId,
      ...accountPayload,
      created_at: new Date().toISOString(),
    };
  }
}

/**
 * Fuerza la recolección inmediata de una instantánea.
 */
export async function triggerSnapshot(projectId, accountId) {
  const res = await fetch(`${API_BASE}/accounts/${accountId}/snapshot`, {
    method: "POST",
    headers: {
      "X-Project-Id": projectId,
    },
  });
  if (!res.ok) {
    throw new Error(`Error ${res.status} al solicitar snapshot`);
  }
  return await res.json();
}

/**
 * Obtiene la serie temporal de crecimiento y métricas de una cuenta.
 */
export async function getAccountGrowth(projectId, accountId, params = {}) {
  const query = new URLSearchParams(params).toString();
  const url = `${API_BASE}/accounts/${accountId}/growth${query ? `?${query}` : ""}`;

  try {
    const res = await fetch(url, {
      headers: {
        "X-Project-Id": projectId,
      },
    });
    if (!res.ok) {
      console.warn("Fallo HTTP al obtener growth, usando mock.");
      return MOCK_GROWTH_DATA[accountId] || MOCK_GROWTH_DATA[1];
    }
    return await res.json();
  } catch (err) {
    console.warn("Error de red en getAccountGrowth, usando mock.", err);
    return MOCK_GROWTH_DATA[accountId] || MOCK_GROWTH_DATA[1];
  }
}
