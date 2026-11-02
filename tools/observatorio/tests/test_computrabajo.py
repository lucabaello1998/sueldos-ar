"""Parseo del listado de Computrabajo y filtros de sanidad sobre montos."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.observatorio.fuentes.computrabajo import (
    Aviso,
    hay_siguiente,
    parsear_avisos,
    permitido,
)
from tools.observatorio.normalizar import (
    MAXIMO,
    MINIMO,
    Monto,
    agregar_rubro,
    es_centinela,
    filtrar_avisos,
    fuera_de_rango,
    parsear_monto,
    parsear_numero,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture(scope="module")
def html_listado() -> str:
    return (FIXTURES / "computrabajo-desarrollador.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def avisos(html_listado: str) -> list[Aviso]:
    return parsear_avisos(html_listado)


# --------------------------------------------------------------------------
# Montos en formato argentino
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("1.234.567,89", 1234567.89),
        ("2.000.000,00", 2000000.0),
        ("11111", 11111.0),
        ("$ 950.000", 950000.0),
        ("1.111.111", 1111111.0),
    ],
)
def test_parsear_numero_arg(texto: str, esperado: float) -> None:
    assert parsear_numero(texto) == pytest.approx(esperado)


def test_parsear_monto_simple() -> None:
    monto = parsear_monto("$ 2.000.000,00 (Mensual)")
    assert monto is not None
    assert (monto.minimo, monto.maximo) == (2000000, 2000000)
    assert monto.punto_medio == 2000000
    assert not monto.es_rango


def test_parsear_monto_rango() -> None:
    monto = parsear_monto("$ 800.000,00 - $ 1.200.000,00 (Mensual)")
    assert monto is not None
    assert (monto.minimo, monto.maximo) == (800000, 1200000)
    assert monto.es_rango
    assert monto.punto_medio == 1000000


def test_parsear_monto_sin_periodo_asume_mensual() -> None:
    monto = parsear_monto("$ 1.500.000,00")
    assert monto is not None
    assert monto.periodo == "mensual"
    assert monto.punto_medio == 1500000


def test_parsear_monto_anual_se_lleva_a_mensual() -> None:
    monto = parsear_monto("$ 24.000.000,00 (Anual)")
    assert monto is not None
    assert monto.periodo == "anual"
    assert monto.punto_medio == 2000000


@pytest.mark.parametrize("texto", [None, "", "A convenir", "(Mensual)"])
def test_parsear_monto_sin_valor(texto: str | None) -> None:
    assert parsear_monto(texto) is None


# --------------------------------------------------------------------------
# Filtros de sanidad
# --------------------------------------------------------------------------


@pytest.mark.parametrize("valor", [11111, 2222, 2000, 9999999])
def test_centinelas(valor: int) -> None:
    assert es_centinela(Monto(valor, valor))
    resultado = filtrar_avisos(
        [{"titulo": "t", "empresa": "", "url": "u", "salario_min": valor, "salario_max": valor}]
    )
    assert resultado.centinela == 1
    assert resultado.validos == []


def test_fuera_de_rango() -> None:
    assert fuera_de_rango(Monto(MINIMO - 1, MINIMO - 1))
    assert fuera_de_rango(Monto(MAXIMO + 1, MAXIMO + 1))
    assert not fuera_de_rango(Monto(MINIMO, MINIMO))
    assert not fuera_de_rango(Monto(MAXIMO, MAXIMO))

    resultado = filtrar_avisos(
        [
            {
                "titulo": "bajo",
                "empresa": "",
                "url": "a",
                "salario_min": 100000,
                "salario_max": 100000,
            },
            {
                "titulo": "alto",
                "empresa": "",
                "url": "b",
                "salario_min": 50_000_000,
                "salario_max": 50_000_000,
            },
        ]
    )
    assert resultado.fuera_de_rango == 2
    assert resultado.validos == []


def test_descarta_centinela_antes_que_rango() -> None:
    """Un centinela también está fuera de rango: se cuenta una sola vez."""
    resultado = filtrar_avisos(
        [{"titulo": "t", "empresa": "", "url": "u", "salario_min": 2222, "salario_max": 2222}]
    )
    assert resultado.centinela == 1
    assert resultado.fuera_de_rango == 0


def test_descarta_spam_repetido() -> None:
    """El mismo monto en más del 40% de los avisos con salario es spam."""
    avisos = [
        {
            "titulo": f"spam {i}",
            "empresa": "",
            "url": f"s{i}",
            "salario_min": 900000,
            "salario_max": 900000,
        }
        for i in range(5)
    ] + [
        {
            "titulo": "ok",
            "empresa": "",
            "url": "o1",
            "salario_min": 2000000,
            "salario_max": 2000000,
        },
        {
            "titulo": "ok",
            "empresa": "",
            "url": "o2",
            "salario_min": 3000000,
            "salario_max": 3000000,
        },
        {
            "titulo": "ok",
            "empresa": "",
            "url": "o3",
            "salario_min": 4000000,
            "salario_max": 4000000,
        },
    ]
    resultado = filtrar_avisos(avisos)
    assert resultado.spam == 5
    assert len(resultado.validos) == 3
    assert all(a["salario_min"] != 900000 for a in resultado.validos)


def test_no_descarta_si_el_monto_es_minoria() -> None:
    avisos = [
        {
            "titulo": f"a{i}",
            "empresa": "",
            "url": f"u{i}",
            "salario_min": 2000000,
            "salario_max": 2000000,
        }
        for i in range(2)
    ] + [
        {"titulo": "b", "empresa": "", "url": "b1", "salario_min": 3000000, "salario_max": 3000000},
        {"titulo": "c", "empresa": "", "url": "c1", "salario_min": 4000000, "salario_max": 4000000},
        {"titulo": "d", "empresa": "", "url": "d1", "salario_min": 5000000, "salario_max": 5000000},
    ]
    resultado = filtrar_avisos(avisos)
    assert resultado.spam == 0
    assert len(resultado.validos) == 5


def test_aviso_sin_salario_no_cuenta_como_descarte() -> None:
    resultado = filtrar_avisos(
        [{"titulo": "t", "empresa": "", "url": "u", "salario_min": None, "salario_max": None}]
    )
    assert resultado.sin_salario == 1
    assert resultado.total_descartados == 0


# --------------------------------------------------------------------------
# Listado real
# --------------------------------------------------------------------------


def test_cantidad_de_avisos_del_fixture(avisos: list[Aviso]) -> None:
    """El fixture es un listado real: 20 tarjetas, 8 con salario declarado."""
    assert len(avisos) == 20
    con_salario = [a for a in avisos if a.salario_texto]
    assert len(con_salario) == 8


def test_avisos_del_fixture_tienen_titulo_y_url(avisos: list[Aviso]) -> None:
    for aviso in avisos:
        assert aviso.titulo
        assert aviso.url.startswith("https://ar.computrabajo.com/")
        assert "#" not in aviso.url


def test_salarios_del_fixture_se_parsean(avisos: list[Aviso]) -> None:
    montos = [parsear_monto(a.salario_texto) for a in avisos if a.salario_texto]
    assert all(m is not None for m in montos)
    # El fixture trae basura a propósito: hay centinelas y un monto absurdo.
    assert any(es_centinela(m) for m in montos if m)


def test_agregacion_del_fixture_descarta_la_basura(avisos: list[Aviso]) -> None:
    """De 8 avisos con salario, sobreviven solo los montos plausibles."""
    internos = []
    for aviso in avisos:
        monto = parsear_monto(aviso.salario_texto)
        internos.append(
            {
                "titulo": aviso.titulo,
                "empresa": aviso.empresa,
                "url": aviso.url,
                "salario_min": monto.minimo if monto else None,
                "salario_max": monto.maximo if monto else None,
            }
        )
    resumen = agregar_rubro(internos)
    filtro = resumen["_filtro"]
    assert filtro.sin_salario == 12
    # Antes de mirar el monto se descartan los avisos que no son tech.
    assert filtro.no_tech == 2
    assert filtro.centinela == 5  # 2.000 · 11.111 · 2.222 · 9.999.999
    assert filtro.fuera_de_rango == 0
    assert filtro.spam == 0
    # El "Programador CNC" de $ 2.000.000 no es un aviso tech: ya se descartó.
    assert resumen["n"] == 1
    # Con un solo aviso no se publica mediana.
    assert resumen["mediana"] is None
    assert resumen["suficiente"] is False


def test_hay_siguiente_pagina(html_listado: str) -> None:
    assert hay_siguiente(html_listado)


def test_robots_permite_listados() -> None:
    reglas = [
        "/hojas-de-vida/*",
        "/ofertas-de-trabajo/*sal=",
        "/Ajax/*",
    ]
    assert permitido("https://ar.computrabajo.com/trabajo-de-desarrollador", reglas)
    assert permitido("https://ar.computrabajo.com/trabajo-de-devops?p=2", reglas)
    assert not permitido("https://ar.computrabajo.com/Ajax/foo", reglas)
    assert not permitido("https://ar.computrabajo.com/ofertas-de-trabajo/x?sal=100", reglas)
