"""Entrypoint del observatorio: ``python -m tools.observatorio.construir``.

Recolecta avisos, normaliza, agrega y escribe ``docs/data/*.json`` más el
reporte ``docs/observatorio.html`` con sus gráficos SVG.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from tools.observatorio import graficar
from tools.observatorio.fuentes import computrabajo, indec
from tools.observatorio.normalizar import (
    CENTINELAS,
    MAXIMO,
    MINIMO,
    REPETICIONES_RELLENO,
    UMBRAL_SPAM,
    Monto,
    agregar,
    agregar_rubro,
    es_centinela,
    es_ruido_no_tech,
    fuera_de_rango,
    parsear_monto,
)

RAIZ = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"

METODOLOGIA = (
    "Mediana de salarios publicados en avisos de Computrabajo Argentina, agrupados "
    "por rubro tech. Son avisos de empresas, no encuestas ni liquidaciones reales: "
    "solo reflejan a quienes declaran el monto, y un rango se resume con su punto "
    "medio. Los rubros con menos de 3 avisos quedan sin mediana y los de 3 o 4 se "
    "marcan como muestra chica."
)


def _avisos_a_dicts(avisos: list[computrabajo.Aviso]) -> list[dict]:
    """Convierte avisos crudos al formato interno con montos ya parseados.

    Los sueldos por hora no se pueden comparar con los mensuales: si se publican
    como si fueran mensuales, un "200.000 la hora" entra como un sueldo bajo y
    ensucia la mediana. Se descartan antes de llegar a la tabla.
    """
    salida: list[dict] = []
    for aviso in avisos:
        monto = parsear_monto(aviso.salario_texto)
        if monto is not None and monto.periodo != "mensual":
            continue
        salida.append(
            {
                "titulo": aviso.titulo,
                "empresa": aviso.empresa,
                "url": aviso.url,
                "salario_min": monto.minimo if monto else None,
                "salario_max": monto.maximo if monto else None,
            }
        )
    return salida


def _monto_plausible(aviso: dict) -> int | None:
    """Punto medio del aviso si declara un monto plausible, antes de deduplicar."""
    minimo, maximo = aviso.get("salario_min"), aviso.get("salario_max")
    if minimo is None or maximo is None:
        return None
    if es_ruido_no_tech(aviso.get("titulo")):
        return None
    monto = Monto(int(minimo), int(maximo))
    if es_centinela(monto) or fuera_de_rango(monto):
        return None
    return monto.punto_medio


def detectar_relleno(por_rubro: dict[str, list[dict]]) -> set[int]:
    """Montos exactos que se repiten demasiadas veces en toda la corrida.

    Un mismo número no redondo que aparece en cinco avisos o más (entre rubros
    distintos) no es una banda salarial: es un aviso de prueba o un avisante
    que copia y pega el mismo valor. Los múltiplos de $ 100.000 se excluyen
    porque son sueldos redondos legítimos (``$ 2.000.000`` lo ofrecen muchas
    empresas de verdad).
    """
    frecuencia: Counter[int] = Counter()
    for avisos in por_rubro.values():
        for aviso in avisos:
            medio = _monto_plausible(aviso)
            if medio is not None:
                frecuencia[medio] += 1
    return {
        medio
        for medio, veces in frecuencia.items()
        if veces >= REPETICIONES_RELLENO and medio % 100_000 != 0
    }


def construir_sueldos(
    por_rubro: dict[str, list[dict]],
    terminos: list[dict[str, str]],
    generado: datetime,
) -> dict:
    """Arma el snapshot ``sueldos.json`` a partir de los avisos por rubro."""
    nombres = {t["rubro"]: t["nombre"] for t in terminos}
    bloqueados = detectar_relleno(por_rubro)
    rubros: list[dict] = []
    descartados = {
        "fuera_de_rango": 0,
        "centinela": 0,
        "spam": 0,
        "no_tech": 0,
        "duplicado": 0,
        "atipico": 0,
    }
    total_avisos_vistos = 0
    total_sin_salario = 0
    unicos_globales: dict[str, dict] = {}

    for rubro_id, avisos in por_rubro.items():
        resumen = agregar_rubro(avisos, bloqueados)
        filtro = resumen.pop("_filtro")
        validos = resumen.pop("avisos")
        suficiente = resumen.pop("suficiente")
        total_avisos_vistos += len(avisos)
        total_sin_salario += filtro.sin_salario

        for clave, valor in filtro.descartados.items():
            descartados[clave] = descartados.get(clave, 0) + valor

        for aviso in validos:
            unicos_globales.setdefault(aviso["url"], aviso)

        detalle = sorted(
            (
                {
                    "titulo": a["titulo"],
                    "empresa": a["empresa"],
                    "salario_min": a["salario_min"],
                    "salario_max": a["salario_max"],
                    "url": a["url"],
                }
                for a in validos
            ),
            key=lambda a: (a["titulo"], a["url"]),
        )

        rubros.append(
            {
                "id": rubro_id,
                "nombre": nombres.get(rubro_id, rubro_id),
                "n": resumen["n"],
                "ofertas": len(avisos),
                "con_salario": len(avisos) - filtro.sin_salario,
                "mediana": resumen["mediana"],
                "p25": resumen["p25"],
                "p75": resumen["p75"],
                "min": resumen["min"],
                "max": resumen["max"],
                "suficiente": suficiente,
                "avisos": detalle,
            }
        )

    rubros.sort(key=lambda r: (r["mediana"] is None, -(r["mediana"] or 0), r["id"]))

    medios = [
        int(round((a["salario_min"] + a["salario_max"]) / 2)) for a in unicos_globales.values()
    ]
    general = agregar(medios)

    # Transparencia: sobre ofertas únicas, cuántas publican sueldo y cuántas
    # publican un monto que se puede tomar en serio.
    unicas = {a["url"]: a for avisos in por_rubro.values() for a in avisos}.values()
    ofertas_unicas = len(unicas)
    declaran = sum(1 for a in unicas if a["salario_min"] is not None)
    plausibles = sum(
        1 for a in unicas if (medio := _monto_plausible(a)) is not None and medio not in bloqueados
    )

    return {
        "generado": generado.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fuente": "Computrabajo Argentina (avisos con salario publicado)",
        "url_fuente": "https://ar.computrabajo.com/",
        "metodologia": METODOLOGIA,
        "rubros": rubros,
        "mediana_general": general["mediana"],
        "n_general": general["n"],
        "descartados": descartados,
        "transparencia": {
            "ofertas_unicas": ofertas_unicas,
            "declaran_salario": declaran,
            "declaran_salario_pct": round(100 * declaran / ofertas_unicas, 1)
            if ofertas_unicas
            else 0.0,
            "monto_plausible": plausibles,
            "monto_plausible_pct": round(100 * plausibles / declaran, 1) if declaran else 0.0,
            "montos_repetidos": sorted(bloqueados),
        },
        "resumen_corrida": {
            "terminos_consultados": len(terminos),
            "terminos_sin_datos": sorted(
                {t["rubro"] for t in terminos if not por_rubro.get(t["rubro"])}
            ),
            "avisos_recolectados": total_avisos_vistos,
            "avisos_utilizables": len(unicos_globales),
            "sin_salario_publicado": total_sin_salario,
            "filtros": {
                "minimo_pesos": MINIMO,
                "maximo_pesos": MAXIMO,
                "centinelas": sorted(CENTINELAS),
                "umbral_spam": UMBRAL_SPAM,
                "repeticiones_relleno": REPETICIONES_RELLENO,
            },
        },
    }


def actualizar_historico(historico_previo: dict, sueldos: dict, fecha: str) -> dict:
    """Agrega (o reemplaza) la corrida del día sin tocar las anteriores."""
    corridas = [c for c in historico_previo.get("corridas", []) if c.get("fecha") != fecha]
    corridas.append(
        {
            "fecha": fecha,
            "mediana_general": sueldos.get("mediana_general"),
            "rubros": [
                {"id": r["id"], "mediana": r["mediana"], "n": r["n"]}
                for r in sueldos.get("rubros", [])
            ],
        }
    )
    corridas.sort(key=lambda c: c["fecha"])
    return {"corridas": corridas}


def _leer_json(ruta: Path, defecto: dict, estricto: bool = False) -> dict:
    if not ruta.exists():
        return defecto
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        if estricto:
            # Un histórico truncado no se reemplaza por uno vacío: se aborta y se
            # conserva lo que había (o se recupera del backup de git).
            raise ValueError(f"{ruta} está corrupto ({error.msg}). No se toca.") from error
        return defecto


def _escribir_json(ruta: Path, datos: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def ejecutar(
    offline: bool = False,
    paginas: int = 3,
    docs: Path | None = None,
    fixtures: Path | None = None,
    terminos: list[dict[str, str]] | None = None,
    generado: datetime | None = None,
) -> dict:
    """Corre una corrida completa y devuelve un resumen para consola."""
    docs = docs or RAIZ / "docs"
    fixtures = fixtures or FIXTURES
    terminos = terminos or computrabajo.TERMINOS
    generado = generado or datetime.now(UTC)

    avisos, warnings = computrabajo.recolectar(
        terminos=terminos,
        paginas=paginas,
        offline=offline,
        fixtures=fixtures,
    )

    por_rubro = {rid: _avisos_a_dicts(lista) for rid, lista in avisos.items()}
    sueldos = construir_sueldos(por_rubro, terminos, generado)

    datos_dir = docs / "data"
    ruta_sueldos = datos_dir / "sueldos.json"
    ruta_historico = datos_dir / "historico.json"

    # Una corrida sin datos no puede pisar el último snapshot bueno: se corta acá,
    # antes de escribir nada, y main devuelve error.
    if not sueldos["rubros"]:
        return {
            "sueldos": sueldos,
            "historico": _leer_json(ruta_historico, {"corridas": []}),
            "indec": {"disponible": False, "series": [], "motivo": "sin datos de avisos"},
            "warnings": [*warnings, "No se recolectaron rubros: no se tocó ningún archivo."],
            "archivos": [],
        }

    historico_previo = _leer_json(ruta_historico, {"corridas": []}, estricto=True)

    _escribir_json(ruta_sueldos, sueldos)

    historico = actualizar_historico(
        historico_previo,
        sueldos,
        generado.date().isoformat(),
    )
    _escribir_json(ruta_historico, historico)

    contexto = indec.obtener(offline=offline, fixtures=fixtures, hoy=generado)
    _escribir_json(datos_dir / "indec.json", contexto)

    graficos = graficar.escribir_salidas(sueldos, historico, contexto, docs)

    return {
        "sueldos": sueldos,
        "historico": historico,
        "indec": contexto,
        "warnings": warnings,
        "archivos": [ruta_sueldos, ruta_historico, *graficos],
    }


def _regenerar_html(docs: Path) -> dict:
    """Rehace HTML y SVG desde los JSON ya generados, sin salir a la red."""
    datos = docs / "data"
    sueldos = _leer_json(datos / "sueldos.json", None)
    if not sueldos:
        raise SystemExit(f"falta {datos / 'sueldos.json'}: corré la corrida completa primero")
    historico = _leer_json(datos / "historico.json", {"corridas": []})
    contexto = _leer_json(datos / "indec.json", {"disponible": False, "series": []})
    graficos = graficar.escribir_salidas(sueldos, historico, contexto, docs)
    return {
        "sueldos": sueldos,
        "historico": historico,
        "indec": contexto,
        "warnings": [],
        "archivos": graficos,
    }


def _imprimir_resumen(resultado: dict) -> None:
    sueldos = resultado["sueldos"]
    print("=" * 68)
    print(f"Observatorio · {sueldos['generado']}")
    print(f"Mediana general: {sueldos.get('mediana_general')} (n={sueldos.get('n_general')})")
    print("-" * 68)
    print(f"{'rubro':26} {'n':>3}  {'mediana':>12}  {'p25':>12}  {'p75':>12}")
    for rubro in sueldos["rubros"]:
        if rubro.get("mediana") is None:
            marca = "  (sin datos)"
        elif rubro.get("suficiente", True):
            marca = ""
        else:
            marca = "  (muestra chica)"
        print(
            f"{rubro['id']:26} {rubro['n']:>3}  "
            f"{rubro['mediana'] or 0:>12,}  {rubro['p25'] or 0:>12,}  "
            f"{rubro['p75'] or 0:>12,}".replace(",", ".")
            + marca
        )
    print("-" * 68)
    print(f"descartados: {sueldos['descartados']}")
    print(f"corrida: {sueldos['resumen_corrida']}")
    if not resultado["indec"].get("disponible"):
        print(f"INDEC no disponible: {resultado['indec'].get('motivo')}")
    for warning in resultado["warnings"]:
        print(f"  ! {warning}")
    print("-" * 68)
    for archivo in resultado["archivos"]:
        print(f"  escrito: {archivo}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tools.observatorio.construir",
        description="Genera el observatorio de sueldos tech argentino.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="no usa red: lee fixtures/ (para tests y CI)",
    )
    parser.add_argument("--paginas", type=int, default=3, help="páginas por término (default 3)")
    parser.add_argument("--docs", type=Path, default=None, help="carpeta de salida (default docs/)")
    parser.add_argument("--fixtures", type=Path, default=None, help="carpeta de fixtures")
    parser.add_argument(
        "--solo-html",
        action="store_true",
        help="regenera HTML y SVG desde docs/data, sin salir a la red",
    )
    args = parser.parse_args(argv)

    if args.solo_html:
        resultado = _regenerar_html(args.docs or RAIZ / "docs")
        _imprimir_resumen(resultado)
        return 0

    resultado = ejecutar(
        offline=args.offline,
        paginas=args.paginas,
        docs=args.docs,
        fixtures=args.fixtures,
    )
    _imprimir_resumen(resultado)

    if not resultado["sueldos"]["rubros"]:
        print("ERROR: no se recolectó ningún rubro.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
