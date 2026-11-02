using SueldosAr.Core.Modelos;

namespace SueldosAr.Core.Calculadoras;

/// <summary>
/// Indemnización por despido sin justa causa.
/// Art. 245: un mes de sueldo por año de servicio o fracción mayor a tres meses, sobre la mejor
/// remuneración mensual normal y habitual de los últimos doce meses.
/// Art. 232: preaviso de 1 mes hasta 5 años y de 2 meses desde 5 años.
/// Art. 233: integración del mes de despido.
/// Art. 123: SAC proporcional sobre la indemnización.
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

        var remuneracion = mejorRemuneracion
            ?? empleado.MejorRemuneracionSemestre
            ?? empleado.SueldoBasico;

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

        // Art. 232: preaviso.
        var mesesPreaviso = anios >= 5 ? 2 : 1;
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

    /// <summary>Años de servicio contando como año completo la fracción mayor a tres meses (art. 245).</summary>
    public static int AniosConFraccion(DateOnly ingreso, DateOnly egreso)
    {
        if (egreso < ingreso)
            throw new ArgumentException("El egreso no puede ser anterior al ingreso.", nameof(egreso));

        var anios = egreso.Year - ingreso.Year;
        if (egreso.Month < ingreso.Month ||
            (egreso.Month == ingreso.Month && egreso.Day < ingreso.Day))
            anios--;

        anios = Math.Max(0, anios);

        // Fracción posterior al último aniversario.
        var ultimoAniversario = ingreso.AddYears(anios);
        var mesesFraccion = (egreso.Year - ultimoAniversario.Year) * 12 + egreso.Month - ultimoAniversario.Month;
        if (egreso.Day < ultimoAniversario.Day)
            mesesFraccion--;

        if (mesesFraccion > 3)
            anios++;

        return Math.Max(1, anios);
    }

    private static int MesesDelSemestreHasta(DateOnly fecha)
    {
        var inicioSemestre = fecha.Month <= 6 ? 1 : 7;
        var meses = fecha.Month - inicioSemestre + 1;
        return Math.Clamp(meses, 1, 6);
    }
}
