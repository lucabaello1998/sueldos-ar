using System.Globalization;
using SueldosAr.Core;
using SueldosAr.Core.Calculadoras;
using SueldosAr.Core.Carga;
using SueldosAr.Core.Modelos;

// Los importes se formatean con la cultura argentina también del lado del servidor.
var cultura = new CultureInfo("es-AR");
CultureInfo.DefaultThreadCurrentCulture = cultura;
CultureInfo.DefaultThreadCurrentUICulture = cultura;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddCors(o => o.AddDefaultPolicy(p => p.AllowAnyOrigin().AllowAnyHeader().AllowAnyMethod()));

var app = builder.Build();

app.UseDefaultFiles();
app.UseStaticFiles();
app.UseCors();

app.MapGet("/api/parametros", () => ParametrosRepositorio.Todos().Select(p => new
{
    p.Id,
    p.Nombre,
    p.Fuente,
    p.VigenciaDesde,
    p.Estimado,
    p.Nota,
    minimoNoImponible = p.MinimoNoImponible,
    deduccionEspecial = p.DeduccionEspecial,
    escala = p.Escala.Tramos.Select(t => new
    {
        hasta = t.Hasta == decimal.MaxValue ? (decimal?)null : t.Hasta,
        t.Aliquota
    })
}));

app.MapPost("/api/liquidacion", (PedidoLiquidacion pedido) =>
{
    try
    {
        var (empleado, periodo, parametros) = pedido.Armar();
        return Results.Ok(Proyectar(Liquidador.Liquidar(empleado, periodo, parametros)));
    }
    catch (Exception ex) when (ex is ArgumentException or KeyNotFoundException)
    {
        return Results.BadRequest(new { error = ex.Message });
    }
});

app.MapPost("/api/sac", (PedidoLiquidacion pedido) =>
{
    try
    {
        var (empleado, periodo, parametros) = pedido.Armar();
        return Results.Ok(Liquidador.LiquidarSac(empleado, periodo, parametros));
    }
    catch (Exception ex) when (ex is ArgumentException or KeyNotFoundException)
    {
        return Results.BadRequest(new { error = ex.Message });
    }
});

app.MapPost("/api/vacaciones", (PedidoVacaciones pedido) =>
{
    try
    {
        var resultado = Vacaciones.Calcular(
            DateOnly.Parse(pedido.FechaIngreso),
            pedido.Anio,
            pedido.SueldoBasico,
            pedido.DiasTomados,
            ParametrosRepositorio.ParaPeriodo(new Periodo(pedido.Anio, 1)).DivisorVacaciones);

        return Results.Ok(resultado);
    }
    catch (Exception ex) when (ex is ArgumentException or FormatException)
    {
        return Results.BadRequest(new { error = ex.Message });
    }
});

app.MapPost("/api/indemnizacion", (PedidoIndemnizacion pedido) =>
{
    try
    {
        var parametros = pedido.ParametrosId is { Length: > 0 } id
            ? ParametrosRepositorio.Obtener(id)
            : ParametrosRepositorio.ParaPeriodo(new Periodo(2026, 1));

        var empleado = new Empleado
        {
            Nombre = pedido.Nombre ?? "Trabajador",
            SueldoBasico = pedido.SueldoBasico,
            FechaIngreso = DateOnly.Parse(pedido.FechaIngreso),
            Edad = pedido.Edad,
            MejorRemuneracionSemestre = pedido.MejorRemuneracion
        };

        var resultado = Indemnizacion.Calcular(empleado, DateOnly.Parse(pedido.FechaDespido), parametros, pedido.MejorRemuneracion);
        return Results.Ok(resultado);
    }
    catch (Exception ex) when (ex is ArgumentException or FormatException or KeyNotFoundException)
    {
        return Results.BadRequest(new { error = ex.Message });
    }
});

app.MapGet("/api/salud", () => Results.Ok(new { estado = "ok", version = "1.0.0" }));

// La API expone un contrato plano: no serializa el dominio (Periodo tiene propiedades calculadas que se referencian).
static object Proyectar(Recibo r) => new
{
    empleado = r.Empleado,
    periodo = new { anio = r.Periodo.Anio, mes = r.Periodo.Mes, dias = r.Periodo.DiasDelMes },
    conceptos = r.Conceptos.Select(c => new
    {
        codigo = c.Codigo,
        detalle = c.Detalle,
        importe = c.Importe,
        tipo = c.Tipo.ToString(),
        baseLegal = c.Base
    }),
    bruto = r.Bruto,
    totalAportes = r.TotalAportes,
    ganancias = r.Ganancias,
    otrasDeducciones = r.OtrasDeducciones,
    neto = r.Neto,
    contribuciones = r.Contribuciones,
    costoEmpleador = r.CostoEmpleador,
    baseImponibleGanancias = r.BaseImponibleGanancias,
    aliquotaMarginal = r.AliquotaMarginal,
    advertencias = r.Advertencias
};

app.Run();

/// <summary>Datos que manda la UI para liquidar un mes.</summary>
public sealed record PedidoLiquidacion
{
    public string? Nombre { get; init; }
    public decimal SueldoBasico { get; init; }
    public string FechaIngreso { get; init; } = "2016-01-01";
    public int? Edad { get; init; }
    public bool AfiliadoSindicato { get; init; }
    public bool ZonaDesfavorable { get; init; }
    public decimal HorasExtrasAl50 { get; init; }
    public decimal HorasExtrasAl100 { get; init; }
    public int? DiasTrabajados { get; init; }
    public decimal OtrasDeducciones { get; init; }
    public decimal? MejorRemuneracionSemestre { get; init; }
    public int Anio { get; init; } = 2026;
    public int Mes { get; init; } = 1;
    public string? ParametrosId { get; init; }

    public (Empleado Empleado, Periodo Periodo, Parametros Parametros) Armar()
    {
        var periodo = new Periodo(Anio, Mes);

        var parametros = ParametrosId is { Length: > 0 } id
            ? ParametrosRepositorio.Obtener(id)
            : ParametrosRepositorio.ParaPeriodo(periodo);

        var empleado = new Empleado
        {
            Nombre = Nombre ?? "Trabajador",
            SueldoBasico = SueldoBasico,
            FechaIngreso = DateOnly.Parse(FechaIngreso),
            Edad = Edad,
            AfiliadoSindicato = AfiliadoSindicato,
            ZonaDesfavorable = ZonaDesfavorable,
            HorasExtrasAl50 = HorasExtrasAl50,
            HorasExtrasAl100 = HorasExtrasAl100,
            DiasTrabajados = DiasTrabajados,
            OtrasDeducciones = OtrasDeducciones,
            MejorRemuneracionSemestre = MejorRemuneracionSemestre
        };

        return (empleado, periodo, parametros);
    }
}

public sealed record PedidoVacaciones
{
    public string FechaIngreso { get; init; } = "2016-01-01";
    public int Anio { get; init; } = 2026;
    public decimal SueldoBasico { get; init; }
    public int? DiasTomados { get; init; }
}

public sealed record PedidoIndemnizacion
{
    public string? Nombre { get; init; }
    public decimal SueldoBasico { get; init; }
    public string FechaIngreso { get; init; } = "2016-01-01";
    public string FechaDespido { get; init; } = "2026-01-31";
    public decimal? MejorRemuneracion { get; init; }
    public int? Edad { get; init; }
    public string? ParametrosId { get; init; }
}
