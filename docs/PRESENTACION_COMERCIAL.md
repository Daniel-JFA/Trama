# TRAMA — Presentación Comercial y Hoja de Ruta Tecnológica

> **Documento:** Presentación Comercial Ejecutiva & Plan Estratégico de Ingeniería (10 Diapositivas)  
> **Producto:** TRAMA — Inteligencia de Redes Sociales, Análisis CIB y War Room Electoral  
> **Versión:** v0.3.0 -> v1.0 Enterprise  
> **Enfoque:** 100% Honesto y Riguroso. Presenta las capacidades operativas activas hoy y la hoja de ruta de ingeniería para alcanzar la escala masiva (>100k nodos WebGL, Firehose 24/7 y NLP semántico).

---

## Estructura de la Presentación

```
┌────────────────────────────────────────────────────────────────────────┐
│                        MAPA DE LA PRESENTACIÓN                         │
├─────────┬──────────────────────────────────────────────────────────────┤
│ Slide 1 │ Portada & Propuesta de Valor Estructural                     │
│ Slide 2 │ El Diagnóstico: La Ceguera del Monitoreo Tradicional         │
│ Slide 3 │ Capacidades Operativas Hoy: Motor TRAMA v0.3.0               │
│ Slide 4 │ Caso de Estudio y Validación: Benchmark #ReformaDelAgua      │
│ Slide 5 │ El Cuarto de Guerra: ECI, Aliados Puente y Rutas Tácticas    │
│ Slide 6 │ Hoja de Ruta Tecnológica: Fases hacia la Escala Total        │
│ Slide 7 │ Arquitectura de Ingeniería detrás de los Retos Pendientes    │
│ Slide 8 │ Modelo Comercial Realista: Auditoría, Acompañamiento & SaaS │
│ Slide 9 │ Programa Early Adopters: Construyamos el Caso Juntos (PoC)   │
│ Slide 10│ Cierre: Demo en Vivo y Acceso Inmediato a la Plataforma      │
└─────────┴──────────────────────────────────────────────────────────────┘
```

---

### Diapositiva 1: Portada y Propuesta de Valor
* **Título:** TRAMA — La Verdad Estructural de la Conversación Digital
* **Subtítulo:** Auditoría topológica de influencia, detección matemática de astroturfing y hoja de ruta tecnológica hacia la monitorización masiva en tiempo real.
* **Badges:**
  - `Motor Operativo Hoy (v0.3.0)`: Leiden en C, PageRank, ECI y forense CIB de 4 reglas.
  - `Auditoría por Dataset`: Ingesta CSV con sanitización y streaming SSE.
  - `Proyección Tecnológica`: Roadmap estructurado hacia WebGL masivo (>100k) y Firehose.
  - `Cero Promesas Falsas`: Capacidades demostradas y validadas matemáticamente.

---

### Diapositiva 2: El Diagnóstico en la Industria
* **Título:** El Problema: Cuando las Métricas Tradicionales Engañan
* **Dolor 1 - Métricas de Vanidad Infladas:** El social listening tradicional solo cuenta menciones. Una red de 20 bots puede emitir 10.000 tuits y fingir un consenso que confunde a los analistas.
* **Dolor 2 - Aislamiento en Cámara de Eco:** La mayoría de los candidatos cree que va ganando porque su equipo monitorea comentarios favorables dentro de su propia burbuja, ignorando que los indecisos están en otra comunidad.
* **Dolor 3 - Carencia de Análisis Relacional:** El monitoreo plano no responde quién articula el mensaje, quiénes son los aliados puente para dialogar con los rivales, ni por qué rutas de penetración llevar la propuesta.

---

### Diapositiva 3: Qué Tenemos Operativo Hoy (v0.3.0)
* **Título:** Capacidades Operativas Activas en el Código
* **Banner:** Software funcional, probado con 31 tests automatizados (100% pasando) y disponible en local en este momento.
* **Pilares Activos:**
  1. *Cartografía Leiden en C:* Particionamiento acelerado (<50ms). Encuentra facciones reales sin sesgo humano en `python-igraph`.
  2. *Influencia y Puentes:* PageRank normalizado (0-100) para influencia real y Betweenness centrality para identificar *Gatekeepers* frontera.
  3. *Cuarto de Guerra (ECI):* Echo Chamber Index calcula el % de encierro del candidato. Genera rutas hacia indecisos y aliados estratégicos.
  4. *Forense CIB de 4 Factores:* Heurística explicable: picos temporales anómalos, nomenclatura por script, ratio posts/seguidores y topología en abanico.

---

### Diapositiva 4: Caso de Estudio y Validación (#ReformaDelAgua)
* **Título:** Benchmark de Referencia y Verificación Matemática
* **El Caso Controlado:** Diseñado para demostrar la capacidad del software de desarticular operaciones encubiertas (150 perfiles, 4 comunidades, 12 semanas):
  - Semanas 1 a 5: Actividad aparentemente orgánica de baja intensidad.
  - Semanas 6 y 7: Activación sincrónica de una "Red Amplificadora" de 32 cuentas que dispara picos masivos hacia un hub central (`@AgroFuturoCol`).
  - Detección inmediata en TRAMA: Identificación con anillo magenta pulsante y exposición visual del pico en la barra de Time-Travel.

---

### Diapositiva 5: El Cuarto de Guerra (War Room Político)
* **Título:** De la Observación a la Acción Táctica
* **Echo Chamber Index (ECI):** Cuantifica qué tan encerrado está el candidato en su propia comunidad. Un ECI $> 70\%$ dispara alerta roja: la campaña está saturando a sus propios convencidos mientras los indecisos son cooptados por rivales.
* **Strategic Broker Finder:** Localiza automáticamente los 5 articuladores con credibilidad en la frontera entre comunidades para tender puentes.
* **Expansion Paths:** Algoritmo de rutas óptimas para penetrar nichos neutrales sin ser rechazado.
* **Dirty War Shield:** Detección temprana de ataques coordinados dirigidos a desprestigiar al candidato.

---

### Diapositiva 6: Hoja de Ruta Tecnológica (Roadmap hacia la Escala Total)
* **Título:** Cómo Alcanzaremos la Escala Total
* **Fase 1: Hoy (v0.3.0) — [Completada]:**
  - Motor Leiden en C (`python-igraph`), PageRank, Betweenness, Echo Chamber Index (ECI), Forense CIB 4 reglas, SQLite + Alembic relacional.
* **Fase 2: Próxima (Sprints 3-4) — [En Desarrollo]:**
  - NLP semántico (MinHash/LSH), redes CooRnet de co-compartición estrecha ($\Delta t \le 45\text{ s}$), simulación en Web Worker (60 FPS estables), modo 100% offline (Graphology) y reportes corporativos en PDF.
* **Fase 3: Meta (Sprints 5-6) — [Escala Enterprise]:**
  - Streaming Firehose 24/7 (Bluesky Jetstream y X API v2), motor columnar DuckDB en memoria para millones de eventos, motor gráfico WebGL (>100.000 nodos), SaaS multi-tenant con RBAC y Row-Level Security en PostgreSQL.

---

### Diapositiva 7: Arquitectura de Ingeniería detrás de los Retos Pendientes
* **Título:** Diseño de Solución para los Retos Técnicos
* **Reto 1: Escala >100k Nodos:** Migración a motor gráfico WebGL con Sigma.js v3 y renderizado acelerado por GPU (*Instanced Drawing*). Simulación física en Web Worker independiente mediante `Float32Array`.
* **Reto 2: Ingesta en Vivo 24/7:** Cliente WebSocket para consumo directo del Jetstream de Bluesky (AT Protocol) e ingestor de la API v2 de X, procesando eventos hacia almacenamiento columnar DuckDB + Apache Parquet.
* **Reto 3: Detección de Textos (NLP):** Integración de modelo multilingüe ligero (MiniLM) con hashing LSH/MinHash para detectar campañas de mensajes coordinados idénticos o parafraseados con similitud $>85\%$.
* **Reto 4: Seguridad Multi-Tenant:** Autenticación JWT y control de acceso basado en roles (RBAC: Admin, Lead Investigator, Analyst) con políticas de aislamiento estricto (RLS) en PostgreSQL.

---

### Diapositiva 8: Modelo Comercial Realista
* **Título:** Oferta Comercial Factible Hoy
* **01. Auditoría Forense Express ($800 - $1.500 USD por investigación):**
  - Entrega de dataset o tema clave. Radiografía completa de comunidades, ECI del vocero y reporte pericial de cuentas sospechosas en 48 horas.
* **02. Cuarto de Guerra por Campaña ($3.500 - $8.000 USD al mes):**
  - Acompañamiento táctico semanal, actualización periódica del grafo, alertas de guerra sucia, rutas hacia votantes indecisos y sesión con el estratega.
* **03. Licenciamiento Enterprise (Suscripción Anual para Agencias y Gobiernos):**
  - Instalación On-Premise privada, acceso a todo el roadmap (v1.0), capacitación a analistas y soporte empresarial.

---

### Diapositiva 9: Programa Early Adopters (Construyamos el Caso Juntos)
* **Título:** Propuesta de Piloto y Alianza Estratégica
* **1. Prueba de Concepto (PoC) Gratuita:** Analizamos una conversación o hashtag crítico de tu interés con hasta 5.000 nodos y te entregamos el reporte completo sin costo inicial.
* **2. Co-diseño de Inteligencia:** Tu equipo de estrategia retroalimenta los hallazgos y prioriza las funciones que más valor le aporten a la contienda.
* **3. Conversión a Éxito Comprobado:** Al validar que TRAMA reveló datos que el social listening tradicional no vio, cerramos el acompañamiento para toda la campaña.

---

### Diapositiva 10: Cierre y Demo en Vivo
* **Título:** Acceso Inmediato a la Plataforma
* **Demo Activa:** `http://localhost:3001`
* **Landing & Captura de Leads:** `http://localhost:3001/landing`
* **API Swagger Docs:** `http://localhost:8000/docs`
* **Contacto:** `contacto@trama-intelligence.io`
