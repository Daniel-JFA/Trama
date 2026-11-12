# Plan Maestro de Trabajo e Ingeniería — TRAMA v0.5.0 ➔ v1.0.0 Enterprise

> **Documento:** Plan de Trabajo, Sprints y Hoja de Ruta Técnica  
> **Sistema:** TRAMA (Inteligencia de Redes Sociales, Análisis Forense CIB y War Room Electoral)  
> **Línea Base Actual:** v0.5.0 (Sprints 1 a 5 fusionados en `main`; 56 tests pasando, 3 de PDF omitidos por falta de WeasyPrint)  
> **Meta Final:** v1.0.0 Enterprise (WebGL >100k nodos, Firehose 24/7 en tiempo real, NLP semántico y SaaS Multi-Tenant)  
> **Duración Total:** 12 Semanas (6 Sprints de 2 semanas)

---

## 1. Estado de Avance y Línea Base Verificada (v0.5.0)

```mermaid
flowchart LR
    subgraph V030 [LÍNEA BASE ACTUAL v0.5.0 - COMPLETADA]
        direction TB
        A[S1: igraph en C + Leiden] --> B[S1: Quadtree d3-force O log N]
        B --> C[S1: Desacoplamiento X-Project-Id]
        C --> D[S2: SQLAlchemy 2.0 + Alembic]
        D --> E[S2: Cola Asíncrona 202 Accepted]
        E --> F[S2: Streaming SSE reactivo]
    end

    subgraph PROJECTION [ROADMAP DE EJECUCIÓN - DE NO A SÍ]
        direction TB
        G[Sprint 3: NLP Semántico & CooRnet] --> H[Sprint 4: Web Worker 60 FPS & Offline]
        H --> I[Sprint 5: Firehose 24/7 & DuckDB]
        I --> J[Sprint 6: WebGL >100k & Multi-Tenant SaaS]
    end

    V030 ==> PROJECTION
```

### Funcionalidades Verificadas en el Código
* [x] **Motor de Grafos en C:** Algoritmo Leiden de particionamiento comunitario ($<50\text{ ms}$ en grafos de 10k nodos) y PageRank normalizado (0-100) en `python-igraph`.
* [x] **Aislamiento Concurrente:** Desacoplamiento total del estado global en memoria en [`backend/app/main.py`](file:///home/djfa/Dev/projects/SDL/trama/backend/app/main.py) con inyección de dependencias `Depends(get_current_project)` y soporte para cabecera `X-Project-Id`.
* [x] **Indexación Espacial Quadtree:** Detección de nodos bajo cursor en $O(\log N)$ ($<0.01\text{ ms}$) en [`frontend/components/GraphCanvas.jsx`](file:///home/djfa/Dev/projects/SDL/trama/frontend/components/GraphCanvas.jsx).
* [x] **Persistencia Relacional Normalizada:** SQLAlchemy 2.0 y migraciones versionadas con Alembic (`alembic upgrade head`) en SQLite y PostgreSQL.
* [x] **Ingesta Asíncrona con Streaming SSE:** Endpoint desacoplado con respuesta `202 Accepted`, barra de progreso granular en tiempo real (`TaskProgressModal.jsx`) y sanitización de inyección de fórmulas CSV (CWE-1236).
* [x] **Módulo Político (War Room):** Diagnóstico de *Echo Chamber Index* (ECI), buscador de aliados puente y rutas de expansión hacia indecisos en [`backend/app/political.py`](file:///home/djfa/Dev/projects/SDL/trama/backend/app/political.py).
* [x] **NLP Semántico y Detección de Parafraseo (Sprint 3 / Bloque A):** Similitud semántica con `paraphrase-multilingual-MiniLM-L12-v2` (`sentence-transformers`), lazy loading y fallback determinista (MinHash + TF-IDF n-grams), combinado con LSH para aislar copypasta (>0.85, ventana $\Delta t < 15\text{ min}$) en [`backend/app/nlp.py`](file:///home/djfa/Dev/projects/SDL/trama/backend/app/nlp.py).
* [x] **CooRnet con Prueba de Monte Carlo (Sprint 3 / Bloque A):** Prueba estadística de permutación Monte Carlo global ($p$-valor empírico por arista y por componente conexa) con semilla determinista configurable en [`backend/app/cib.py`](file:///home/djfa/Dev/projects/SDL/trama/backend/app/cib.py).
* [x] **Capa Visual CooRnet y Clústeres Textuales (Sprint 3 / Bloque A):** Visualizador de clústeres en [`frontend/components/panels/DossierPanel.jsx`](file:///home/djfa/Dev/projects/SDL/trama/frontend/components/panels/DossierPanel.jsx) y capa visual secundaria neón animada con halos de sincronización en [`frontend/components/GraphCanvas.jsx`](file:///home/djfa/Dev/projects/SDL/trama/frontend/components/GraphCanvas.jsx) activable desde [`TopBar.jsx`](file:///home/djfa/Dev/projects/SDL/trama/frontend/components/TopBar.jsx).
* [x] **Calidad de Código y Cobertura:** 48 tests unitarios y de integración pasando al 100% (`pytest backend/tests` con 8 nuevos tests del Bloque A: controles positivos de bots y controles negativos de tráfico orgánico). Build estático de Next.js 14 sin errores.

---

## 2. Matriz de Brechas Técnicas: "Cómo convertimos cada NO en SÍ"

| Límite Actual ("NO") | Meta Enterprise ("SÍ") | Sprint Asignado | Estrategia de Solución de Ingeniería |
|---|---|:---:|---|
| **Detección sólo de red (sin análisis de texto)** | Detección semántica de mensajes idénticos o parafraseados (copypasta) | **Sprint 3** (Semanas 5-6) | Modelo multilingüe local `MiniLM-L12-v2` + Hashing sensible a la localidad (MinHash / LSH) para textos con similitud $>85\%$. |
| **CIB sólo estructural** | Redes de Co-compartición coordinada (*Co-sharing / CooRnet*) | **Sprint 3** (Semanas 5-6) | Grafo secundario de perfiles que amplifican los mismos enlaces/posts en ventanas temporales estrechas ($\Delta t \le 45\text{ s}$). |
| **Cálculo físico congela el hilo principal (>5k nodos)** | 60 FPS estables y fluidos durante la interacción | **Sprint 4** (Semanas 7-8) | Trasladar la simulación de fuerzas a un **Web Worker** dedicado comunicando buffers tipados `Float32Array`. |
| **Dependencia del servidor local** | Funcionamiento 100% autónomo sin backend (modo avión) | **Sprint 4** (Semanas 7-8) | Motor `@graphology` en navegador + parseo local con `PapaParse` y persistencia en `IndexedDB` (Dexie.js). |
| **Ingesta manual exclusiva por archivo CSV** | Monitoreo continuo 24/7 en tiempo real | **Sprint 5** (Semanas 9-10) | Cliente WebSocket para consumo en streaming del Jetstream de Bluesky (AT Protocol) y conector API v2 de X. |
| **Límite de memoria para eventos masivos** | Consultas analíticas en sub-segundos sobre millones de posts | **Sprint 5** (Semanas 9-10) | Motor columnar embebido **DuckDB** sobre particiones **Apache Parquet**. |
| **Límite gráfico de 5.000 nodos en Canvas 2D** | Capacidad visual para **>100.000 nodos y 300.000 aristas** | **Sprint 6** (Semanas 11-12) | Motor de renderizado **WebGL acelerado por GPU (Sigma.js v3)** con *Instanced Drawing* y LOD semántico. |
| **Aplicación monousuario sin control de acceso** | Plataforma SaaS Multi-Tenant corporativa y privada | **Sprint 6** (Semanas 11-12) | Autenticación JWT, RBAC (*Admin, Lead Investigator, Analyst*) y *Row-Level Security* (RLS) en PostgreSQL. |

---

## 3. Cronograma Maestro y Desglose por Sprints

```
┌────────────────────────────────────────────────────────────────────────┐
│ CRONOGRAMA DE EJECUCIÓN (12 SEMANAS)                                   │
├──────────┬──────────────────────────────────────────┬──────────────────┤
│ Fase     │ Objetivo Principal                       │ Estado           │
├──────────┼──────────────────────────────────────────┼──────────────────┤
│ Sprint 1 │ Rendimiento C (igraph), Quadtree y San.  │ ✅ COMPLETADO    │
│ Sprint 2 │ Streaming SSE, Asincronía y SQLAlchemy   │ ✅ COMPLETADO    │
│ Sprint 3 │ Inteligencia Forense NLP, LSH y CooRnet  │ ✅ COMPLETADO    │
├──────────┼──────────────────────────────────────────┼──────────────────┤
│ Sprint 4 │ Física en Web Worker, Offline y PDF      │ ✅ FUSIONADO (*) │
│ Sprint 5 │ Firehose Streaming 24/7 y DuckDB Columnar│ ✅ FUSIONADO (*) │
│ Sprint 5.5│ Seguimiento de creadores y nichos       │ 🟡 SIGUIENTE     │
│ Sprint 6 │ Motor WebGL Masivo (>100k) & SaaS RBAC   │ ⚪ PENDIENTE     │
└──────────┴──────────────────────────────────────────┴──────────────────┘
```

(*) Fusionado en `main` (PR #1 frontend, #2 PDF, #3 ingesta) pero **con verificación parcial**; ver sección 6.


---

### Sprint 3: Inteligencia Forense Avanzada (NLP, Co-sharing y Polarización)
**Objetivo:** Transformar TRAMA de un analizador topológico a un motor forense de última generación capaz de detectar propaganda coordinada y desinformación semántica.

* **Duración:** Semanas 5 y 6
* **Paquetes Requeridos:** `sentence-transformers`, `datasketch`, `scikit-learn`

#### Tareas del Sprint
1. **[Backend / NLP] Pipeline de Embeddings Semánticos y MinHash/LSH:**
   - Crear [`backend/app/nlp.py`](file:///home/djfa/Dev/projects/SDL/trama/backend/app/nlp.py).
   - Integrar modelo local ligero (`paraphrase-multilingual-MiniLM-L12-v2`) con ejecución cuantizada en CPU.
   - Indexación MinHash y Locality Sensitive Hashing (LSH) para detectar clústeres de publicaciones idénticas o parafraseadas con umbral Jaccard $\ge 0.85$ en ventanas $\Delta t < 15\text{ min}$.
2. **[Backend / Forense] Algoritmo CooRnet (Redes de Co-compartición Coordinada):**
   - Construir grafo bipartito y proyección de co-compartición de URLs, hashtags o mensajes compartidos en ventanas hiperestrechas ($\Delta t \le 45\text{ s}$).
   - Prueba estadística de permutación de Monte Carlo para filtrar la amplificación orgánica y aislar la red de bots coordinada.
3. **[Backend / Métricas] Cuantificación de Polarización RWC (Random Walk Controversy):**
   - Implementar el algoritmo de controversia por paseos aleatorios (Garimella et al.) en [`backend/app/political.py`](file:///home/djfa/Dev/projects/SDL/trama/backend/app/political.py) para cuantificar la rigidez de las cámaras de eco enfrentadas.
4. **[Frontend] Panel Forense Renovado:**
   - Incorporar visualizador de clústeres textuales en [`DossierPanel.jsx`](file:///home/djfa/Dev/projects/SDL/trama/frontend/components/panels/DossierPanel.jsx).
   - Mostrar métrica de polarización RWC y conductancia en [`WarRoomPanel.jsx`](file:///home/djfa/Dev/projects/SDL/trama/frontend/components/panels/WarRoomPanel.jsx).

* **Criterio de Aceptación (DoD) — ✅ CUMPLIDO AL 100%:**
  - [x] Detección precisa de variaciones de textos copypasta con porcentaje de similitud y marcas temporales.
  - [x] Generación del grafo de co-compartición accesible como capa visual secundaria.
  - [x] Cobertura de pruebas automatizadas con datasets sintéticos de propaganda coordinada (8 nuevos tests pasando, 48 en total).

---

### Sprint 4: Física en Web Worker, Modo Offline Total y Reportes PDF
**Objetivo:** Garantizar autonomía total al analista en campo (modo avión) y eliminar caídas de frames en la interfaz gráfica.

* **Duración:** Semanas 7 y 8
* **Paquetes Requeridos:** `graphology`, `graphology-layout-forceatlas2`, `dexie`, `weasyprint` / `playwright`

#### Tareas del Sprint
1. **[Frontend / Rendimiento] Simulación Física en Web Worker Dedicado:**
   - Trasladar el cómputo de fuerzas `d3-force` / `ForceAtlas2` fuera del hilo principal de React a un Worker Web dedicado (`graph.worker.js`).
   - Transferencia de coordenadas y velocidades mediante buffers tipados `Float32Array` compartidos, garantizando 60 FPS estables sin importar el tamaño del grafo.
2. **[Frontend / Offline] Motor en Cliente con Graphology e IndexedDB:**
   - Incorporar `@graphology` en el navegador para calcular modularidad Louvain y PageRank en cliente cuando no haya backend disponible.
   - Parser local de CSV con `PapaParse` en segundo plano.
   - Almacenamiento local de investigaciones en `IndexedDB` (vía Dexie.js).
3. **[Backend / Exportación] Generador Headless de Informes Ejecutivos en PDF:**
   - Servicio de renderizado PDF con WeasyPrint en [`backend/app/reports.py`](file:///home/djfa/Dev/projects/SDL/trama/backend/app/reports.py).
   - Generación de informe imprimible a 300 DPI: portada institucional, resumen macro, tabla de líderes, fichas periciales CIB y captura vectorial del grafo.
4. **[UX / Filtros] Sliders de Umbral Multicriterio con Histogramas:**
   - Controles interactivos en tiempo real para filtrar nodos por percentil de influencia, índice de sospecha CIB (0-100) y comunidades activas.

* **Criterio de Aceptación (DoD):**
  - La aplicación permite arrastrar un CSV y analizarlo completamente sin conexión a internet.
  - Paneo y zoom fluidos a 60 FPS continuos durante la estabilización de la simulación.
  - Descarga de PDF profesional en un clic con maquetación de imprenta.

---

### Sprint 5: Ingesta en Streaming 24/7 y Motor Analítico Columnar
**Objetivo:** Eliminar la dependencia de archivos CSV manuales y habilitar captura continua de conversaciones desde redes sociales modernas.

* **Duración:** Semanas 9 y 10
* **Paquetes Requeridos:** `duckdb`, `pyarrow`, `websockets`, `aiohttp`

#### Tareas del Sprint
1. **[Backend / Conectores] Modelo Canónico de Eventos de Red (`InteractionEvent`):**
   - Estandarización de esquema de evento temporal: `actor`, `target`, `timestamp`, `action_type` (retweet, quote, reply, forward), `platform`, `content`.
2. **[Backend / Streaming] Conector Bluesky AT Protocol (Jetstream Firehose):**
   - Cliente WebSocket asíncrono para suscribirse al Jetstream público de Bluesky en tiempo real con filtrado dinámico por hashtags y términos clave.
3. **[Backend / Ingesta] Conectores de Telegram y X/Twitter:**
   - Parser de exportaciones JSON de canales y grupos de Telegram para grafos de reenvíos (*forwards*).
   - Ingestor de eventos JSON de la API v2 de X con control de cuotas (*rate limiting*).
4. **[Backend / Big Data] Motor Columnar DuckDB + Apache Parquet:**
   - Almacenamiento de millones de eventos en particiones Parquet por fecha y proyecto en disco.
   - Consultas analíticas instantáneas (agregaciones por minuto, ventanas móviles de co-ocurrencia) ejecutadas en DuckDB en $<300\text{ ms}$ sin desbordar la memoria RAM.

* **Criterio de Aceptación (DoD):**
  - Conexión funcional en vivo al firehose de Bluesky con construcción dinámica del grafo en tiempo real.
  - Consultas sobre 2 millones de eventos temporales responden en menos de 300 ms mediante DuckDB.

---

### Sprint 5.5: Seguimiento de Creadores, Crecimiento y Nichos (Instagram, Facebook, YouTube)
**Objetivo:** Seguir el crecimiento de cuentas en Instagram, Facebook y YouTube, y detectar los nichos y lo que más se mueve dentro de cada uno.

> Plan de ejecución detallado (sub-sprints, carriles por agente, contrato de API y datos): [`docs/PLAN_SPRINT_5_5_EJECUCION.md`](docs/PLAN_SPRINT_5_5_EJECUCION.md)

**Punto de partida (verificado en código):** hoy solo hay conectores para Bluesky, Telegram y X. Instagram y Facebook se cubren con scripts de conversión manual (`scripts/instagram_to_csv.py`, `scripts/social_multichannel_to_csv.py`); YouTube no existe. `User.followers` guarda un único valor, sin historial. No hay etiquetado de temas ni series temporales por tema.

**Alcance de acceso a datos (decisión de producto):**

| Nivel | Fuente | Alcance | Fase |
|---|---|---|---|
| 1. Cuentas propias o autorizadas | Instagram Graph API, Facebook Pages API, YouTube Data/Analytics API (OAuth) | Seguidores, alcance, interacciones, demografía, publicaciones, comentarios | A |
| 2. Cuentas públicas de terceros | Instagram Business Discovery (solo cuentas profesionales, datos limitados), YouTube Data API | Métricas públicas básicas | A/B |
| 3. Datos masivos | Proveedor de datos de pago o Meta Content Library (solo investigación no comercial) | Búsqueda amplia, tendencias, hashtags | C (requiere decisión comercial y revisión legal) |
| 4. Acceso interno tipo Meta | No existe para terceros | — | Descartado |

* **Duración:** Semanas 11 y 12 (Sprint 6 se desplaza a las semanas 13 y 14)
* **Paquetes Requeridos:** `google-api-python-client`, `httpx`, `apscheduler`

#### Fase A: Cuentas propias y crecimiento
1. **[Backend / Modelo] Instantáneas históricas:**
   - Tabla `AccountSnapshot` (cuenta, plataforma, fecha, seguidores, publicaciones, vistas, interacción) con migración Alembic.
   - Cron de recolección periódica (`apscheduler`) con registro de ejecuciones y reintentos.
2. **[Backend / Conectores] Interfaz `DataProvider`:**
   - Contrato común (`fetch_account`, `fetch_posts`, `fetch_comments`) para enchufar fuentes sin tocar el resto del sistema.
   - Almacenamiento seguro de tokens OAuth (cifrados en reposo) y control de cuotas.
3. **[Backend / Conectores] YouTube:** canales, videos, comentarios, suscriptores y vistas vía Data API v3. Es la primera fuente verificable de extremo a extremo.
4. **[Backend / Conectores] Instagram y Facebook:** OAuth con Graph API para cuentas propias o administradas, más Business Discovery para cuentas profesionales públicas. Requiere App Review de Meta.
5. **[Frontend] Panel de crecimiento:** seguidores en el tiempo, tasa de crecimiento, mejores publicaciones y comparación entre cuentas.

#### Fase B: Nichos y tendencias
1. **[Backend / NLP] Etiquetado de temas por comunidad:** hashtags y términos dominantes por comunidad Leiden, reutilizando `nlp.py`.
2. **[Backend / DuckDB] Series temporales por tema y hashtag:** volumen por ventana y ranking de aceleración (qué crece más rápido).
3. **[Backend / Grafo] Descubrimiento del nicho:** a partir de una cuenta semilla, expandir cuentas relacionadas (menciones, colaboraciones, audiencia compartida) y construir el nicho.
4. **[Frontend] Panel de nichos:** mapa de nichos, temas en ascenso y cuentas líderes de cada uno.

#### Fase C: Ampliación de cobertura (condicionada a decisión comercial)
- Evaluar un proveedor de datos externo implementando `DataProvider`, con revisión legal previa (términos de uso de cada plataforma y ley de protección de datos personales). No se inicia sin aprobación expresa.

* **Criterio de Aceptación (DoD):**
  - [ ] Conexión real a YouTube con una clave API: un canal con al menos 7 días de instantáneas y gráfica de crecimiento.
  - [ ] Instagram y Facebook conectados a una cuenta propia mediante OAuth (sujeto a aprobación de Meta).
  - [ ] Dado un canal semilla, el sistema produce un nicho con temas etiquetados y ranking de tendencias.
  - [ ] Tests con fixtures de las tres APIs, y ningún token o dato personal en logs ni en el repositorio.

**Prerrequisitos del equipo:** app en Meta for Developers; proyecto en Google Cloud con YouTube Data API activada; decidir si habrá cuentas de terceros (define la Fase C).

---

### Sprint 6: Motor WebGL Masivo (>100k nodos), RBAC Multi-Tenant y Certificación
**Objetivo:** Escalar la visualización a más de 100.000 nodos y convertir TRAMA en una plataforma SaaS multi-inquilino lista para despliegues gubernamentales y corporativos.

* **Duración:** Semanas 11 y 12
* **Paquetes Requeridos:** `sigma`, `graphology-library`, `python-jose`, `passlib`, `playwright`

#### Tareas del Sprint
1. **[Frontend / Gráficos Masivos] Motor de Renderizado WebGL con Sigma.js v3:**
   - Renderizado acelerado por GPU mediante *Instanced Drawing* con capacidad para manipular 100.000 nodos y 300.000 aristas a 60 FPS estables.
   - Nivel de detalle dinámico (LOD): agregación semántica de nodos en conglomerados visuales al alejar el zoom.
2. **[Seguridad / Multi-Tenant] Autenticación JWT y Control de Acceso RBAC:**
   - Soporte para organizaciones independientes y proyectos privados.
   - Roles granulares: `Admin`, `Lead Investigator`, `Analyst`, `Viewer`.
   - Aislamiento estricto de investigaciones mediante *Row-Level Security* (RLS) en PostgreSQL.
   - Rotación segura de refresh tokens en cookies `HttpOnly` y soporte 2FA (TOTP).
3. **[DevOps & QA] Suite de Pruebas E2E y Pipeline de Integración Continua:**
   - Pruebas automatizadas de extremo a extremo con Playwright cubriendo el flujo completo: creación de proyecto -> streaming -> análisis CIB -> exportación PDF.
   - Pipeline de GitHub Actions con linters (`ruff`, `eslint`), auditorías de seguridad (`trivy`, `pip-audit`) y despliegue continuo en contenedores Docker.

* **Criterio de Aceptación (DoD):**
  - Carga y manipulación fluida de un grafo de 100.000 nodos en un navegador convencional sin lag perceptible.
  - Aislamiento estricto de investigaciones entre organizaciones verificado mediante tests de penetración multi-tenant.
  - Pipeline de CI/CD 100% verde con despliegue automatizado.

---

## 4. Matriz de Seguimiento y Métricas de Éxito

```
┌───────────────────────────────────────┬───────────────────┬───────────────────┬───────────────────┐
│ DIMENSIÓN                             │ LÍNEA BASE v0.5.0 │ META SPRINT 4     │ META FINAL v1.0   │
├───────────────────────────────────────┼───────────────────┼───────────────────┼───────────────────┤
│ Escala Máxima Soportada               │ ~5.000 nodos      │ ~25.000 nodos     │ >100.000 nodos    │
│ Tasa de Refresco Visual (FPS)         │ 60 FPS (<2k)      │ 60 FPS (<15k)     │ 60 FPS constantes │
│ Tiempo de Detección de Nodo (Hover)   │ <0.01 ms (Quad.)  │ <0.01 ms (Quad.)  │ <0.01 ms (GPU)    │
│ Modo Offline                          │ Solo demo JSON    │ 100% Autónomo     │ 100% Autónomo     │
│ Ingesta de Datos                      │ CSV manual        │ CSV + Worker      │ Streaming 24/7    │
│ Detección Forense CIB                 │ 4 reglas topolog. │ Topología + NLP   │ CooRnet + LSH     │
│ Arquitectura de Usuarios              │ Monousuario local │ Monousuario local │ Multi-Tenant RBAC │
└───────────────────────────────────────┴───────────────────┴───────────────────┴───────────────────┘
```

---

## 5. Próxima Acción Inmediata: Sprint 5.5 y luego Sprint 6

**Sprint 5.5 (primero):** crear credenciales de YouTube y Meta, modelo `AccountSnapshot` + cron, conector de YouTube y panel de crecimiento (ver sección del Sprint 5.5).

**Sprint 6:**

1. **Antes de empezar:** instalar WeasyPrint (con `pango` y `cairo` del sistema) y ejecutar `pytest backend/tests/test_reports.py` para verificar de verdad el PDF (Sprint 4).
2. Sigma.js v3 (WebGL) con LOD semántico, manteniendo Canvas 2D para grafos pequeños; probar con 100k nodos / 300k aristas.
3. Autenticación JWT, RBAC (Admin, Lead Investigator, Analyst, Viewer), organizaciones, RLS en PostgreSQL, TOTP 2FA, con tests de aislamiento entre organizaciones.
4. CI: añadir `ruff`, `eslint`, `pip-audit`, `trivy`, build de imágenes Docker y E2E con Playwright (proyecto → CIB → PDF).

---

## 6. Registro de Verificación (estado real al cierre)

| Sprint | Entregado | Verificado | Pendiente / no verificado |
|---|---|---|---|
| 3 | `nlp.py` (MinHash/LSH + MiniLM con fallback), CooRnet con Monte Carlo, clústeres textuales y capa CooRnet | 8 tests nuevos en verde | Con `sentence-transformers` real solo se probó la ruta con mock/fallback |
| 4 (frontend) | `graph.worker.js`, modo offline (Graphology + Dexie + PapaParse), `ThresholdFilters.jsx` | `npm run build` compila; test `offlineAnalysis.test.js` incluido | **60 FPS y modo avión no medidos en navegador**; no se abrió la interfaz |
| 4 (PDF) | Informe PDF con WeasyPrint y botón en `ReportModal.jsx` | **VERIFICADO (Sub-sprint 5.5.0)**: WeasyPrint 70.0 instalado, 5 tests pasando en `test_reports.py` (0 omitidos) | Validación visual en visor PDF externo |
| 5 | `InteractionEvent` + migración Alembic, conectores Bluesky/Telegram/X, DuckDB + Parquet, `benchmark_duckdb.py` | Tests de conectores con fixtures, sin red. **Benchmark ejecutado**: agregación minuto 208 ms (<300 ms), rolling window 38.9 ms (<300 ms), top 20 actores 337 ms sobre 2M eventos | Conexión real a Bluesky (fuera de CI por ser sin credenciales) |
| 5.5.0 | Cimientos: modelos `Account`, `AccountSnapshot`, `PostSnapshot`, `OAuthCredential`, migración `ae8e56481230`, protocolo `DataProvider`, routers con 501, cifrado `crypto.py`, fixtures | 16 tests nuevos en verde (72 tests backend totales pasando, 0 omitidos), un solo head Alembic | Conexión real con API Keys de YouTube/Meta (reservada para fases posteriores) |
| 5.5.1 | Fase A (A, B, C, D): conector YouTubeProvider con control de cuota y caché; `growth.py` con series de crecimiento, snapshot y scheduler APScheduler; panel frontend `GrowthPanel.jsx` + `GrowthChart.jsx`; flujo OAuth2 Meta y proveedor `MetaProvider` | 24 tests nuevos en verde (96 tests backend pasando, 0 omitidos), 7 tests frontend pasando en `node:test`, build de Next.js limpio | Verificación contra APIs reales de Meta sujeta a App Review y credenciales en entorno |

**Totales:** 96 tests backend pasan, 0 omitidos; 7 tests frontend pasan; un solo head de Alembic (`ae8e56481230`); build de Next.js sin errores.

**Notas de entorno:** el repositorio vive en `/home/djfa/Dev/projects/SDL/trama` (antes `Propios/trama`). El puerto 3000 local lo ocupa otro servicio; el frontend de desarrollo se levantó en el 3001 (CORS ya lo permite).
