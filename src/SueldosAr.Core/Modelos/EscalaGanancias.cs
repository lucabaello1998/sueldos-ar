namespace SueldosAr.Core.Modelos;

/// <summary>
/// Escala progresiva del impuesto a las ganancias (art. 90 LIG). Se define por tramos marginales:
/// cada peso paga la alícuota del tramo en el que cae, no la del tramo más alto.
/// </summary>
public sealed class EscalaGanancias
{
    private readonly IReadOnlyList<Tramo> _tramos;

    public EscalaGanancias(IEnumerable<Tramo> tramos)
    {
        var lista = tramos.OrderBy(t => t.Hasta).ToList();
        if (lista.Count == 0)
            throw new ArgumentException("La escala necesita al menos un tramo.", nameof(tramos));

        if (lista[^1].Hasta != decimal.MaxValue)
            lista[^1] = lista[^1] with { Hasta = decimal.MaxValue };

        _tramos = lista;
    }

    public IReadOnlyList<Tramo> Tramos => _tramos;

    public decimal Calcular(decimal baseImponible)
    {
        if (baseImponible <= 0)
            return 0;

        decimal impuesto = 0;
        decimal piso = 0;

        foreach (var tramo in _tramos)
        {
            if (baseImponible <= piso)
                break;

            var gravado = Math.Min(baseImponible, tramo.Hasta) - piso;
            impuesto += gravado * tramo.Aliquota;
            piso = tramo.Hasta;
        }

        return Math.Round(impuesto, 2, MidpointRounding.AwayFromZero);
    }

    /// <summary>Alícuota marginal que aplica al último peso de la base.</summary>
    public decimal AliquotaMarginal(decimal baseImponible)
    {
        foreach (var tramo in _tramos)
            if (baseImponible <= tramo.Hasta)
                return tramo.Aliquota;

        return _tramos[^1].Aliquota;
    }
}

/// <summary>Un tramo de la escala. <see cref="Hasta"/> es el techo acumulado del tramo.</summary>
public sealed record Tramo(decimal Hasta, decimal Aliquota);
