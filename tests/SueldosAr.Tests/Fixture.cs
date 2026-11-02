using SueldosAr.Core;
using SueldosAr.Core.Calculadoras;
using SueldosAr.Core.Carga;
using SueldosAr.Core.Modelos;

namespace SueldosAr.Tests;

/// <summary>Helper para no repetir el armado de parámetros en cada test.</summary>
internal static class Fixture
{
    public static Parametros Parametros2024 => ParametrosRepositorio.Obtener("2024-07");

    public static Parametros ConEscalaSimple(params (decimal hasta, decimal alicuota)[] tramos) => new()
    {
        Id = "test",
        Nombre = "Escala de prueba",
        Fuente = "Test",
        VigenciaDesde = new DateOnly(2024, 1, 1),
        MinimoNoImponible = 0,
        DeduccionEspecial = 0,
        Escala = new EscalaGanancias(tramos.Select(t => new Tramo(t.hasta, t.alicuota)))
    };

    public static Empleado EmpleadoBase(decimal basico = 1_000_000m) => new()
    {
        Nombre = "Empleado de prueba",
        SueldoBasico = basico,
        FechaIngreso = new DateOnly(2016, 1, 1),
        Edad = 35
    };

    public static readonly Periodo Periodo2026 = new(2026, 3);
}
