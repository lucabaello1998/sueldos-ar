using SueldosAr.Core.Modelos;

namespace SueldosAr.Core.Calculadoras;

/// <summary>
/// Indemnización por despido sin justa causa.
/// Art. 245: un mes de sueldo por año de servicio o fracción mayor a tres meses, sobre la mejor
/// remuneración mensual normal y habitual de los últimos doce meses.
/// Art. 231: preaviso de 1 mes con antigüedad de hasta 5 años y de 2 meses si es mayor.
/// Art. 232: indemnización sustitutiva del preaviso (no se calcula acá: se informa el preaviso).
/// Art. 233: integración del mes de despido.
/// Art. 123: SAC proporcional sobre la indemnización (1/12 por mes o fracción mayor a 15 días).
/// </summary>
public static class Indemnizacion
{
    public static ResultadoIndemnizacion Calcular(
        Empleado empleado,
        DateOnly fechaDespido,
        Parametros parametros,
        decimal? mejorRemuneracion = null)
    {
        ArgumentNullException.ThrowIfNull(empleado);
        ArgumentNullException.ThrowIfNull(parametros);

        if (fechaDespido < empleado.FechaIngreso)
            throw new ArgumentException("La fecha de despido no puede ser anterior al ingreso.", nameof(fechaDespido));

        if (empleado.SueldoBasico < 0)
            throw new ArgumentOutOfRangeException(nameof(empleado), "El sueldo básico no puede ser negativo.");

        // La "mejor remuneración normal y habitual" incluye antigüedad y zona: si no
        // la informaron, se reconstruye con el básico del mes de despido en vez de
        // tomar el básico pelado (que subestima la indemnización).
        var remuneracion = mejorRemuneracion
            ?? empleado.MejorRemuneracionSemestre
            ?? RemuneracionHabitual(empleado, fechaDespido, parametros);

        if (remuneracion < 0)
            throw new ArgumentOutOfRangeException(nameof(mejorRemuneracion), "La remuneración no puede ser negativa.");

        var anios = AniosConFraccion(empleado.FechaIngreso, fechaDespido);

        // Art. 245: tope y piso.
        var baseCalculo = remuneracion;
        var topeAplicado = false;
        var pisoAplicado = false;

        if (parametros.TopeIndemnizacion is { } tope && baseCalculo > tope)
        {
            baseCalculo = tope;
            topeAplicado = true;
        }

        if (parametros.PisoIndemnizacion is { } piso && baseCalculo < piso)
        {
            baseCalculo = piso;
            pisoAplicado = true;
        }

        var antiguedad = Pesos.Redondear(baseCalculo * anios);

        // Art. 231: "no exceda de cinco años" → 1 mes; "mayor" → 2 meses. Se compara
        // la fecha, no los años redondeados: 5 años y un día ya es "mayor".
        var mesesPreaviso = fechaDespido > empleado.FechaIngreso.AddYears(5) ? 2 : 1;
        var preaviso = Pesos.Redondear(remuneracion * mesesPreaviso);

        // Art. 233: días que faltan para fin de mes.
        var diasRestantes = DateTime.DaysInMonth(fechaDespido.Year, fechaDespido.Month) - fechaDespido.Day;
        var integracion = Pesos.Redondear(remuneracion / 30m * diasRestantes);

        // Art. 123: SAC proporcional sobre la indemnización (1/12 por mes o fracción mayor a 15 días).
        var mesesSemestre = MesesDelSemestreHasta(fechaDespido);
        var sac = Pesos.Redondear(antiguedad * mesesSemestre / 12m);

        var total = antiguedad + preaviso + integracion + sac;

        return new ResultadoIndemnizacion
        {
            AniosComputados = anios,
            MejorRemuneracion = remuneracion,
            Antiguedad = antiguedad,
            Preaviso = preaviso,
            IntegracionMesDespido = integracion,
            SacSobreIndemnizacion = sac,
            Total = total,
            TopeAplicado = topeAplicado,
            PisoAplicado = pisoAplicado,
            MesesPreaviso = mesesPreaviso
        };
    }

    /// <summary>
    /// Años de servicio con la regla del art. 245: se cuenta el año completo y se suma uno si
    /// sobra una fracción **mayor a tres meses** (importan los días: 3 meses y 1 día es "mayor").
    /// Con menos de tres meses no hay año que computar: devuelve 0 y la antigüedad indemnizable
    /// queda en cero (el preaviso y la integración se liquidan igual).
    /// </summary>
    public static int AniosConFraccion(DateOnly ingreso, DateOnly egreso)
    {
        if (egreso < ingreso)
            throw new ArgumentException("El egreso no puede ser anterior al ingreso.", nameof(egreso));

        var anios = egreso.Year - ingreso.Year;
        if (egreso.Month < ingreso.Month || (egreso.Month == ingreso.Month && egreso.Day < ingreso.Day))
            anios--;

        anios = Math.Max(0, anios);

        // Fracción posterior al último aniversario, con días.
        var ultimoAniversario = ingreso.AddYears(anios);
        if (egreso > ultimoAniversario.AddMonths(3))
            anios++;

        return anios;
    }

    /// <summary>Básico + antigüedad + zona desfavorable al momento del despido.</summary>
    private static decimal RemuneracionHabitual(Empleado empleado, DateOnly fecha, Parametros parametros)
    {
        var periodo = Periodo.De(fecha);
        var anios = empleado.AniosAntiguedad(periodo);
        var conAntiguedad = empleado.SueldoBasico * (1 + empleado.PorcentajeAntiguedadPorAnio * anios);
        var conZona = empleado.ZonaDesfavorable ? conAntiguedad * (1 + parametros.ZonaDesfavorable) : conAntiguedad;
        return Pesos.Redondear(conZona);
    }

    /// <summary>
    /// Meses del semestre que cuentan para el SAC sobre la indemnización: los meses completos
    /// anteriores y el mes del despido solo si se trabajaron más de 15 días (art. 123).
    /// </summary>
    private static int MesesDelSemestreHasta(DateOnly fecha)
    {
        var inicioSemestre = fecha.Month <= 6 ? 1 : 7;
        var meses = fecha.Month - inicioSemestre;
        if (fecha.Day > 15)
            meses++;
        return Math.Clamp(meses, 0, 6);
    }
}
