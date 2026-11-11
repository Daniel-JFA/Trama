"use client";

import { useState } from "react";
import Link from "next/link";

export default function LandingPage({ onOpenApp }) {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    company: "",
    role: "PR / Asuntos Públicos",
    use_case: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.email || !formData.name) return;

    setSubmitting(true);
    setError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/leads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Error al registrar solicitud" }));
        throw new Error(err.detail || "Error en el servidor");
      }
      setSubmitted(true);
    } catch (err) {
      setError(err.message || "No se pudo enviar la solicitud. Intenta nuevamente.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="landing-root">
      {/* ─── Header / Navigation ─────────────────────────────────────────── */}
      <header className="landing-nav">
        <div className="landing-nav-inner">
          <div className="landing-brand">
            <span className="brand-logo">🕸️</span>
            <span className="brand-text">TRAMA</span>
            <span className="brand-badge">INTEL v0.2</span>
          </div>
          <nav className="landing-links">
            <a href="#solucion">Solución</a>
            <a href="#casos">Casos de Uso</a>
            <a href="#precios">Precios</a>
            <a href="#auditoria" className="nav-btn-highlight">
              Auditoría Gratuita
            </a>
            {onOpenApp ? (
              <button className="nav-btn-app" onClick={onOpenApp}>
                Abrir App ➔
              </button>
            ) : (
              <Link href="/" className="nav-btn-app">
                Abrir App ➔
              </Link>
            )}
          </nav>
        </div>
      </header>

      {/* ─── Hero Section ────────────────────────────────────────────────── */}
      <section className="landing-hero">
        <div className="hero-badge">
          <span>⚡ Nuevo: Motor Forense de Comportamiento Inauténtico (CIB)</span>
        </div>
        <h1 className="hero-title">
          Ver lo invisible.<br />
          <span className="hero-title-gradient">Desarma la manipulación en redes</span><br />
          antes de que se vuelva viral.
        </h1>
        <p className="hero-subtitle">
          Transforma miles de interacciones en grafos forenses interactivos. Detecta granjas de bots, 
          rastrea cuentas puente y descubre operaciones de <i>astroturfing</i> con evidencia matemática irrefutable.
        </p>

        <div className="hero-actions">
          {onOpenApp ? (
            <button className="btn-hero-primary" onClick={onOpenApp}>
              🚀 Explorar Sandbox en Vivo
            </button>
          ) : (
            <Link href="/" className="btn-hero-primary">
              🚀 Explorar Sandbox en Vivo
            </Link>
          )}
          <a href="#auditoria" className="btn-hero-secondary">
            🔍 Solicitar Auditoría de Red
          </a>
        </div>

        {/* Hero KPI strip */}
        <div className="hero-kpis">
          <div className="hero-kpi-item">
            <span className="hero-kpi-val">&lt; 60s</span>
            <span className="hero-kpi-lbl">Tiempo de análisis por grafo</span>
          </div>
          <div className="hero-kpi-sep" />
          <div className="hero-kpi-item">
            <span className="hero-kpi-val">94%</span>
            <span className="hero-kpi-lbl">Precisión en detección de ráfagas CIB</span>
          </div>
          <div className="hero-kpi-sep" />
          <div className="hero-kpi-item">
            <span className="hero-kpi-val">100%</span>
            <span className="hero-kpi-lbl">Exportable a Gephi y PDF ejecutivo</span>
          </div>
        </div>
      </section>

      {/* ─── Problem vs Solution ─────────────────────────────────────────── */}
      <section id="solucion" className="landing-section">
        <div className="section-header">
          <span className="section-tag">EL PROBLEMA vs. LA SOLUCIÓN</span>
          <h2 className="section-title">El monitoreo tradicional de palabras clave ya no basta</h2>
          <p className="section-desc">
            El *social listening* tradicional cuenta menciones pero es ciego a la estructura. TRAMA revela quién controla realmente la conversación.
          </p>
        </div>

        <div className="comparison-grid">
          <div className="comp-column comp-column-bad">
            <h3 className="comp-col-title">❌ Social Listening Tradicional</h3>
            <ul className="comp-list">
              <li>Cuenta volumen bruto sin distinguir cuentas orgánicas de bots.</li>
              <li>Genera pánico por falsas tendencias orquestadas por la competencia.</li>
              <li>No explica cómo viajan los mensajes entre comunidades enfrentadas.</li>
              <li>Informes basados en capturas desordenadas difíciles de defender.</li>
            </ul>
          </div>

          <div className="comp-column comp-column-good">
            <div className="comp-col-badge">INTELIGENCIA TRAMA</div>
            <h3 className="comp-col-title">✅ Inteligencia Estructural de Grafos</h3>
            <ul className="comp-list">
              <li><b>Algoritmo Louvain:</b> Segmenta comunidades automáticamente por afinidad.</li>
              <li><b>Motor Forense CIB:</b> Identifica ráfagas sincronizadas y sufijos numéricos.</li>
              <li><b>Cuentas Puente:</b> Aísla a los intermediarios que cruzan narrativas.</li>
              <li><b>Informes Ejecutivos:</b> Resúmenes con hallazgos clasificados por severidad.</li>
            </ul>
          </div>
        </div>
      </section>

      {/* ─── Features Grid ───────────────────────────────────────────────── */}
      <section id="casos" className="landing-section">
        <div className="section-header">
          <span className="section-tag">CAPACIDADES FORENSES</span>
          <h2 className="section-title">Tecnología de grafos diseñada para investigación rigurosa</h2>
        </div>

        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon" style={{ background: "rgba(139, 124, 246, 0.15)", color: "#8B7CF6" }}>
              🕸️
            </div>
            <h3 className="feature-title">Grafo Interactivo 2D con Física Elástica</h3>
            <p className="feature-desc">
              Visualiza miles de conexiones con simulación `d3-force`, nubes ambientales de comunidad y arrastre libre de perfiles.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon" style={{ background: "rgba(224, 96, 184, 0.15)", color: "#E060B8" }}>
              🤖
            </div>
            <h3 className="feature-title">Detección Forense de Astroturfing (CIB)</h3>
            <p className="feature-desc">
              Puntaje de 0 a 100 evaluando sincronización horaria, entropía de nombres, ratio posts/seguidores y topología en abanico.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon" style={{ background: "rgba(90, 209, 179, 0.15)", color: "#5AD1B3" }}>
              ⏳
            </div>
            <h3 className="feature-title">Línea de Tiempo y Time-Travel</h3>
            <p className="feature-desc">
              Reproduce la evolución histórica semana a semana para descubrir el momento exacto en que se activó la operación coordinada.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon" style={{ background: "rgba(232, 193, 90, 0.15)", color: "#E8C15A" }}>
              ⚖️
            </div>
            <h3 className="feature-title">Auditoría de Solapamiento Jaccard</h3>
            <p className="feature-desc">
              Compara perfiles e influencers para descubrir audiencias redundantes o alianzas no declaradas con diagramas de Venn interactivos.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon" style={{ background: "rgba(139, 124, 246, 0.15)", color: "#8B7CF6" }}>
              📄
            </div>
            <h3 className="feature-title">Informes Ejecutivos en 1 Clic</h3>
            <p className="feature-desc">
              Genera reportes de inteligencia estructurados con metodología transparente, listos para imprimir o presentar a clientes y directores.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon" style={{ background: "rgba(90, 209, 179, 0.15)", color: "#5AD1B3" }}>
              📥
            </div>
            <h3 className="feature-title">Importación Flexible CSV e Instagram</h3>
            <p className="feature-desc">
              Importa cualquier red con formato `source,target` o procesa descargas de datos de Instagram con scripts listos para usar.
            </p>
          </div>
        </div>
      </section>

      {/* ─── Pricing Section ─────────────────────────────────────────────── */}
      <section id="precios" className="landing-section">
        <div className="section-header">
          <span className="section-tag">PLANES Y PRECIOS</span>
          <h2 className="section-title">Invierte en claridad estructural</h2>
          <p className="section-desc">
            Acceso anticipado para las primeras 50 agencias y redacciones con 40% de descuento vitalicio.
          </p>
        </div>

        <div className="pricing-grid">
          {/* Investigator */}
          <div className="pricing-card">
            <h3 className="pricing-tier-name">Investigator</h3>
            <div className="pricing-price">
              <span className="price-curr">$</span>
              <span className="price-amount">49</span>
              <span className="price-period">/ mes</span>
            </div>
            <p className="pricing-tagline">Para periodistas independientes y analistas OSINT.</p>
            <ul className="pricing-features">
              <li>✓ Hasta 5 investigaciones activas</li>
              <li>✓ Hasta 5,000 nodos por grafo</li>
              <li>✓ Detección forense CIB básica</li>
              <li>✓ Exportación de capturas PNG HD</li>
              <li>✓ Importación CSV ilimitada</li>
            </ul>
            <a href="#auditoria" className="btn-pricing btn-pricing-ghost">
              Comenzar prueba
            </a>
          </div>

          {/* Pro (Featured) */}
          <div className="pricing-card pricing-card-featured">
            <div className="pricing-badge">MÁS POPULAR — FOUNDER DEAL</div>
            <h3 className="pricing-tier-name">Pro Agency</h3>
            <div className="pricing-price">
              <span className="price-curr">$</span>
              <span className="price-amount">199</span>
              <span className="price-period">/ mes</span>
            </div>
            <p className="pricing-tagline">Para agencias de PR, consultoras y salas de redacción.</p>
            <ul className="pricing-features">
              <li>✓ Investigaciones y proyectos ilimitados</li>
              <li>✓ Hasta 50,000 nodos por grafo</li>
              <li>✓ <b>Motor CIB multidimensional completo</b></li>
              <li>✓ <b>Informes Ejecutivos de Inteligencia</b></li>
              <li>✓ <b>Exportación GEXF para Gephi</b></li>
              <li>✓ Análisis de solapamiento Jaccard</li>
              <li>✓ Soporte prioritario por email y chat</li>
            </ul>
            <a href="#auditoria" className="btn-pricing btn-pricing-primary">
              Obtener 40% Off Vitalicio
            </a>
          </div>

          {/* Enterprise */}
          <div className="pricing-card">
            <h3 className="pricing-tier-name">Enterprise</h3>
            <div className="pricing-price">
              <span className="price-curr">$</span>
              <span className="price-amount">699</span>
              <span className="price-period">/ mes</span>
            </div>
            <p className="pricing-tagline">Para corporaciones, partidos políticos y gobiernos.</p>
            <ul className="pricing-features">
              <li>✓ Capacidad de nodos y proyectos ilimitada</li>
              <li>✓ Informes con <b>Marca Blanca (White-label)</b></li>
              <li>✓ Conector para X API v2 y fuentes custom</li>
              <li>✓ Despliegue en servidor privado on-premise</li>
              <li>✓ SLA 99.9% y gestor de cuenta dedicado</li>
            </ul>
            <a href="#auditoria" className="btn-pricing btn-pricing-ghost">
              Contactar Ventas
            </a>
          </div>
        </div>
      </section>

      {/* ─── Lead Capture Form ────────────────────────────────────────────── */}
      <section id="auditoria" className="landing-section landing-lead-section">
        <div className="lead-card">
          <div className="lead-left">
            <span className="section-tag" style={{ color: "#5AD1B3" }}>AUDITORÍA DE RED GRATUITA</span>
            <h2 className="lead-title">¿Sospechas de un ataque coordinado o quieres auditar una tendencia?</h2>
            <p className="lead-desc">
              Envíanos el tema o hashtag que quieres analizar. Nuestro equipo procesará los datos en TRAMA y te entregará 
              un mapa interactivo y un informe ejecutivo en menos de 24 horas sin costo.
            </p>
            <div className="lead-trust">
              <span>🔒 Datos 100% confidenciales bajo acuerdo de no divulgación.</span>
            </div>
          </div>

          <div className="lead-right">
            {submitted ? (
              <div className="lead-success-box">
                <div className="lead-success-icon">✅</div>
                <h3 className="lead-success-title">¡Solicitud recibida con éxito!</h3>
                <p className="lead-success-desc">
                  Nos pondremos en contacto contigo en <b>{formData.email}</b> en las próximas horas para coordinar tu auditoría.
                </p>
                {onOpenApp ? (
                  <button className="btn-hero-primary" onClick={onOpenApp} style={{ marginTop: "16px" }}>
                    Ir a la App mientras tanto
                  </button>
                ) : (
                  <Link href="/" className="btn-hero-primary" style={{ marginTop: "16px" }}>
                    Ir a la App mientras tanto
                  </Link>
                )}
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="lead-form">
                <h3 className="lead-form-title">Solicitar Auditoría & Acceso Pro</h3>
                
                <div className="form-group">
                  <label className="form-label">Tu nombre completo *</label>
                  <input
                    type="text"
                    required
                    placeholder="Ej. Sofía Mendoza"
                    className="form-input"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Correo electrónico profesional *</label>
                  <input
                    type="email"
                    required
                    placeholder="sofia@agencia.com"
                    className="form-input"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  />
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Empresa / Medio</label>
                    <input
                      type="text"
                      placeholder="Ej. Crisis Comms Latam"
                      className="form-input"
                      value={formData.company}
                      onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Tu rol</label>
                    <select
                      className="form-input"
                      value={formData.role}
                      onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                    >
                      <option value="PR / Asuntos Públicos">PR / Asuntos Públicos</option>
                      <option value="Periodista / Editor">Periodista / Editor</option>
                      <option value="Brand Safety / Marketing">Brand Safety / Marketing</option>
                      <option value="Consultor Político">Consultor Político</option>
                      <option value="Investigador OSINT">Investigador OSINT</option>
                    </select>
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Tema o hashtag a auditar</label>
                  <input
                    type="text"
                    placeholder="Ej. #ReformaTributaria o @CuentaObjetivo"
                    className="form-input"
                    value={formData.use_case}
                    onChange={(e) => setFormData({ ...formData, use_case: e.target.value })}
                  />
                </div>

                {error && <div className="form-error">{error}</div>}

                <button type="submit" className="btn-form-submit" disabled={submitting}>
                  {submitting ? "Procesando solicitud..." : "Solicitar Auditoría Gratuita ➔"}
                </button>
              </form>
            )}
          </div>
        </div>
      </section>

      {/* ─── Footer ──────────────────────────────────────────────────────── */}
      <footer className="landing-footer">
        <div className="landing-footer-inner">
          <div className="footer-left">
            <span className="brand-text">TRAMA</span>
            <p className="footer-tagline">
              Mapeo de conversaciones y detección de astroturfing para toma de decisiones críticas.
            </p>
          </div>
          <div className="footer-right">
            <span>© 2026 TRAMA Analytics. Todos los derechos reservados.</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
