using SueldosAr.Core.Modelos;

namespace SueldosAr.Core.Calculadoras;

/// <summary>
/// Horas extras (art. 201 LCT): 50% de recargo en días hábiles y 100% en feriados, sábados después
/// de las 13 h y domingos. El valor hora se obtiene dividiendo el sueldo por la cantidad de horas
/// mensuales (200 por defecto, ajustable por convenio).
/// </summary>
public static class HorasExtras
{
    public static decimal ValorHora(decimal sueldoMensual, decimal horasMensuales = 200m)
    {
        if (horasMensuales <= 0)
            throw new ArgumentOutOfRangeException(nameof(horasMensuales), "Las horas mensuales tienen que ser mayores a cero.");

        return Pesos.Redondear(sueldoMensual / horasMensuales);
    }

    public static decimal Calcular(
        decimal sueldoMensual,
        decimal horasAl50,
        decimal horasAl100,
        decimal horasMensuales = 200m)
    {
        if (horasAl50 < 0 || horasAl100 < 0)
            throw new ArgumentOutOfRangeException(nameof(horasAl50), "Las horas extras no pueden ser negativas.");
        if (horasMensuales <= 0)
            throw new ArgumentOutOfRangeException(nameof(horasMensuales), "Las horas mensuales tienen que ser mayores a cero.");

        // Se usa el mismo valor hora redondeado que muestra el recibo: si no, el
        // detalle dice $5.000,01 y la cuenta usó 5.000,005.
        var valorHora = ValorHora(sueldoMensual, horasMensuales);

        return Pesos.Redondear(valorHora * horasAl50 * 1.5m + valorHora * horasAl100 * 2m);
    }
}
