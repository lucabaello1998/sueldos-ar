namespace SueldosAr.Core.Modelos;

/// <summary>
/// Parámetros legales de un período. Todo lo que cambia por ley o por resolución vive acá y no en el código,
/// para que actualizar el año sea editar un JSON y no tocar la lógica.
/// </summary>
public sealed record Parametros
{
    public required string Id { get; init; }

    public required string Nombre { get; init; }

    public required string Fuente { get; init; }

    public required DateOnly VigenciaDesde { get; init; }

    /// <summary>True si los valores son una actualización estimada y no la publicación oficial del organismo.</summary>
    public bool Estimado { get; init; }

    public string? Nota { get; init; }

    // --- Aportes del trabajador (LCT art. 19 y Ley 19.032) ---
    public decimal TasaJubilacion { get; init; } = 0.11m;
    public decimal TasaObraSocial { get; init; } = 0.03m;
    public decimal TasaPami { get; init; } = 0.03m;
    public int EdadPami { get; init; } = 70;
    public decimal TasaSindicato { get; init; } = 0.02m;

    // --- Contribuciones patronales (Decreto 814/2001) ---
    public decimal ContribucionJubilacion { get; init; } = 0.1017m;
    public decimal ContribucionObraSocial { get; init; } = 0.06m;
    public decimal ContribucionAsignaciones { get; init; } = 0.015m;
    public decimal ContribucionFondoEmpleo { get; init; } = 0.005m;
    public decimal ContribucionSeguroVida { get; init; } = 0.004m;

    // --- Adicionales y bases de cálculo ---
    public decimal ZonaDesfavorable { get; init; } = 0.22m;
    public decimal HorasMensuales { get; init; } = 200m;
    public decimal DivisorVacaciones { get; init; } = 25m;

    // --- Ganancias 4ª categoría ---
    public decimal MinimoNoImponible { get; init; }
    public decimal DeduccionEspecial { get; init; }
    public required EscalaGanancias Escala { get; init; }

    // --- Indemnizaciones (art. 245 LCT) ---
    /// <summary>Tope del art. 245 (3 veces el promedio del CCT). Null = sin tope.</summary>
    public decimal? TopeIndemnizacion { get; init; }

    /// <summary>Piso indemnizatorio (fallo Vizzoti / ley 27.742). Null = sin piso.</summary>
    public decimal? PisoIndemnizacion { get; init; }
}
