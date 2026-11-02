using SueldosAr.Core.Modelos;

namespace SueldosAr.Core.Calculadoras;

public sealed record ResultadoGanancias(
    decimal BaseImponible,
    decimal MinimoNoImponible,
    decimal DeduccionEspecial,
    decimal Impuesto,
    decimal AliquotaMarginal);

/// <summary>
/// Impuesto a las ganancias, cuarta categoría, relación de dependencia (arts. 82 y 90 LIG).
/// Base = bruto − aportes obligatorios − mínimo no imponible − deducción especial − otras deducciones.
/// </summary>
public static class Ganancias
{
    public static ResultadoGanancias Calcular(
        decimal bruto,
        decimal aportesObligatorios,
        Parametros parametros,
        decimal otrasDeducciones = 0)
    {
        ArgumentNullException.ThrowIfNull(parametros);

        var mni = parametros.MinimoNoImponible;
        var especial = parametros.DeduccionEspecial;

        var baseImponible = bruto - aportesObligatorios - mni - especial - otrasDeducciones;
        if (baseImponible <= 0)
            return new ResultadoGanancias(0, mni, especial, 0, 0);

        var impuesto = parametros.Escala.Calcular(baseImponible);

        return new ResultadoGanancias(
            Pesos.Redondear(baseImponible),
            mni,
            especial,
            impuesto,
            parametros.Escala.AliquotaMarginal(baseImponible));
    }
}
