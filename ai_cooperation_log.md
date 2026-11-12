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

### Sub-sprint 5.5.1 — Actualización Carril A: OAuth + YouTube Analytics API & Backfill Histórico
* **Fecha:** 2026-11-12
* **Rama:** `s55-a`
* **Nicho objetivo:** Tecnología / Desarrollo de Software y AI (alineado al proyecto TRAMA)
* **Archivos modificados/creados:**
  - `backend/app/providers/youtube.py`: Añadido soporte para Google OAuth2 (`get_google_auth_url`, `exchange_code_for_tokens`, `refresh_google_token`), inicialización de cliente YouTube Analytics API v2 con credenciales OAuth, métodos analíticos (`fetch_channel_daily_metrics`, `fetch_video_analytics`, `fetch_audience_retention`, `fetch_traffic_sources`, `fetch_demographics`) y backfill histórico por bloques (`backfill_channel_history`). Dataclasses tipadas: `YouTubeDailyMetric`, `YouTubeVideoAnalytics`, `TrafficSourceItem`, `DemographicsItem`, `AudienceRetentionPoint`, `BackfillResult`.
  - `backend/tests/fixtures/youtube/`: Nuevas fixtures JSON con especificación oficial de Google Discovery: `analytics_channel_daily.json`, `analytics_video_metrics.json`, `analytics_traffic_sources.json`, `analytics_demographics.json`, `analytics_audience_retention.json`, `oauth_token_response.json`.
  - `backend/tests/test_youtube_provider.py`: 21 tests unitarios pasando al 100% sin red (+12 tests nuevos para OAuth, Analytics API y Backfill).
* **Resultados de verificación:**
  - `pytest backend/tests/test_youtube_provider.py`: 21 passed en 0.27s.
  - `pytest backend/tests`: 108 passed en 8.45s (0 regresiones).
  - `npm test --prefix frontend`: 7 passed en 212ms.
* **No verificado contra API real:**
  - Consultas en vivo contra los servidores de Google API (OAuth en navegador y llamadas de red a YouTube Analytics API v2), al no haber credenciales reales inyectadas en el entorno local durante los tests automatizados (mocked discovery).
* **Petición al Integrador:**
  - Nuevas columnas o tablas requeridas para no volcar métricas en `raw`:
    1. Tabla `AccountAnalyticsDaily`: `account_id`, `date`, `views`, `watch_time_minutes`, `average_view_duration_seconds`, `average_view_percentage`, `subscribers_gained`, `subscribers_lost`, `net_subscribers`, `impressions`, `ctr`, `traffic_sources` (JSON), `demographics` (JSON).
    2. Columnas en `PostSnapshot`: `impressions` (BigInteger), `ctr` (Float), `subscribers_gained` (Integer), `subscribers_lost` (Integer), `retention_rate_pct` (Float), `average_view_duration_seconds` (Integer).
    3. Exponer endpoints de Google OAuth en `routers/oauth.py` (`/oauth/google/start` y `/oauth/google/callback`) usando los métodos de `YouTubeProvider`.

### Sub-sprint 5.5.1 — Integración Fase A (Carril INT): Fusión s55-a, Migración Analítica y OAuth Google/YouTube
* **Fecha:** 2026-11-12
* **Rama:** `main` (fusión de `s55-a`)
* **Archivos modificados/creados:**
  - `backend/alembic/versions/065a57b9d092_add_account_analytics_daily_and_post_.py`: Migración encadenada sobre `ae8e56481230` creando `account_analytics_daily` y añadiendo columnas analíticas (`impressions`, `ctr`, `subscribers_gained`, `subscribers_lost`, `retention_rate_pct`, `average_view_duration_seconds`) a `post_snapshots`.
  - `backend/app/models.py`: Modelos SQLAlchemy `AccountAnalyticsDaily`, relación `analytics_daily` en `Account`, y columnas analíticas tipadas en `PostSnapshot`.
  - `backend/app/routers/oauth.py`: Habilitación de `"google"` y `"youtube"` en `/oauth/{provider}/start` y `/oauth/{provider}/callback` con validación HMAC anti-CSRF `state` y almacenamiento cifrado en reposo en `OAuthCredential`.
  - `backend/tests/conftest.py`: Inyección de fixtures de entorno para `GOOGLE_OAUTH_CLIENT_ID` y `GOOGLE_OAUTH_CLIENT_SECRET`.
  - `backend/tests/test_api_contract.py`: Cobertura de endpoints OAuth Google/YouTube (start, rechazo anti-CSRF y callback autorizado sin exponer tokens).
* **Resultados de verificación:**
  - `pytest backend/tests`: 109 passed en 8.57s (0 regresiones).
  - `alembic heads`: Un solo head activo (`065a57b9d092`).
  - Test de migración en SQLite con datos existentes: `upgrade head` y `downgrade -1` probados exitosamente preservando datos preexistentes.
  - `npm run build`: Compilación exitosa en Next.js (0 errores).
* **No verificado contra API real:**
  - Canje real de credenciales contra servidores de Google OAuth y Meta Graph API (sujeto a App Review y credenciales en entorno real).


