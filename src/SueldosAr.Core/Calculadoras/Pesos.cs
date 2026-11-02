namespace SueldosAr.Core.Calculadoras;

/// <summary>Redondeo monetario: dos decimales, medio hacia arriba (criterio de liquidación).</summary>
public static class Pesos
{
    public static decimal Redondear(decimal valor) =>
        Math.Round(valor, 2, MidpointRounding.AwayFromZero);

    public static decimal Porcentaje(decimal baseImponible, decimal tasa) =>
        Redondear(baseImponible * tasa);
}
