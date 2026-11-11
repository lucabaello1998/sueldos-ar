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
        var dias = DiasDelPeriodo(empleado, periodo);
        var diasTrabajados = Math.Min(dias, diasMes);
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

        // La zona desfavorable es remunerativa: también es base de horas extras.
        var baseHora = basico + antiguedad + zona;
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
        // Las "otras deducciones" (adelantos) no son deducibles del impuesto: solo
        // salen del neto. Pasarlas como deducción hacía que un adelanto bajara la
        // retención y el empleado cobrara de más.
        var ganancias = Ganancias.Calcular(bruto, aportes.Total, parametros);
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

        // La ley se actualiza por IPC: si el período es posterior al juego de parámetros, la escala
        // de ganancias puede estar vieja. No se inventan valores: se avisa.
        var mesesDeAtraso = (periodo.Anio - parametros.VigenciaDesde.Year) * 12 + periodo.Mes - parametros.VigenciaDesde.Month;
        if (mesesDeAtraso > 0)
            advertencias.Add(
                $"Los parámetros cargados son de {parametros.VigenciaDesde:MM/yyyy} y el período es {periodo.Mes:00}/{periodo.Anio}: " +
                "la escala de ganancias puede estar desactualizada. Cargá el JSON del período en Parametros/.");
        else if (mesesDeAtraso < 0)
            advertencias.Add(
                $"Los parámetros cargados son de {parametros.VigenciaDesde:MM/yyyy}, posteriores al período {periodo.Mes:00}/{periodo.Anio}: " +
                "se usan igual, pero los importes no son los que regían en ese período.");

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

        // Si entró (o egresó) a mitad del semestre, se prorratea desde esa fecha y no
        // desde el 1 de enero / 1 de julio.
        var dias = empleado.DiasTrabajados is { } pedidos
            ? Math.Min(pedidos, diasSemestre)
            : Sac.DiasTrabajadosDelSemestre(periodo, empleado.FechaIngreso, empleado.FechaEgreso);

        return Sac.Calcular(mejor, dias, diasSemestre);
    }

    /// <summary>
    /// Días del período que corresponden al empleado: los que informó, o los del mes
    /// recortados por la fecha de ingreso y la de egreso.
    /// </summary>
    private static int DiasDelPeriodo(Empleado empleado, Periodo periodo)
    {
        if (empleado.DiasTrabajados is { } informados)
        {
            if (informados < 0)
                throw new ArgumentOutOfRangeException(nameof(empleado), "Los días trabajados no pueden ser negativos.");
            return Math.Min(informados, periodo.DiasDelMes);
        }

        var desde = empleado.FechaIngreso > periodo.Primero ? empleado.FechaIngreso : periodo.Primero;
        var hasta = periodo.Ultimo;
        if (empleado.FechaEgreso is { } egreso && egreso < hasta)
            hasta = egreso;

        if (hasta < desde)
            throw new ArgumentException("El empleado no trabajó ningún día del período.", nameof(empleado));

        return hasta.DayNumber - desde.DayNumber + 1;
    }
}
