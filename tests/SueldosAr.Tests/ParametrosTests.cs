using SueldosAr.Core.Carga;
using SueldosAr.Core.Modelos;
using Xunit;

namespace SueldosAr.Tests;

public class ParametrosTests
{
    [Fact]
    public void Carga_el_juego_de_parametros_desde_el_json_embebido()
    {
        var p = ParametrosRepositorio.Obtener("2024-07");

        Assert.Equal("2024-07", p.Id);
        Assert.Equal(new DateOnly(2024, 7, 1), p.VigenciaDesde);
        Assert.False(p.Estimado);
        Assert.False(string.IsNullOrWhiteSpace(p.Fuente));
    }

    [Fact]
    public void La_escala_de_la_ley_tiene_nueve_tramos()
    {
        var escala = ParametrosRepositorio.Obtener("2024-07").Escala;

        Assert.Equal(9, escala.Tramos.Count);
        Assert.Equal(0.05m, escala.Tramos[0].Aliquota);
        Assert.Equal(0.35m, escala.Tramos[^1].Aliquota);
    }

    [Fact]
    public void Los_tramos_quedan_ordenados_por_techo()
    {
        var tramos = ParametrosRepositorio.Obtener("2024-07").Escala.Tramos;

        for (var i = 1; i < tramos.Count; i++)
            Assert.True(tramos[i].Hasta > tramos[i - 1].Hasta);
    }

    [Fact]
    public void Para_un_periodo_posterior_a_la_vigencia_usa_el_ultimo_disponible()
    {
        var p = ParametrosRepositorio.ParaPeriodo(new Periodo(2026, 3));

        Assert.Equal("2024-07", p.Id);
    }

    [Fact]
    public void Un_id_inexistente_falla_con_un_mensaje_claro()
    {
        var ex = Assert.Throws<KeyNotFoundException>(() => ParametrosRepositorio.Obtener("1999-01"));
        Assert.Contains("1999-01", ex.Message);
    }

    [Fact]
    public void Las_tasas_de_aportes_estan_en_el_rango_legal()
    {
        var p = ParametrosRepositorio.Obtener("2024-07");

        Assert.Equal(0.11m, p.TasaJubilacion);
        Assert.Equal(0.03m, p.TasaObraSocial);
        Assert.Equal(0.03m, p.TasaPami);
        Assert.Equal(70, p.EdadPami);
    }
}
