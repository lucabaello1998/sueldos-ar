namespace SueldosAr.Core.Modelos;

/// <summary>Datos del trabajador que hacen al cálculo. Nada de esto sale del sistema real de nadie.</summary>
public sealed record Empleado
{
    public required string Nombre { get; init; }

    public required decimal SueldoBasico { get; init; }

    public required DateOnly FechaIngreso { get; init; }

    public DateOnly? FechaEgreso { get; init; }

    /// <summary>Edad al cierre del período. A los 70 años corresponde el aporte a PAMI (INSSJP).</summary>
    public int? Edad { get; init; }

    public bool AfiliadoSindicato { get; init; }

    /// <summary>Adicional por antigüedad, típicamente 1% del básico por año (varía por convenio).</summary>
    public decimal PorcentajeAntiguedadPorAnio { get; init; } = 0.01m;

    /// <summary>Zona desfavorable (Patagonia): adicional del 22% sobre el básico (art. 1 Ley 19.587 y CCT).</summary>
    public bool ZonaDesfavorable { get; init; }

    public decimal HorasExtrasAl50 { get; init; }

    public decimal HorasExtrasAl100 { get; init; }

    /// <summary>Días trabajados en el mes. Si es null se toman todos los días del período.</summary>
    public int? DiasTrabajados { get; init; }

    /// <summary>Otras deducciones informadas por el empleado (adelantos, cuota sindical extraordinaria, etc.).</summary>
    public decimal OtrasDeducciones { get; init; }

    /// <summary>
    /// Mejor remuneración mensual normal y habitual del semestre. Si es null se usa el bruto del período
    /// como aproximación, y el recibo lo marca como tal.
    /// </summary>
    public decimal? MejorRemuneracionSemestre { get; init; }

    /// <summary>Años de antigüedad cumplidos al último día del período.</summary>
    public int AniosAntiguedad(Periodo periodo)
    {
        var corte = periodo.Ultimo;
        if (FechaEgreso is { } egreso && egreso < corte)
            corte = egreso;

        if (corte < FechaIngreso)
            return 0;

        var anios = corte.Year - FechaIngreso.Year;
        if (corte.Month < FechaIngreso.Month ||
            (corte.Month == FechaIngreso.Month && corte.Day < FechaIngreso.Day))
            anios--;

        return Math.Max(0, anios);
    }

    /// <summary>Meses completos trabajados entre el ingreso y el cierre del período (para SAC y preaviso).</summary>
    public int MesesTrabajados(Periodo periodo)
    {
        var corte = periodo.Ultimo;
        if (FechaEgreso is { } egreso && egreso < corte)
            corte = egreso;

        if (corte < FechaIngreso)
            return 0;

        var meses = (corte.Year - FechaIngreso.Year) * 12 + corte.Month - FechaIngreso.Month;
        if (corte.Day < FechaIngreso.Day)
            meses--;

        return Math.Max(0, meses);
    }
}
