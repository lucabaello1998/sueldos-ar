using System.Reflection;
using System.Text.Json;
using System.Text.Json.Serialization;
using SueldosAr.Core.Modelos;

namespace SueldosAr.Core.Carga;

/// <summary>
/// Carga los juegos de parámetros embebidos en el assembly (carpeta Parametros/*.json).
/// Agregar un período nuevo es copiar un JSON: no hace falta tocar código.
/// </summary>
public static class ParametrosRepositorio
{
    private static readonly JsonSerializerOptions Opciones = new()
    {
        PropertyNameCaseInsensitive = true,
        ReadCommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true,
        Converters = { new JsonStringEnumConverter() }
    };

    private static readonly Lazy<IReadOnlyList<Parametros>> Cache = new(Cargar);

    public static IReadOnlyList<Parametros> Todos() => Cache.Value;

    public static Parametros Obtener(string id) =>
        Todos().FirstOrDefault(p => p.Id.Equals(id, StringComparison.OrdinalIgnoreCase))
        ?? throw new KeyNotFoundException($"No hay parámetros cargados con el id '{id}'.");

    /// <summary>El juego de parámetros vigente al último día del período.</summary>
    public static Parametros ParaPeriodo(Periodo periodo)
    {
        var corte = periodo.Ultimo;

        return Todos()
            .Where(p => p.VigenciaDesde <= corte)
            .OrderByDescending(p => p.VigenciaDesde)
            .FirstOrDefault()
            ?? Todos().OrderBy(p => p.VigenciaDesde).First();
    }

    private static IReadOnlyList<Parametros> Cargar()
    {
        var assembly = Assembly.GetExecutingAssembly();
        var recursos = assembly.GetManifestResourceNames()
            .Where(n => n.Contains(".Parametros.", StringComparison.Ordinal) && n.EndsWith(".json", StringComparison.Ordinal))
            .OrderBy(n => n)
            .ToList();

        if (recursos.Count == 0)
            throw new InvalidOperationException("No hay archivos de parámetros embebidos en el assembly.");

        var lista = new List<Parametros>(recursos.Count);

        foreach (var recurso in recursos)
        {
            using var stream = assembly.GetManifestResourceStream(recurso)
                ?? throw new InvalidOperationException($"No se pudo abrir el recurso '{recurso}'.");

            var dto = JsonSerializer.Deserialize<ParametrosDto>(stream, Opciones)
                ?? throw new InvalidOperationException($"El recurso '{recurso}' está vacío.");

            lista.Add(dto.Convertir());
        }

        return lista.OrderBy(p => p.VigenciaDesde).ToList();
    }

    private sealed record ParametrosDto
    {
        public string Id { get; init; } = "";
        public string Nombre { get; init; } = "";
        public string Fuente { get; init; } = "";
        public DateOnly VigenciaDesde { get; init; }
        public bool Estimado { get; init; }
        public string? Nota { get; init; }

        public decimal TasaJubilacion { get; init; } = 0.11m;
        public decimal TasaObraSocial { get; init; } = 0.03m;
        public decimal TasaPami { get; init; } = 0.03m;
        public int EdadPami { get; init; } = 70;
        public decimal TasaSindicato { get; init; } = 0.02m;

        public decimal ContribucionJubilacion { get; init; } = 0.1017m;
        public decimal ContribucionObraSocial { get; init; } = 0.06m;
        public decimal ContribucionAsignaciones { get; init; } = 0.015m;
        public decimal ContribucionFondoEmpleo { get; init; } = 0.005m;
        public decimal ContribucionSeguroVida { get; init; } = 0.004m;

        public decimal ZonaDesfavorable { get; init; } = 0.22m;
        public decimal HorasMensuales { get; init; } = 200m;
        public decimal DivisorVacaciones { get; init; } = 25m;

        public decimal MinimoNoImponible { get; init; }
        public decimal DeduccionEspecial { get; init; }
        public List<TramoDto> Escala { get; init; } = [];

        public decimal? TopeIndemnizacion { get; init; }
        public decimal? PisoIndemnizacion { get; init; }

        public Parametros Convertir() => new()
        {
            Id = Id,
            Nombre = Nombre,
            Fuente = Fuente,
            VigenciaDesde = VigenciaDesde,
            Estimado = Estimado,
            Nota = Nota,
            TasaJubilacion = TasaJubilacion,
            TasaObraSocial = TasaObraSocial,
            TasaPami = TasaPami,
            EdadPami = EdadPami,
            TasaSindicato = TasaSindicato,
            ContribucionJubilacion = ContribucionJubilacion,
            ContribucionObraSocial = ContribucionObraSocial,
            ContribucionAsignaciones = ContribucionAsignaciones,
            ContribucionFondoEmpleo = ContribucionFondoEmpleo,
            ContribucionSeguroVida = ContribucionSeguroVida,
            ZonaDesfavorable = ZonaDesfavorable,
            HorasMensuales = HorasMensuales,
            DivisorVacaciones = DivisorVacaciones,
            MinimoNoImponible = MinimoNoImponible,
            DeduccionEspecial = DeduccionEspecial,
            Escala = new EscalaGanancias(Escala.Select(t => new Tramo(
                t.Hasta ?? decimal.MaxValue,
                t.Aliquota))),
            TopeIndemnizacion = TopeIndemnizacion,
            PisoIndemnizacion = PisoIndemnizacion
        };
    }

    private sealed record TramoDto
    {
        public decimal? Hasta { get; init; }
        public decimal Aliquota { get; init; }
    }
}
