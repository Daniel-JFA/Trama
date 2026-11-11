# TRAMA — Manual de Usuario Oficial

**Versión del Sistema:** v0.3.0  
**Audiencia:** Analistas de Inteligencia, Jefes de Campaña (War Room), Periodistas de Investigación y Estrategas de Marca.

---

## 1. Introducción y Filosofía de TRAMA

**TRAMA** es una plataforma de análisis relacional de redes, detección forense de Comportamiento Inauténtico Coordinado (*Coordinated Inauthentic Behavior* - CIB / Astroturfing) y asesoramiento táctico para cuartos de guerra (*War Rooms*).

A diferencia de las herramientas de social listening tradicionales basadas en conteo plano de menciones y nubes de palabras, TRAMA analiza la **topología de la red**: quién habla con quién, qué comunidades concentran el debate, qué cuentas actúan como puentes estratégicos y qué nodos exhiben comportamientos coordinados y artificiales.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        FLUJO OPERATIVO DE TRAMA                        │
│                                                                        │
│  [CSV / Redes] ──► [Motor igraph C] ──► [Leiden + PageRank + CIB]      │
│                            │                         │                 │
│                            ▼                         ▼                 │
│                 [Persistencia SQLite/PG]  [Canvas 2D d3-force]         │
│                                                      │                 │
│         ┌──────────────────┬─────────────────┼──────────────────┐      │
│         ▼                  ▼                 ▼                  ▼      │
│   [Panel Resumen]   [Forense CIB]     [War Room Político]  [Informes]  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Acceso y Puesta en Marcha

### 2.1 Acceso Rápido Local
1. **Frontend:** Abre en tu navegador `http://localhost:3001` (o `http://localhost:3000` si está libre).
2. **Landing Page y Registro:** Accede a `http://localhost:3001/landing`.
3. **Backend API:** Documentación interactiva Swagger disponible en `http://localhost:8000/docs`.

### 2.2 Modo de Operación Autónomo
TRAMA cuenta con un mecanismo de respaldo automático (*fallback*): si el servidor backend no responde en 2.5 segundos, la interfaz carga el conjunto de datos de demostración precompilado (`sample-graph.json`), permitiendo demostraciones y capacitaciones sin conexión al servidor.

---

## 3. Navegación por la Interfaz

La pantalla principal de TRAMA está organizada en cuatro zonas:

```
┌────────────────────────────────────────────────────────────────────────┐
│ [Logo] [Buscador]  [Filtros]  [Proyectos] [Subir CSV] [Exportar] [Info] │ TopBar
├─────────────────────────────────────────────────┬──────────────────────┤
│                                                 │                      │
│                                                 │   PANEL LATERAL:     │
│                                                 │   - Resumen          │
│               CANVAS INTERACTIVO                │   - Expediente CIB   │
│                 (Grafo 2D Física)               │   - Comparativa      │
│                                                 │   - War Room         │
│                                                 │                      │
├─────────────────────────────────────────────────┴──────────────────────┤
│ [◄ Semana Anterior]  [Barra de Tiempo: Semanas 1 a 12]  [► Siguiente]   │ Time-Travel
└────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Atajos de Teclado Globales
Para agilizar el trabajo de analistas de campo, TRAMA incluye atajos rápidos:

| Tecla | Acción |
|---|---|
| `Espacio` + Arrastrar | Paneo libre del lienzo |
| `+` / `-` | Acercar / Alejar zoom |
| `F` | Ajustar vista completa (*Fit to View*) |
| `/` | Enfocar buscador de usuarios |
| `Esc` | Limpiar selección de nodo o búsqueda |
| `1` | Cambiar a pestaña **Resumen** |
| `2` | Cambiar a pestaña **Expediente CIB** |
| `3` | Cambiar a pestaña **Comparativa** |
| `4` | Cambiar a pestaña **War Room** |

---

## 4. Guía Visual del Grafo (Simbología)

El motor gráfico 2D utiliza codificación visual por capas para revelar información crítica al instante:

```
         ┌───────────────────┐
         │ ( (  O  ) )       │  Halo translúcido = Alto PageRank (Hub de influencia)
         └───────────────────┘
         ┌───────────────────┐
         │    ◎  O  ◎        │  Doble baliza turquesa = Alta Intermediación (Nodo Puente)
         └───────────────────┘
         ┌───────────────────┐
         │   ⚡  [O]  ⚡      │  Anillo magenta pulsante = Probabilidad CIB/Bot ≥ 60%
         └───────────────────┘
         ┌───────────────────┐
         │  ░░░░░░░░░░░░░    │  Nubes poligonales = Comunidades detectadas por Leiden
         └───────────────────┘
```

1. **Tamaño del Nodo:** Proporcional a la **influencia** (PageRank normalizado 0-100). A mayor diámetro, mayor capacidad de difusión.
2. **Color del Nodo:** Determinado por su **comunidad de afinidad** detectada mediante el algoritmo Leiden.
3. **Halo Translúcido Exterior:** Rodea a nodos con influencia $\ge 45$. Indica cuentas con alta tracción de audiencia.
4. **Baliza Turquesa (Radar):** Rodea a nodos con centralidad de intermediación (*Betweenness*) $\ge 40$. Son los **articuladores** o puentes entre distintas comunidades.
5. **Anillo Magenta Discontinuo y Pulsante:** Alerta de **comportamiento coordinado inauténtico / bot** (probabilidad $\ge 60\%$).
6. **Envolventes Comunitarias (Cascos Convexos):** Áreas sombreadas de fondo que agrupan a los miembros de cada facción ideológica o temática.

---

## 5. Gestión de Proyectos e Ingesta de Datos

### 5.1 Crear y Gestionar Proyectos
1. Haz clic en el botón **"Proyectos"** en la barra superior.
2. Aparecerá el modal de gestión donde puedes:
   - Crear una nueva investigación indicando Nombre, Tema/Hashtag y Descripción.
   - Seleccionar un proyecto guardado para cargarlo instantáneamente.
   - Eliminar proyectos antiguos (el proyecto demo base está protegido contra eliminación accidental).

### 5.2 Importación de Datasets (CSV)
TRAMA acepta archivos CSV delimitados por comas que representen interacciones dirigidas (`source,target`).

#### Formato Requerido
```csv
source,target
@CanalNoticias,@DefensoriaPueblo
@CandidatoA,@LiderRegional
@ActivistaAmbiental,@CanalNoticias
```

* Las columnas `source` y `target` admiten nombres con o sin `@`.
* El sistema requiere un mínimo de 3 nodos para generar el grafo.
* **Seguridad de Ingesta:** El motor sanitiza automáticamente fórmulas maliciosas de hojas de cálculo (`=`, `+`, `-`, `@`, `\t`, `\r`) para prevenir vulnerabilidades CWE-1236.
* **Progreso en Tiempo Real:** Al subir un archivo pesado, TRAMA activa un modal con barra de progreso en vivo vía Server-Sent Events (SSE), mostrando cada etapa:
  1. *Sanitización y lectura* (15%)
  2. *Construcción topológica* (40%)
  3. *Particionamiento Leiden* (65%)
  4. *Cálculo de métricas C* (80%)
  5. *Auditoría forense CIB* (90%)
  6. *Indexación final* (100%)

---

## 6. Paneles de Análisis Especializado

### 6.1 Panel 1: Resumen de Red
Ofrece la radiografía macroscópica de la conversación:
* **Métricas Principales:** Total de perfiles, volumen de interacciones, número de comunidades y densidad de conexión.
* **Distribución de Comunidades:** Porcentaje de ocupación de cada facción con leyenda de colores y nombre temático.
* **Top Influencers:** Listado de las 5 cuentas con mayor PageRank de la red.

### 6.2 Panel 2: Expediente Forense CIB
Diseñado para desenmascarar operaciones de guerra sucia, granjas de bots y campañas de astroturfing.
* **Auditoría Individual:** Al hacer clic en cualquier cuenta sospechosa, el panel muestra:
  - **Índice de Sospecha:** De 0 a 100%.
  - **Evidencias Explicables:** Tarjetas detalladas que justifican la calificación:
    - *Ráfagas temporales:* Picos anómalos de actividad en semanas específicas vs. el promedio histórico.
    - *Nomenclatura artificial:* Cuentas generadas por script con sufijos numéricos de 4+ dígitos.
    - *Desproporción actividad/audiencia:* Cuentas con miles de publicaciones y casi nulos seguidores.
    - *Topología en abanico (Fan-in):* Concentración masiva de menciones hacia un único hub central.
* **Lista de Cuentas Hostiles:** Acceso directo a todos los perfiles que superan el umbral del 60% de sospecha.

### 6.3 Panel 3: Comparativa de Nodos
Permite enfrentar analíticamente dos o tres perfiles seleccionados:
* Comparativa lado a lado de: Influencia (PageRank), Intermediación (Betweenness), Seguidores y Nivel de Sospecha.
* **Índice de Solapamiento Jaccard:** Cuantifica qué porcentaje de audiencia o vecindad comparten las cuentas seleccionadas.

### 6.4 Panel 4: War Room Político (Cuarto de Guerra)
El centro neurálgico para estrategas electorales y directores de comunicación en crisis.

1. **Selector de Candidato:** Escoge cualquier cuenta de la red para auditar su posicionamiento.
2. **Echo Chamber Index (ECI):**
   - Mide de 0% a 100% el encierro del candidato dentro de su propia burbuja.
   - Un ECI $> 70\%$ indica que el candidato solo le habla a sus propios convencidos.
3. **Buscador de Aliados Puente (*Strategic Brokers*):**
   - Identifica cuentas con alta intermediación que tienen un pie en tu comunidad y otro en comunidades rivales o indecisas.
   - Prioriza las mejores opciones de acercamiento político con mayor retorno.
4. **Rutas de Penetración (*Expansion Paths*):**
   - Determina el camino más corto y de mayor credibilidad para que el mensaje del candidato penetre en comunidades indecisas sin ser bloqueado.
5. **Escudo Anti-Guerra Sucia (*Dirty War Shield*):**
   - Detecta si existen clústeres de bots atacando coordinadamente al candidato o distorsionando la conversación en su contra.
6. **Recomendaciones Tácticas Automatizadas:**
   - Plan de acción semanal adaptado a los hallazgos de la red.

---

## 7. Herramientas Temporales (Time-Travel)

Ubicado en la parte inferior de la pantalla:
* **Slider Semanal (Semanas 1 a 12):** Desplaza el control deslizante para reconstruir la red en cada momento del tiempo.
* **Histograma de Volumen:** Muestra barras con la cantidad de publicaciones por semana.
* **Detección de Operaciones Coordinadas:** En el caso de demostración `#ReformaDelAgua`, deslizar a las **semanas 6 y 7** revela visualmente cómo la "Red amplificadora" despierta repentinamente con un pico artificial coordinado hacia `@AgroFuturoCol`.

---

## 8. Exportación y Entregables

TRAMA permite compartir hallazgos con clientes, directores de campaña o redacciones:

1. **Informe Ejecutivo Completo:**
   - Haz clic en **"Informe Ejecutivo"** en la barra superior.
   - Despliega un documento corporativo interactivo con:
     - Resumen general de la conversación y estado de polarización.
     - Auditoría del candidato seleccionado (ECI, comunidad y aliados clave).
     - Tabla de los 10 principales líderes de opinión.
     - Fichas forenses de cuentas CIB anómalas.
     - Recomendaciones estratégicas de campaña.
2. **Exportar a Gephi (GEXF):** Descarga el grafo completo con atributos normalizados (`comm`, `influence`, `bridge`, `bot`) para análisis profundo en Gephi.
3. **Exportar SVG Vectorial:** Descarga el grafo en formato `.svg` de alta resolución con nodos y aristas agrupados en capas, ideal para presentaciones, publicaciones impresas o diseño editorial.
4. **Captura PNG:** Exporta una imagen rápida en alta definición del lienzo actual.

---

## 9. Solución de Problemas Frecuentes

* **¿Por qué la interfaz dice "Datos: Muestra local (sin backend)"?**  
  Significa que el frontend no logró conectar con el servidor backend en `http://localhost:8000`. Asegúrate de que el backend esté corriendo con:
  ```bash
  cd backend && .venv/bin/uvicorn app.main:app --port 8000
  ```
* **Al subir un CSV obtengo error 422 o de formato:**  
  Asegúrate de que el archivo tenga encabezado `source,target`, esté separado por comas simples y tenga al menos 3 filas de interacciones.
* **No veo los anillos magenta de bots:**  
  Los anillos de alerta se muestran en perfiles con índice de sospecha $\ge 60\%$. Puedes activar el filtro rápido de cuentas sospechosas desde la barra de herramientas.
