"""Gráficos SVG hechos a mano y reporte HTML autocontenido.

Sin matplotlib, sin JS, sin CDN: el HTML final se abre offline y se ve igual.
"""

from __future__ import annotations

import html
import math
from datetime import datetime
from pathlib import Path

#: Paleta para las series del gráfico de líneas.
PALETA = ["#5eead4", "#fbbf24", "#f472b6", "#93c5fd", "#c4b5fd", "#fca5a5"]

ANCHO = 860
FILA = 46
MARGEN_IZQ = 210
MARGEN_DER = 130


def formatear_pesos(valor: float | int | None) -> str:
    """Abrevía un monto en pesos: ``$ 1,85 M``, ``$ 950 K``, ``$ 120``."""
    if valor is None:
        return "s/d"
    valor = float(valor)
    if abs(valor) >= 1_000_000:
        return f"$ {valor / 1_000_000:.2f} M".replace(".", ",")
    if abs(valor) >= 1_000:
        return f"$ {valor / 1_000:.0f} K"
    return f"$ {valor:.0f}"


def formatear_numero(valor: float | int | None) -> str:
    """Formato argentino con punto de miles."""
    if valor is None:
        return "s/d"
    return f"{int(round(valor)):,}".replace(",", ".")


def _escapar(texto: object) -> str:
    return html.escape(str(texto), quote=True)


def _achicar(texto: str, limite: int = 26) -> str:
    return texto if len(texto) <= limite else texto[: limite - 1] + "…"


# --------------------------------------------------------------------------
# Gráfico de barras: mediana por rubro
# --------------------------------------------------------------------------


def svg_barras(rubros: list[dict]) -> str:
    """Barras horizontales con la mediana por rubro, ordenadas de mayor a menor."""
    datos = [r for r in rubros if r.get("mediana")]
    if not datos:
        return _svg_vacio("Sin rubros con datos suficientes para graficar.")

    datos = sorted(datos, key=lambda r: r["mediana"], reverse=True)
    maximo = max(r["mediana"] for r in datos) or 1
    ancho_barra = ANCHO - MARGEN_IZQ - MARGEN_DER
    alto = len(datos) * FILA + 40

    partes = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ANCHO} {alto}" '
        f'role="img" aria-label="Mediana salarial por rubro" class="grafico">',
        '<text x="0" y="14" class="eje-titulo">Mediana mensual por rubro (pesos)</text>',
    ]

    for i, rubro in enumerate(datos):
        y = 34 + i * FILA
        mediana = rubro["mediana"]
        largo = max(3.0, ancho_barra * mediana / maximo)
        n = rubro.get("n", 0)
        partes.append(
            f'<text x="0" y="{y + 16}" class="etiqueta-rubro">'
            f"{_escapar(_achicar(rubro.get('nombre') or rubro['id']))}</text>"
        )
        partes.append(
            f'<rect x="{MARGEN_IZQ}" y="{y}" width="{largo:.1f}" height="22" '
            f'rx="4" fill="#5eead4" opacity="0.85"></rect>'
        )
        partes.append(
            f'<text x="{MARGEN_IZQ + largo + 10:.1f}" y="{y + 16}" class="etiqueta-valor">'
            f"{_escapar(formatear_pesos(mediana))}</text>"
        )
        partes.append(
            f'<text x="{MARGEN_IZQ + largo + 10:.1f}" y="{y + 30}" class="etiqueta-n">n={n}</text>'
        )

    partes.append("</svg>")
    return "\n".join(partes)


# --------------------------------------------------------------------------
# Gráfico de líneas: evolución histórica
# --------------------------------------------------------------------------


def svg_linea(historico: dict, max_series: int = 4) -> str | None:
    """Evolución de la mediana por rubro. ``None`` si hay menos de 2 corridas."""
    corridas = historico.get("corridas") or []
    if len(corridas) < 2:
        return None

    fechas = [c["fecha"] for c in corridas]
    series: dict[str, dict[str, float]] = {}
    pesos: dict[str, int] = {}
    for corrida in corridas:
        for rubro in corrida.get("rubros", []):
            if rubro.get("mediana") is None:
                continue
            series.setdefault(rubro["id"], {})[corrida["fecha"]] = rubro["mediana"]
            pesos[rubro["id"]] = pesos.get(rubro["id"], 0) + rubro.get("n", 0)

    completas = {k: v for k, v in series.items() if len(v) >= 2}
    if not completas:
        return None
    elegidas = sorted(completas, key=lambda k: pesos.get(k, 0), reverse=True)[:max_series]

    alto, margen_sup, margen_inf = 320, 30, 46
    ancho_util = ANCHO - 70
    todos = [v for k in elegidas for v in completas[k].values()]
    y_min, y_max = min(todos), max(todos)
    if y_max == y_min:
        y_max = y_min + 1

    def x(i: int) -> float:
        if len(fechas) == 1:
            return 20.0
        return 20 + ancho_util * i / (len(fechas) - 1)

    def y(valor: float) -> float:
        return (
            alto - margen_inf - (alto - margen_sup - margen_inf) * (valor - y_min) / (y_max - y_min)
        )

    partes = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ANCHO} {alto}" '
        f'role="img" aria-label="Evolución de la mediana salarial" class="grafico">',
        '<text x="0" y="14" class="eje-titulo">Evolución de la mediana por rubro</text>',
        f'<line x1="20" y1="{alto - margen_inf}" x2="{20 + ancho_util}" '
        f'y2="{alto - margen_inf}" stroke="#334155" stroke-width="1"></line>',
    ]

    for idx, rubro_id in enumerate(elegidas):
        color = PALETA[idx % len(PALETA)]
        puntos = [(f, completas[rubro_id][f]) for f in fechas if f in completas[rubro_id]]
        camino = " ".join(
            f"{'M' if j == 0 else 'L'}{x(fechas.index(f)):.1f},{y(v):.1f}"
            for j, (f, v) in enumerate(puntos)
        )
        partes.append(
            f'<path d="{camino}" fill="none" stroke="{color}" stroke-width="2.5" '
            f'stroke-linejoin="round" stroke-linecap="round"></path>'
        )
        for f, v in puntos:
            partes.append(
                f'<circle cx="{x(fechas.index(f)):.1f}" cy="{y(v):.1f}" r="4" fill="{color}"></circle>'
            )
        partes.append(
            f'<text x="{24 + ancho_util}" y="{margen_sup + 14 + idx * 18}" '
            f'class="leyenda" fill="{color}">{_escapar(rubro_id)}</text>'
        )

    for i, fecha in enumerate(fechas):
        partes.append(
            f'<text x="{x(i):.1f}" y="{alto - 22}" class="etiqueta-fecha" '
            f'text-anchor="middle">{_escapar(fecha)}</text>'
        )

    partes.append(
        f'<text x="0" y="{y(y_max) + 4:.1f}" class="etiqueta-n">'
        f"{_escapar(formatear_pesos(y_max))}</text>"
    )
    partes.append("</svg>")
    return "\n".join(partes)


def _svg_vacio(mensaje: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ANCHO} 120" '
        f'role="img" aria-label="Sin datos" class="grafico">'
        f'<text x="0" y="60" class="etiqueta-n">{_escapar(mensaje)}</text></svg>'
    )


# --------------------------------------------------------------------------
# Reporte HTML
# --------------------------------------------------------------------------

_CSS = """
:root {
  color-scheme: dark;
  --fondo: #0b1120;
  --panel: #131c31;
  --panel-2: #1b2540;
  --borde: #26314f;
  --texto: #e6edf7;
  --tenue: #94a3b8;
  --acento: #5eead4;
  --alerta: #fbbf24;
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 2.5rem 1.25rem 4rem;
  background: var(--fondo); color: var(--texto);
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  line-height: 1.55;
}
main { max-width: 960px; margin: 0 auto; }
header h1 { font-size: 1.9rem; margin: 0 0 .35rem; letter-spacing: -.02em; }
header p { color: var(--tenue); margin: 0; font-size: .95rem; }
h2 { font-size: 1.15rem; margin: 2.5rem 0 .9rem; letter-spacing: -.01em; }
h2::before {
  content: ""; display: inline-block; width: 3px; height: .95em;
  background: var(--acento); border-radius: 2px;
  margin-right: .55rem; vertical-align: -.08em;
}
.tarjetas { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-top: 1.75rem; }
.tarjeta { background: var(--panel); border: 1px solid var(--borde); border-radius: 12px; padding: 1.1rem 1.2rem; }
.tarjeta .rotulo { color: var(--tenue); font-size: .78rem; text-transform: uppercase; letter-spacing: .08em; }
.tarjeta .valor { font-size: 1.65rem; font-weight: 650; margin-top: .3rem; letter-spacing: -.02em; }
.tarjeta .nota { color: var(--tenue); font-size: .82rem; margin-top: .2rem; }
.panel { background: var(--panel); border: 1px solid var(--borde); border-radius: 12px; padding: 1.25rem; overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: .92rem; }
th, td { text-align: right; padding: .55rem .6rem; border-bottom: 1px solid var(--borde); white-space: nowrap; }
th:first-child, td:first-child { text-align: left; }
thead th { color: var(--tenue); font-weight: 600; font-size: .78rem; text-transform: uppercase; letter-spacing: .06em; }
tbody tr:hover { background: var(--panel-2); }
tbody tr:last-child td { border-bottom: 0; }
.grafico { width: 100%; height: auto; display: block; }
.eje-titulo { fill: var(--tenue); font-size: 12px; font-family: system-ui, sans-serif; }
.etiqueta-rubro { fill: var(--texto); font-size: 13px; font-family: system-ui, sans-serif; }
.etiqueta-valor { fill: var(--acento); font-size: 13px; font-weight: 600; font-family: system-ui, sans-serif; }
.etiqueta-n { fill: var(--tenue); font-size: 11px; font-family: system-ui, sans-serif; }
.etiqueta-fecha { fill: var(--tenue); font-size: 11px; font-family: system-ui, sans-serif; }
.eje-valor { fill: var(--tenue); font-size: 11px; font-family: system-ui, sans-serif; }
.leyenda { fill: var(--tenue); font-size: 11px; font-family: system-ui, sans-serif; }
.aviso { border-left: 3px solid var(--alerta); background: #1f1a10; padding: .8rem 1rem; border-radius: 0 8px 8px 0; color: #fde68a; font-size: .9rem; }
.muestra { display: inline-block; margin-left: .4rem; padding: .05rem .4rem; border-radius: 999px; background: #2a2312; color: #fbbf24; font-size: .68rem; text-transform: uppercase; letter-spacing: .05em; vertical-align: .1em; }
ul, ol { padding-left: 1.2rem; }
li { margin: .35rem 0; }
a { color: var(--acento); text-decoration: none; border-bottom: 1px solid #5eead440; }
a:hover { border-bottom-color: var(--acento); }
footer { margin-top: 3rem; padding-top: 1.25rem; border-top: 1px solid var(--borde); color: var(--tenue); font-size: .85rem; }
code { background: var(--panel-2); padding: .1rem .35rem; border-radius: 4px; font-size: .88em; }
@media (max-width: 640px) { body { padding: 1.5rem .9rem 3rem; } header h1 { font-size: 1.45rem; } }
"""


def _tabla_rubros(rubros: list[dict]) -> str:
    if not rubros:
        return '<p class="aviso">No se recolectaron avisos con salario en esta corrida.</p>'
    filas = []
    for rubro in sorted(rubros, key=lambda r: r.get("mediana") or 0, reverse=True):
        suficiente = rubro.get("suficiente", True)
        nombre = _escapar(rubro.get("nombre") or rubro["id"])
        if not suficiente and rubro.get("mediana"):
            nombre += ' <span class="muestra" title="Menos de 5 avisos: tomalo como referencia, no como mediana firme">muestra chica</span>'
        filas.append(
            "<tr>"
            f"<td>{nombre}</td>"
            f"<td>{rubro.get('ofertas', rubro.get('n', 0))}</td>"
            f"<td>{rubro.get('con_salario', rubro.get('n', 0))}</td>"
            f"<td>{rubro.get('n', 0)}</td>"
            f"<td>{_escapar(formatear_pesos(rubro.get('mediana')))}</td>"
            f"<td>{_escapar(formatear_pesos(rubro.get('p25')))}</td>"
            f"<td>{_escapar(formatear_pesos(rubro.get('p75')))}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr>"
        "<th>Rubro</th><th>Ofertas</th><th>Con sueldo</th><th>Utilizables</th>"
        "<th>Mediana</th><th>P25</th><th>P75</th>"
        "</tr></thead><tbody>" + "".join(filas) + "</tbody></table>"
    )


def svg_series_indec(series: list[dict]) -> str:
    """Líneas de las series de índice del INDEC (base 2016=100)."""
    indices = [s for s in series if s.get("tipo") == "indice" and s.get("serie")]
    if not indices:
        return _svg_vacio("Sin series de índice para graficar.")

    fechas = sorted({f for s in indices for f in s["serie"]})[-72:]
    if len(fechas) < 2:
        return _svg_vacio("Las series oficiales tienen muy pocos puntos.")

    valores = [float(s["serie"][f]) for s in indices for f in fechas if f in s["serie"]]
    y_min, y_max = min(valores), max(valores)
    if y_max == y_min:
        y_max = y_min + 1

    # Escala "linda": paso redondo y extremos múltiplos del paso, para que las
    # etiquetas del eje no queden en valores raros.
    bruto = max((y_max - y_min) / 4, 1)
    magnitud = 10 ** math.floor(math.log10(bruto))
    paso = magnitud
    for factor in (1, 2, 2.5, 5, 10):
        paso = factor * magnitud
        if paso >= bruto:
            break
    y_min = math.floor(y_min / paso) * paso
    y_max = math.ceil(y_max / paso) * paso
    lineas = max(1, int(round((y_max - y_min) / paso)))

    alto = 320
    margen_izq, margen_der = 52, 168
    margen_sup, margen_inf = 26, 34
    ancho_util = ANCHO - margen_izq - margen_der

    def x(i: int) -> float:
        return margen_izq + ancho_util * i / (len(fechas) - 1)

    def y(valor: float) -> float:
        return (
            alto - margen_inf - (alto - margen_sup - margen_inf) * (valor - y_min) / (y_max - y_min)
        )

    partes = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ANCHO} {alto}" '
        f'role="img" aria-label="Índice de salarios del INDEC" class="grafico">',
        '<text x="0" y="14" class="eje-titulo">Índice de salarios (base 2016 = 100)</text>',
    ]

    for k in range(lineas + 1):
        valor = y_min + paso * k
        partes.append(
            f'<line x1="{margen_izq}" y1="{y(valor):.1f}" x2="{margen_izq + ancho_util}" '
            f'y2="{y(valor):.1f}" stroke="#1e293b" stroke-width="1"></line>'
        )
        partes.append(
            f'<text x="{margen_izq - 8}" y="{y(valor) + 4:.1f}" '
            f'text-anchor="end" class="eje-valor">{_escapar(formatear_numero(valor))}</text>'
        )

    for idx, serie in enumerate(indices):
        color = PALETA[idx % len(PALETA)]
        puntos = [(i, f) for i, f in enumerate(fechas) if f in serie["serie"]]
        camino = " ".join(
            f"{'M' if j == 0 else 'L'}{x(i):.1f},{y(float(serie['serie'][f])):.1f}"
            for j, (i, f) in enumerate(puntos)
        )
        partes.append(
            f'<path d="{camino}" fill="none" stroke="{color}" stroke-width="2.2" '
            f'stroke-linejoin="round" stroke-linecap="round"></path>'
        )
        alto_leyenda = margen_sup + 18 * idx
        partes.append(
            f'<line x1="{margen_izq + ancho_util + 12}" y1="{alto_leyenda}" '
            f'x2="{margen_izq + ancho_util + 30}" y2="{alto_leyenda}" '
            f'stroke="{color}" stroke-width="2.5"></line>'
        )
        partes.append(
            f'<text x="{margen_izq + ancho_util + 36}" y="{alto_leyenda + 4}" '
            f'class="leyenda">{_escapar(_achicar(serie.get("nombre") or "", 24))}</text>'
        )

    for i in (0, len(fechas) // 2, len(fechas) - 1):
        partes.append(
            f'<text x="{x(i):.1f}" y="{alto - 12}" text-anchor="middle" '
            f'class="eje-valor">{_escapar(fechas[i][:7])}</text>'
        )

    partes.append("</svg>")
    return "".join(partes)


def _seccion_indec(indec: dict) -> str:
    series = indec.get("series") or []
    if not series:
        motivos = indec.get("faltantes") or [indec.get("motivo", "sin datos")]
        return (
            '<p class="aviso">Las series oficiales no están disponibles en esta '
            f"corrida: {_escapar('; '.join(str(m) for m in motivos))}.</p>"
        )

    filas = []
    for serie in series:
        ultimo = serie.get("ultimo")
        if serie.get("tipo") == "pesos":
            valor = formatear_pesos(ultimo)
            nota = "en pesos"
        else:
            valor = formatear_numero(ultimo)
            nota = "índice"
        variacion = serie.get("variacion_12m_pct")
        variacion_txt = f"{variacion:+.1f}%" if isinstance(variacion, (int, float)) else "—"
        filas.append(
            "<tr>"
            f"<td>{_escapar(serie.get('nombre') or serie.get('id'))}"
            f'<br><span style="color:var(--tenue);font-size:.78rem">'
            f"<code>{_escapar(serie.get('id'))}</code></span></td>"
            f'<td>{_escapar(valor)} <span style="color:var(--tenue)">{nota}</span></td>'
            f"<td>{_escapar(serie.get('hasta'))}</td>"
            f"<td>{_escapar(variacion_txt)}</td>"
            "</tr>"
        )

    tabla = (
        "<table><thead><tr><th>Serie oficial</th><th>Último dato</th>"
        "<th>Período</th><th>Var. interanual</th></tr></thead><tbody>"
        + "".join(filas)
        + "</tbody></table>"
    )

    faltantes = indec.get("faltantes") or []
    nota_faltantes = (
        f'<p style="color:var(--tenue)">Series omitidas: '
        f"{_escapar('; '.join(str(m) for m in faltantes))}.</p>"
        if faltantes
        else ""
    )

    return (
        '<div class="panel">'
        f"{tabla}"
        f"{svg_series_indec(series)}"
        f"{nota_faltantes}"
        '<p style="margin-bottom:0;color:var(--tenue)">Fuente: '
        f'<a href="{_escapar(indec.get("url_catalogo"))}">INDEC vía datos.gob.ar</a>. '
        "El índice (base 2016 = 100) mide evolución, no nivel en pesos. La "
        "remuneración promedio sí está en pesos y corresponde a todo el sector "
        "privado registrado, no solo a tecnología: sirve como piso de "
        "comparación, no como sueldo tech.</p>"
        "</div>"
    )


def generar_html(
    sueldos: dict,
    historico: dict,
    indec: dict,
    generado: datetime | None = None,
) -> str:
    """Arma el HTML autocontenido del observatorio."""
    generado = generado or datetime.now()
    rubros = sueldos.get("rubros", [])
    descartados = sueldos.get("descartados", {})
    total_avisos = sum(r.get("n", 0) for r in rubros)

    mediana_general = sueldos.get("mediana_general")
    transparencia = sueldos.get("transparencia", {})
    ofertas = transparencia.get("ofertas_unicas") or 0
    declaran = transparencia.get("declaran_salario") or 0
    plausibles = transparencia.get("monto_plausible") or 0
    pct_declaran = transparencia.get("declaran_salario_pct") or 0.0
    pct_plausible = transparencia.get("monto_plausible_pct") or 0.0
    busquedas = (sueldos.get("resumen_corrida") or {}).get("terminos_consultados") or 0
    sin_datos = (sueldos.get("resumen_corrida") or {}).get("terminos_sin_datos") or []
    repetidos = transparencia.get("montos_repetidos") or []
    descartados_monto = max(0, declaran - plausibles)

    # Si alguna búsqueda no devolvió nada, se dice: una corrida parcial no puede
    # parecer completa.
    nota_parcial = (
        f" Además, {len(sin_datos)} de las {busquedas} búsquedas no devolvieron avisos "
        "en esta corrida, así que la muestra es parcial."
        if sin_datos
        else ""
    )

    # Los ejemplos salen solo de lo que se observó en esta corrida: si no hubo
    # montos repetidos, no se inventan números de relleno.
    if repetidos:
        razon = (
            "El resto repite valores de relleno como "
            + ", ".join(f"<code>{formatear_numero(m)}</code>" for m in repetidos[:3])
            + ". "
        )
    elif descartados_monto:
        razon = "El resto no declara un monto comparable (rangos, “a convenir” o valores fuera de rango). "
    else:
        razon = ""

    tarjetas = [
        (
            "Ofertas relevadas",
            formatear_numero(ofertas),
            f"avisos únicos en {busquedas} búsquedas",
        ),
        (
            "Publican sueldo",
            f"{pct_declaran:.0f}%",
            f"{formatear_numero(declaran)} de {formatear_numero(ofertas)} ofertas",
        ),
        (
            "Monto utilizable",
            f"{pct_plausible:.0f}%",
            f"{formatear_numero(plausibles)} de {formatear_numero(declaran)} con sueldo",
        ),
        (
            "Mediana general",
            formatear_pesos(mediana_general),
            f"{sueldos.get('n_general', total_avisos)} avisos únicos",
        ),
    ]

    hallazgo = (
        '<p class="aviso"><strong>El dato que importa:</strong> de '
        f"{formatear_numero(declaran)} ofertas que declaran un sueldo, "
        f"{formatear_numero(plausibles)} publican un monto que se puede usar "
        f"({pct_plausible:.0f}%). "
        f"{razon}"
        f"{nota_parcial} "
        "Por eso la tabla muestra pocos rubros con muestra suficiente: no es "
        "un error de scraping, es cómo se publica el salario en Argentina."
        "</p>"
    )
    tarjetas_html = "".join(
        f'<div class="tarjeta"><div class="rotulo">{_escapar(rotulo)}</div>'
        f'<div class="valor">{_escapar(valor)}</div>'
        f'<div class="nota">{_escapar(nota)}</div></div>'
        for rotulo, valor, nota in tarjetas
    )

    linea = svg_linea(historico)
    grafico_linea = (
        f'<h2>Evolución histórica</h2><div class="panel">{linea}</div>'
        if linea
        else '<h2>Evolución histórica</h2><p class="aviso">Se necesitan al menos '
        "dos corridas en días distintos para dibujar la serie.</p>"
    )

    fuentes = [
        (
            "Computrabajo Argentina — avisos con salario publicado",
            "https://ar.computrabajo.com/",
            "Listados públicos <code>/trabajo-de-&lt;termino&gt;</code>. Son avisos "
            "publicados por empresas, no encuestas ni liquidaciones reales.",
        ),
        (
            "INDEC — Índice de Salarios y remuneración promedio (vía datos.gob.ar)",
            "https://datos.gob.ar/series/api/search/?q=indice%20de%20salarios",
            "Cinco series oficiales mensuales: índice total, privado registrado, "
            "público, privado no registrado y remuneración bruta promedio del "
            "sector privado registrado (en pesos).",
        ),
    ]
    fuentes_html = "".join(
        f'<li><a href="{_escapar(url)}">{_escapar(nombre)}</a><br>'
        f'<span style="color:var(--tenue)">{detalle}</span></li>'
        for nombre, url, detalle in fuentes
    )

    return f"""<!DOCTYPE html>
<html lang="es-AR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Observatorio de sueldos tech · Argentina</title>
<style>{_CSS}</style>
</head>
<body>
<main>
<header>
  <h1>Observatorio de sueldos tech · Argentina</h1>
  <p>Generado el {_escapar(generado.strftime("%d/%m/%Y %H:%M"))} · datos de
  avisos publicados, no de encuestas.</p>
</header>

<div class="tarjetas">{tarjetas_html}</div>

{hallazgo}

<h2>Mediana por rubro</h2>
<div class="panel">{_tabla_rubros(rubros)}</div>

<h2>Comparación</h2>
<div class="panel">{svg_barras(rubros)}</div>

{grafico_linea}

<h2>Contexto oficial: índice de salarios (INDEC)</h2>
{_seccion_indec(indec)}

<h2>Metodología</h2>
<div class="panel">
<p style="margin-top:0">{_escapar(sueldos.get("metodologia", ""))}</p>
<ol>
  <li>Se recorren hasta 3 páginas por término, con pausa de 1,5 s entre requests
  y respetando <code>robots.txt</code>.</li>
  <li>Varios términos alimentan el mismo rubro: <code>desarrollador-java</code>,
  <code>desarrollador-net</code> y <code>desarrollador-python</code> suman a
  <strong>Backend</strong>. Así la muestra de cada rubro es más grande y más
  específica que buscando solo el nombre genérico.</li>
  <li>Solo se usan avisos que declaran un monto. Los que no publican salario
  quedan afuera del cálculo.</li>
  <li>Un rango se resume con su punto medio; los agregados usan esos puntos
  medios.</li>
  <li>Filtros de sanidad: se descartan avisos de puestos que no son tech
  (programador CNC, ventas, mantenimiento), montos fuera de $ 150.000 –
  $ 20.000.000, valores de relleno (<code>1.111.111</code>, <code>9.999.999</code>,
  escaleras y dígitos repetidos), avisos duplicados, montos repetidos en más del
  40% de un rubro (spam) y valores atípicos fuera de 1,5 × rango
  intercuartílico cuando hay al menos 5 avisos.</li>
  <li>Con menos de 3 avisos no se publica mediana (<code>s/d</code>). Entre 3 y
  4 avisos se marca <strong>muestra chica</strong>: el número es descriptivo y
  puede moverse mucho con un solo aviso.</li>
</ol>
<p style="margin-bottom:0;color:var(--tenue)">Los agregados son de avisos, no de
personas: un aviso con rango amplio mueve la mediana tanto como uno con monto
exacto, y las empresas que no publican salario no están representadas.</p>
<p style="margin-bottom:0;color:var(--tenue)">En esta corrida se descartaron
{_escapar(formatear_numero(sum(descartados.values())))} avisos: relleno o
centinela {_escapar(formatear_numero(descartados.get("centinela", 0)))},
fuera de rango {_escapar(formatear_numero(descartados.get("fuera_de_rango", 0)))},
duplicados {_escapar(formatear_numero(descartados.get("duplicado", 0)))},
no tech {_escapar(formatear_numero(descartados.get("no_tech", 0)))},
spam {_escapar(formatear_numero(descartados.get("spam", 0)))} y atípicos
{_escapar(formatear_numero(descartados.get("atipico", 0)))}.</p>
</div>

<h2>Fuentes</h2>
<div class="panel"><ul style="margin:0">{fuentes_html}</ul></div>

<footer>
  Proyecto <strong>sueldos-ar</strong> · observatorio generado automáticamente.
  Datos crudos en <a href="data/sueldos.json">data/sueldos.json</a>,
  <a href="data/historico.json">data/historico.json</a> y
  <a href="data/indec.json">data/indec.json</a>.
</footer>
</main>
</body>
</html>
"""


def escribir_salidas(
    sueldos: dict,
    historico: dict,
    indec: dict,
    docs: Path,
) -> list[Path]:
    """Escribe los SVG y el HTML en ``docs/``. Devuelve las rutas generadas."""
    assets = docs / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    generadas: list[Path] = []

    ruta_barras = assets / "grafico-rubros.svg"
    ruta_barras.write_text(svg_barras(sueldos.get("rubros", [])), encoding="utf-8", newline="\n")
    generadas.append(ruta_barras)

    linea = svg_linea(historico)
    ruta_linea = assets / "grafico-historico.svg"
    if linea:
        ruta_linea.write_text(linea, encoding="utf-8", newline="\n")
        generadas.append(ruta_linea)
    elif ruta_linea.exists():
        ruta_linea.unlink()  # no dejar un gráfico viejo de una serie que ya no aplica

    ruta_html = docs / "observatorio.html"
    ruta_html.write_text(generar_html(sueldos, historico, indec), encoding="utf-8", newline="\n")
    generadas.append(ruta_html)
    return generadas
