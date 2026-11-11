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
        var r = Indemnizacion.Calcular(Con(1_000_000m, new DateOnly(2016, 3, 1), mejor: 1_000_000m), new DateOnly(2026, 3, 10), Fixture.Parametros2024);

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
        var r = Indemnizacion.Calcular(Con(1_000_000m, new DateOnly(2016, 3, 1), mejor: 1_000_000m), new DateOnly(2026, 3, 10), Fixture.Parametros2024);

        // Marzo tiene 31 días: quedan 21. El mes del despido no suma para el SAC
        // (se trabajaron 10 días, no más de 15): enero y febrero = 2/12.
        Assert.Equal(700_000m, r.IntegracionMesDespido);
        Assert.Equal(1_666_666.67m, r.SacSobreIndemnizacion);
        Assert.Equal(14_366_666.67m, r.Total);
    }

    [Fact]
    public void Menos_de_cinco_anios_lleva_un_mes_de_preaviso()
    {
        var r = Indemnizacion.Calcular(Con(1_000_000m, new DateOnly(2022, 1, 1), mejor: 1_000_000m), new DateOnly(2026, 1, 31), Fixture.Parametros2024);

        Assert.Equal(1, r.MesesPreaviso);
        Assert.Equal(1_000_000m, r.Preaviso);
    }

    [Fact]
    public void Con_cinco_anios_exactos_el_preaviso_sigue_siendo_un_mes()
    {
        // Art. 231: un mes "hasta" cinco años; dos recién cuando es "mayor".
        var exactos = Indemnizacion.Calcular(Con(1_000_000m, new DateOnly(2021, 1, 1), mejor: 1_000_000m), new DateOnly(2026, 1, 1), Fixture.Parametros2024);
        var unDiaMas = Indemnizacion.Calcular(Con(1_000_000m, new DateOnly(2021, 1, 1), mejor: 1_000_000m), new DateOnly(2026, 1, 2), Fixture.Parametros2024);

        Assert.Equal(1, exactos.MesesPreaviso);
        Assert.Equal(2, unDiaMas.MesesPreaviso);
    }

    [Fact]
    public void Un_servicio_de_menos_de_tres_meses_no_genera_antiguedad_indemnizable()
    {
        // Art. 245: se computa la fracción mayor a tres meses. Un mes y medio no lo es.
        var r = Indemnizacion.Calcular(Con(1_000_000m, new DateOnly(2026, 1, 1), mejor: 1_000_000m), new DateOnly(2026, 2, 15), Fixture.Parametros2024);

        Assert.Equal(0, r.AniosComputados);
        Assert.Equal(0m, r.Antiguedad);
        Assert.Equal(1_000_000m, r.Preaviso);
    }

    [Fact]
    public void Tres_meses_y_un_dia_ya_cuentan_como_anio()
    {
        Assert.Equal(1, Indemnizacion.AniosConFraccion(new DateOnly(2025, 1, 10), new DateOnly(2025, 4, 11)));
        Assert.Equal(0, Indemnizacion.AniosConFraccion(new DateOnly(2025, 1, 10), new DateOnly(2025, 4, 10)));
    }

    [Fact]
    public void Sin_mejor_remuneracion_usa_basico_mas_antiguedad()
    {
        // La base del art. 245 es la remuneración normal y habitual, no el básico pelado:
        // 10 años al 1% dan 1.100.000.
        var r = Indemnizacion.Calcular(Con(1_000_000m, new DateOnly(2016, 3, 1)), new DateOnly(2026, 3, 10), Fixture.Parametros2024);

        Assert.Equal(1_100_000m, r.MejorRemuneracion);
        Assert.Equal(11_000_000m, r.Antiguedad);
    }

    [Fact]
    public void Un_mes_con_un_solo_dia_no_suma_para_el_sac()
    {
        // Art. 123: la fracción cuenta si supera los 15 días. Despido el 1/7 = cero SAC.
        var r = Indemnizacion.Calcular(Con(1_000_000m, new DateOnly(2015, 7, 1), mejor: 1_000_000m), new DateOnly(2026, 7, 1), Fixture.Parametros2024);

        Assert.Equal(0m, r.SacSobreIndemnizacion);

        var mitad = Indemnizacion.Calcular(Con(1_000_000m, new DateOnly(2015, 7, 1), mejor: 1_000_000m), new DateOnly(2026, 7, 20), Fixture.Parametros2024);
        Assert.Equal(916_666.67m, mitad.SacSobreIndemnizacion);
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
