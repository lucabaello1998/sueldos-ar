using SueldosAr.Core.Calculadoras;
using Xunit;

namespace SueldosAr.Tests;

public class AportesTests
{
    [Fact]
    public void Jubilacion_y_obra_social_son_11_y_3_por_ciento()
    {
        var r = Aportes.Calcular(1_000_000m, Fixture.Parametros2024, edad: 35, afiliadoSindicato: false);

        Assert.Equal(110_000m, r.Jubilacion);
        Assert.Equal(30_000m, r.ObraSocial);
        Assert.Equal(0m, r.Pami);
        Assert.Equal(0m, r.Sindicato);
        Assert.Equal(140_000m, r.Total);
    }

    [Fact]
    public void El_aporte_a_pami_corre_desde_los_70_anios()
    {
        var conSesentaYNueve = Aportes.Calcular(1_000_000m, Fixture.Parametros2024, edad: 69, afiliadoSindicato: false);
        var conSetenta = Aportes.Calcular(1_000_000m, Fixture.Parametros2024, edad: 70, afiliadoSindicato: false);

        Assert.Equal(0m, conSesentaYNueve.Pami);
        Assert.Equal(30_000m, conSetenta.Pami);
        Assert.Equal(170_000m, conSetenta.Total);
    }

    [Fact]
    public void La_cuota_sindical_solo_se_descuenta_si_esta_afiliado()
    {
        var sinAfiliacion = Aportes.Calcular(1_000_000m, Fixture.Parametros2024, 35, afiliadoSindicato: false);
        var conAfiliacion = Aportes.Calcular(1_000_000m, Fixture.Parametros2024, 35, afiliadoSindicato: true);

        Assert.Equal(0m, sinAfiliacion.Sindicato);
        Assert.Equal(20_000m, conAfiliacion.Sindicato);
        Assert.Equal(160_000m, conAfiliacion.Total);
    }

    [Fact]
    public void Sin_edad_informada_no_se_descuenta_pami()
    {
        var r = Aportes.Calcular(500_000m, Fixture.Parametros2024, edad: null, afiliadoSindicato: false);

        Assert.Equal(0m, r.Pami);
        Assert.Equal(70_000m, r.Total);
    }

    [Fact]
    public void Bruto_cero_no_genera_aportes()
    {
        var r = Aportes.Calcular(0m, Fixture.Parametros2024, 35, afiliadoSindicato: true);

        Assert.Equal(0m, r.Total);
    }

    [Fact]
    public void Las_contribuciones_patronales_suman_19_por_ciento()
    {
        var r = Contribuciones.Calcular(1_000_000m, Fixture.Parametros2024);

        Assert.Equal(101_700m, r.Jubilacion);
        Assert.Equal(60_000m, r.ObraSocial);
        Assert.Equal(15_000m, r.Asignaciones);
        Assert.Equal(5_000m, r.FondoEmpleo);
        Assert.Equal(4_000m, r.SeguroVida);
        Assert.Equal(185_700m, r.Total);
    }
}
