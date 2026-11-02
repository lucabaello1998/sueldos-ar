"""Series oficiales del INDEC: descarga, armado y modo offline."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tools.observatorio.fuentes.indec import (
    SERIES,
    _meses_entre,
    _variacion_12m,
    obtener,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture(scope="module")
def offline() -> dict:
    return obtener(offline=True, fixtures=FIXTURES)


def test_hay_cinco_series_definidas() -> None:
    assert len(SERIES) == 5
    claves = {s["clave"] for s in SERIES}
    assert claves == {
        "remuneracion_promedio",
        "indice_total",
        "indice_privado",
        "indice_publico",
        "indice_no_registrado",
    }


def test_offline_lee_el_fixture(offline: dict) -> None:
    assert offline["disponible"] is True
    assert len(offline["series"]) == 5
    assert offline["faltantes"] == []


def test_offline_trae_la_serie_en_pesos(offline: dict) -> None:
    pesos = [s for s in offline["series"] if s["tipo"] == "pesos"]
    assert len(pesos) == 1
    serie = pesos[0]
    assert serie["unidades"] == "Pesos"
    assert serie["ultimo"] > 100_000
    assert serie["serie"][serie["hasta"]] == serie["ultimo"]


def test_offline_series_de_indice_tienen_variacion(offline: dict) -> None:
    indices = [s for s in offline["series"] if s["tipo"] == "indice"]
    assert indices
    for serie in indices:
        assert serie["ultimo"] > 0
        assert isinstance(serie["variacion_12m_pct"], float)


def test_offline_sin_fixture_no_explota(tmp_path: Path) -> None:
    resultado = obtener(offline=True, fixtures=tmp_path)
    assert resultado["disponible"] is False
    assert "fixture" in resultado["motivo"]
    assert resultado["series"] == []


def test_offline_con_fixture_invalido(tmp_path: Path) -> None:
    (tmp_path / "indec-series.json").write_text("{no es json", encoding="utf-8")
    resultado = obtener(offline=True, fixtures=tmp_path)
    assert resultado["disponible"] is False
    assert "inválido" in resultado["motivo"]


def test_variacion_12m() -> None:
    serie = {f"2025-{m:02d}-01": 100.0 for m in range(1, 13)}
    serie["2026-01-01"] = 150.0
    assert _variacion_12m(serie) == 50.0


def test_variacion_12m_sin_historia() -> None:
    assert _variacion_12m({"2026-01-01": 1.0}) is None


def test_meses_entre() -> None:
    assert _meses_entre("2025-01-01", "2026-01-01") == 12
    assert _meses_entre("2026-01-01", "2026-03-01") == 2


def test_obtener_nunca_levanta_excepcion() -> None:
    """Aunque la API falle, ``obtener`` devuelve un dict."""
    hoy = datetime(2026, 10, 30, tzinfo=UTC)
    resultado = obtener(offline=True, fixtures=FIXTURES, hoy=hoy)
    assert isinstance(resultado, dict)
    assert "consultado" in resultado
