"""Regresiones del gauntlet del observatorio: datos que no se pueden publicar
como si fueran buenos (o que directamente rompían la corrida)."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tools.observatorio import construir, graficar
from tools.observatorio.fuentes import computrabajo, indec
from tools.observatorio.normalizar import parsear_monto

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_un_salario_por_hora_no_se_publica_como_mensual():
    monto = parsear_monto("$ 200.000 (Hora)")
    assert monto is not None and monto.periodo == "hora"

    aviso = computrabajo.Aviso(
        titulo="Desarrollador Backend",
        empresa="Acme",
        url="https://example.com/1",
        salario_texto="$ 200.000 (Hora)",
    )

    assert construir._avisos_a_dicts([aviso]) == []


def test_un_fixture_ausente_no_se_reemplaza_por_el_de_otro_rubro(tmp_path):
    # Antes, QA heredaba los 20 avisos de "desarrollador" sin avisar.
    (tmp_path / "computrabajo-desarrollador.html").write_text("<html></html>", encoding="utf-8")

    with pytest.raises(computrabajo.ErrorFuente):
        computrabajo.leer_fixture(tmp_path, "qa")


def test_una_corrida_sin_datos_no_escribe_nada(tmp_path):
    docs = tmp_path / "docs"
    resultado = construir.ejecutar(
        offline=True,
        docs=docs,
        fixtures=tmp_path / "sin-fixtures",
        terminos=[{"rubro": "qa", "nombre": "QA", "slug": "qa"}],
        generado=datetime(2026, 11, 11, tzinfo=UTC),
    )

    assert resultado["archivos"] == []
    assert not (docs / "data" / "sueldos.json").exists()
    assert any("no se tocó ningún archivo" in w for w in resultado["warnings"])


def test_un_historico_truncado_aborta_y_conserva_el_archivo(tmp_path):
    docs = tmp_path / "docs"
    datos = docs / "data"
    datos.mkdir(parents=True)
    roto = datos / "historico.json"
    roto.write_text("{truncado", encoding="utf-8")

    with pytest.raises(ValueError, match="corrupto"):
        construir.ejecutar(
            offline=True,
            docs=docs,
            fixtures=FIXTURES,
            terminos=[{"rubro": "desarrollo", "nombre": "Desarrollo", "slug": "desarrollador"}],
            generado=datetime(2026, 11, 11, tzinfo=UTC),
        )

    assert roto.read_text(encoding="utf-8") == "{truncado"


def test_la_variacion_interanual_usa_la_fecha_exacta():
    # Con un hueco, la "posición 13" es de hace 24 meses: mejor no publicar nada.
    con_hueco = {
        f"2020-{mes:02d}-01": 100.0 + i for i, mes in enumerate((1, 3, 5, 7, 9, 11), start=1)
    }
    con_hueco["2022-01-01"] = 200.0
    assert indec._variacion_12m(con_hueco) is None

    completa = {"2025-11-01": 100.0, "2026-11-01": 150.0}
    assert indec._variacion_12m(completa) == 50.0


def test_una_serie_toda_en_nulo_es_un_faltante_y_no_un_crash(monkeypatch):
    # Una serie con todos los valores en null dejaba `serie` vacío y `max()` explotaba
    # dentro de _armar, tumbando todo el pipeline.
    monkeypatch.setattr(
        indec, "_get_json", lambda url: {"data": [["2026-01-01", None]], "meta": [{}]}
    )

    datos = indec.obtener(hoy=datetime(2026, 11, 11, tzinfo=UTC))

    assert datos["disponible"] is False
    assert datos["series"] == []
    assert datos["faltantes"]


def test_el_informe_no_inventa_ejemplos_de_relleno():
    sueldos = {
        "rubros": [{"id": "backend", "n": 10, "mediana": 2_000_000}],
        "descartados": {},
        "mediana_general": 2_000_000,
        "n_general": 10,
        "transparencia": {
            "ofertas_unicas": 10,
            "declaran_salario": 10,
            "declaran_salario_pct": 100.0,
            "monto_plausible": 10,
            "monto_plausible_pct": 100.0,
            "montos_repetidos": [],
        },
        "resumen_corrida": {"terminos_consultados": 3, "terminos_sin_datos": []},
    }

    html = graficar.generar_html(sueldos, {"corridas": []}, {"series": []})

    # El fallback inventaba "11.111, 2.222" para explicar los descartes.
    assert "<code>11.111</code>" not in html
    assert "<code>2.222</code>" not in html
    assert "valores de relleno como" not in html


def test_el_informe_avisa_cuando_la_muestra_es_parcial():
    sueldos = {
        "rubros": [{"id": "backend", "n": 10, "mediana": 2_000_000}],
        "descartados": {},
        "mediana_general": 2_000_000,
        "n_general": 10,
        "transparencia": {
            "ofertas_unicas": 10,
            "declaran_salario": 10,
            "declaran_salario_pct": 100.0,
            "monto_plausible": 5,
            "monto_plausible_pct": 50.0,
            "montos_repetidos": [],
        },
        "resumen_corrida": {"terminos_consultados": 4, "terminos_sin_datos": ["qa", "devops"]},
    }

    html = graficar.generar_html(sueldos, {"corridas": []}, {"series": []})

    assert "muestra es parcial" in html
    assert "2 de las 4" in html


def test_el_json_del_observatorio_no_lleva_duplicados_en_los_terminos_sin_datos():
    terminos = [
        {"rubro": "qa", "nombre": "QA", "slug": "qa-1"},
        {"rubro": "qa", "nombre": "QA", "slug": "qa-2"},
        {"rubro": "backend", "nombre": "Backend", "slug": "backend"},
    ]
    sueldos = construir.construir_sueldos({}, terminos, datetime(2026, 11, 11, tzinfo=UTC))

    assert sueldos["resumen_corrida"]["terminos_sin_datos"] == ["backend", "qa"]
    assert json.dumps(sueldos)  # serializable
