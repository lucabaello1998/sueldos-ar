using SueldosAr.Core;
using SueldosAr.Core.Modelos;
using Xunit;

namespace SueldosAr.Tests;

public class LiquidacionTests
{
    private static Recibo Liquidar(Empleado e, Parametros? p = null) =>
        Liquidador.Liquidar(e, Fixture.Periodo2026, p ?? Fixture.Parametros2024);

    [Fact]
    public void El_recibo_descuenta_aportes_y_calcula_el_neto()
    {
        var r = Liquidar(Fixture.EmpleadoBase());

        Assert.Equal(1_100_000m, r.Bruto);          // 1.000.000 + 10% de antigüedad
        Assert.Equal(154_000m, r.TotalAportes);     // 14%
        Assert.Equal(0m, r.Ganancias);
        Assert.Equal(946_000m, r.Neto);
    }

    [Fact]
    public void Cada_concepto_trae_su_base_legal()
    {
        var r = Liquidar(Fixture.EmpleadoBase());

        Assert.All(r.Conceptos, c => Assert.False(string.IsNullOrWhiteSpace(c.Base)));
        Assert.Contains(r.Conceptos, c => c.Codigo == "110" && c.Detalle.Contains("10 años"));
        Assert.Contains(r.Conceptos, c => c.Codigo == "200" && c.Base.Contains("24.241"));
    }

    [Fact]
    public void El_costo_del_empleador_incluye_las_contribuciones()
    {
        var r = Liquidar(Fixture.EmpleadoBase());

        Assert.Equal(204_270m, r.Contribuciones);   // 18,57%
        Assert.Equal(1_304_270m, r.CostoEmpleador);
    }

    [Fact]
    public void Prorratea_el_basico_por_los_dias_trabajados()
    {
        var empleado = Fixture.EmpleadoBase() with { DiasTrabajados = 15 };
        var r = Liquidar(empleado);

        var basico = r.Conceptos.Single(c => c.Codigo == "100");
        Assert.Equal(483_870.97m, basico.Importe);   // 1.000.000 × 15 / 31
        Assert.Contains("15 de 31", basico.Base);
    }

    [Fact]
    public void La_zona_desfavorable_suma_22_por_ciento()
    {
        var empleado = Fixture.EmpleadoBase() with { ZonaDesfavorable = true };
        var r = Liquidar(empleado);

        var zona = r.Conceptos.Single(c => c.Codigo == "120");
        Assert.Equal(242_000m, zona.Importe);        // 22% de 1.100.000
        Assert.Equal(1_342_000m, r.Bruto);
    }

    [Fact]
    public void Las_horas_extras_se_pagan_al_50_y_al_100()
    {
        var empleado = Fixture.EmpleadoBase() with { HorasExtrasAl50 = 10, HorasExtrasAl100 = 4 };
        var r = Liquidar(empleado);

        var extras = r.Conceptos.Single(c => c.Codigo == "130");
        Assert.Equal(126_500m, extras.Importe);      // 5.500 × (10×1,5 + 4×2)
        Assert.Contains("Art. 201", extras.Base);
    }

    [Fact]
    public void Un_sueldo_alto_paga_ganancias_y_baja_el_neto()
    {
        var empleado = Fixture.EmpleadoBase(20_000_000m);
        var r = Liquidar(empleado);

        Assert.True(r.Ganancias > 0);
        Assert.True(r.BaseImponibleGanancias > 0);
        Assert.Equal(r.Bruto - r.TotalAportes - r.Ganancias, r.Neto);
        Assert.Contains(r.Conceptos, c => c.Codigo == "300");
    }

    [Fact]
    public void Un_empleado_mayor_de_70_aporta_a_pami()
    {
        var empleado = Fixture.EmpleadoBase() with { Edad = 72 };
        var r = Liquidar(empleado);

        Assert.Equal(187_000m, r.TotalAportes);      // 14% + 3% de PAMI
        Assert.Contains(r.Conceptos, c => c.Codigo == "220");
    }

    [Fact]
    public void Los_dias_trabajados_se_topean_a_los_del_mes()
    {
        var empleado = Fixture.EmpleadoBase() with { DiasTrabajados = 90 };
        var r = Liquidar(empleado);

        Assert.Equal(1_100_000m, r.Bruto);
    }

    [Fact]
    public void Un_ingreso_posterior_al_periodo_es_un_error()
    {
        var empleado = Fixture.EmpleadoBase() with { FechaIngreso = new DateOnly(2026, 6, 1) };

        Assert.Throws<ArgumentException>(() => Liquidar(empleado));
    }

    [Fact]
    public void El_sac_del_semestre_usa_la_mejor_remuneracion_informada()
    {
        var empleado = Fixture.EmpleadoBase() with { MejorRemuneracionSemestre = 1_500_000m };
        var sac = Liquidador.LiquidarSac(empleado, Fixture.Periodo2026, Fixture.Parametros2024);

        // Al 31/03 van 90 días de 181.
        Assert.Equal(90, sac.DiasTrabajados);
        Assert.Equal(372_928.18m, sac.Importe);
    }

    [Fact]
    public void El_sac_sin_mejor_remuneracion_usa_el_bruto_del_mes()
    {
        var sac = Liquidador.LiquidarSac(Fixture.EmpleadoBase(), Fixture.Periodo2026, Fixture.Parametros2024);

        Assert.Equal(1_100_000m, sac.MejorRemuneracion);
    }

    [Fact]
    public void Avisa_cuando_los_parametros_son_anteriores_al_periodo()
    {
        var r = Liquidador.Liquidar(Fixture.EmpleadoBase(), new Periodo(2026, 3), Fixture.Parametros2024);

        Assert.Contains(r.Advertencias, a => a.Contains("desactualizada") && a.Contains("07/2024"));
    }

    [Fact]
    public void No_avisa_cuando_el_periodo_coincide_con_los_parametros()
    {
        var r = Liquidador.Liquidar(Fixture.EmpleadoBase(), new Periodo(2024, 7), Fixture.Parametros2024);

        Assert.DoesNotContain(r.Advertencias, a => a.Contains("desactualizada"));
    }
}
