# Plan de Ejecución — Sprint 5.5: Seguimiento de Creadores, Crecimiento y Nichos

> Complementa `PLAN_DE_TRABAJO.md` (sección Sprint 5.5). Este documento descompone el sprint en sub-sprints ejecutables por varios agentes en paralelo, con archivos asignados por carril para evitar conflictos.
> Base: `main` en v0.5.0 (56 tests pasando, 3 omitidos; un solo head de Alembic `e2df3eeb0964`).

## 0. Reglas de ejecución (obligatorias)

1. **Un carril = un conjunto de archivos propios.** Nadie edita archivos de otro carril. Los archivos compartidos (`backend/app/main.py`, `backend/app/models.py`, `backend/requirements.txt`, `frontend/package.json`) solo los toca el **Integrador**.
2. **Rama por carril:** `s55-<carril>` desde `main`. PR pequeño y frecuente; el Integrador fusiona.
3. **Migraciones Alembic en cadena, no en paralelo.** Solo el Integrador crea migraciones. Un carril que necesite una columna o tabla la pide al Integrador. Debe haber siempre un único head.
4. **Routers propios:** cada carril backend expone su API con un `APIRouter` en su archivo; el Integrador lo registra en `main.py` con una línea.
5. **Contrato primero:** los esquemas de la sección 2 son fijos. Cambiarlos requiere acordarlo con el Integrador.
6. **Sin red en tests.** Toda API externa se prueba con fixtures JSON guardadas en `backend/tests/fixtures/`. Las pruebas reales con credenciales son manuales y quedan fuera de CI.
7. **Seguridad:** ningún token, clave o dato personal en el repo, en logs ni en fixtures. Las credenciales entran solo por variables de entorno. Los tokens OAuth se guardan cifrados en reposo.
8. **Definición de terminado de cada tarea:** tests nuevos en verde, `pytest backend/tests` sin regresiones, `npm run build` sin errores (si toca frontend), PR descrito con qué se verificó y qué no.
9. **Informe honesto:** si algo no se pudo verificar (por ejemplo, sin credenciales), se dice en el PR. No se marca como hecho lo que no se probó.
10. Protocolo de log: si existe `ai_cooperation_log.md` en la raíz de este proyecto, añadir una entrada al terminar.

## 1. Mapa de carriles y propiedad de archivos

| Carril | Responsable | Archivos propios (crear/editar) |
|---|---|---|
| **INT** Integrador | 1 agente | `backend/app/main.py`, `backend/app/models.py`, `backend/app/schemas.py` (solo lo del contrato), `backend/alembic/versions/*`, `backend/requirements.txt`, `frontend/package.json`, `PLAN_DE_TRABAJO.md` |
| **A** YouTube | 1 agente | `backend/app/providers/youtube.py`, `backend/tests/test_youtube_provider.py`, `backend/tests/fixtures/youtube/*` |
| **B** Snapshots y scheduler | 1 agente | `backend/app/scheduler.py`, `backend/app/routers/growth.py`, `backend/app/growth.py`, `backend/tests/test_growth.py` |
| **C** Panel de crecimiento | 1 agente | `frontend/components/panels/GrowthPanel.jsx`, `frontend/components/charts/GrowthChart.jsx`, `frontend/lib/growthApi.js`, `frontend/__tests__/growth.test.js` |
| **D** Meta (Instagram/Facebook) | 1 agente | `backend/app/providers/meta.py`, `backend/app/oauth.py`, `backend/app/routers/oauth.py`, `backend/tests/test_meta_provider.py`, `backend/tests/fixtures/meta/*` |
| **E** Temas y tendencias | 1 agente | `backend/app/topics.py`, `backend/app/routers/trends.py`, `backend/tests/test_topics.py` |
| **F** Descubrimiento de nichos | 1 agente | `backend/app/niches.py`, `backend/app/routers/niches.py`, `backend/tests/test_niches.py` |
| **G** Panel de nichos | 1 agente | `frontend/components/panels/NichePanel.jsx`, `frontend/components/charts/TrendChart.jsx`, `frontend/lib/nicheApi.js`, `frontend/__tests__/niche.test.js` |

## 2. Contrato compartido (fijado por el Integrador en el sub-sprint 5.5.0)

### 2.1 Modelo de datos nuevo

```
Account            id, project_id, platform ('youtube'|'instagram'|'facebook'),
                   external_id, handle, display_name, is_owned (bool),
                   created_at, UNIQUE(platform, external_id, project_id)

AccountSnapshot    id, account_id (FK), taken_at (UTC), followers, following,
                   posts_count, total_views, engagement_rate (float, nullable),
                   raw (JSON, sin datos personales)
                   INDEX(account_id, taken_at)

PostSnapshot       id, account_id (FK), external_post_id, published_at,
                   taken_at, views, likes, comments, shares, text (nullable),
                   hashtags (JSON list)

OAuthCredential    id, account_id (FK), provider, access_token_enc,
                   refresh_token_enc, expires_at, scopes
                   (tokens cifrados; nunca se exponen por API)
```

### 2.2 Interfaz `DataProvider` (`backend/app/providers/base.py`)

```python
class DataProvider(Protocol):
    platform: str
    def fetch_account(self, external_id: str) -> AccountData: ...
    def fetch_posts(self, external_id: str, since: datetime | None = None,
                    limit: int = 50) -> list[PostData]: ...
    def fetch_comments(self, post_id: str, limit: int = 100) -> list[CommentData]: ...
    def search_related(self, external_id: str, limit: int = 25) -> list[AccountData]: ...
```

Errores comunes: `ProviderAuthError`, `ProviderQuotaError` (con `retry_after`), `ProviderNotFoundError`. Los datos se normalizan a dataclasses `AccountData`, `PostData`, `CommentData` definidas en `base.py`.

### 2.3 API HTTP (todas con cabecera `X-Project-Id`)

| Método y ruta | Carril | Descripción |
|---|---|---|
| `POST /accounts` | B | Registra una cuenta a seguir `{platform, external_id, is_owned}` |
| `GET /accounts` | B | Lista cuentas del proyecto |
| `POST /accounts/{id}/snapshot` | B | Fuerza una instantánea ahora |
| `GET /accounts/{id}/growth?from=&to=&bucket=day` | B | Serie temporal `[{date, followers, delta, growth_pct}]` + resumen (crecimiento 7/30 días, mejores publicaciones) |
| `GET /oauth/{provider}/start` y `/callback` | D | Flujo OAuth para cuentas propias |
| `GET /trends?from=&to=&community_id=` | E | Temas/hashtags con volumen y aceleración |
| `POST /niches/discover` `{seed_account_id, depth}` | F | Lanza el descubrimiento (tarea asíncrona 202, mismo patrón que la ingesta) |
| `GET /niches/{id}` | F | Cuentas del nicho, temas etiquetados, líderes y tendencias |

## 3. Sub-sprints

### Sub-sprint 5.5.0 — Cimientos (INT, 2-3 días)  ▶ desbloquea todo lo demás

| # | Tarea | Resultado verificable |
|---|---|---|
| 0.1 | Modelos `Account`, `AccountSnapshot`, `PostSnapshot`, `OAuthCredential` en `models.py` | Importan sin error |
| 0.2 | Una migración Alembic con las cuatro tablas | `alembic upgrade head` y `downgrade -1` funcionan; un solo head |
| 0.3 | `backend/app/providers/base.py` con el protocolo, dataclasses y errores | Test que valida un proveedor falso contra el protocolo |
| 0.4 | Esqueleto de routers (`routers/growth.py`, `trends.py`, `niches.py`, `oauth.py`) con rutas que devuelven 501, registrados en `main.py` | `GET /openapi.json` lista las rutas del contrato |
| 0.5 | Dependencias en `requirements.txt`: `google-api-python-client`, `httpx`, `apscheduler`, `cryptography` | `pip install -r` limpio |
| 0.6 | Cifrado de tokens: utilidad `encrypt/decrypt` con clave de entorno `TRAMA_TOKEN_KEY` | Test de ida y vuelta; falla con clave ausente |
| 0.7 | Fixtures y `conftest` para proveedores falsos | Los carriles pueden empezar con mocks |
| 0.8 | En paralelo y sin credenciales: ejecutar la deuda de verificación de los Sprints 4 y 5 (WeasyPrint, benchmark DuckDB) y anotar resultados en la sección 6 del plan | Resultados reales registrados |

**Salida del sub-sprint:** `main` con el contrato, el esquema y los esqueletos. Los carriles A-D arrancan desde ahí.

### Sub-sprint 5.5.1 — Fase A: cuentas propias y crecimiento (carriles A, B, C, D en paralelo, ~1 semana)

| Carril | Tareas | Criterio de terminado |
|---|---|---|
| **A** | 1. `YouTubeProvider` con Data API v3: canal (suscriptores, vistas, videos), videos recientes, comentarios, `search_related` (canales destacados/relacionados). 2. Manejo de cuota (10.000 unidades/día por defecto): contador, `ProviderQuotaError`, caché de respuestas. 3. Fixtures JSON y tests de paginación, canal inexistente, cuota agotada. | Tests en verde sin red. Prueba manual con clave real documentada en el PR (resultado de un canal de ejemplo). |
| **B** | 1. Servicio `growth.py`: toma una instantánea con el proveedor adecuado y la guarda. 2. `scheduler.py` con `apscheduler`: instantáneas diarias por cuenta, reintentos con backoff, no duplicar si ya hay una del día. 3. Implementar rutas `/accounts*` y `/accounts/{id}/growth` (deltas, % y mejores publicaciones). 4. Tests con proveedor falso y reloj controlado. | 7 días simulados producen serie correcta; el cron no se ejecuta dos veces el mismo día; un fallo de un proveedor no detiene a los demás. |
| **C** | 1. `GrowthPanel.jsx` y `GrowthChart.jsx`: seguidores en el tiempo, delta 7/30 días, mejores publicaciones, comparación de hasta 4 cuentas. 2. `growthApi.js` contra el contrato (con datos simulados mientras B no esté). 3. Estados vacío, carga y error. 4. La integración en `TopBar`/`GraphExplorer` la hace el Integrador con una línea. | `npm run build` sin errores; test de componente con datos simulados; capturas de pantalla en el PR. |
| **D** | 1. `oauth.py`: flujo OAuth2 de Meta (`state` anti-CSRF, PKCE si aplica), guardado cifrado de tokens, renovación del token de larga duración. 2. `MetaProvider`: Instagram Graph API (cuentas profesionales propias: seguidores, publicaciones, insights de alcance e interacción) y Facebook Pages API (seguidores, publicaciones, insights). 3. Business Discovery de Instagram para cuentas profesionales públicas, con los campos que permita la API. 4. Fixtures y tests de token caducado, permisos insuficientes y límite de tasa. | Tests en verde sin red. Documentar en el PR qué permisos exige App Review de Meta. Sin credenciales, queda marcado como "no verificado contra la API real". |

**Puerta de salida del 5.5.1:** el Integrador fusiona A, B, C y D; se hace la prueba manual de extremo a extremo con YouTube real (ver DoD global).

### Sub-sprint 5.5.2 — Fase B: nichos y tendencias (carriles E, F, G en paralelo, ~1 semana)

| Carril | Tareas | Criterio de terminado |
|---|---|---|
| **E** | 1. `topics.py`: etiquetar cada comunidad Leiden con términos y hashtags dominantes (TF-IDF por comunidad, reutilizando `nlp.py` sin modificarlo). 2. Series temporales por tema/hashtag con DuckDB sobre los eventos y `PostSnapshot`. 3. Ranking de **aceleración** (pendiente de volumen reciente frente a la línea base, con suavizado para evitar falsos positivos por poco volumen). 4. Ruta `GET /trends`. | Dataset sintético con un tema que despega: aparece primero en el ranking. Un tema con volumen mínimo no aparece. Tiempo de consulta con 1M de eventos medido y anotado. |
| **F** | 1. `niches.py`: desde una cuenta semilla, expandir cuentas relacionadas vía `search_related`, menciones y colaboraciones hasta `depth` (máx. 2), con tope de cuentas y de cuota. 2. Agrupar el vecindario con Leiden y nombrar el nicho con los temas de E. 3. Calcular líderes y la posición de la semilla dentro del nicho. 4. Ruta `/niches/discover` como tarea asíncrona 202 con progreso SSE (mismo patrón que la ingesta). | Con proveedor falso, un grafo sintético de 3 nichos se separa correctamente. Respeta el presupuesto de cuota y se detiene con gracia. |
| **G** | 1. `NichePanel.jsx`: mapa del nicho, temas en ascenso, cuentas líderes, "dónde está mi cuenta". 2. `TrendChart.jsx`: series por tema con marca de aceleración. 3. `nicheApi.js` con progreso de la tarea. | `npm run build` sin errores; tests de componente; capturas en el PR. |

### Sub-sprint 5.5.3 — Integración, calidad y cierre (INT + todos, 2-3 días)

| # | Tarea | Resultado |
|---|---|---|
| 3.1 | Fusionar rama por rama, con un solo head de Alembic | `main` verde |
| 3.2 | Prueba manual de extremo a extremo con YouTube real: registrar un canal, acumular instantáneas, ver crecimiento, descubrir nicho | Capturas y registro en el plan |
| 3.3 | Revisión de seguridad: tokens cifrados, nada sensible en logs ni fixtures, `state` OAuth, validación de entradas | Informe corto |
| 3.4 | Actualizar `PLAN_DE_TRABAJO.md` (estado real, qué se verificó y qué no) y `docs/MANUAL_DE_USUARIO.md` | Documentos al día |
| 3.5 | Etiquetar `v0.6.0` solo si se cumple el DoD global | Tag |

## 4. Definición de terminado global del Sprint 5.5

- [ ] YouTube real: un canal con historial de instantáneas y gráfica de crecimiento visible en la interfaz.
- [ ] Instagram y Facebook: flujo OAuth y proveedor implementados y probados con fixtures. La verificación contra la API real queda **condicionada** a la aprobación de Meta; si no hay credenciales, se declara explícitamente como no verificado.
- [ ] Dado un canal semilla, el sistema produce un nicho con temas etiquetados y ranking de tendencias.
- [ ] `pytest backend/tests` sin regresiones, `npm run build` sin errores, un solo head de Alembic.
- [ ] Ningún secreto en el repositorio ni en logs.

## 5. Riesgos y dependencias

| Riesgo | Mitigación |
|---|---|
| La aprobación de Meta (App Review) tarda semanas | Solicitarla de inmediato; probar con cuentas de prueba y roles de desarrollador; el resto del sprint no depende de ella |
| Cuota de YouTube (10.000 unidades/día) | Caché, presupuesto de cuota por tarea, lotes de ids |
| Business Discovery solo da datos limitados | Documentarlo en el producto; no prometer análisis de terceros en Instagram |
| Conflictos de fusión en archivos compartidos | Propiedad de archivos por carril; routers propios; solo el Integrador toca `main.py` y `models.py` |
| Cuentas de terceros y datos personales | La Fase C no empieza sin decisión comercial y revisión legal |

## 6. Prerrequisitos del equipo (antes del 5.5.1)

1. Proyecto en Google Cloud con YouTube Data API v3 activada y una clave API (`YOUTUBE_API_KEY`).
2. App en Meta for Developers con Instagram Graph API y Facebook Login; solicitar App Review (`META_APP_ID`, `META_APP_SECRET`).
3. Generar `TRAMA_TOKEN_KEY` (clave Fernet) y guardarla solo en el entorno.
4. Al menos una cuenta propia de cada plataforma para las pruebas manuales.
