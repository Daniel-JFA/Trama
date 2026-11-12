# Bitácora de Cooperación Multi-Agente (AI Cooperation Log) — Proyecto TRAMA

## Sprint 5.5: Seguimiento de Creadores, Crecimiento y Nichos

### Sub-sprint 5.5.0 — Cimientos (Carril INT - Integrador)
* **Fecha:** 2026-11-11
* **Rama:** `s55-int` ➔ `main`
* **Archivos creados:**
  - `backend/alembic/versions/ae8e56481230_create_creator_growth_and_niche_tables.py`
  - `backend/app/providers/__init__.py`
  - `backend/app/providers/base.py`
  - `backend/app/dependencies.py`
  - `backend/app/crypto.py`
  - `backend/app/routers/__init__.py`
  - `backend/app/routers/growth.py`
  - `backend/app/routers/oauth.py`
  - `backend/app/routers/trends.py`
  - `backend/app/routers/niches.py`
  - `backend/tests/test_base_provider.py`
  - `backend/tests/test_crypto.py`
  - `backend/tests/test_api_contract.py`
  - `backend/tests/fixtures/youtube/channel_sample.json`
  - `backend/tests/fixtures/youtube/videos_sample.json`
  - `backend/tests/fixtures/meta/instagram_user_sample.json`
  - `backend/tests/fixtures/meta/facebook_page_sample.json`
* **Archivos modificados:**
  - `backend/requirements.txt`: añadidas dependencias (`google-api-python-client`, `httpx`, `apscheduler`, `cryptography`, `weasyprint`).
  - `backend/app/models.py`: modelos `Account`, `AccountSnapshot`, `PostSnapshot`, `OAuthCredential`.
  - `backend/app/schemas.py`: contratos de payloads y respuestas HTTP para crecimiento, tendencias y nichos.
  - `backend/app/main.py`: registro de routers 501 e inyección desacoplada de `get_current_project`.
  - `backend/tests/conftest.py`: fixtures para tokens y mock providers.
  - `PLAN_DE_TRABAJO.md`: actualización de la tabla de verificación de Sprint 4, 5 y 5.5.0.
* **Resultados de verificación:**
  - `pytest tests`: 72 passed, 0 skipped en 7.48s (los 3 tests de PDF con WeasyPrint ahora pasan).
  - `alembic heads`: Un solo head activo (`ae8e56481230`).
  - Migración testeada con `upgrade head` y `downgrade -1`.
  - Benchmark DuckDB ejecutado: 2M eventos particionados (agregación por minuto: 208 ms, rolling window: 38.9 ms).
* **Estado:** Cimientos listos para arranque paralelo de carriles A, B, C y D.


### Sub-sprint 5.5.1 — Fase A: Cuentas Propias y Crecimiento (Carriles A, B, C, D)
* **Fecha:** 2026-11-11
* **Carril A (YouTube):**
  - Implementado `YouTubeProvider` (`backend/app/providers/youtube.py`) con control de cuota (10.000 unidades/día), caché en memoria y manejo de errores.
  - Fixtures en `backend/tests/fixtures/youtube/` (`comments_sample.json`, `error_quota_exceeded.json`).
  - Tests unitarios en `backend/tests/test_youtube_provider.py` (9 tests pasando sin red).
* **Carril B (Snapshots y Scheduler):**
  - Servicio `growth.py` con `take_account_snapshot`, control de duplicados diarios UTC y cálculo de métricas de crecimiento 7d/30d y deltas.
  - Planificador `scheduler.py` con APScheduler y aislamiento ante fallos individuales.
  - Router `routers/growth.py` con endpoints `/accounts` (201), `/accounts` (200), `/accounts/{id}/snapshot` (200) y `/accounts/{id}/growth` (200).
  - Tests en `backend/tests/test_growth.py` (5 tests pasando).
* **Carril C (Panel de Crecimiento Frontend):**
  - Cliente `frontend/lib/growthApi.js` con fallback mock y conexión a endpoints reales.
  - Gráfica interactiva `GrowthChart.jsx` (SVG reactivo, área degradada, tooltips, multicuenta).
  - Componente `GrowthPanel.jsx` (resumen KPI, tabla de mejores posts, modal para registrar cuentas).
  - Tests frontend en `frontend/__tests__/growth.test.js` (7 tests pasando con `node:test`).
  - Build de Next.js (`npm run build`) validado con 0 errores.
* **Carril D (Meta & OAuth):**
  - Flujo OAuth2 completo en `backend/app/oauth.py` (anti-CSRF HMAC `state`, intercambio de tokens y guardado cifrado con Fernet).
  - `MetaProvider` (`backend/app/providers/meta.py`) para Instagram y Facebook con traducción canónica de errores (`OAuthException` 190, 17, 10).
  - Router `routers/oauth.py` con `/oauth/{provider}/start` (200) y `/oauth/{provider}/callback` (validación anti-CSRF).
  - Fixtures en `backend/tests/fixtures/meta/` (`instagram_media_sample.json`, errores de expiración, rate limit y permisos).
  - Tests en `backend/tests/test_meta_provider.py` (10 tests pasando).
* **Verificación de Cierre Fase A:**
  - `pytest tests`: 96 passed, 0 skipped en 9.15s.
  - `npm test`: 7 passed en 117ms.
  - `npm run build`: Compilación exitosa en Next.js.
  - `alembic heads`: Un solo head activo (`ae8e56481230`).
