using SueldosAr.Core.Calculadoras;
using SueldosAr.Core.Modelos;
using Xunit;

namespace SueldosAr.Tests;

public class GananciasTests
{
    [Fact]
    public void Un_bruto_bajo_el_minimo_no_imponible_no_paga()
    {
        var r = Ganancias.Calcular(2_500_000m, 350_000m, Fixture.Parametros2024);

        Assert.Equal(0m, r.BaseImponible);
        Assert.Equal(0m, r.Impuesto);
    }

    [Fact]
    public void Aplica_la_alicuota_del_primer_tramo_sobre_el_excedente()
    {
        // 8.000.000 − 14% de aportes − 1.875.000 − 4.500.000 = 505.000 → 5%
        var r = Ganancias.Calcular(8_000_000m, 1_120_000m, Fixture.Parametros2024);

        Assert.Equal(505_000m, r.BaseImponible);
        Assert.Equal(0.05m, r.AliquotaMarginal);
        Assert.Equal(25_250m, r.Impuesto);
    }

    [Fact]
    public void La_escala_es_progresiva_por_tramos_y_no_plana()
    {
        var escala = Fixture.Parametros2024.Escala;

        // 20.000.000 recorre siete tramos: 5, 9, 12, 15, 19, 23 y 27%.
        Assert.Equal(3_867_187.50m, escala.Calcular(20_000_000m));
        Assert.Equal(0.27m, escala.AliquotaMarginal(20_000_000m));
    }

    [Fact]
    public void El_ultimo_tramo_no_tiene_techo()
    {
        var escala = Fixture.Parametros2024.Escala;
        var ultimo = escala.Tramos[^1];

        Assert.Equal(decimal.MaxValue, ultimo.Hasta);
        Assert.Equal(0.35m, ultimo.Aliquota);
        Assert.True(escala.Calcular(500_000_000m) > 0);
    }

    [Fact]
    public void Un_salario_en_el_limite_superior_del_primer_tramo_paga_el_5_por_ciento()
    {
        var escala = Fixture.ConEscalaSimple((1_000_000m, 0.05m), (decimal.MaxValue, 0.30m)).Escala;

        Assert.Equal(50_000m, escala.Calcular(1_000_000m));
        Assert.Equal(50_000m, escala.Calcular(1_000_001m) - 0.30m);
    }

    [Fact]
    public void Base_negativa_por_otras_deducciones_devuelve_cero()
    {
        var r = Ganancias.Calcular(8_000_000m, 1_120_000m, Fixture.Parametros2024, otrasDeducciones: 10_000_000m);

        Assert.Equal(0m, r.Impuesto);
        Assert.Equal(0m, r.BaseImponible);
    }

    [Fact]
    public void La_escala_necesita_al_menos_un_tramo()
    {
        Assert.Throws<ArgumentException>(() => new EscalaGanancias([]));
    }
}
