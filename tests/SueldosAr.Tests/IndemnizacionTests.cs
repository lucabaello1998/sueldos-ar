using SueldosAr.Core.Calculadoras;
using SueldosAr.Core.Modelos;
using Xunit;

namespace SueldosAr.Tests;

public class IndemnizacionTests
{
    private static Empleado Con(decimal basico, DateOnly ingreso, decimal? mejor = null) => new()
    {
        Nombre = "Despedido de prueba",
        SueldoBasico = basico,
        FechaIngreso = ingreso,
        Edad = 40,
        MejorRemuneracionSemestre = mejor
    };

    [Fact]
    public void Un_mes_por_anio_sobre_la_mejor_remuneracion()
    {
        var r = Indemnizacion.Calcular(Con(1_000_000m, new DateOnly(2016, 3, 1)), new DateOnly(2026, 3, 10), Fixture.Parametros2024);

        Assert.Equal(10, r.AniosComputados);
        Assert.Equal(10_000_000m, r.Antiguedad);
        Assert.Equal(2, r.MesesPreaviso);
        Assert.Equal(2_000_000m, r.Preaviso);
    }

    [Fact]
    public void La_fraccion_mayor_a_tres_meses_cuenta_como_un_anio()
    {
        var conCuatroMeses = Indemnizacion.AniosConFraccion(new DateOnly(2020, 1, 10), new DateOnly(2024, 5, 20));
        var conDosMeses = Indemnizacion.AniosConFraccion(new DateOnly(2020, 1, 10), new DateOnly(2024, 3, 20));

        Assert.Equal(5, conCuatroMeses);
        Assert.Equal(4, conDosMeses);
    }

    [Fact]
    public void Integra_el_mes_de_despido_y_el_sac_proporcional()
    {
        var r = Indemnizacion.Calcular(Con(1_000_000m, new DateOnly(2016, 3, 1)), new DateOnly(2026, 3, 10), Fixture.Parametros2024);

        // Marzo tiene 31 días: quedan 21.
        Assert.Equal(700_000m, r.IntegracionMesDespido);
        // Enero a marzo del semestre: 3/12 de la indemnización por antigüedad.
        Assert.Equal(2_500_000m, r.SacSobreIndemnizacion);
        Assert.Equal(15_200_000m, r.Total);
    }

    [Fact]
    public void Menos_de_cinco_anios_lleva_un_mes_de_preaviso()
    {
        var r = Indemnizacion.Calcular(Con(1_000_000m, new DateOnly(2022, 1, 1)), new DateOnly(2026, 1, 31), Fixture.Parametros2024);

        Assert.Equal(1, r.MesesPreaviso);
        Assert.Equal(1_000_000m, r.Preaviso);
    }

    [Fact]
    public void Aplica_el_tope_del_art_245_cuando_esta_configurado()
    {
        var parametros = Fixture.Parametros2024 with { TopeIndemnizacion = 800_000m };
        var r = Indemnizacion.Calcular(Con(1_000_000m, new DateOnly(2016, 3, 1)), new DateOnly(2026, 3, 10), parametros);

        Assert.True(r.TopeAplicado);
        Assert.Equal(8_000_000m, r.Antiguedad);
    }

    [Fact]
    public void Aplica_el_piso_cuando_la_remuneracion_es_muy_baja()
    {
        var parametros = Fixture.Parametros2024 with { PisoIndemnizacion = 1_500_000m };
        var r = Indemnizacion.Calcular(Con(600_000m, new DateOnly(2020, 1, 1)), new DateOnly(2026, 1, 31), parametros);

        Assert.True(r.PisoAplicado);
        Assert.Equal(1_500_000m * 6, r.Antiguedad);
    }

    [Fact]
    public void El_primer_anio_incompleto_cuenta_como_un_anio()
    {
        var r = Indemnizacion.Calcular(Con(1_000_000m, new DateOnly(2025, 11, 1)), new DateOnly(2026, 2, 28), Fixture.Parametros2024);

        Assert.Equal(1, r.AniosComputados);
        Assert.Equal(1_000_000m, r.Antiguedad);
    }

    [Fact]
    public void Un_despido_anterior_al_ingreso_es_un_error()
    {
        Assert.Throws<ArgumentException>(() =>
            Indemnizacion.Calcular(Con(1_000_000m, new DateOnly(2020, 1, 1)), new DateOnly(2019, 1, 1), Fixture.Parametros2024));
    }
}
