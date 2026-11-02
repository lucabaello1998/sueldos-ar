namespace SueldosAr.Core.Modelos;

public enum TipoConcepto
{
    Remunerativo,
    Descuento,
    Contribucion
}

/// <summary>Una línea del recibo, con el artículo que la respalda.</summary>
public sealed record Concepto(
    string Codigo,
    string Detalle,
    decimal Importe,
    TipoConcepto Tipo,
    string Base);

/// <summary>Resultado completo de una liquidación: lo que ve el empleado y lo que le cuesta al empleador.</summary>
public sealed record Recibo
{
    public required string Empleado { get; init; }
    public required Periodo Periodo { get; init; }
    public required IReadOnlyList<Concepto> Conceptos { get; init; }

    public decimal Bruto { get; init; }
    public decimal TotalAportes { get; init; }
    public decimal Ganancias { get; init; }
    public decimal OtrasDeducciones { get; init; }
    public decimal Neto { get; init; }
    public decimal Contribuciones { get; init; }
    public decimal CostoEmpleador { get; init; }

    public decimal BaseImponibleGanancias { get; init; }
    public decimal AliquotaMarginal { get; init; }

    public IReadOnlyList<string> Advertencias { get; init; } = [];
}

/// <summary>SAC (sueldo anual complementario).</summary>
public sealed record ResultadoSac(
    decimal MejorRemuneracion,
    int DiasTrabajados,
    int DiasDelSemestre,
    decimal Importe,
    bool Proporcional);

/// <summary>Vacaciones: días que corresponden y lo que se paga por ellos.</summary>
public sealed record ResultadoVacaciones(
    int AniosAntiguedad,
    int DiasCorresponden,
    int DiasTomados,
    decimal ValorDia,
    decimal Importe);

/// <summary>Indemnización por despido sin justa causa (arts. 232, 233, 245 y 123 LCT).</summary>
public sealed record ResultadoIndemnizacion
{
    public int AniosComputados { get; init; }
    public decimal MejorRemuneracion { get; init; }
    public decimal Antiguedad { get; init; }
    public decimal Preaviso { get; init; }
    public decimal IntegracionMesDespido { get; init; }
    public decimal SacSobreIndemnizacion { get; init; }
    public decimal Total { get; init; }
    public bool TopeAplicado { get; init; }
    public bool PisoAplicado { get; init; }
    public int MesesPreaviso { get; init; }
}
