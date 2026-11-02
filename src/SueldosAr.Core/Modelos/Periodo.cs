namespace SueldosAr.Core.Modelos;

/// <summary>Período de liquidación (mes y año).</summary>
public readonly record struct Periodo
{
    public int Anio { get; }
    public int Mes { get; }

    public Periodo(int anio, int mes)
    {
        if (anio is < 2000 or > 2100)
            throw new ArgumentOutOfRangeException(nameof(anio), anio, "El año debe estar entre 2000 y 2100.");
        if (mes is < 1 or > 12)
            throw new ArgumentOutOfRangeException(nameof(mes), mes, "El mes debe estar entre 1 y 12.");

        Anio = anio;
        Mes = mes;
    }

    public int DiasDelMes => DateTime.DaysInMonth(Anio, Mes);

    public DateOnly Primero => new(Anio, Mes, 1);

    public DateOnly Ultimo => new(Anio, Mes, DiasDelMes);

    /// <summary>1 = enero-junio, 2 = julio-diciembre.</summary>
    public int Semestre => Mes <= 6 ? 1 : 2;

    public int DiasDelSemestre => Semestre == 1
        ? DateTime.IsLeapYear(Anio) ? 182 : 181
        : 184;

    public Periodo Anterior => Mes == 1 ? new Periodo(Anio - 1, 12) : new Periodo(Anio, Mes - 1);

    public static Periodo De(DateOnly fecha) => new(fecha.Year, fecha.Month);

    public override string ToString() => $"{Anio:D4}-{Mes:D2}";
}
