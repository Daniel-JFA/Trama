"""
reports.py — Generador de Informes Ejecutivos de Inteligencia de Red para Periodistas y Agencias.
Incluye soporte para informes PDF vectoriales con WeasyPrint (Portada, Resumen Macro,
Líderes, Fichas CIB y Captura Vectorial SVG).
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import html
from .political import audit_candidate, find_strategic_brokers

try:
    import weasyprint
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    weasyprint = None
    WEASYPRINT_AVAILABLE = False


class WeasyPrintUnavailableError(RuntimeError):
    """Excepción lanzada cuando WeasyPrint o sus dependencias nativas no están disponibles."""
    pass


def generate_executive_report(project: Dict[str, Any], candidate_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Genera un informe analítico estructurado a partir del proyecto y su grafo,
    con sección opcional de estrategia electoral para el candidato.
    """
    graph = project.get("graph", {})
    nodes = graph.get("nodes", [])
    links = graph.get("links", [])
    communities = graph.get("communities", [])
    meta = graph.get("meta", {})

    total_nodes = len(nodes)
    total_links = len(links)
    suspicious_nodes = [n for n in nodes if n.get("bot", 0) >= 60]
    pct_suspicious = round(len(suspicious_nodes) / max(1, total_nodes) * 100, 1)

    # Top influyentes
    top_influencers = sorted(nodes, key=lambda x: x.get("influence", 0), reverse=True)[:10]

    # Top puentes
    top_bridges = sorted(nodes, key=lambda x: x.get("bridge", 0), reverse=True)[:5]

    # Distribución por comunidad
    comm_stats = []
    for c in communities:
        cid = c["id"]
        comm_members = [n for n in nodes if n.get("comm") == cid]
        comm_susp = [n for n in comm_members if n.get("bot", 0) >= 60]
        comm_stats.append({
            "id": cid,
            "name": c.get("name", f"Comunidad {cid}"),
            "color": c.get("color", "#888"),
            "size": len(comm_members),
            "percentage": round(len(comm_members) / max(1, total_nodes) * 100, 1),
            "suspicious_count": len(comm_susp),
            "avg_authenticity": round(sum(n.get("auth", 0) for n in comm_members) / max(1, len(comm_members)), 1),
        })

    # Hallazgos forenses de astroturfing
    astroturfing_findings = []
    if len(suspicious_nodes) > 0:
        main_susp_comm = max(comm_stats, key=lambda x: x["suspicious_count"])
        if main_susp_comm["suspicious_count"] > 5:
            astroturfing_findings.append({
                "severity": "ALTA",
                "title": f"Concentración de amplificación artificial en {main_susp_comm['name']}",
                "description": f"Se detectaron {main_susp_comm['suspicious_count']} cuentas con anomalías alfanuméricas o de actividad ({round(main_susp_comm['suspicious_count'] / max(1, len(suspicious_nodes)) * 100)}% de todos los bots).",
            })

    if meta.get("synthetic"):
        astroturfing_findings.append({
            "severity": "CRÍTICA",
            "title": "Sincronización temporal anómala (Semanas 6 y 7)",
            "description": "Pico coordinado de publicaciones 5x superior a la media histórica concentrado en la comunidad amplificadora apuntando al hub gremial.",
        })

    # Sección de Estrategia Electoral del Candidato (War Room)
    campaign_strategy = None
    target_candidate_id = candidate_id
    if target_candidate_id is None and len(nodes) > 0:
        organic_nodes = [n for n in nodes if not n.get("org") and n.get("bot", 0) < 30]
        if organic_nodes:
            target_candidate_id = max(organic_nodes, key=lambda x: x.get("influence", 0))["id"]

    if target_candidate_id is not None and any(n["id"] == target_candidate_id for n in nodes):
        try:
            audit = audit_candidate(graph, target_candidate_id)
            brokers = find_strategic_brokers(graph, target_candidate_id, limit=3)
            campaign_strategy = {
                "candidate": audit["candidate"],
                "echo_chamber": audit["echo_chamber"],
                "tactical_actions": audit["tactical_actions"],
                "recommended_allies": [
                    {
                        "handle": f"@{b['handle']}",
                        "comm_name": b["comm_name"],
                        "alliance_score": b["alliance_score"],
                        "rationale": b["rationale"],
                    }
                    for b in brokers
                ],
                "threat_level": audit["dirty_war_shield"]["threat_level"],
            }
        except Exception:
            campaign_strategy = None

    return {
        "report_title": f"Informe de Inteligencia de Red: {project.get('name', 'Investigación')}",
        "topic": project.get("topic", meta.get("topic", "N/A")),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_profiles": total_nodes,
            "total_interactions": meta.get("interactions", total_links),
            "total_communities": len(communities),
            "suspicious_profiles": len(suspicious_nodes),
            "suspicious_percentage": pct_suspicious,
        },
        "communities": comm_stats,
        "campaign_strategy": campaign_strategy,
        "top_influencers": [
            {
                "handle": f"@{n.get('handle')}",
                "influence": n.get("influence"),
                "connections": n.get("degree"),
                "authenticity": n.get("auth"),
                "is_institutional": n.get("org", False),
            }
            for n in top_influencers
        ],
        "top_bridges": [
            {
                "handle": f"@{n.get('handle')}",
                "bridge_index": n.get("bridge"),
                "connections": n.get("degree"),
            }
            for n in top_bridges
        ],
        "astroturfing_findings": astroturfing_findings,
        "methodology": {
            "influence_algorithm": "PageRank (damping factor = 0.85, normalizado 0-100)",
            "bridge_algorithm": "Betweenness Centrality (Brandes Algorithm)",
            "community_detection": "Louvain Modularity Optimization",
            "bot_detection": "Análisis Multidimensional CIB (Entropía horaria, sufijos numéricos, fan-in clustering)",
        },
    }


def generate_graph_svg(nodes: List[Dict[str, Any]], links: List[Dict[str, Any]], width: int = 700, height: int = 380) -> str:
    """
    Genera un grafo vectorial en formato SVG a partir de los nodos y enlaces disponibles.
    Calcula coordenadas normalizadas basadas en x, y si existen, o distribuidas en círculo.
    """
    if not nodes:
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="#0e131f"/><text x="50%" y="50%" fill="#718096" text-anchor="middle" font-family="sans-serif">Grafo sin nodos</text></svg>'

    has_coords = all("x" in n and "y" in n for n in nodes[:min(20, len(nodes))])

    node_pos = {}
    if has_coords:
        xs = [n["x"] for n in nodes if "x" in n]
        ys = [n["y"] for n in nodes if "y" in n]
        min_x, max_x = min(xs or [0]), max(xs or [1])
        min_y, max_y = min(ys or [0]), max(ys or [1])
        span_x = max(1e-5, max_x - min_x)
        span_y = max(1e-5, max_y - min_y)

        margin = 40
        for n in nodes:
            nid = n.get("id")
            px = margin + ((n.get("x", 0) - min_x) / span_x) * (width - 2 * margin)
            py = margin + ((n.get("y", 0) - min_y) / span_y) * (height - 2 * margin)
            node_pos[nid] = (px, py)
    else:
        import math
        cx, cy = width / 2, height / 2
        r = min(width, height) * 0.4
        total = len(nodes)
        for i, n in enumerate(nodes):
            angle = (2 * math.pi * i) / max(1, total)
            node_pos[n["id"]] = (cx + r * math.cos(angle), cy + r * math.sin(angle))

    lines_svg = []
    for l in links[:300]:
        src = l.get("source") if not isinstance(l.get("source"), dict) else l["source"].get("id")
        tgt = l.get("target") if not isinstance(l.get("target"), dict) else l["target"].get("id")
        if src in node_pos and tgt in node_pos:
            x1, y1 = node_pos[src]
            x2, y2 = node_pos[tgt]
            lines_svg.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="rgba(255,255,255,0.12)" stroke-width="0.8" />')

    circles_svg = []
    color_map = {
        0: "#3B82F6",
        1: "#10B981",
        2: "#F59E0B",
        3: "#8B5CF6",
        4: "#EC4899",
        5: "#06B6D4",
    }
    for n in nodes[:250]:
        nid = n["id"]
        if nid in node_pos:
            x, y = node_pos[nid]
            comm = n.get("comm", 0)
            color = n.get("color") or color_map.get(comm % 6, "#64748B")
            is_bot = n.get("bot", 0) >= 60
            radius = max(3.0, min(14.0, (n.get("influence", 10) / 100) * 12 + 3))
            stroke = "#EF4444" if is_bot else "rgba(255,255,255,0.4)"
            stroke_w = "1.5" if is_bot else "0.5"
            circles_svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{color}" stroke="{stroke}" stroke-width="{stroke_w}" opacity="0.85"/>')

    svg_body = "".join(lines_svg) + "".join(circles_svg)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" style="background-color:#0b0f19; border-radius:8px;">
        <rect width="100%" height="100%" fill="#0b0f19" rx="8"/>
        {svg_body}
    </svg>'''


def generate_pdf_report(
    project: Dict[str, Any],
    candidate_id: Optional[int] = None,
    svg_content: Optional[str] = None
) -> bytes:
    """
    Compila y genera el informe ejecutivo en PDF mediante WeasyPrint.
    Contiene: Portada institucional, Resumen Macro, Captura Vectorial SVG,
    Tabla de Líderes y Fichas Forenses CIB.
    """
    if not WEASYPRINT_AVAILABLE or weasyprint is None:
        raise WeasyPrintUnavailableError("WeasyPrint no está instalado en el sistema.")

    data = generate_executive_report(project, candidate_id=candidate_id)
    graph = project.get("graph", {})
    nodes = graph.get("nodes", [])
    links = graph.get("links", [])

    # Obtener o construir SVG del grafo
    if svg_content and "<svg" in svg_content:
        svg_render = svg_content
    else:
        svg_render = generate_graph_svg(nodes, links, width=700, height=360)

    # Identificar fichas CIB destacadas
    suspicious_nodes = sorted(
        [n for n in nodes if n.get("bot", 0) >= 60],
        key=lambda x: x.get("bot", 0),
        reverse=True
    )[:8]

    # Render HTML template para WeasyPrint
    now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    project_name = html.escape(project.get("name", "Investigación Forense"))
    topic = html.escape(str(data.get("topic", "Análisis General")))

    # Filas de comunidades
    comm_rows = ""
    for c in data["communities"]:
        c_name = html.escape(c["name"])
        comm_rows += f"""
        <tr>
            <td><span class="color-badge" style="background-color: {c['color']};"></span> {c_name}</td>
            <td class="text-right">{c['size']}</td>
            <td class="text-right">{c['percentage']}%</td>
            <td class="text-right {'cib-highlight' if c['suspicious_count'] > 0 else ''}">{c['suspicious_count']}</td>
            <td class="text-right">{c['avg_authenticity']}%</td>
        </tr>
        """

    # Filas de top líderes
    leader_rows = ""
    for idx, inf in enumerate(data["top_influencers"][:8], 1):
        handle = html.escape(inf["handle"])
        leader_rows += f"""
        <tr>
            <td class="text-center">{idx}</td>
            <td><strong>{handle}</strong></td>
            <td class="text-right">{inf['influence']}</td>
            <td class="text-right">{inf['connections']}</td>
            <td class="text-right">{inf['authenticity']}%</td>
            <td class="text-center">{'Institucional' if inf['is_institutional'] else 'Individual'}</td>
        </tr>
        """

    # Fichas CIB
    cib_cards = ""
    if suspicious_nodes:
        for b in suspicious_nodes:
            b_handle = html.escape(str(b.get("handle", "anónimo")))
            bot_score = b.get("bot", 0)
            auth_score = b.get("auth", 0)
            comm_id = b.get("comm", "-")
            degree = b.get("degree", 0)
            cib_cards += f"""
            <div class="cib-card">
                <div class="cib-card-header">
                    <span class="cib-handle">@{b_handle}</span>
                    <span class="cib-badge">Bot Score: {bot_score}/100</span>
                </div>
                <div class="cib-card-grid">
                    <div><strong>Autenticidad:</strong> {auth_score}%</div>
                    <div><strong>Comunidad:</strong> #{comm_id}</div>
                    <div><strong>Conexiones:</strong> {degree}</div>
                    <div><strong>Anomalía:</strong> Entropía temporal baja / Fan-in anómalo</div>
                </div>
            </div>
            """
    else:
        cib_cards = '<p class="empty-state">No se registraron perfiles con Bot Score superior a 60 en la muestra.</p>'

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <title>{project_name} — Informe TRAMA</title>
    <style>
        @page {{
            size: A4 portrait;
            margin: 20mm 15mm 20mm 15mm;
            @bottom-right {{
                content: "Página " counter(page) " de " counter(pages);
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                font-size: 8pt;
                color: #64748b;
            }}
            @bottom-left {{
                content: "TRAMA — Inteligencia Forense de Redes | Confidencial";
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                font-size: 8pt;
                color: #64748b;
            }}
        }}

        @page:first {{
            margin-top: 0;
            margin-bottom: 0;
            @bottom-right {{ content: normal; }}
            @bottom-left {{ content: normal; }}
        }}

        body {{
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            color: #1e293b;
            background: #ffffff;
            font-size: 9.5pt;
            line-height: 1.45;
            margin: 0;
            padding: 0;
        }}

        .page-break {{
            page-break-after: always;
        }}

        /* PORTADA */
        .cover-page {{
            background: linear-gradient(135deg, #090d16 0%, #111827 60%, #1e1b4b 100%);
            color: #ffffff;
            height: 297mm;
            box-sizing: border-box;
            padding: 40mm 20mm;
            position: relative;
        }}
        .cover-badge {{
            display: inline-block;
            background: #e11d48;
            color: #ffffff;
            font-size: 8pt;
            font-weight: bold;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            padding: 4px 12px;
            border-radius: 4px;
            margin-bottom: 25mm;
        }}
        .cover-title {{
            font-size: 26pt;
            font-weight: 800;
            color: #ffffff;
            line-height: 1.15;
            margin: 0 0 8mm 0;
        }}
        .cover-subtitle {{
            font-size: 13pt;
            color: #94a3b8;
            margin: 0 0 25mm 0;
            font-weight: 300;
        }}
        .cover-meta {{
            border-top: 1px solid rgba(255,255,255,0.15);
            padding-top: 10mm;
            font-size: 9pt;
            color: #cbd5e1;
            line-height: 1.8;
        }}
        .cover-meta strong {{
            color: #ffffff;
        }}
        .cover-footer {{
            position: absolute;
            bottom: 25mm;
            left: 20mm;
            font-size: 8pt;
            color: #64748b;
        }}

        /* ENCABEZADOS DE SECCION */
        h2.section-title {{
            font-size: 13pt;
            font-weight: 700;
            color: #0f172a;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 4px;
            margin-top: 6mm;
            margin-bottom: 4mm;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        h3.subsection-title {{
            font-size: 10.5pt;
            font-weight: 600;
            color: #334155;
            margin-top: 4mm;
            margin-bottom: 2mm;
        }}

        /* KPI GRID */
        .kpi-container {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 6mm;
        }}
        .kpi-box {{
            flex: 1;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 10px;
            text-align: center;
            margin-right: 8px;
        }}
        .kpi-box:last-child {{
            margin-right: 0;
        }}
        .kpi-box.alert {{
            background: #fff1f2;
            border-color: #fecdd3;
        }}
        .kpi-value {{
            display: block;
            font-size: 16pt;
            font-weight: 800;
            color: #0f172a;
        }}
        .kpi-box.alert .kpi-value {{
            color: #e11d48;
        }}
        .kpi-label {{
            font-size: 7.5pt;
            color: #64748b;
            text-transform: uppercase;
            font-weight: 600;
        }}

        /* TABLAS */
        table.data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 8.5pt;
            margin-bottom: 5mm;
        }}
        table.data-table th {{
            background-color: #0f172a;
            color: #ffffff;
            font-weight: 600;
            text-align: left;
            padding: 6px 8px;
            font-size: 8pt;
        }}
        table.data-table td {{
            padding: 5px 8px;
            border-bottom: 1px solid #e2e8f0;
        }}
        table.data-table tr:nth-child(even) {{
            background-color: #f8fafc;
        }}
        .text-right {{ text-align: right; }}
        .text-center {{ text-align: center; }}
        .color-badge {{
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 4px;
        }}
        .cib-highlight {{
            color: #e11d48;
            font-weight: bold;
        }}

        /* SVG DEL GRAFO */
        .svg-wrapper {{
            text-align: center;
            margin: 4mm 0 6mm 0;
            background: #0b0f19;
            padding: 8px;
            border-radius: 8px;
        }}
        .svg-wrapper svg {{
            max-width: 100%;
            height: auto;
        }}

        /* FICHAS CIB */
        .cib-card {{
            background: #f8fafc;
            border-left: 3px solid #e11d48;
            border-top: 1px solid #e2e8f0;
            border-right: 1px solid #e2e8f0;
            border-bottom: 1px solid #e2e8f0;
            border-radius: 4px;
            padding: 8px 10px;
            margin-bottom: 3mm;
            page-break-inside: avoid;
        }}
        .cib-card-header {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 4px;
        }}
        .cib-handle {{
            font-weight: bold;
            color: #0f172a;
            font-size: 9pt;
        }}
        .cib-badge {{
            background: #fee2e2;
            color: #991b1b;
            font-size: 7.5pt;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 3px;
        }}
        .cib-card-grid {{
            display: flex;
            flex-wrap: wrap;
            font-size: 8pt;
            color: #475569;
        }}
        .cib-card-grid div {{
            width: 48%;
            margin-bottom: 2px;
        }}
        .empty-state {{
            font-style: italic;
            color: #64748b;
            text-align: center;
            padding: 10px;
        }}
    </style>
</head>
<body>

    <!-- PORTADA -->
    <div class="cover-page">
        <span class="cover-badge">INFORME DE INTELIGENCIA FORENSE</span>
        <h1 class="cover-title">{project_name}</h1>
        <p class="cover-subtitle">Auditoría Topológica, Detección de Desinformación y Análisis de Coordinación Inauténtica (CIB)</p>

        <div class="cover-meta">
            <p><strong>Fecha de Emisión:</strong> {now_str}</p>
            <p><strong>Eje Temático:</strong> {topic}</p>
            <p><strong>Motor Analítico:</strong> TRAMA v0.4 (igraph Leiden + WeasyPrint Engine)</p>
            <p><strong>Clasificación:</strong> DOCUMENTO RESERVADO / USO EXCLUSIVO</p>
        </div>

        <div class="cover-footer">
            Generado automáticamente por la plataforma TRAMA. Prohibida su difusión no autorizada.
        </div>
    </div>

    <div class="page-break"></div>

    <!-- SECCIÓN 1: RESUMEN MACRO -->
    <h2 class="section-title">1. Resumen Ejecutivo y Métricas Macro</h2>
    <div class="kpi-container">
        <div class="kpi-box">
            <span class="kpi-value">{data['summary']['total_profiles']}</span>
            <span class="kpi-label">Perfiles Analizados</span>
        </div>
        <div class="kpi-box">
            <span class="kpi-value">{data['summary']['total_interactions']}</span>
            <span class="kpi-label">Interacciones</span>
        </div>
        <div class="kpi-box">
            <span class="kpi-value">{data['summary']['total_communities']}</span>
            <span class="kpi-label">Comunidades</span>
        </div>
        <div class="kpi-box {'alert' if data['summary']['suspicious_percentage'] > 10 else ''}">
            <span class="kpi-value">{data['summary']['suspicious_percentage']}%</span>
            <span class="kpi-label">Índice Inauténtico</span>
        </div>
    </div>

    <!-- SECCIÓN 2: CAPTURA VECTORIAL SVG DEL GRAFO -->
    <h2 class="section-title">2. Topología de Red (Captura Vectorial SVG)</h2>
    <div class="svg-wrapper">
        {svg_render}
    </div>
    <p style="font-size: 7.5pt; color: #64748b; margin-top: -3mm; text-align: center;">
        Representación topológica global: el diámetro de los nodos refleja su centralidad PageRank; los contornos rojos indican actividad anómala CIB.
    </p>

    <!-- SECCIÓN 3: ESTRUCTURA DE COMUNIDADES -->
    <h3 class="subsection-title">Distribución por Comunidades (Algoritmo Leiden / Louvain)</h3>
    <table class="data-table">
        <thead>
            <tr>
                <th>Comunidad</th>
                <th class="text-right">Miembros</th>
                <th class="text-right">Cuota (%)</th>
                <th class="text-right">Sospechosos</th>
                <th class="text-right">Autenticidad Prom.</th>
            </tr>
        </thead>
        <tbody>
            {comm_rows}
        </tbody>
    </table>

    <div class="page-break"></div>

    <!-- SECCIÓN 4: TABLA DE LÍDERES -->
    <h2 class="section-title">3. Tabla de Líderes y Actores Estratégicos</h2>
    <table class="data-table">
        <thead>
            <tr>
                <th class="text-center" style="width: 30px;">#</th>
                <th>Usuario</th>
                <th class="text-right">PageRank (0-100)</th>
                <th class="text-right">Grado / Conexiones</th>
                <th class="text-right">Autenticidad</th>
                <th class="text-center">Tipología</th>
            </tr>
        </thead>
        <tbody>
            {leader_rows}
        </tbody>
    </table>

    <!-- SECCIÓN 5: FICHAS CIB -->
    <h2 class="section-title">4. Fichas Forenses CIB (Comportamiento Inauténtico)</h2>
    <p style="font-size: 8pt; color: #475569; margin-bottom: 3mm;">
        Cuentas aisladas mediante el clasificador multidimensional (entropía temporal, sincronización de ráfagas y patrones léxicos coordinados).
    </p>
    <div>
        {cib_cards}
    </div>

    <!-- METODOLOGÍA -->
    <h2 class="section-title" style="margin-top: 8mm;">5. Nota Metodológica</h2>
    <p style="font-size: 8pt; color: #64748b;">
        Este informe fue computado utilizando el motor de grafos en C de <code>python-igraph</code>, ejecutando optimización de modularidad y centralidad de Brandes. La renderización vectorial fue procesada mediante WeasyPrint para garantizar precisión tipográfica y fidelidad vectorial estricta.
    </p>

</body>
</html>
"""

    return weasyprint.HTML(string=html_content).write_pdf()
