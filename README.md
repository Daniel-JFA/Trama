# TRAMA — Análisis de redes sociales

Software de mapeo de conversaciones para agencias de marketing, periodismo de investigación e influencers. Transforma un conjunto de interacciones en un grafo interactivo donde la influencia, las comunidades y las señales de amplificación artificial son visibles de un vistazo.

---

## Puesta en marcha

### Requisitos

- Python 3.11+
- Node.js 18+
- npm 9+

### Backend (FastAPI + NetworkX)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate           # Windows

pip install -r requirements.txt

# Exportar grafo de demo al frontend (solo primera vez o al actualizar synth.py)
python scripts/export_sample.py

# Iniciar servidor
uvicorn app.main:app --reload --port 8000
```

El backend queda disponible en `http://localhost:8000`. Documentación interactiva en `http://localhost:8000/docs`.

### Frontend (Next.js 14)

```bash
cd frontend
npm install
npm run dev
```

Abre `http://localhost:3000`.

> La interfaz funciona sin backend: si el servidor no responde en 2.5s, carga automáticamente `/public/sample-graph.json`.

---

## Endpoints de la API

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/health` | Estado del servidor |
| `GET` | `/api/graph` | Grafo activo completo |
| `GET` | `/api/overlap?ids=0,8,15` | Solapamiento Jaccard entre vecindades |
| `POST` | `/api/import` | Importar CSV `source,target` |
| `POST` | `/api/reset` | Restaurar dataset sintético |

### Formato del CSV para importar

```csv
source,target
@ElFaroDigital,@GuardianesDelRio
@AgroFuturoCol,@ElFaroDigital
...
```

Las columnas `source` y `target` son handles con o sin `@`. Se requieren mínimo 3 nodos.

---

## Dataset sintético

El grafo de demo simula el debate ficticio `#ReformaDelAgua` con 150 perfiles en 4 comunidades. **Ningún handle corresponde a cuentas reales.**

El caso plantado es el siguiente: la "Red amplificadora" (32 cuentas, ~72% conectadas a `@AgroFuturoCol`) muestra un pico de actividad coordinado en las semanas 6-7. Un periodista puede descubrir la operación explorando el grafo.

Semilla determinista: `random.Random(20260727)` — el grafo es siempre idéntico.

---

## Arquitectura del proyecto

```
trama/
├── backend/
│   ├── app/
│   │   ├── main.py       API FastAPI con CORS
│   │   ├── synth.py      Generador de datos sintéticos
│   │   └── metrics.py    PageRank, betweenness, bot heuristic
│   └── scripts/
│       └── export_sample.py
└── frontend/
    ├── app/              Next.js App Router
    ├── components/
    │   └── GraphExplorer.jsx   Componente principal (canvas 2D + d3-force)
    ├── lib/
    │   └── loadGraph.js  Carga con fallback local
    └── public/
        └── sample-graph.json
```

---

## Roadmap y Estado de Sprints

> Para ver el detalle técnico completo de historias de usuario, arquitectura, criterios de aceptación y tareas de ingeniería, consulta el documento maestro:  
> 📋 **[PLAN_DE_TRABAJO.md](PLAN_DE_TRABAJO.md)**

### Estado Actual (v0.2.0 — Completado)

- [x] Subida e importación de CSV directamente desde la interfaz
- [x] Persistencia de investigaciones y proyectos múltiples (SQLite)
- [x] Detección forense CIB (análisis temporal de ráfagas, entropía y topología)
- [x] Visualizador temporal evolutivo (Time-Travel de 12 semanas)
- [x] Módulo War Room político (Echo Chamber Index, aliados puente y rutas de expansión)
- [x] Exportador de grafo a Gephi (GEXF) y reporte analítico ejecutivo
- [x] Landing page comercial (`/landing`) con captura de leads

### Próximos Sprints de Desarrollo

* **Sprint 1 (Semanas 1-2):** Estabilidad, eliminación de estado global, aceleración 20x con `python-igraph`, indexación Quadtree en Canvas y sanitización de CSV.
* **Sprint 2 (Semanas 3-4):** Tareas asíncronas (Arq + Redis), streaming SSE de progreso y persistencia en PostgreSQL 16 con Alembic.
* **Sprint 3 (Semanas 5-6):** Inteligencia forense avanzada (NLP embeddings MiniLM, redes de co-difusión CooRnet y polarización RWC).
* **Sprint 4 (Semanas 7-8):** Física desacoplada en Web Worker, modo 100% offline con Graphology y generación de reportes PDF profesionales.
* **Sprint 5 (Semanas 9-10):** Ingesta multicanal en vivo (Bluesky Jetstream, Telegram, X API v2) y motor analítico columnar DuckDB + Parquet.
* **Sprint 6 (Semanas 11-12):** Motor WebGL masivo (Sigma.js v3 para >100.000 nodos), arquitectura SaaS multi-tenant con RBAC y suite E2E con Playwright.

---

## Notas técnicas

- El índice de autenticidad (`auth = 100 - bot`) en datos importados usa una **heurística placeholder** documentada en `backend/app/metrics.py`. No es un clasificador validado.
- Las métricas de PageRank y betweenness centrality se calculan con NetworkX sobre el grafo completo cada vez que se importa o resetea el dataset.
- La simulación de fuerza (d3-force) corre en el hilo principal del navegador sobre un canvas 2D. Para grafos mayores de 5 000 nodos se recomienda migrar a un worker.
