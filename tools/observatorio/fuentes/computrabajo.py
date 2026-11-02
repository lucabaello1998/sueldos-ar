"""Fuente: Computrabajo Argentina — avisos con salario publicado.

Solo se leen las páginas de listado públicas (``/trabajo-de-<termino>``), que
``robots.txt`` permite. No se entra a ninguna oferta ni a datos de candidatos.
"""

from __future__ import annotations

import html as html_mod
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

BASE = "https://ar.computrabajo.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

CABECERAS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "es-AR,es;q=0.9",
}

#: Pausa entre requests, en segundos. No bajar: es un sitio de terceros.
PAUSA_SEG = 1.5

#: Términos que se consultan. Varios términos pueden alimentar el mismo rubro:
#: buscar "desarrollador-java" y "desarrollador-net" da mucha mejor muestra de
#: backend que buscar solo "desarrollador-backend" (los avisos que declaran
#: sueldo suelen ser los de búsquedas tecnológicas específicas).
TERMINOS: list[dict[str, str]] = [
    {"rubro": "desarrollo", "nombre": "Desarrollo (general)", "slug": "desarrollador"},
    {"rubro": "desarrollo", "nombre": "Desarrollo (general)", "slug": "programador"},
    {"rubro": "backend", "nombre": "Backend", "slug": "desarrollador-backend"},
    {"rubro": "backend", "nombre": "Backend", "slug": "desarrollador-java"},
    {"rubro": "backend", "nombre": "Backend", "slug": "desarrollador-net"},
    {"rubro": "backend", "nombre": "Backend", "slug": "desarrollador-python"},
    {"rubro": "frontend", "nombre": "Frontend", "slug": "desarrollador-frontend"},
    {"rubro": "frontend", "nombre": "Frontend", "slug": "desarrollador-react"},
    {"rubro": "full-stack", "nombre": "Full Stack", "slug": "full-stack"},
    {"rubro": "datos", "nombre": "Datos", "slug": "analista-de-datos"},
    {"rubro": "datos", "nombre": "Datos", "slug": "base-de-datos"},
    {"rubro": "devops", "nombre": "DevOps / Infra", "slug": "devops"},
    {"rubro": "devops", "nombre": "DevOps / Infra", "slug": "seguridad-informatica"},
    {"rubro": "qa", "nombre": "QA / Testing", "slug": "tester-qa"},
    {"rubro": "qa", "nombre": "QA / Testing", "slug": "qa"},
    {"rubro": "soporte", "nombre": "Soporte técnico", "slug": "soporte-tecnico"},
    {"rubro": "funcional", "nombre": "Análisis funcional", "slug": "analista-funcional"},
    {"rubro": "funcional", "nombre": "Análisis funcional", "slug": "analista-de-sistemas"},
]


class ErrorFuente(RuntimeError):
    """Error recuperable de la fuente: se informa y se sigue con el resto."""


@dataclass
class Aviso:
    """Un aviso del listado, todavía sin normalizar el salario."""

    titulo: str
    empresa: str
    url: str
    salario_texto: str | None = None


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------


def _pedir(url: str, timeout: int = 60) -> str:
    """Baja una URL y devuelve el texto HTML."""
    req = urllib.request.Request(url, headers=CABECERAS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, "replace")
    except urllib.error.HTTPError as exc:
        raise ErrorFuente(f"HTTP {exc.code} en {url}") from exc
    except urllib.error.URLError as exc:
        raise ErrorFuente(f"no se pudo conectar a {url}: {exc.reason}") from exc


def url_listado(slug: str, pagina: int = 1) -> str:
    """Arma la URL del listado para un término y una página."""
    url = f"{BASE}/trabajo-de-{slug}"
    if pagina > 1:
        url += f"?p={pagina}"
    return url


def leer_robots() -> list[str]:
    """Devuelve las reglas ``Disallow`` de ``robots.txt`` para ``User-agent: *``."""
    texto = _pedir(f"{BASE}/robots.txt", timeout=30)
    reglas: list[str] = []
    aplica = False
    for linea in texto.splitlines():
        linea = linea.split("#", 1)[0].strip()
        if not linea:
            continue
        clave, _, valor = linea.partition(":")
        clave = clave.strip().lower()
        valor = valor.strip()
        if clave == "user-agent":
            aplica = valor == "*"
        elif clave == "disallow" and aplica and valor:
            reglas.append(valor)
    return reglas


def _patron_robots(regla: str) -> re.Pattern[str]:
    """Convierte una regla de robots.txt (con ``*``) en regex."""
    partes = [re.escape(p) for p in regla.split("*")]
    return re.compile("^" + ".*".join(partes))


def permitido(url: str, reglas: list[str]) -> bool:
    """True si la ruta de ``url`` no cae en ninguna regla ``Disallow``."""
    ruta = urllib.parse.urlsplit(url).path
    query = urllib.parse.urlsplit(url).query
    objetivo = f"{ruta}?{query}" if query else ruta
    return not any(_patron_robots(r).search(objetivo) for r in reglas)


# --------------------------------------------------------------------------
# Parseo del listado
# --------------------------------------------------------------------------

_RE_ARTICULO = re.compile(
    r"<article\b(?=[^>]*data-offers-grid-offer-item-container)(.*?)(?=<article\b|</main>|\Z)", re.S
)
_RE_TITULO = re.compile(r"<h2[^>]*>\s*<a[^>]*href=\"([^\"]*)\"[^>]*>(.*?)</a>", re.S)
_RE_EMPRESA = re.compile(r"<a[^>]*offer-grid-article-company-url[^>]*>(.*?)</a>", re.S)
_RE_SALARIO = re.compile(r'icon i_salary"?></span>\s*([^<]+)')
_RE_SIGUIENTE = re.compile(r'<span[^>]*class="[^"]*buildLink[^"]*"[^>]*data-path="([^"]+)"')
_RE_ETIQUETAS = re.compile(r"<[^>]+>")


def _limpiar(fragmento: str) -> str:
    """Saca tags, normaliza espacios y desescapa entidades HTML."""
    texto = _RE_ETIQUETAS.sub(" ", fragmento)
    texto = html_mod.unescape(texto)
    return re.sub(r"\s+", " ", texto).strip()


def parsear_avisos(html: str) -> list[Aviso]:
    """Extrae los avisos (con o sin salario) de una página de listado."""
    avisos: list[Aviso] = []
    for bloque in _RE_ARTICULO.findall(html):
        m_titulo = _RE_TITULO.search(bloque)
        if not m_titulo:
            continue
        href, titulo_html = m_titulo.group(1), m_titulo.group(2)
        titulo = _limpiar(titulo_html)
        if not titulo:
            continue

        href = html_mod.unescape(href).split("#", 1)[0]
        url = href if href.startswith("http") else BASE + href

        m_empresa = _RE_EMPRESA.search(bloque)
        empresa = _limpiar(m_empresa.group(1)) if m_empresa else ""

        m_salario = _RE_SALARIO.search(bloque)
        salario = _limpiar(m_salario.group(1)) if m_salario else None

        avisos.append(
            Aviso(
                titulo=titulo,
                empresa=empresa,
                url=url,
                salario_texto=salario or None,
            )
        )
    return avisos


def hay_siguiente(html: str) -> bool:
    """True si el listado tiene link a la página siguiente."""
    return _RE_SIGUIENTE.search(html) is not None


# --------------------------------------------------------------------------
# Recolección
# --------------------------------------------------------------------------


def leer_fixture(fixtures: Path, slug: str) -> str:
    """Lee el HTML de ejemplo guardado para un término (modo offline)."""
    candidatos = [
        fixtures / f"computrabajo-{slug}.html",
        fixtures / f"computrabajo-{slug}-p1.html",
        fixtures / "computrabajo-listado.html",
        fixtures / "computrabajo-desarrollador.html",
    ]
    for ruta in candidatos:
        if ruta.exists():
            return ruta.read_text(encoding="utf-8")
    raise ErrorFuente(f"falta el fixture de Computrabajo para '{slug}' en {fixtures}")


def recolectar(
    terminos: list[dict[str, str]] | None = None,
    paginas: int = 3,
    offline: bool = False,
    fixtures: Path | None = None,
    pausa: float = PAUSA_SEG,
    avisos_por_termino: dict[str, list[Aviso]] | None = None,
) -> tuple[dict[str, list[Aviso]], list[str]]:
    """Recorre los términos y devuelve ``{rubro: [avisos]}`` más warnings.

    Varios términos pueden aportar al mismo rubro (ver ``TERMINOS``); al final
    se juntan y se deduplican por URL. En modo ``offline`` solo lee
    ``fixtures/``. Un término que falla o trae 0 avisos se informa como warning
    y no corta la corrida.
    """
    terminos = TERMINOS if terminos is None else terminos
    por_rubro: dict[str, list[Aviso]] = {}
    nombres: dict[str, str] = {}
    avisos_por_termino = {} if avisos_por_termino is None else avisos_por_termino
    warnings: list[str] = []
    sin_fixture: list[str] = []

    reglas: list[str] = []
    if not offline:
        try:
            reglas = leer_robots()
        except ErrorFuente as exc:
            warnings.append(f"robots.txt no disponible ({exc}); se sigue igual")

    for i, termino in enumerate(terminos):
        slug, rubro = termino["slug"], termino["rubro"]
        nombres.setdefault(rubro, termino.get("nombre", rubro))
        acumulado: list[Aviso] = []

        for pagina in range(1, paginas + 1):
            if offline:
                if pagina > 1:
                    break  # los fixtures son de una sola página
                try:
                    html = leer_fixture(fixtures or Path("fixtures"), slug)
                except ErrorFuente:
                    sin_fixture.append(slug)
                    break
            else:
                url = url_listado(slug, pagina)
                if reglas and not permitido(url, reglas):
                    warnings.append(f"robots.txt bloquea {url}; se omite")
                    break
                if i or pagina > 1:
                    time.sleep(pausa)
                try:
                    html = _pedir(url)
                except ErrorFuente as exc:
                    if pagina == 1:
                        warnings.append(f"'{slug}': {exc}")
                    break

            encontrados = parsear_avisos(html)
            acumulado.extend(encontrados)
            if offline or not encontrados or not hay_siguiente(html):
                break

        if not acumulado:
            if slug not in sin_fixture:
                warnings.append(f"'{slug}': 0 avisos, se ignora")
            continue

        avisos_por_termino[slug] = acumulado
        por_rubro.setdefault(rubro, []).extend(acumulado)

    if sin_fixture:
        warnings.append(
            f"offline: sin fixture para {len(sin_fixture)} términos ({', '.join(sin_fixture)})"
        )

    # Deduplicar por URL dentro de cada rubro: la paginación y los términos
    # cruzados repiten el mismo aviso.
    salida: dict[str, list[Aviso]] = {}
    for rubro, avisos in por_rubro.items():
        vistos: set[str] = set()
        unicos: list[Aviso] = []
        for aviso in avisos:
            if aviso.url in vistos:
                continue
            vistos.add(aviso.url)
            unicos.append(aviso)
        salida[rubro] = unicos

    return salida, warnings


def nombre_rubro(rubro_id: str) -> str:
    """Nombre legible de un rubro, según ``TERMINOS``."""
    for termino in TERMINOS:
        if termino["rubro"] == rubro_id:
            return termino.get("nombre", rubro_id)
    return rubro_id
