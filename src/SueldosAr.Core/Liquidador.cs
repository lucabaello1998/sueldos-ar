using SueldosAr.Core.Calculadoras;
using SueldosAr.Core.Modelos;

namespace SueldosAr.Core;

/// <summary>
/// Arma el recibo del mes: remunerativos, aportes, ganancias y costo del empleador, dejando
/// cada concepto con su base legal para que el resultado se pueda auditar línea por línea.
/// </summary>
public static class Liquidador
{
    public static Recibo Liquidar(Empleado empleado, Periodo periodo, Parametros parametros)
    {
        ArgumentNullException.ThrowIfNull(empleado);
        ArgumentNullException.ThrowIfNull(parametros);

        if (empleado.SueldoBasico < 0)
            throw new ArgumentOutOfRangeException(nameof(empleado), "El sueldo básico no puede ser negativo.");

        if (empleado.FechaIngreso > periodo.Ultimo)
            throw new ArgumentException("El empleado ingresó después del cierre del período.", nameof(empleado));

        var advertencias = new List<string>();
        var conceptos = new List<Concepto>();

        var diasMes = periodo.DiasDelMes;
        var diasTrabajados = Math.Clamp(empleado.DiasTrabajados ?? diasMes, 0, diasMes);
        var proporcionDias = (decimal)diasTrabajados / diasMes;

        // --- Remunerativos ---
        var basico = Pesos.Redondear(empleado.SueldoBasico * proporcionDias);
        conceptos.Add(new Concepto("100", "Sueldo básico", basico, TipoConcepto.Remunerativo,
            diasTrabajados == diasMes
                ? "Sueldo mensual convenido"
                : $"Prorrateado por {diasTrabajados} de {diasMes} días"));

        var anios = empleado.AniosAntiguedad(periodo);
        var antiguedad = Pesos.Redondear(basico * empleado.PorcentajeAntiguedadPorAnio * anios);
        if (antiguedad > 0)
            conceptos.Add(new Concepto("110", $"Antigüedad ({anios} años)", antiguedad, TipoConcepto.Remunerativo,
                $"Art. 1° del CCT: {empleado.PorcentajeAntiguedadPorAnio:P0} por año"));

        var zona = empleado.ZonaDesfavorable
            ? Pesos.Redondear((basico + antiguedad) * parametros.ZonaDesfavorable)
            : 0m;
        if (zona > 0)
            conceptos.Add(new Concepto("120", "Zona desfavorable", zona, TipoConcepto.Remunerativo,
                $"Ley 19.587 / CCT: {parametros.ZonaDesfavorable:P0} sobre básico + antigüedad"));

        var baseHora = basico + antiguedad;
        var extras = HorasExtras.Calcular(baseHora, empleado.HorasExtrasAl50, empleado.HorasExtrasAl100,
            parametros.HorasMensuales);
        if (extras > 0)
        {
            var valorHora = HorasExtras.ValorHora(baseHora, parametros.HorasMensuales);
            var detalle = empleado.HorasExtrasAl50 > 0 && empleado.HorasExtrasAl100 > 0
                ? $"{empleado.HorasExtrasAl50:0.##} h al 50% y {empleado.HorasExtrasAl100:0.##} h al 100%"
                : empleado.HorasExtrasAl100 > 0
                    ? $"{empleado.HorasExtrasAl100:0.##} h al 100%"
                    : $"{empleado.HorasExtrasAl50:0.##} h al 50%";

            conceptos.Add(new Concepto("130", $"Horas extras ({detalle})", extras, TipoConcepto.Remunerativo,
                $"Art. 201 LCT — valor hora ${valorHora:N2} sobre {parametros.HorasMensuales:0} h mensuales"));
        }

        var bruto = conceptos.Where(c => c.Tipo == TipoConcepto.Remunerativo).Sum(c => c.Importe);

        // --- Aportes del trabajador ---
        var aportes = Aportes.Calcular(bruto, parametros, empleado.Edad, empleado.AfiliadoSindicato);

        if (aportes.Jubilacion > 0)
            conceptos.Add(new Concepto("200", "Jubilación", -aportes.Jubilacion, TipoConcepto.Descuento,
                $"Ley 24.241: {parametros.TasaJubilacion:P0}"));
        if (aportes.ObraSocial > 0)
            conceptos.Add(new Concepto("210", "Obra social", -aportes.ObraSocial, TipoConcepto.Descuento,
                $"Ley 23.660: {parametros.TasaObraSocial:P0}"));
        if (aportes.Pami > 0)
            conceptos.Add(new Concepto("220", "PAMI (INSSJP)", -aportes.Pami, TipoConcepto.Descuento,
                $"Ley 19.032: {parametros.TasaPami:P0} desde los {parametros.EdadPami} años"));
        if (aportes.Sindicato > 0)
            conceptos.Add(new Concepto("230", "Cuota sindical", -aportes.Sindicato, TipoConcepto.Descuento,
                $"Afiliación gremial: {parametros.TasaSindicato:P0}"));

        // --- Ganancias ---
        var ganancias = Ganancias.Calcular(bruto, aportes.Total, parametros, empleado.OtrasDeducciones);
        if (ganancias.Impuesto > 0)
            conceptos.Add(new Concepto("300", "Retención de ganancias", -ganancias.Impuesto, TipoConcepto.Descuento,
                $"Art. 90 LIG — tramo {ganancias.AliquotaMarginal:P0} sobre base ${ganancias.BaseImponible:N2}"));
        else if (ganancias.BaseImponible <= 0)
            advertencias.Add($"Sin retención de ganancias: el bruto no supera el mínimo no imponible más la deducción especial (${parametros.MinimoNoImponible + parametros.DeduccionEspecial:N0}).");

        if (empleado.OtrasDeducciones > 0)
            conceptos.Add(new Concepto("310", "Otras deducciones", -empleado.OtrasDeducciones, TipoConcepto.Descuento,
                "Adelantos y deducciones informadas"));

        // --- Contribuciones patronales (informativo, no afectan el neto) ---
        var contribuciones = Contribuciones.Calcular(bruto, parametros);
        conceptos.Add(new Concepto("400", "Contribuciones patronales", contribuciones.Total, TipoConcepto.Contribucion,
            "Decreto 814/2001: jubilación, obra social, asignaciones, FNE y seguro de vida"));

        var totalAportes = aportes.Total;
        var neto = bruto - totalAportes - ganancias.Impuesto - empleado.OtrasDeducciones;
        var costo = bruto + contribuciones.Total;

        if (parametros.Estimado)
            advertencias.Add($"Los parámetros {parametros.Id} son una actualización estimada: revisá la escala vigente antes de usarlos en producción.");

        return new Recibo
        {
            Empleado = empleado.Nombre,
            Periodo = periodo,
            Conceptos = conceptos,
            Bruto = bruto,
            TotalAportes = totalAportes,
            Ganancias = ganancias.Impuesto,
            OtrasDeducciones = empleado.OtrasDeducciones,
            Neto = Pesos.Redondear(neto),
            Contribuciones = contribuciones.Total,
            CostoEmpleador = Pesos.Redondear(costo),
            BaseImponibleGanancias = ganancias.BaseImponible,
            AliquotaMarginal = ganancias.AliquotaMarginal,
            Advertencias = advertencias
        };
    }

    /// <summary>SAC del semestre para un empleado, tomando la mejor remuneración informada o el bruto.</summary>
    public static ResultadoSac LiquidarSac(Empleado empleado, Periodo periodo, Parametros parametros)
    {
        ArgumentNullException.ThrowIfNull(empleado);
        ArgumentNullException.ThrowIfNull(parametros);

        var recibo = Liquidar(empleado, periodo, parametros);
        var mejor = empleado.MejorRemuneracionSemestre ?? recibo.Bruto;
        var diasSemestre = periodo.DiasDelSemestre;
        var dias = Math.Min(Sac.DiasTranscurridosDelSemestre(periodo), diasSemestre);

        return Sac.Calcular(mejor, dias, diasSemestre);
    }
}
