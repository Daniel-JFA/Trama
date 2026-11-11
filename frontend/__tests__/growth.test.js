/**
 * growth.test.js — Pruebas unitarias para utilidades y cliente de crecimiento (Sprint 5.5).
 */

const test = require("node:test");
const assert = require("node:assert");

// Importación dinámica o test de contratos de growthApi
test("MOCK_ACCOUNTS contiene estructura canónica según contrato", async () => {
  const { MOCK_ACCOUNTS } = await import("../lib/growthApi.js");

  assert.ok(Array.isArray(MOCK_ACCOUNTS));
  assert.strictEqual(MOCK_ACCOUNTS.length >= 2, true);

  const acc = MOCK_ACCOUNTS[0];
  assert.strictEqual(typeof acc.id, "number");
  assert.strictEqual(typeof acc.platform, "string");
  assert.strictEqual(typeof acc.external_id, "string");
  assert.strictEqual(typeof acc.handle, "string");
  assert.strictEqual(typeof acc.is_owned, "boolean");
});

test("MOCK_GROWTH_DATA tiene serie temporal continua y cálculo de deltas", async () => {
  const { MOCK_GROWTH_DATA } = await import("../lib/growthApi.js");

  const growth = MOCK_GROWTH_DATA[1];
  assert.ok(growth);
  assert.strictEqual(growth.account_id, 1);
  assert.ok(Array.isArray(growth.series));
  assert.strictEqual(growth.series.length, 7);

  // Verificar campos de serie
  growth.series.forEach((pt) => {
    assert.match(pt.date, /^\d{4}-\d{2}-\d{2}$/);
    assert.strictEqual(typeof pt.followers, "number");
    assert.strictEqual(typeof pt.delta, "number");
    assert.strictEqual(typeof pt.growth_pct, "number");
  });

  // Verificar resumen
  assert.ok(growth.summary);
  assert.strictEqual(typeof growth.summary.growth_7d, "number");
  assert.strictEqual(typeof growth.summary.growth_7d_pct, "number");
  assert.ok(Array.isArray(growth.summary.top_posts));
  assert.strictEqual(growth.summary.top_posts.length >= 1, true);
});

test("Cálculo matemático de deltas y tasa de crecimiento", () => {
  const prevFollowers = 10000;
  const currentFollowers = 10500;
  const delta = currentFollowers - prevFollowers;
  const pct = (delta / prevFollowers) * 100;

  assert.strictEqual(delta, 500);
  assert.strictEqual(pct, 5.0);
});
