using SueldosAr.Core.Modelos;

namespace SueldosAr.Core.Calculadoras;

/// <summary>
/// Sueldo anual complementario (Ley 23.041, art. 121 LCT).
/// Se paga en dos cuotas: junio (devengado enero-junio) y diciembre (julio-diciembre).
/// Importe = 50% de la mejor remuneración mensual del semestre, proporcional a los días trabajados.
/// </summary>
public static class Sac
{
    public static ResultadoSac Calcular(
        decimal mejorRemuneracion,
        int diasTrabajados,
        int diasDelSemestre)
    {
        if (mejorRemuneracion < 0)
            throw new ArgumentOutOfRangeException(nameof(mejorRemuneracion), "La remuneración no puede ser negativa.");
        if (diasDelSemestre <= 0)
            throw new ArgumentOutOfRangeException(nameof(diasDelSemestre), "El semestre tiene que tener días.");
        if (diasTrabajados < 0)
            throw new ArgumentOutOfRangeException(nameof(diasTrabajados), "Los días trabajados no pueden ser negativos.");

        var dias = Math.Min(diasTrabajados, diasDelSemestre);
        var proporcional = dias < diasDelSemestre;

        var importe = proporcional
            ? Pesos.Redondear(mejorRemuneracion / 2m * dias / diasDelSemestre)
            : Pesos.Redondear(mejorRemuneracion / 2m);

        return new ResultadoSac(mejorRemuneracion, dias, diasDelSemestre, importe, proporcional);
    }

    /// <summary>Días del semestre que van del 1 de enero o 1 de julio al cierre del período.</summary>
    public static int DiasTranscurridosDelSemestre(Periodo periodo)
    {
        var inicio = periodo.Semestre == 1
            ? new DateOnly(periodo.Anio, 1, 1)
            : new DateOnly(periodo.Anio, 7, 1);

        return periodo.Ultimo.DayNumber - inicio.DayNumber + 1;
    }
}
