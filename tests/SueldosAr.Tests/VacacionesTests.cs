using SueldosAr.Core.Calculadoras;
using Xunit;

namespace SueldosAr.Tests;

public class VacacionesTests
{
    [Theory]
    [InlineData(0, 14)]
    [InlineData(4, 14)]
    [InlineData(5, 21)]
    [InlineData(9, 21)]
    [InlineData(10, 28)]
    [InlineData(19, 28)]
    [InlineData(20, 35)]
    [InlineData(35, 35)]
    public void Los_dias_salen_del_art_150(int anios, int esperados)
    {
        Assert.Equal(esperados, Vacaciones.DiasPorAntiguedad(anios));
    }

    [Fact]
    public void La_antiguedad_que_cuenta_es_la_del_31_de_diciembre_anterior()
    {
        var ingreso = new DateOnly(2020, 8, 15);

        // En 2026 se computa la antigüedad al 31/12/2025: 5 años.
        Assert.Equal(5, Vacaciones.AniosParaDias(ingreso, 2026));
    }

    [Fact]
    public void El_pago_es_el_bruto_dividido_25_por_los_dias()
    {
        var r = Vacaciones.Calcular(new DateOnly(2015, 1, 1), 2026, 1_000_000m);

        Assert.Equal(28, r.DiasCorresponden);
        Assert.Equal(40_000m, r.ValorDia);
        Assert.Equal(1_120_000m, r.Importe);
    }

    [Fact]
    public void Se_pueden_tomar_menos_dias_de_los_que_corresponden()
    {
        var r = Vacaciones.Calcular(new DateOnly(2015, 1, 1), 2026, 1_000_000m, diasTomados: 7);

        Assert.Equal(7, r.DiasTomados);
        Assert.Equal(280_000m, r.Importe);
    }

    [Fact]
    public void No_se_pueden_tomar_mas_dias_de_los_que_corresponden()
    {
        Assert.Throws<ArgumentOutOfRangeException>(() =>
            Vacaciones.Calcular(new DateOnly(2015, 1, 1), 2026, 1_000_000m, diasTomados: 40));
    }

    [Fact]
    public void Dias_corridos_cuentan_ambos_extremos()
    {
        Assert.Equal(15, Vacaciones.DiasCorridos(new DateOnly(2026, 1, 1), new DateOnly(2026, 1, 15)));
    }

    [Fact]
    public void Un_rango_invertido_es_un_error()
    {
        Assert.Throws<ArgumentException>(() =>
            Vacaciones.DiasCorridos(new DateOnly(2026, 2, 1), new DateOnly(2026, 1, 1)));
    }
}
