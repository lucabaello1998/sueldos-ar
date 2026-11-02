using SueldosAr.Core.Modelos;

namespace SueldosAr.Core.Calculadoras;

/// <summary>
/// Vacaciones (arts. 150 y 155 LCT).
/// Días corridos según antigüedad al 31/12 del año anterior; se pagan sobre el sueldo mensual dividido 25.
/// </summary>
public static class Vacaciones
{
    public static int DiasPorAntiguedad(int anios) => anios switch
    {
        < 5 => 14,
        < 10 => 21,
        < 20 => 28,
        _ => 35
    };

    /// <summary>Antigüedad que se computa para los días de vacaciones: la del 31/12 del año anterior.</summary>
    public static int AniosParaDias(DateOnly fechaIngreso, int anioDeVacaciones) =>
        Math.Max(0, anioDeVacaciones - 1 - fechaIngreso.Year);

    public static ResultadoVacaciones Calcular(
        DateOnly fechaIngreso,
        int anioDeVacaciones,
        decimal brutoMensual,
        int? diasTomados = null,
        decimal divisor = 25m)
    {
        if (brutoMensual < 0)
            throw new ArgumentOutOfRangeException(nameof(brutoMensual), "El bruto no puede ser negativo.");
        if (divisor <= 0)
            throw new ArgumentOutOfRangeException(nameof(divisor), "El divisor tiene que ser mayor a cero.");

        var anios = AniosParaDias(fechaIngreso, anioDeVacaciones);
        var corresponden = DiasPorAntiguedad(anios);
        var tomados = diasTomados ?? corresponden;

        if (tomados < 0 || tomados > corresponden)
            throw new ArgumentOutOfRangeException(nameof(diasTomados),
                $"Los días tomados ({tomados}) tienen que estar entre 0 y {corresponden}.");

        var valorDia = Pesos.Redondear(brutoMensual / divisor);
        var importe = Pesos.Redondear(valorDia * tomados);

        return new ResultadoVacaciones(anios, corresponden, tomados, valorDia, importe);
    }

    /// <summary>Días corridos entre dos fechas, ambos inclusive.</summary>
    public static int DiasCorridos(DateOnly desde, DateOnly hasta)
    {
        if (hasta < desde)
            throw new ArgumentException("La fecha de fin no puede ser anterior a la de inicio.", nameof(hasta));

        return hasta.DayNumber - desde.DayNumber + 1;
    }
}
