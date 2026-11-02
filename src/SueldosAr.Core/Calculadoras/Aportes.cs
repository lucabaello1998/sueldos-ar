using SueldosAr.Core.Modelos;

namespace SueldosAr.Core.Calculadoras;

public sealed record ResultadoAportes(decimal Jubilacion, decimal ObraSocial, decimal Pami, decimal Sindicato)
{
    public decimal Total => Jubilacion + ObraSocial + Pami + Sindicato;
}

/// <summary>
/// Aportes a cargo del trabajador sobre el bruto remunerativo.
/// Jubilación 11% (Ley 24.241), obra social 3% (Ley 23.660), PAMI 3% a partir de los 70 años (Ley 19.032)
/// y cuota sindical 2% solo si está afiliado.
/// </summary>
public static class Aportes
{
    public static ResultadoAportes Calcular(decimal bruto, Parametros parametros, int? edad, bool afiliadoSindicato)
    {
        ArgumentNullException.ThrowIfNull(parametros);

        if (bruto <= 0)
            return new ResultadoAportes(0, 0, 0, 0);

        var jubilacion = Pesos.Porcentaje(bruto, parametros.TasaJubilacion);
        var obraSocial = Pesos.Porcentaje(bruto, parametros.TasaObraSocial);

        var pami = edad >= parametros.EdadPami
            ? Pesos.Porcentaje(bruto, parametros.TasaPami)
            : 0m;

        var sindicato = afiliadoSindicato
            ? Pesos.Porcentaje(bruto, parametros.TasaSindicato)
            : 0m;

        return new ResultadoAportes(jubilacion, obraSocial, pami, sindicato);
    }
}

/// <summary>Contribuciones patronales (no se descuentan del bolsillo del empleado, pero son parte del costo).</summary>
public sealed record ResultadoContribuciones(
    decimal Jubilacion,
    decimal ObraSocial,
    decimal Asignaciones,
    decimal FondoEmpleo,
    decimal SeguroVida)
{
    public decimal Total => Jubilacion + ObraSocial + Asignaciones + FondoEmpleo + SeguroVida;
}

public static class Contribuciones
{
    public static ResultadoContribuciones Calcular(decimal bruto, Parametros parametros)
    {
        ArgumentNullException.ThrowIfNull(parametros);

        if (bruto <= 0)
            return new ResultadoContribuciones(0, 0, 0, 0, 0);

        return new ResultadoContribuciones(
            Pesos.Porcentaje(bruto, parametros.ContribucionJubilacion),
            Pesos.Porcentaje(bruto, parametros.ContribucionObraSocial),
            Pesos.Porcentaje(bruto, parametros.ContribucionAsignaciones),
            Pesos.Porcentaje(bruto, parametros.ContribucionFondoEmpleo),
            Pesos.Porcentaje(bruto, parametros.ContribucionSeguroVida));
    }
}
