"""
generate_pitch_deck.py — Generador automatizado de la presentación comercial y estratégica
para TRAMA v0.3.0 -> v1.0.
100% honesto: Presenta el estado operativo actual (v0.3.0) y la hoja de ruta de ingeniería
hacia la escala masiva (WebGL >100k nodos, Firehose tiempo real y NLP semántico).
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

# ─── Paleta de Colores Institucional TRAMA ──────────────────────────────────
BG_DARK = RGBColor(10, 15, 29)         # #0A0F1D (Fondo principal azul oscuro profundo)
CARD_BG = RGBColor(21, 30, 52)         # #151E34 (Fondo de tarjetas y contenedores)
CARD_BORDER = RGBColor(40, 53, 86)     # #283556 (Borde sutil de tarjeta)

COLOR_GOLD = RGBColor(245, 158, 11)    # #F59E0B (Oro/Ámbar - Influencia / PageRank)
COLOR_VIOLET = RGBColor(139, 92, 246)  # #8B5CF6 (Violeta - Topología / Comunidades)
COLOR_CYAN = RGBColor(6, 182, 212)     # #06B6D4 (Cian/Turquesa - Puentes / Alianzas)
COLOR_MAGENTA = RGBColor(236, 72, 153) # #EC4899 (Magenta - Alerta CIB / Bots)
COLOR_EMERALD = RGBColor(16, 185, 129) # #10B981 (Esmeralda - Éxito / Operativo hoy)

TEXT_WHITE = RGBColor(255, 255, 255)   # Blanco puro
TEXT_MUTED = RGBColor(148, 163, 184)   # Slate 400 (Subtítulos y notas)
TEXT_BODY = RGBColor(203, 213, 225)    # Slate 300 (Cuerpo de texto)

FONT_HEADING = "Helvetica"
FONT_BODY = "Arial"


def create_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    def set_slide_background(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = BG_DARK
        bg.line.fill.background()
        return bg

    def add_header(slide, title, category="TRAMA INTELLIGENCE"):
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.4))
        tf_cat = cat_box.text_frame
        tf_cat.word_wrap = True
        tf_cat.margin_left = tf_cat.margin_right = tf_cat.margin_top = tf_cat.margin_bottom = 0
        p_cat = tf_cat.paragraphs[0]
        p_cat.text = category.upper()
        p_cat.font.name = FONT_HEADING
        p_cat.font.size = Pt(11)
        p_cat.font.bold = True
        p_cat.font.color.rgb = COLOR_CYAN

        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.75), Inches(11.7), Inches(0.8))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        tf_title.margin_left = tf_title.margin_right = tf_title.margin_top = tf_title.margin_bottom = 0
        p_title = tf_title.paragraphs[0]
        p_title.text = title
        p_title.font.name = FONT_HEADING
        p_title.font.size = Pt(26)
        p_title.font.bold = True
        p_title.font.color.rgb = TEXT_WHITE

    def add_card(slide, left, top, width, height, bg=CARD_BG, border=CARD_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg
        card.line.color.rgb = border
        card.line.width = Pt(1.2)
        return card

    card_w3 = Inches(3.64)

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 1: PORTADA & PROPUESTA DE VALOR
    # ══════════════════════════════════════════════════════════════════════════
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_background(s1)

    glow = s1.shapes.add_shape(MSO_SHAPE.OVAL, Inches(7.5), Inches(0.5), Inches(5.5), Inches(5.5))
    glow.fill.solid()
    glow.fill.fore_color.rgb = RGBColor(30, 27, 75)
    glow.line.fill.background()

    tb = s1.shapes.add_textbox(Inches(0.8), Inches(1.2), Inches(8.0), Inches(5.0))
    tf = tb.text_frame
    tf.word_wrap = True

    p0 = tf.paragraphs[0]
    p0.text = "INTELIGENCIA DE REDES & WAR ROOM ELECTORAL"
    p0.font.name = FONT_HEADING
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_CYAN

    p1 = tf.add_paragraph()
    p1.text = "TRAMA"
    p1.font.name = FONT_HEADING
    p1.font.size = Pt(56)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_WHITE
    p1.space_before = Pt(8)

    p2 = tf.add_paragraph()
    p2.text = "La Verdad Estructural de la Conversación Digital"
    p2.font.name = FONT_HEADING
    p2.font.size = Pt(24)
    p2.font.bold = True
    p2.font.color.rgb = COLOR_GOLD
    p2.space_before = Pt(4)

    p3 = tf.add_paragraph()
    p3.text = "Auditoría topológica de influencia, detección matemática de astroturfing y hoja de ruta tecnológica hacia la monitorización masiva en tiempo real."
    p3.font.name = FONT_BODY
    p3.font.size = Pt(15)
    p3.font.color.rgb = TEXT_MUTED
    p3.space_before = Pt(18)

    # Badges derecha
    add_card(s1, Inches(8.8), Inches(1.5), Inches(3.7), Inches(4.8))
    tb_b = s1.shapes.add_textbox(Inches(9.1), Inches(1.8), Inches(3.1), Inches(4.2))
    tf_b = tb_b.text_frame
    tf_b.word_wrap = True

    pb_h = tf_b.paragraphs[0]
    pb_h.text = "ESTADO DEL PRODUCTO"
    pb_h.font.size = Pt(13)
    pb_h.font.bold = True
    pb_h.font.color.rgb = COLOR_EMERALD

    badges = [
        ("🟢 Motor Operativo Hoy (v0.3.0)", "Leiden en C, PageRank, ECI y forense CIB de 4 reglas activos."),
        ("🎯 Auditoría por Dataset", "Ingesta CSV con sanitización y streaming reactivo SSE."),
        ("🚀 Proyección Tecnológica", "Roadmap estructurado hacia WebGL masivo (>100k) y Firehose."),
        ("⚖️ Cero Promesas Falsas", "Capacidades demostradas y validadas matemáticamente."),
    ]
    for b_title, b_desc in badges:
        p_t = tf_b.add_paragraph()
        p_t.text = b_title
        p_t.font.size = Pt(12)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_WHITE
        p_t.space_before = Pt(12)

        p_d = tf_b.add_paragraph()
        p_d.text = b_desc
        p_d.font.size = Pt(10)
        p_d.font.color.rgb = TEXT_MUTED

    ft = s1.shapes.add_textbox(Inches(0.8), Inches(6.8), Inches(11.7), Inches(0.4))
    ft_p = ft.text_frame.paragraphs[0]
    ft_p.text = "TRAMA v0.3.0 | Propuesta Comercial & Plan Estratégico de Ingeniería"
    ft_p.font.size = Pt(10)
    ft_p.font.color.rgb = RGBColor(100, 116, 139)

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 2: EL PROBLEMA REAL EN LA INDUSTRIA
    # ══════════════════════════════════════════════════════════════════════════
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_background(s2)
    add_header(s2, "El Problema: La Ceguera del Monitoreo Tradicional", "DIAGNÓSTICO DEL MERCADO")

    sub2 = s2.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.7), Inches(0.5))
    p_sub2 = sub2.text_frame.paragraphs[0]
    p_sub2.text = "Las campañas y marcas gastan presupuestos millonarios en herramientas que solo cuentan palabras y menciones."
    p_sub2.font.size = Pt(15)
    p_sub2.font.color.rgb = TEXT_MUTED

    cards_p = [
        ("Métricas de Vanidad Infladas", COLOR_MAGENTA,
         "Las menciones brutas engañan. Una red de 20 cuentas automatizadas puede generar 10.000 tuits y fingir una tendencia nacional sin que el social listening tradicional note la coordinación."),
        ("Aislamiento en Cámara de Eco", COLOR_GOLD,
         "La mayoría de los candidatos cree que va ganando porque su equipo monitorea comentarios favorables dentro de su propia burbuja, ignorando que el voto indeciso está en otra comunidad."),
        ("Carencia de Análisis Relacional", COLOR_CYAN,
         "El monitoreo plano no responde quién articula el mensaje, quiénes son los aliados puente para dialogar con los rivales, ni por qué rutas de penetración llevar la propuesta."),
    ]
    for i, (ctitle, ccolor, cdesc) in enumerate(cards_p):
        left_pos = Inches(0.8 + i * 4.0)
        add_card(s2, left_pos, Inches(2.2), card_w3, Inches(4.3))

        tb_c = s2.shapes.add_textbox(left_pos + Inches(0.3), Inches(2.5), card_w3 - Inches(0.6), Inches(3.7))
        tfc = tb_c.text_frame
        tfc.word_wrap = True

        p_num = tfc.paragraphs[0]
        p_num.text = f"DIAGNÓSTICO 0{i+1}"
        p_num.font.size = Pt(11)
        p_num.font.bold = True
        p_num.font.color.rgb = ccolor

        p_t = tfc.add_paragraph()
        p_t.text = ctitle
        p_t.font.size = Pt(18)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_WHITE
        p_t.space_before = Pt(8)

        p_d = tfc.add_paragraph()
        p_d.text = cdesc
        p_d.font.size = Pt(13)
        p_d.font.color.rgb = TEXT_BODY
        p_d.space_before = Pt(14)

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 3: QUÉ TENEMOS HOY (CAPACIDADES OPERATIVAS v0.3.0)
    # ══════════════════════════════════════════════════════════════════════════
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_background(s3)
    add_header(s3, "Qué Tenemos Operativo Hoy: Motor TRAMA v0.3.0", "CAPACIDADES ACTIVAS")

    banner3 = add_card(s3, Inches(0.8), Inches(1.5), Inches(11.7), Inches(0.85), bg=RGBColor(15, 30, 45), border=COLOR_EMERALD)
    tb_b3 = s3.shapes.add_textbox(Inches(1.1), Inches(1.62), Inches(11.1), Inches(0.6))
    p_b3 = tb_b3.text_frame.paragraphs[0]
    p_b3.text = "✓ Software funcional, probado con 31 tests automatizados (100% pasando) y disponible en local ahora mismo."
    p_b3.font.size = Pt(13)
    p_b3.font.bold = True
    p_b3.font.color.rgb = COLOR_EMERALD

    features_now = [
        ("Cartografía Leiden en C", COLOR_VIOLET,
         "Particionamiento comunitario acelerado (<50ms). Encuentra facciones reales sin sesgo humano en python-igraph."),
        ("Influencia y Puentes", COLOR_GOLD,
         "PageRank normalizado (0-100) para influencia real y Betweenness centrality para identificar 'Gatekeepers' frontera."),
        ("Cuarto de Guerra (ECI)", COLOR_CYAN,
         "Echo Chamber Index calcula el % de encierro del candidato. Genera rutas hacia indecisos y aliados estratégicos."),
        ("Forense CIB de 4 Factores", COLOR_MAGENTA,
         "Heurística explicable: picos temporales anómalos, nomenclatura por script, ratio posts/seguidores y topología en abanico."),
    ]
    card_w4 = Inches(2.7)
    for k, (f_tit, f_col, f_desc) in enumerate(features_now):
        left_pos = Inches(0.8 + k * 2.95)
        add_card(s3, left_pos, Inches(2.6), card_w4, Inches(4.1))
        tb_f = s3.shapes.add_textbox(left_pos + Inches(0.2), Inches(2.8), card_w4 - Inches(0.4), Inches(3.7))
        tff = tb_f.text_frame
        tff.word_wrap = True

        p_ft = tff.paragraphs[0]
        p_ft.text = f_tit
        p_ft.font.size = Pt(15)
        p_ft.font.bold = True
        p_ft.font.color.rgb = f_col

        p_fd = tff.add_paragraph()
        p_fd.text = f_desc
        p_fd.font.size = Pt(12)
        p_fd.font.color.rgb = TEXT_BODY
        p_fd.space_before = Pt(12)

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 4: CASO DE ESTUDIO TÉCNICO (#ReformaDelAgua)
    # ══════════════════════════════════════════════════════════════════════════
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_background(s4)
    add_header(s4, "Caso de Estudio y Validación: #ReformaDelAgua", "BENCHMARK DE REFERENCIA")

    add_card(s4, Inches(0.8), Inches(1.6), Inches(7.5), Inches(5.1))
    tb_cs = s4.shapes.add_textbox(Inches(1.1), Inches(1.9), Inches(6.9), Inches(4.5))
    tfcs = tb_cs.text_frame
    tfcs.word_wrap = True

    p_csh = tfcs.paragraphs[0]
    p_csh.text = "DESARTICULACIÓN DE OPERACIÓN ARTIFICIAL SIMULADA"
    p_csh.font.size = Pt(15)
    p_csh.font.bold = True
    p_csh.font.color.rgb = COLOR_CYAN

    p_csd = tfcs.add_paragraph()
    p_csd.text = "Para verificar matemáticamente el sistema, diseñamos un benchmark reproducible (150 perfiles, 4 comunidades, 12 semanas) con una operación encubierta plantada:\n\n" \
                "1. En las semanas 1 a 5, la red operó de forma aparentemente orgánica.\n" \
                "2. En las semanas 6 y 7, una 'Red Amplificadora' de 32 perfiles despertó con picos sincronizados (>3x media) concentrados hacia un hub (@AgroFuturoCol).\n" \
                "3. TRAMA aisló la operación al instante con el anillo magenta pulsante y expuso la coordinación en la barra de Time-Travel."
    p_csd.font.size = Pt(12)
    p_csd.font.color.rgb = TEXT_BODY
    p_csd.space_before = Pt(8)

    # Métricas del caso a la derecha
    benchmarks = [
        ("150 Nodos", "4 Comunidades en conflicto", COLOR_GOLD),
        ("32 Cuentas", "Clúster CIB detectado al 100%", COLOR_MAGENTA),
        ("Sem. 6-7", "Pico temporal aislado en Time-Travel", COLOR_EMERALD),
    ]
    for b_idx, (b_val, b_lbl, b_col) in enumerate(benchmarks):
        top_pos = Inches(1.6 + b_idx * 1.75)
        add_card(s4, Inches(8.7), top_pos, Inches(3.8), Inches(1.5))
        tb_bm = s4.shapes.add_textbox(Inches(9.0), top_pos + Inches(0.2), Inches(3.2), Inches(1.1))
        tfbm = tb_bm.text_frame
        tfbm.word_wrap = True

        p_bv = tfbm.paragraphs[0]
        p_bv.text = b_val
        p_bv.font.size = Pt(26)
        p_bv.font.bold = True
        p_bv.font.color.rgb = b_col

        p_bl = tfbm.add_paragraph()
        p_bl.text = b_lbl
        p_bl.font.size = Pt(11)
        p_bl.font.color.rgb = TEXT_MUTED

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 5: EL CUARTO DE GUERRA (WAR ROOM POLÍTICO)
    # ══════════════════════════════════════════════════════════════════════════
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_background(s5)
    add_header(s5, "Módulo War Room: De la Observación a la Acción Táctica", "ESTRATEGIA ELECTORAL")

    add_card(s5, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.1))
    tb_wr1 = s5.shapes.add_textbox(Inches(1.1), Inches(1.9), Inches(5.0), Inches(4.5))
    tfwr1 = tb_wr1.text_frame
    tfwr1.word_wrap = True

    p_w1h = tfwr1.paragraphs[0]
    p_w1h.text = "ECHO CHAMBER INDEX (ECI)"
    p_w1h.font.size = Pt(17)
    p_w1h.font.bold = True
    p_w1h.font.color.rgb = COLOR_GOLD

    p_w1d = tfwr1.add_paragraph()
    p_w1d.text = "¿El candidato habla al país o solo a su club de fans?\n\n" \
                 "• El ECI mide de 0% a 100% el grado de encierro dentro del nicho afín.\n" \
                 "• Un ECI > 70% dispara alerta roja: la campaña está saturando a sus propios convencidos mientras los indecisos son cooptados por rivales.\n" \
                 "• Permite calibrar discursos y evaluar si una declaración logró romper el cerco mediático."
    p_w1d.font.size = Pt(12)
    p_w1d.font.color.rgb = TEXT_BODY
    p_w1d.space_before = Pt(8)

    add_card(s5, Inches(6.9), Inches(1.6), Inches(5.6), Inches(5.1))
    tb_wr2 = s5.shapes.add_textbox(Inches(7.2), Inches(1.9), Inches(5.0), Inches(4.5))
    tfwr2 = tb_wr2.text_frame
    tfwr2.word_wrap = True

    p_w2h = tfwr2.paragraphs[0]
    p_w2h.text = "RUTAS HACIA INDECISOS Y ESCUDO"
    p_w2h.font.size = Pt(17)
    p_w2h.font.bold = True
    p_w2h.font.color.rgb = COLOR_CYAN

    p_w2d = tfwr2.add_paragraph()
    p_w2d.text = "Herramientas de intervención territorial digital:\n\n" \
                 "• Strategic Broker Finder: Localiza automáticamente los 5 articuladores con credibilidad en la frontera entre comunidades.\n" \
                 "• Expansion Paths: Algoritmo de rutas óptimas para penetrar nichos neutrales sin ser rechazado.\n" \
                 "• Dirty War Shield: Detección temprana de ataques coordinados dirigidos a desprestigiar al candidato."
    p_w2d.font.size = Pt(12)
    p_w2d.font.color.rgb = TEXT_BODY
    p_w2d.space_before = Pt(8)

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 6: HOJA DE RUTA TECNOLÓGICA (ROADMAP HACIA EL OBJETIVO)
    # ══════════════════════════════════════════════════════════════════════════
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_background(s6)
    add_header(s6, "Hoja de Ruta: Cómo Alcanzaremos la Escala Total", "ROADMAP DE INGENIERÍA")

    roadmap_steps = [
        ("FASE 1: HOY (v0.3.0)", COLOR_EMERALD, "COMPLETADA",
         ["Motor Leiden en C (igraph)", "PageRank y Betweenness", "Echo Chamber Index (ECI)", "Forense CIB 4 reglas", "SQLite + Alembic relacional"]),
        ("FASE 2: PRÓXIMA (Sprints 3-4)", COLOR_GOLD, "EN DESARROLLO",
         ["NLP semántico (MinHash/LSH)", "Redes CooRnet de co-compartición", "Física en Web Worker (60 FPS)", "Modo 100% Offline (Graphology)", "Reportes corporativos en PDF"]),
        ("FASE 3: META (Sprints 5-6)", COLOR_MAGENTA, "ESCALA ENTERPRISE",
         ["Streaming Firehose 24/7 (Bluesky/X)", "Motor columnar DuckDB en memoria", "WebGL masivo (>100k nodos)", "SaaS Multi-Tenant con RBAC/JWT", "Row-Level Security en PostgreSQL"]),
    ]
    for r_i, (r_title, r_col, r_badge, r_bullets) in enumerate(roadmap_steps):
        left_pos = Inches(0.8 + r_i * 4.0)
        add_card(s6, left_pos, Inches(1.6), card_w3, Inches(5.1))
        tb_r = s6.shapes.add_textbox(left_pos + Inches(0.3), Inches(1.9), card_w3 - Inches(0.6), Inches(4.5))
        tfr = tb_r.text_frame
        tfr.word_wrap = True

        p_rt = tfr.paragraphs[0]
        p_rt.text = r_title
        p_rt.font.size = Pt(14)
        p_rt.font.bold = True
        p_rt.font.color.rgb = r_col

        p_rb = tfr.add_paragraph()
        p_rb.text = f"[{r_badge}]"
        p_rb.font.size = Pt(11)
        p_rb.font.bold = True
        p_rb.font.color.rgb = TEXT_MUTED
        p_rb.space_before = Pt(2)

        for bit in r_bullets:
            p_it = tfr.add_paragraph()
            p_it.text = f"• {bit}"
            p_it.font.size = Pt(11)
            p_it.font.color.rgb = TEXT_BODY
            p_it.space_before = Pt(8)

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 7: LA TECNOLOGÍA DETRÁS DE CADA HITO
    # ══════════════════════════════════════════════════════════════════════════
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_background(s7)
    add_header(s7, "Arquitectura de Solución para los Retos Pendientes", "DISEÑO DE INGENIERÍA")

    tech_solutions = [
        ("Reto 1: Escala >100k Nodos", COLOR_MAGENTA,
         "Solución: Migración a motor gráfico WebGL con Sigma.js v3 y renderizado acelerado por GPU (Instanced Drawing). Simulación física en Web Worker independiente mediante Float32Array."),
        ("Reto 2: Ingesta en Vivo 24/7", COLOR_CYAN,
         "Solución: Cliente WebSocket para consumo directo del Jetstream de Bluesky (AT Protocol) e ingestor de la API v2 de X, procesando eventos hacia almacenamiento columnar DuckDB + Apache Parquet."),
        ("Reto 3: Detección de Textos", COLOR_GOLD,
         "Solución: Integración de modelo multilingüe ligero (MiniLM) con hashing LSH/MinHash para detectar campañas de mensajes coordinados idénticos o parafraseados con similitud >85%."),
        ("Reto 4: Seguridad Multi-Tenant", COLOR_VIOLET,
         "Solución: Autenticación JWT y control de acceso basado en roles (RBAC: Admin, Lead Investigator, Analyst) con políticas de aislamiento estricto (RLS) en PostgreSQL."),
    ]
    card_w2x2 = Inches(5.6)
    card_h2x2 = Inches(2.35)
    for t_idx, (t_name, t_color, t_expl) in enumerate(tech_solutions):
        row = t_idx // 2
        col = t_idx % 2
        left_pos = Inches(0.8 + col * 6.1)
        top_pos = Inches(1.6 + row * 2.65)
        add_card(s7, left_pos, top_pos, card_w2x2, card_h2x2)

        tb_ts = s7.shapes.add_textbox(left_pos + Inches(0.3), top_pos + Inches(0.2), card_w2x2 - Inches(0.6), card_h2x2 - Inches(0.4))
        tfts = tb_ts.text_frame
        tfts.word_wrap = True

        p_tt = tfts.paragraphs[0]
        p_tt.text = t_name
        p_tt.font.size = Pt(14)
        p_tt.font.bold = True
        p_tt.font.color.rgb = t_color

        p_te = tfts.add_paragraph()
        p_te.text = t_expl
        p_te.font.size = Pt(11)
        p_te.font.color.rgb = TEXT_BODY
        p_te.space_before = Pt(6)

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 8: MODELO DE VENTA HONESTO Y FACTIBLE HOY
    # ══════════════════════════════════════════════════════════════════════════
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_background(s8)
    add_header(s8, "Modelo Comercial Realista: Consultoría & Software", "MONETIZACIÓN")

    business_models = [
        ("01. Auditoría Forense Express", "$800 - $1.500 USD", "Por Investigación", COLOR_CYAN,
         ["Entrega de dataset o tema clave", "Radiografía completa de comunidades", "Cálculo del ECI del vocero", "Informe pericial de cuentas CIB", "Entrega en 48 horas laborales"]),
        ("02. Cuarto de Guerra por Campaña", "$3.500 - $8.000 USD", "Por Mes de Campaña", COLOR_GOLD,
         ["Acompañamiento táctico semanal", "Actualización continua de grafos", "Alertas de guerra sucia y ataques", "Rutas hacia votantes indecisos", "Sesión semanal con el estratega"]),
        ("03. Licenciamiento Enterprise", "Suscripción Anual", "Para Agencias y Gobiernos", COLOR_MAGENTA,
         ["Instalación On-Premise privada", "Acceso a todo el roadmap (v1.0)", "Capacitación a equipo de análisis", "Soporte y adaptadores a medida", "Contrato SLA empresarial"]),
    ]
    for m_i, (m_tit, m_pri, m_mod, m_col, m_pts) in enumerate(business_models):
        left_pos = Inches(0.8 + m_i * 4.0)
        add_card(s8, left_pos, Inches(1.6), card_w3, Inches(5.1))
        tb_m = s8.shapes.add_textbox(left_pos + Inches(0.3), Inches(1.9), card_w3 - Inches(0.6), Inches(4.5))
        tfm = tb_m.text_frame
        tfm.word_wrap = True

        p_mt = tfm.paragraphs[0]
        p_mt.text = m_tit
        p_mt.font.size = Pt(13)
        p_mt.font.bold = True
        p_mt.font.color.rgb = m_col

        p_mp = tfm.add_paragraph()
        p_mp.text = m_pri
        p_mp.font.size = Pt(22)
        p_mp.font.bold = True
        p_mp.font.color.rgb = TEXT_WHITE
        p_mp.space_before = Pt(4)

        p_mm = tfm.add_paragraph()
        p_mm.text = m_mod
        p_mm.font.size = Pt(11)
        p_mm.font.color.rgb = TEXT_MUTED

        for pt in m_pts:
            p_pt = tfm.add_paragraph()
            p_pt.text = f"✓ {pt}"
            p_pt.font.size = Pt(11)
            p_pt.font.color.rgb = TEXT_BODY
            p_pt.space_before = Pt(8)

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 9: PROGRAMA DE ADOPCIÓN TEMPRANA (PILOTO)
    # ══════════════════════════════════════════════════════════════════════════
    s9 = prs.slides.add_slide(blank_layout)
    set_slide_background(s9)
    add_header(s9, "Programa Early Adopters: Construyamos el Caso Juntos", "PROPUESTA DE PILOTO")

    add_card(s9, Inches(0.8), Inches(1.6), Inches(11.7), Inches(5.1))
    tb_pilot = s9.shapes.add_textbox(Inches(1.1), Inches(1.9), Inches(11.1), Inches(4.5))
    tf_pi = tb_pilot.text_frame
    tf_pi.word_wrap = True

    p_pi_h = tf_pi.paragraphs[0]
    p_pi_h.text = "¿CÓMO GANAMOS CREDIBILIDAD Y RESULTADOS REALES?"
    p_pi_h.font.size = Pt(16)
    p_pi_h.font.bold = True
    p_pi_h.font.color.rgb = COLOR_CYAN

    p_pi_d = tf_pi.add_paragraph()
    p_pi_d.text = "En lugar de prometer victorias mágicas ficticias, ofrecemos una alianza estratégica transparente para tu campaña o agencia:\n\n" \
                 "1. Prueba de Concepto (PoC) Piloto Gratuita:\n" \
                 "   Analizamos una conversación o hashtag crítico de tu interés con hasta 5.000 nodos.\n" \
                 "   Te entregamos el reporte completo de comunidades, índice ECI y cuentas sospechosas sin costo inicial.\n\n" \
                 "2. Co-diseño de Inteligencia:\n" \
                 "   Tu equipo de estrategia retroalimenta los hallazgos y prioriza las funciones que más valor le aporten a la contienda.\n\n" \
                 "3. Conversión a Éxito Comprobado:\n" \
                 "   Al validar que TRAMA reveló datos que el social listening tradicional no vio, firmamos el acompañamiento para toda la campaña."
    p_pi_d.font.size = Pt(13)
    p_pi_d.font.color.rgb = TEXT_BODY
    p_pi_d.space_before = Pt(10)

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 10: CIERRE Y DEMO EN VIVO
    # ══════════════════════════════════════════════════════════════════════════
    s10 = prs.slides.add_slide(blank_layout)
    set_slide_background(s10)

    glow10 = s10.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.5), Inches(0.5), Inches(6.5), Inches(6.5))
    glow10.fill.solid()
    glow10.fill.fore_color.rgb = RGBColor(20, 20, 50)
    glow10.line.fill.background()

    add_header(s10, "Demo en Vivo Inmediata & Próximos Pasos", "ACCESO DIRECTO")

    add_card(s10, Inches(0.8), Inches(1.6), Inches(5.6), Inches(4.9))
    tb_cta1 = s10.shapes.add_textbox(Inches(1.1), Inches(1.9), Inches(5.0), Inches(4.3))
    tf_c1 = tb_cta1.text_frame
    tf_c1.word_wrap = True

    p_c1_h = tf_c1.paragraphs[0]
    p_c1_h.text = "PROBEMOS CON TUS PROPIOS DATOS"
    p_c1_h.font.size = Pt(16)
    p_c1_h.font.bold = True
    p_c1_h.font.color.rgb = COLOR_CYAN

    p_c1_b = tf_c1.add_paragraph()
    p_c1_b.text = "No te fíes solo de las diapositivas:\n\n" \
                 "• El software está ejecutándose en este momento.\n" \
                 "• Podemos cargar un archivo CSV de interacciones en vivo y ver el grafo desplegarse en tiempo real.\n" \
                 "• Evaluemos a tu candidato frente a sus rivales y auditemos su Echo Chamber Index ahora mismo."
    p_c1_b.font.size = Pt(13)
    p_c1_b.font.color.rgb = TEXT_BODY
    p_c1_b.space_before = Pt(14)

    add_card(s10, Inches(6.9), Inches(1.6), Inches(5.6), Inches(4.9))
    tb_cta2 = s10.shapes.add_textbox(Inches(7.2), Inches(1.9), Inches(5.0), Inches(4.3))
    tf_c2 = tb_cta2.text_frame
    tf_c2.word_wrap = True

    p_c2_h = tf_c2.paragraphs[0]
    p_c2_h.text = "CANALES DE ACCESO"
    p_c2_h.font.size = Pt(16)
    p_c2_h.font.bold = True
    p_c2_h.font.color.rgb = COLOR_GOLD

    contacts = [
        ("🌐 Demo Activa", "http://localhost:3001"),
        ("🚀 Landing & Leads", "http://localhost:3001/landing"),
        ("🛠️ API Swagger Docs", "http://localhost:8000/docs"),
        ("📩 Contacto Directo", "contacto@trama-intelligence.io"),
        ("🤝 Modalidad", "Piloto PoC sin costo para proyectos calificados"),
    ]
    for c_label, c_val in contacts:
        pct = tf_c2.add_paragraph()
        pct.text = c_label
        pct.font.size = Pt(13)
        pct.font.bold = True
        pct.font.color.rgb = TEXT_WHITE
        pct.space_before = Pt(8)

        pcv = tf_c2.add_paragraph()
        pcv.text = c_val
        pcv.font.size = Pt(11)
        pcv.font.color.rgb = COLOR_CYAN
        pcv.space_before = Pt(2)

    return prs


if __name__ == "__main__":
    from pathlib import Path
    prs = create_presentation()
    out_dir = str(Path(__file__).resolve().parent.parent.parent / "docs")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "TRAMA_Presentacion_Comercial.pptx")
    prs.save(out_file)
    print(f"Presentación actualizada en: {out_file}")

    artifact_dir = "/home/djfa/.gemini/antigravity-cli/brain/41c7c876-ad9a-4f8c-98d2-a43386da4181"
    os.makedirs(artifact_dir, exist_ok=True)
    artifact_file = os.path.join(artifact_dir, "TRAMA_Presentacion_Comercial.pptx")
    prs.save(artifact_file)
    print(f"Copia en artefactos: {artifact_file}")
