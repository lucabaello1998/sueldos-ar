"""Fuente: series oficiales de salarios vía la API de datos.gob.ar.

Se usa la API JSON oficial (sin scraping). Si una serie falla o no está
actualizada, se omite y se informa: nunca se rellenan valores a mano.

Series usadas (verificadas contra el catálogo al 2026-07):

* ``153.1_RNERACIDIO_2009_M_21`` — remuneración bruta promedio de los
  asalariados registrados del sector privado, **en pesos**. Es el único dato
  oficial que se puede comparar contra una mediana de avisos.
* ``149.1_TL_INDIIOS_OCTU_0_21`` — Índice de Salarios, total país.
* ``149.1_SOR_PRIADO_OCTU_0_25`` — Índice, empleo registrado privado.
* ``149.1_SOR_PUBICO_OCTU_0_14`` — Índice, empleo registrado público.
* ``149.1_SOR_PRIADO_OCTU_0_28`` — Índice, empleo privado no registrado.

El RIPTE (``158.1_REPTE_0_0_5``) figura en el catálogo pero la API lo devuelve
sin observaciones, así que no se usa.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

API_SERIES = "https://apis.datos.gob.ar/series/api/series/"
URL_CATALOGO = "https://datos.gob.ar/series/api/search/?q=indice%20de%20salarios"

#: Series oficiales, en el orden en que se muestran.
SERIES: list[dict[str, str]] = [
    {
        "clave": "remuneracion_promedio",
        "id": "153.1_RNERACIDIO_2009_M_21",
        "nombre": "Remuneración bruta promedio · privado registrado",
        "tipo": "pesos",
    },
    {
        "clave": "indice_total",
        "id": "149.1_TL_INDIIOS_OCTU_0_21",
        "nombre": "Índice de salarios · total país",
        "tipo": "indice",
    },
    {
        "clave": "indice_privado",
        "id": "149.1_SOR_PRIADO_OCTU_0_25",
        "nombre": "Índice · privado registrado",
        "tipo": "indice",
    },
    {
        "clave": "indice_publico",
        "id": "149.1_SOR_PUBICO_OCTU_0_14",
        "nombre": "Índice · sector público",
        "tipo": "indice",
    },
    {
        "clave": "indice_no_registrado",
        "id": "149.1_SOR_PRIADO_OCTU_0_28",
        "nombre": "Índice · privado no registrado",
        "tipo": "indice",
    },
]

#: Si la última observación es más vieja que esto, se considera desactualizada.
MESES_MAXIMOS_SIN_ACTUALIZAR = 18

USER_AGENT = "sueldos-ar-observatorio/1.0 (+https://github.com/lucabaello1998)"


class ErrorIndec(RuntimeError):
    """La API de series no respondió o devolvió algo inesperado."""


def _get_json(url: str, timeout: int = 60) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ErrorIndec(f"HTTP {exc.code} en {url}") from exc
    except urllib.error.URLError as exc:
        raise ErrorIndec(f"no se pudo conectar: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise ErrorIndec(f"respuesta no es JSON válido: {exc}") from exc


def url_serie(serie_id: str, desde: str = "2016-01-01") -> str:
    """URL de descarga de una serie, para citarla en el JSON."""
    return (
        API_SERIES
        + "?"
        + urllib.parse.urlencode({"ids": serie_id, "start_date": desde, "limit": 1000})
    )


def descargar_serie(serie_id: str, desde: str = "2016-01-01") -> dict:
    """Baja los puntos de una serie como ``{fecha: valor}`` más su metadata."""
    url = url_serie(serie_id, desde)
    datos = _get_json(url)
    puntos = datos.get("data") or []
    if not puntos:
        raise ErrorIndec(f"la serie {serie_id} vino vacía")
    return {
        "url": url,
        "meta": (datos.get("meta") or [{}])[-1],
        "serie": {fecha: valor for fecha, valor in puntos if valor is not None},
    }


def _meses_entre(desde: str, hasta: str) -> int:
    """Diferencia en meses entre dos fechas ISO ``YYYY-MM-DD``."""
    a = datetime.strptime(desde[:10], "%Y-%m-%d")
    b = datetime.strptime(hasta[:10], "%Y-%m-%d")
    return (b.year - a.year) * 12 + (b.month - a.month)


def _variacion_12m(serie: dict[str, float]) -> float | None:
    """Variación porcentual contra la observación de 12 meses antes."""
    fechas = sorted(serie)
    if len(fechas) < 13:
        return None
    actual, previa = fechas[-1], fechas[-13]
    if not serie[previa]:
        return None
    return round((serie[actual] / serie[previa] - 1) * 100, 2)


def _armar(serie: dict[str, float], meta: dict, url: str, hoy: datetime) -> dict:
    """Construye la ficha de una serie a partir de sus puntos."""
    campo = meta.get("field", {})
    dataset = meta.get("dataset", {})
    hasta = max(serie)
    meses = _meses_entre(hasta, hoy.strftime("%Y-%m-%d"))
    if meses > MESES_MAXIMOS_SIN_ACTUALIZAR:
        raise ErrorIndec(
            f"la serie {campo.get('id', '?')} no se actualiza desde {hasta} ({meses} meses)"
        )

    return {
        "id": campo.get("id", ""),
        "descripcion": campo.get("description", ""),
        "unidades": campo.get("units", ""),
        "fuente": dataset.get("source", "INDEC"),
        "dataset": dataset.get("title", ""),
        "url_fuente": url,
        "desde": min(serie),
        "hasta": hasta,
        "ultimo": serie[hasta],
        "variacion_12m_pct": _variacion_12m(serie),
        "serie": dict(sorted(serie.items())),
    }


def obtener(
    offline: bool = False,
    fixtures: Path | None = None,
    hoy: datetime | None = None,
) -> dict:
    """Devuelve el contexto oficial listo para ``indec.json``.

    Nunca levanta excepción: las series que fallan se informan en
    ``faltantes`` y el resto se publica.
    """
    hoy = hoy or datetime.now(UTC)
    fixtures = fixtures or Path("fixtures")
    consultado = hoy.strftime("%Y-%m-%dT%H:%M:%SZ")

    if offline:
        return _desde_fixture(fixtures, consultado)

    fichas: list[dict] = []
    faltantes: list[str] = []
    for definicion in SERIES:
        try:
            descarga = descargar_serie(definicion["id"])
            ficha = _armar(descarga["serie"], descarga["meta"], descarga["url"], hoy)
        except ErrorIndec as exc:
            faltantes.append(f"{definicion['nombre']}: {exc}")
            continue
        ficha["clave"] = definicion["clave"]
        ficha["nombre"] = definicion["nombre"]
        ficha["tipo"] = definicion["tipo"]
        fichas.append(ficha)

    return {
        "disponible": bool(fichas),
        "consultado": consultado,
        "url_catalogo": URL_CATALOGO,
        "series": fichas,
        "faltantes": faltantes,
    }


def _desde_fixture(fixtures: Path, consultado: str) -> dict:
    """Modo offline: lee ``fixtures/indec-series.json`` ya normalizado."""
    ruta = fixtures / "indec-series.json"
    if not ruta.exists():
        return {
            "disponible": False,
            "motivo": f"modo offline sin fixture {ruta.name}",
            "consultado": consultado,
            "series": [],
            "faltantes": [],
        }
    try:
        guardado = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "disponible": False,
            "motivo": f"fixture indec-series.json inválido: {exc}",
            "consultado": consultado,
            "series": [],
            "faltantes": [],
        }

    if "series" in guardado:
        guardado.setdefault("disponible", bool(guardado["series"]))
        guardado.setdefault("consultado", consultado)
        guardado.setdefault("faltantes", [])
        return guardado

    return {
        "disponible": False,
        "motivo": "el fixture no tiene el formato esperado (clave 'series')",
        "consultado": consultado,
        "series": [],
        "faltantes": [],
    }
