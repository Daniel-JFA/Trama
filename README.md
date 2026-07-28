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

## Roadmap

### Fase 2

- [ ] Subida de CSV directamente desde la interfaz (drag & drop)
- [ ] Proyectos persistentes: guardar múltiples investigaciones (evaluar Neo4j para el almacenamiento del grafo)
- [ ] Score de autenticidad con señales temporales reales (varianza horaria, ratio retweet/original, velocidad de crecimiento)
- [ ] Ingesta de X API v2 (Academic/Pro access): búsqueda por hashtag o conversación
- [ ] Comparación temporal del grafo: ver cómo evolucionó la red entre dos periodos

### Fase 3

- [ ] Embed interactivo para artículos de prensa (iframe con grafo público de solo lectura)
- [ ] Reporte PDF para agencias: resumen ejecutivo, comunidades, top influyentes, señales de bot
- [ ] Rastreo de narrativas entre comunidades: análisis de qué mensajes cruzan las cuentas puente
- [ ] Dashboard de monitoreo continuo (cola de trabajos, alertas por umbral de bot o pico de actividad)

---

## Notas técnicas

- El índice de autenticidad (`auth = 100 - bot`) en datos importados usa una **heurística placeholder** documentada en `backend/app/metrics.py`. No es un clasificador validado.
- Las métricas de PageRank y betweenness centrality se calculan con NetworkX sobre el grafo completo cada vez que se importa o resetea el dataset.
- La simulación de fuerza (d3-force) corre en el hilo principal del navegador sobre un canvas 2D. Para grafos mayores de 5 000 nodos se recomienda migrar a un worker.
