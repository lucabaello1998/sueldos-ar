"""Agregados estadísticos y actualización del histórico."""

from __future__ import annotations

import pytest

from tools.observatorio.construir import actualizar_historico, detectar_relleno
from tools.observatorio.graficar import formatear_pesos, svg_barras, svg_linea
from tools.observatorio.normalizar import (
    Monto,
    agregar,
    agregar_rubro,
    es_ruido_no_tech,
    es_sintetico,
    parsear_monto,
    percentil,
    quitar_atipicos,
)

# --------------------------------------------------------------------------
# Lista vacía
# --------------------------------------------------------------------------


def test_agregar_lista_vacia_no_explota() -> None:
    resumen = agregar([])
    assert resumen == {
        "n": 0,
        "mediana": None,
        "p25": None,
        "p75": None,
        "min": None,
        "max": None,
    }


def test_percentil_lista_vacia() -> None:
    assert percentil([], 25) is None
    assert percentil([], 75) is None


# --------------------------------------------------------------------------
# Mediana / p25 / p75
# --------------------------------------------------------------------------


def test_mediana_lista_impar() -> None:
    resumen = agregar([300, 100, 200])
    assert resumen["n"] == 3
    assert resumen["mediana"] == 200
    assert resumen["min"] == 100
    assert resumen["max"] == 300


def test_mediana_lista_par_promedia_los_del_medio() -> None:
    resumen = agregar([400, 100, 300, 200])
    assert resumen["mediana"] == 250


def test_p25_p75_lista_par() -> None:
    resumen = agregar([100, 200, 300, 400])
    assert resumen["p25"] == 175
    assert resumen["p75"] == 325


def test_p25_p75_lista_impar() -> None:
    resumen = agregar([100, 200, 300])
    assert resumen["p25"] == 150
    assert resumen["p75"] == 250


def test_un_solo_valor() -> None:
    resumen = agregar([1_850_000])
    assert resumen == {
        "n": 1,
        "mediana": 1850000,
        "p25": 1850000,
        "p75": 1850000,
        "min": 1850000,
        "max": 1850000,
    }


def test_percentil_no_depende_del_orden() -> None:
    assert percentil([400, 100, 300, 200], 50) == pytest.approx(250)
    assert percentil([100, 200, 300, 400], 50) == pytest.approx(250)


def test_agregar_devuelve_enteros() -> None:
    resumen = agregar([100, 201, 302])
    assert isinstance(resumen["mediana"], int)
    assert isinstance(resumen["p25"], int)
    assert isinstance(resumen["p75"], int)


# --------------------------------------------------------------------------
# Agregación por rubro
# --------------------------------------------------------------------------


def _aviso(url: str, minimo: int | None, maximo: int | None) -> dict:
    return {
        "titulo": url,
        "empresa": "ACME",
        "url": url,
        "salario_min": minimo,
        "salario_max": maximo,
    }


def test_agregar_rubro_con_rango_usa_punto_medio() -> None:
    avisos = [
        _aviso("a", 800_000, 1_200_000),  # medio 1.000.000
        _aviso("b", 2_000_000, 2_000_000),
        _aviso("c", 3_000_000, 3_000_000),
        _aviso("d", None, None),
    ]
    resumen = agregar_rubro(avisos)
    assert resumen["n"] == 3
    assert resumen["mediana"] == 2_000_000
    assert resumen["min"] == 1_000_000
    assert resumen["max"] == 3_000_000
    assert resumen["_filtro"].sin_salario == 1
    assert len(resumen["avisos"]) == 3


def test_agregar_rubro_sin_avisos_validos() -> None:
    avisos = [_aviso("a", None, None), _aviso("b", 2000, 2000)]
    resumen = agregar_rubro(avisos)
    assert resumen["n"] == 0
    assert resumen["mediana"] is None
    assert resumen["avisos"] == []


def test_spam_no_se_aplica_con_muestra_chica() -> None:
    """Con 2 avisos iguales el 40% no es significativo: no se descarta nada."""
    avisos = [_aviso("a", 2_000_000, 2_000_000), _aviso("b", 2_000_000, 2_000_000)]
    resumen = agregar_rubro(avisos)
    assert resumen["n"] == 2
    assert resumen["_filtro"].spam == 0


# --------------------------------------------------------------------------
# Histórico idempotente
# --------------------------------------------------------------------------


def test_historico_no_duplica_el_mismo_dia() -> None:
    sueldos = {
        "mediana_general": 1_800_000,
        "rubros": [{"id": "desarrollador", "mediana": 1_800_000, "n": 4}],
    }
    primera = actualizar_historico({"corridas": []}, sueldos, "2026-10-30")
    segunda = actualizar_historico(primera, sueldos, "2026-10-30")
    assert len(segunda["corridas"]) == 1
    assert primera == segunda


def test_historico_ordena_por_fecha() -> None:
    sueldos = {"mediana_general": 1, "rubros": []}
    historico = actualizar_historico({"corridas": []}, sueldos, "2026-10-30")
    historico = actualizar_historico(historico, sueldos, "2026-09-01")
    historico = actualizar_historico(historico, sueldos, "2026-11-15")
    assert [c["fecha"] for c in historico["corridas"]] == [
        "2026-09-01",
        "2026-10-30",
        "2026-11-15",
    ]


def test_historico_reemplaza_la_corrida_del_dia() -> None:
    sueldos_viejo = {"mediana_general": 1, "rubros": [{"id": "devops", "mediana": 100, "n": 1}]}
    sueldos_nuevo = {"mediana_general": 2, "rubros": [{"id": "devops", "mediana": 999, "n": 9}]}
    historico = actualizar_historico({"corridas": []}, sueldos_viejo, "2026-10-30")
    historico = actualizar_historico(historico, sueldos_nuevo, "2026-10-30")
    assert len(historico["corridas"]) == 1
    assert historico["corridas"][0]["rubros"][0]["mediana"] == 999


# --------------------------------------------------------------------------
# Gráficos
# --------------------------------------------------------------------------


def test_formatear_pesos_abrevia() -> None:
    assert formatear_pesos(1_850_000) == "$ 1,85 M"
    assert formatear_pesos(950_000) == "$ 950 K"
    assert formatear_pesos(None) == "s/d"


def test_svg_barras_sin_datos_no_explota() -> None:
    svg = svg_barras([])
    assert svg.startswith("<svg")
    assert "Sin rubros" in svg


def test_svg_barras_dibuja_los_rubros() -> None:
    rubros = [
        {"id": "devops", "nombre": "DevOps", "n": 5, "mediana": 2_500_000},
        {"id": "qa", "nombre": "QA", "n": 3, "mediana": 1_500_000},
    ]
    svg = svg_barras(rubros)
    assert svg.count("<rect") == 2
    assert "DevOps" in svg
    assert "$ 2,50 M" in svg


def test_svg_linea_necesita_dos_corridas() -> None:
    assert svg_linea({"corridas": [{"fecha": "2026-10-30", "rubros": []}]}) is None


def test_svg_linea_con_dos_corridas() -> None:
    historico = {
        "corridas": [
            {"fecha": "2026-10-01", "rubros": [{"id": "devops", "mediana": 1_000_000, "n": 3}]},
            {"fecha": "2026-10-30", "rubros": [{"id": "devops", "mediana": 1_200_000, "n": 4}]},
        ]
    }
    svg = svg_linea(historico)
    assert svg is not None
    assert svg.count("<path") == 1
    assert svg.count("<circle") == 2


def test_punto_medio_de_rango_invertido() -> None:
    monto = parsear_monto("$ 1.200.000,00 - $ 800.000,00")
    assert monto is not None
    assert (monto.minimo, monto.maximo) == (800000, 1200000)


def test_monto_es_rango() -> None:
    assert not Monto(1, 1).es_rango
    assert Monto(1, 2).es_rango


# --------------------------------------------------------------------------
# Filtros nuevos: relleno, ruido no tech y atípicos
# --------------------------------------------------------------------------


@pytest.mark.parametrize("valor", [1111111, 2222222, 323232, 9999999, 1234567, 11111, 4444])
def test_detecta_montos_de_relleno(valor: int) -> None:
    assert es_sintetico(valor)


@pytest.mark.parametrize(
    "valor", [2000000, 1500000, 1850000, 3200000, 900000, 1234500, 2000, 70000]
)
def test_no_confunde_sueldos_redondos_con_relleno(valor: int) -> None:
    assert not es_sintetico(valor)


@pytest.mark.parametrize(
    "titulo",
    [
        "Programador CNC Fresador en Italia",
        "Asesor comercial y desarrollador de negocios B2B",
        "Técnico de mantenimiento",
        "Operario de producción",
    ],
)
def test_detecta_avisos_que_no_son_tech(titulo: str) -> None:
    assert es_ruido_no_tech(titulo)


@pytest.mark.parametrize(
    "titulo",
    [
        "Desarrollador Backend Java Senior",
        "Analista de datos",
        "DevOps Engineer",
        "",
    ],
)
def test_no_marca_avisos_tech_como_ruido(titulo: str) -> None:
    assert not es_ruido_no_tech(titulo)


def test_quitar_atipicos_con_muestra_suficiente() -> None:
    valores = [1_000_000, 1_100_000, 1_200_000, 1_300_000, 1_400_000, 15_000_000]
    limpios, fuera = quitar_atipicos(valores)
    assert fuera == 1
    assert 15_000_000 not in limpios


def test_quitar_atipicos_no_toca_muestras_chicas() -> None:
    valores = [1_000_000, 5_000_000, 9_000_000, 1_200_000]
    limpios, fuera = quitar_atipicos(valores)
    assert fuera == 0
    assert limpios == valores


def test_agregar_rubro_marca_muestra_insuficiente() -> None:
    avisos = [_aviso("a", 1_800_000, 1_800_000), _aviso("b", 2_000_000, 2_000_000)]
    resumen = agregar_rubro(avisos)
    assert resumen["suficiente"] is False


def test_agregar_rubro_marca_muestra_suficiente() -> None:
    avisos = [_aviso(f"a{i}", 1_800_000 + i * 100_000, 1_800_000 + i * 100_000) for i in range(5)]
    resumen = agregar_rubro(avisos)
    assert resumen["suficiente"] is True


def test_agregar_rubro_no_publica_mediana_con_dos_avisos() -> None:
    avisos = [_aviso("a", 1_800_000, 1_800_000), _aviso("b", 2_100_000, 2_100_000)]
    resumen = agregar_rubro(avisos)
    assert resumen["n"] == 2
    assert resumen["mediana"] is None
    assert resumen["suficiente"] is False


# --------------------------------------------------------------------------
# Detección de montos de relleno repetidos en toda la corrida
# --------------------------------------------------------------------------


def _aviso_dict(url: str, monto: int) -> dict:
    return {
        "titulo": f"puesto {url}",
        "empresa": "",
        "url": url,
        "salario_min": monto,
        "salario_max": monto,
    }


def test_detectar_relleno_marca_monto_no_redondo_repetido() -> None:
    por_rubro = {
        "backend": [_aviso_dict(f"a{i}", 1_323_233) for i in range(3)],
        "frontend": [_aviso_dict(f"b{i}", 1_323_233) for i in range(2)],
    }
    assert detectar_relleno(por_rubro) == {1_323_233}


def test_detectar_relleno_no_marca_sueldo_redondo() -> None:
    por_rubro = {"backend": [_aviso_dict(f"a{i}", 2_000_000) for i in range(8)]}
    assert detectar_relleno(por_rubro) == set()


def test_detectar_relleno_ignora_muestra_chica() -> None:
    por_rubro = {"backend": [_aviso_dict(f"a{i}", 1_323_233) for i in range(4)]}
    assert detectar_relleno(por_rubro) == set()


def test_detectar_relleno_no_cuenta_centinelas() -> None:
    por_rubro = {"backend": [_aviso_dict(f"a{i}", 11_111) for i in range(10)]}
    assert detectar_relleno(por_rubro) == set()
