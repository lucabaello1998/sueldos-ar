using SueldosAr.Core;
using SueldosAr.Core.Calculadoras;
using SueldosAr.Core.Modelos;
using Xunit;

namespace SueldosAr.Tests;

/// <summary>
/// Regresiones del gauntlet: cada test acá corresponde a un número que estaba mal
/// (o a un caso borde que tiraba una excepción fea en vez de un error claro).
/// </summary>
public class RevisionTests
{
    [Fact]
    public void El_sac_se_prorratea_desde_la_fecha_de_ingreso()
    {
        // Entró el 1/9 y cobra en diciembre: 122 de los 184 días del semestre.
        var empleado = Fixture.EmpleadoBase() with
        {
            FechaIngreso = new DateOnly(2026, 9, 1),
            MejorRemuneracionSemestre = 1_000_000m,
        };

        var sac = Liquidador.LiquidarSac(empleado, new Periodo(2026, 12), Fixture.Parametros2024);

        Assert.Equal(122, sac.DiasTrabajados);
        Assert.True(sac.Proporcional);
        Assert.Equal(331_521.74m, sac.Importe);
    }

    [Fact]
    public void El_sac_respeta_los_dias_que_informa_el_empleado()
    {
        var empleado = Fixture.EmpleadoBase() with
        {
            MejorRemuneracionSemestre = 1_000_000m,
            DiasTrabajados = 1,
        };

        var sac = Liquidador.LiquidarSac(empleado, new Periodo(2026, 6), Fixture.Parametros2024);

        Assert.Equal(1, sac.DiasTrabajados);
        Assert.Equal(2_762.43m, sac.Importe);
    }

    [Fact]
    public void El_basico_se_prorratea_hasta_la_fecha_de_egreso()
    {
        // Egresó el 10/3: cobra 10 de los 31 días de marzo.
        var empleado = Fixture.EmpleadoBase() with { FechaEgreso = new DateOnly(2026, 3, 10) };

        var recibo = Liquidador.Liquidar(empleado, new Periodo(2026, 3), Fixture.Parametros2024);

        var basico = recibo.Conceptos.Single(c => c.Codigo == "100");
        Assert.Equal(322_580.65m, basico.Importe);
        Assert.Contains("10 de 31", basico.Base);
    }

    [Fact]
    public void Un_empleado_que_egreso_antes_del_periodo_no_cobra_nada()
    {
        var empleado = Fixture.EmpleadoBase() with { FechaEgreso = new DateOnly(2026, 1, 31) };

        Assert.Throws<ArgumentException>(() =>
            Liquidador.Liquidar(empleado, new Periodo(2026, 6), Fixture.Parametros2024));
    }

    [Fact]
    public void Los_dias_negativos_se_rechazan_en_vez_de_quedar_en_cero()
    {
        var empleado = Fixture.EmpleadoBase() with { DiasTrabajados = -5 };

        Assert.Throws<ArgumentOutOfRangeException>(() =>
            Liquidador.Liquidar(empleado, new Periodo(2026, 3), Fixture.Parametros2024));
    }

    [Fact]
    public void Un_adelanto_no_baja_la_retencion_de_ganancias()
    {
        // El adelanto sale del neto, no es una deducción del impuesto.
        var conAdelanto = Fixture.EmpleadoBase(8_480_000m) with { OtrasDeducciones = 1_000_000m };
        var sinAdelanto = Fixture.EmpleadoBase(8_480_000m);

        var reciboCon = Liquidador.Liquidar(conAdelanto, new Periodo(2026, 3), Fixture.Parametros2024);
        var reciboSin = Liquidador.Liquidar(sinAdelanto, new Periodo(2026, 3), Fixture.Parametros2024);

        Assert.True(reciboSin.Ganancias > 0);
        Assert.Equal(reciboSin.Ganancias, reciboCon.Ganancias);
        Assert.Equal(1_000_000m, reciboSin.Neto - reciboCon.Neto);
    }

    [Fact]
    public void La_zona_desfavorable_entra_en_la_base_de_las_horas_extras()
    {
        var empleado = Fixture.EmpleadoBase() with
        {
            ZonaDesfavorable = true,
            HorasExtrasAl50 = 10,
        };

        var recibo = Liquidador.Liquidar(empleado, new Periodo(2026, 3), Fixture.Parametros2024);

        // Básico 1.000.000 + 10% de antigüedad + 22% de zona = 1.342.000; valor hora 6.710.
        var extras = recibo.Conceptos.Single(c => c.Codigo == "130");
        Assert.Equal(100_650m, extras.Importe);
        Assert.Contains("Art. 201 LCT", extras.Base);
    }

    [Fact]
    public void Cero_horas_mensuales_es_un_error_claro()
    {
        var parametros = Fixture.Parametros2024 with { HorasMensuales = 0m };
        var empleado = Fixture.EmpleadoBase() with { HorasExtrasAl50 = 1 };

        Assert.Throws<ArgumentOutOfRangeException>(() =>
            Liquidador.Liquidar(empleado, new Periodo(2026, 3), parametros));
    }

    [Fact]
    public void Avisa_cuando_los_parametros_son_posteriores_al_periodo()
    {
        var recibo = Liquidador.Liquidar(Fixture.EmpleadoBase(), new Periodo(2023, 1), Fixture.Parametros2024);

        Assert.Contains(recibo.Advertencias, a => a.Contains("posteriores al período"));
    }
}
