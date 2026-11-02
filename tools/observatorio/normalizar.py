"""Normalización de montos, filtros de sanidad y agregados.

Todo con ``statistics``/``math`` de la stdlib: el observatorio no agrega
dependencias de cálculo.

Los filtros son la parte más importante del módulo. Un tablero de sueldos que
promedia avisos de prueba (``$ 1.111.111``) o búsquedas que trajeron un
"Programador CNC" miente con precisión: por eso cada descarte se cuenta y se
publica.
"""

from __future__ import annotations

import math
import re
import statistics
from dataclasses import dataclass

#: Montos que aparecen una y otra vez en avisos de prueba. No son sueldos.
CENTINELAS: frozenset[int] = frozenset(
    {11111, 2222, 2000, 9999999, 1111111, 2222222, 3333333, 999999}
)

#: Banda de sanidad, en pesos mensuales.
MINIMO = 150_000
MAXIMO = 20_000_000

#: Si un mismo monto supera esta fracción de los avisos de un rubro, es spam.
UMBRAL_SPAM = 0.40

#: Con menos avisos que esto el umbral de spam no es significativo (cualquier
#: valor repetido dos veces superaría el 40%).
MINIMO_PARA_SPAM = 4

#: Debajo de esta cantidad de avisos la mediana no se publica como firme.
MINIMO_MUESTRA = 5

#: Debajo de esta cantidad de avisos no se publica mediana: con una o dos
#: ofertas el número no describe nada.
MINIMO_PUBLICABLE = 3

#: Si un mismo monto exacto aparece esta cantidad de veces o más en toda la
#: corrida, es relleno y no un sueldo (ej. ``1.323.233`` repetido por un mismo
#: avisante en todos sus avisos).
REPETICIONES_RELLENO = 5

#: Meses de un año, para pasar un sueldo anual a mensual.
MESES_POR_ANIO = 12

#: Palabras que delatan un aviso que no es del sector tech. Computrabajo
#: devuelve "programador CNC" o "jefe de ventas" al buscar "programador".
RUIDO_NO_TECH: tuple[str, ...] = (
    "cnc",
    "ventas",
    "vendedor",
    "comercial",
    "produccion",
    "producción",
    "mantenimiento",
    "electricista",
    "mecanico",
    "mecánico",
    "chofer",
    "operario",
    "administrativo",
    "cajero",
    "recepcionista",
    "mozo",
    "limpieza",
    "seguridad",
    "enfermero",
    "docente",
    "abogado",
    "escribano",
    "pasant",
    "practicante",
    "cadete",
    "repositor",
)

_RE_MONTO = re.compile(r"\$\s*(\d[\d.]*(?:,\d{1,2})?)")
_RE_PERIODO = re.compile(r"\(\s*([^)]+?)\s*\)")


@dataclass(frozen=True)
class Monto:
    """Salario de un aviso, ya en pesos y en base mensual."""

    minimo: int
    maximo: int
    periodo: str = "mensual"

    @property
    def punto_medio(self) -> int:
        """Valor representativo del aviso: el punto medio del rango."""
        return int(round((self.minimo + self.maximo) / 2))

    @property
    def es_rango(self) -> bool:
        return self.minimo != self.maximo


def parsear_numero(texto: str) -> float | None:
    """Convierte ``1.234.567,89`` (formato argentino) a ``1234567.89``."""
    limpio = texto.strip().replace(" ", "").replace("\u00a0", "").replace("$", "")
    if not limpio:
        return None
    # Con coma decimal, los puntos son separadores de miles; sin coma, también.
    limpio = limpio.replace(".", "").replace(",", ".") if "," in limpio else limpio.replace(".", "")
    try:
        return float(limpio)
    except ValueError:
        return None


def parsear_monto(texto: str | None) -> Monto | None:
    """Extrae mínimo y máximo de un texto tipo ``$ 800.000,00 - $ 1.200.000,00``.

    Devuelve ``None`` si el texto no tiene ningún monto parseable. Un monto
    suelto se devuelve con mínimo y máximo iguales. Si el aviso aclara que el
    salario es anual, se lleva a mensual para que sea comparable.
    """
    if not texto:
        return None

    valores: list[float] = []
    for bruto in _RE_MONTO.findall(texto):
        numero = parsear_numero(bruto)
        if numero is not None and numero > 0:
            valores.append(numero)
    if not valores:
        return None

    minimo, maximo = min(valores), max(valores)

    periodo = "mensual"
    m_periodo = _RE_PERIODO.search(texto)
    if m_periodo:
        etiqueta = m_periodo.group(1).lower()
        if "anual" in etiqueta or "año" in etiqueta or "ano" in etiqueta:
            periodo = "anual"
            minimo /= MESES_POR_ANIO
            maximo /= MESES_POR_ANIO
        elif "hora" in etiqueta:
            periodo = "hora"

    return Monto(minimo=int(round(minimo)), maximo=int(round(maximo)), periodo=periodo)


def es_sintetico(valor: int) -> bool:
    """True si el número tiene pinta de relleno y no de sueldo.

    Detecta los patrones que usan los avisos de prueba: todos los dígitos
    iguales (``1111111``), un bloque de 2 a 4 dígitos repetido (``323232``),
    cuatro dígitos iguales seguidos (``1.111.111``) o una escalera
    (``1234567``). Los ceros finales no cuentan: ``2.000.000`` es un sueldo
    redondo perfectamente normal.
    """
    s = str(int(valor)).rstrip("0")
    if len(s) < 3:
        return False
    if len(set(s)) == 1:
        return True
    if re.fullmatch(r"(\d{2,4})\1+", s):
        return True
    if re.search(r"(\d)\1{3,}", s):
        return True
    return len(s) >= 7 and ("123456789".startswith(s) or "987654321".startswith(s))


def es_centinela(monto: Monto) -> bool:
    """True si el monto (o alguno de sus extremos) es un valor de prueba."""
    return (
        monto.minimo in CENTINELAS
        or monto.maximo in CENTINELAS
        or es_sintetico(monto.minimo)
        or es_sintetico(monto.maximo)
    )


def fuera_de_rango(monto: Monto) -> bool:
    """True si el punto medio cae fuera de la banda de sanidad."""
    return monto.punto_medio < MINIMO or monto.punto_medio > MAXIMO


def es_ruido_no_tech(titulo: str | None) -> bool:
    """True si el título del aviso delata un puesto que no es del sector tech."""
    if not titulo:
        return False
    texto = titulo.lower()
    return any(palabra in texto for palabra in RUIDO_NO_TECH)


# --------------------------------------------------------------------------
# Filtrado
# --------------------------------------------------------------------------


@dataclass
class ResultadoFiltro:
    """Avisos que sobreviven los filtros y contadores de lo descartado."""

    validos: list[dict]
    fuera_de_rango: int = 0
    centinela: int = 0
    spam: int = 0
    sin_salario: int = 0
    no_tech: int = 0
    duplicado: int = 0
    atipico: int = 0

    @property
    def descartados(self) -> dict[str, int]:
        return {
            "fuera_de_rango": self.fuera_de_rango,
            "centinela": self.centinela,
            "spam": self.spam,
            "no_tech": self.no_tech,
            "duplicado": self.duplicado,
            "atipico": self.atipico,
        }

    @property
    def total_descartados(self) -> int:
        return sum(self.descartados.values())


def _clave_aviso(aviso: dict) -> tuple[str, str, int]:
    titulo = (aviso.get("titulo") or "").strip().lower()
    empresa = (aviso.get("empresa") or "").strip().lower()
    medio = int(round((aviso["salario_min"] + aviso["salario_max"]) / 2))
    return titulo, empresa, medio


def filtrar_avisos(
    avisos: list[dict], bloqueados: frozenset[int] | set[int] = frozenset()
) -> ResultadoFiltro:
    """Aplica todos los filtros de sanidad a los avisos de un rubro.

    Orden: sin salario → no tech → centinela/sintético → fuera de rango →
    duplicado → spam. El umbral de spam se mide sobre los avisos del rubro que
    declaran un monto plausible: si un mismo monto aparece en más del 40% de
    ellos, es un patrón de aviso republicado. Con menos de
    ``MINIMO_PARA_SPAM`` avisos no se aplica, porque el porcentaje no sería
    significativo.

    ``bloqueados`` son montos que ya se detectaron como relleno en toda la
    corrida (se repiten demasiadas veces entre rubros distintos).
    """
    resultado = ResultadoFiltro(validos=[])
    candidatos: list[dict] = []
    vistos: set[tuple[str, str, int]] = set()

    for aviso in avisos:
        minimo, maximo = aviso.get("salario_min"), aviso.get("salario_max")
        if minimo is None or maximo is None:
            resultado.sin_salario += 1
            continue

        if es_ruido_no_tech(aviso.get("titulo")):
            resultado.no_tech += 1
            continue

        monto = Monto(minimo=int(minimo), maximo=int(maximo))
        if monto.punto_medio in bloqueados or es_centinela(monto):
            resultado.centinela += 1
            continue
        if fuera_de_rango(monto):
            resultado.fuera_de_rango += 1
            continue

        clave = _clave_aviso(aviso)
        if clave in vistos:
            resultado.duplicado += 1
            continue

        vistos.add(clave)
        candidatos.append(aviso)

    # Patrón de aviso spam: el mismo monto repetido en demasiados avisos.
    total = len(candidatos)
    if total < MINIMO_PARA_SPAM:
        resultado.validos.extend(candidatos)
        return resultado

    frecuencia: dict[int, int] = {}
    for aviso in candidatos:
        medio = int(round((aviso["salario_min"] + aviso["salario_max"]) / 2))
        frecuencia[medio] = frecuencia.get(medio, 0) + 1

    tope = UMBRAL_SPAM * total
    spam = {m for m, veces in frecuencia.items() if veces > tope}

    for aviso in candidatos:
        medio = int(round((aviso["salario_min"] + aviso["salario_max"]) / 2))
        if medio in spam:
            resultado.spam += 1
        else:
            resultado.validos.append(aviso)

    return resultado


def quitar_atipicos(valores: list[int]) -> tuple[list[int], int]:
    """Descarta valores fuera de 1,5 × rango intercuartílico.

    Solo se aplica con muestra suficiente (``MINIMO_MUESTRA``): con cuatro
    valores el rango intercuartílico no dice nada y borraría sueldos reales.
    Devuelve la lista limpia y cuántos se fueron.
    """
    if len(valores) < MINIMO_MUESTRA:
        return valores, 0

    q1 = percentil(valores, 25)
    q3 = percentil(valores, 75)
    if q1 is None or q3 is None:
        return valores, 0

    iqr = q3 - q1
    if iqr <= 0:
        return valores, 0

    piso = q1 - 1.5 * iqr
    techo = q3 + 1.5 * iqr
    limpios = [v for v in valores if piso <= v <= techo]
    return limpios, len(valores) - len(limpios)


# --------------------------------------------------------------------------
# Agregados
# --------------------------------------------------------------------------


def percentil(valores: list[int | float], p: float) -> float | None:
    """Percentil con interpolación lineal (mismo criterio que numpy)."""
    if not valores:
        return None
    ordenados = sorted(valores)
    if len(ordenados) == 1:
        return float(ordenados[0])
    posicion = (len(ordenados) - 1) * p / 100
    piso = math.floor(posicion)
    techo = math.ceil(posicion)
    if piso == techo:
        return float(ordenados[int(posicion)])
    peso = posicion - piso
    return ordenados[piso] * (1 - peso) + ordenados[techo] * peso


def agregar(valores: list[int | float]) -> dict:
    """Resumen estadístico de una lista de montos.

    Con lista vacía devuelve ``n=0`` y todo en ``None`` (no explota).
    """
    if not valores:
        return {
            "n": 0,
            "mediana": None,
            "p25": None,
            "p75": None,
            "min": None,
            "max": None,
        }
    limpios = [float(v) for v in valores]
    return {
        "n": len(limpios),
        "mediana": _redondear(statistics.median(limpios)),
        "p25": _redondear(percentil(limpios, 25)),
        "p75": _redondear(percentil(limpios, 75)),
        "min": int(min(limpios)),
        "max": int(max(limpios)),
    }


def _redondear(valor: float | None) -> int | None:
    return None if valor is None else int(round(valor))


def agregar_rubro(avisos: list[dict], bloqueados: frozenset[int] | set[int] = frozenset()) -> dict:
    """Agrega un rubro: filtros, outliers, estadísticas y detalle de avisos."""
    filtro = filtrar_avisos(avisos, bloqueados)

    medios = [int(round((a["salario_min"] + a["salario_max"]) / 2)) for a in filtro.validos]
    limpios, atipicos = quitar_atipicos(medios)
    filtro.atipico = atipicos

    resumen = agregar(limpios)
    permitidos = set(limpios)
    resumen["avisos"] = [
        a
        for a in filtro.validos
        if int(round((a["salario_min"] + a["salario_max"]) / 2)) in permitidos
    ]
    resumen["suficiente"] = resumen["n"] >= MINIMO_MUESTRA
    if resumen["n"] < MINIMO_PUBLICABLE:
        # Con una o dos ofertas no se publica mediana: no describe nada.
        resumen["mediana"] = None
        resumen["p25"] = None
        resumen["p75"] = None
    resumen["_filtro"] = filtro
    return resumen
