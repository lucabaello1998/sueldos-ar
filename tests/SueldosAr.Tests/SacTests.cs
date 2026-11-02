using SueldosAr.Core.Calculadoras;
using Xunit;

namespace SueldosAr.Tests;

public class SacTests
{
    [Fact]
    public void Semestre_completo_paga_la_mitad_de_la_mejor_remuneracion()
    {
        var r = Sac.Calcular(1_200_000m, 181, 181);

        Assert.Equal(600_000m, r.Importe);
        Assert.False(r.Proporcional);
    }

    [Fact]
    public void Es_proporcional_a_los_dias_trabajados()
    {
        // 60 días de 181: 600.000 × 60 / 181
        var r = Sac.Calcular(1_200_000m, 60, 181);

        Assert.Equal(198_895.03m, r.Importe);
        Assert.True(r.Proporcional);
    }

    [Fact]
    public void Un_solo_dia_no_explota_y_da_un_valor_chico()
    {
        var r = Sac.Calcular(1_000_000m, 1, 184);

        Assert.Equal(2_717.39m, r.Importe);
    }

    [Fact]
    public void Los_dias_trabajados_se_topean_al_semestre()
    {
        var r = Sac.Calcular(900_000m, 400, 181);

        Assert.Equal(181, r.DiasTrabajados);
        Assert.Equal(450_000m, r.Importe);
    }

    [Fact]
    public void Cero_dias_da_cero()
    {
        Assert.Equal(0m, Sac.Calcular(1_000_000m, 0, 181).Importe);
    }

    [Fact]
    public void El_segundo_semestre_tiene_184_dias()
    {
        Assert.Equal(184, Sac.DiasTranscurridosDelSemestre(new(2026, 12)));
    }

    [Fact]
    public void El_primer_semestre_de_un_anio_bisiesto_tiene_182_dias()
    {
        Assert.Equal(182, Sac.DiasTranscurridosDelSemestre(new(2024, 6)));
    }

    [Fact]
    public void Rechaza_remuneracion_negativa()
    {
        Assert.Throws<ArgumentOutOfRangeException>(() => Sac.Calcular(-1m, 10, 181));
    }
}
