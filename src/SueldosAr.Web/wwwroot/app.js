const formato = new Intl.NumberFormat('es-AR', {
  style: 'currency',
  currency: 'ARS',
  maximumFractionDigits: 2
});

const numero = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 2 });

const pesos = (v) => formato.format(Number(v) || 0);
const pct = (v) => `${numero.format((Number(v) || 0) * 100)}%`;

const compacto = (v) => {
  const n = Number(v) || 0;
  const abs = Math.abs(n);
  if (abs >= 1e6) return `$${numero.format(n / 1e6)} M`;
  if (abs >= 1e3) return `$${numero.format(n / 1e3)} K`;
  return pesos(n);
};

let parametros = null;

/* ---------------- tabs ---------------- */
document.querySelectorAll('.tab').forEach((tab) => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach((t) => {
      t.classList.remove('activo');
      t.setAttribute('aria-selected', 'false');
    });
    document.querySelectorAll('.panel').forEach((p) => p.classList.remove('activo'));

    tab.classList.add('activo');
    tab.setAttribute('aria-selected', 'true');
    document.getElementById(`panel-${tab.dataset.panel}`).classList.add('activo');
  });
});

/* ---------------- parámetros ---------------- */
async function cargarParametros() {
  try {
    const res = await fetch('/api/parametros');
    const lista = await res.json();
    parametros = lista[0];
    const texto = `${parametros.nombre}${parametros.estimado ? ' (estimado)' : ''}`;
    document.getElementById('parametros-texto').textContent = texto;
    document.getElementById('pie-parametros').textContent = texto;
  } catch {
    document.getElementById('parametros-texto').textContent = 'parámetros no disponibles';
  }
}

/* ---------------- helpers de render ---------------- */
function tarjetas(items) {
  return `<div class="tarjetas">${items
    .map(
      (t) => `<div class="tarjeta ${t.destacada ? 'destacada' : ''}">
        <div class="rotulo">${t.rotulo}</div>
        <div class="valor ${t.rojo ? 'rojo' : ''}">${t.valor}</div>
      </div>`
    )
    .join('')}</div>`;
}

function dona(partes, centroEtiqueta, centroValor) {
  const total = partes.reduce((s, p) => s + Math.max(0, p.valor), 0) || 1;
  const radio = 54;
  const grosor = 18;
  const circunferencia = 2 * Math.PI * radio;

  let offset = 0;
  const arcos = partes
    .filter((p) => p.valor > 0)
    .map((p) => {
      const largo = (p.valor / total) * circunferencia;
      const arco = `<circle cx="70" cy="70" r="${radio}" fill="none" stroke="${p.color}"
        stroke-width="${grosor}" stroke-dasharray="${largo} ${circunferencia - largo}"
        stroke-dashoffset="${-offset}" transform="rotate(-90 70 70)" stroke-linecap="butt" />`;
      offset += largo;
      return arco;
    })
    .join('');

  const leyenda = partes
    .filter((p) => p.valor > 0)
    .map(
      (p) => `<span><i style="background:${p.color}"></i>${p.nombre}
        <strong style="color:var(--texto)">${pesos(p.valor)}</strong>
        <span style="opacity:.7">${pct(p.valor / total)}</span></span>`
    )
    .join('');

  return `<div class="dona">
    <svg width="140" height="140" viewBox="0 0 140 140" role="img" aria-label="${centroEtiqueta}: ${centroValor}">
      <circle cx="70" cy="70" r="${radio}" fill="none" stroke="#16202c" stroke-width="${grosor}" />
      ${arcos}
      <text x="70" y="66" text-anchor="middle" fill="#9db0c4" font-size="9" font-family="system-ui">${centroEtiqueta}</text>
      <text x="70" y="82" text-anchor="middle" fill="#e8eef6" font-size="14" font-weight="700" font-family="system-ui">${centroValor}</text>
    </svg>
    <div class="leyenda">${leyenda}</div>
  </div>`;
}

function mostrarError(id, mensaje) {
  document.getElementById(id).innerHTML = `<div class="error">${mensaje}</div>`;
}

async function pedir(url, datos) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(datos)
  });

  const cuerpo = await res.json();
  if (!res.ok) throw new Error(cuerpo.error || 'No se pudo calcular');
  return cuerpo;
}

const datosDelFormulario = (form) => {
  const datos = Object.fromEntries(new FormData(form).entries());
  for (const clave of Object.keys(datos)) {
    if (datos[clave] === '') delete datos[clave];
  }
  return datos;
};

/* ---------------- sueldo ---------------- */
document.getElementById('form-sueldo').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  const form = evento.target;
  const datos = datosDelFormulario(form);

  const [anio, mes] = (datos.periodo || '2026-03').split('-');
  delete datos.periodo;

  const pedido = {
    ...datos,
    anio: Number(anio),
    mes: Number(mes),
    sueldoBasico: Number(datos.sueldoBasico || 0),
    edad: datos.edad ? Number(datos.edad) : null,
    horasExtrasAl50: Number(datos.horasExtrasAl50 || 0),
    horasExtrasAl100: Number(datos.horasExtrasAl100 || 0),
    diasTrabajados: datos.diasTrabajados ? Number(datos.diasTrabajados) : null,
    otrasDeducciones: Number(datos.otrasDeducciones || 0),
    afiliadoSindicato: datos.afiliadoSindicato === 'on',
    zonaDesfavorable: datos.zonaDesfavorable === 'on'
  };

  try {
    const recibo = await pedir('/api/liquidacion', pedido);
    document.getElementById('resultado-sueldo').innerHTML = renderRecibo(recibo);
  } catch (error) {
    mostrarError('resultado-sueldo', error.message);
  }
});

function renderRecibo(r) {
  const remunerativos = r.conceptos.filter((c) => c.tipo === 'Remunerativo' || c.tipo === 0);
  const descuentos = r.conceptos.filter((c) => c.tipo === 'Descuento' || c.tipo === 1);
  const contribuciones = r.conceptos.filter((c) => c.tipo === 'Contribucion' || c.tipo === 2);

  const filas = (lista, clase = '') =>
    lista
      .map(
        (c) => `<tr>
          <td><strong>${c.codigo}</strong> ${c.detalle}<span class="base">${c.baseLegal}</span></td>
          <td class="num ${clase}">${pesos(c.importe)}</td>
        </tr>`
      )
      .join('');

  const advertencias = (r.advertencias || [])
    .map((a) => `<div class="advertencia">${a}</div>`)
    .join('');

  return `
    ${advertencias}
    ${tarjetas([
      { rotulo: 'Bruto', valor: pesos(r.bruto) },
      { rotulo: 'Aportes + ganancias', valor: pesos(-(r.totalAportes + r.ganancias)), rojo: true },
      { rotulo: 'Neto a cobrar', valor: pesos(r.neto), destacada: true },
      { rotulo: 'Costo empleador', valor: pesos(r.costoEmpleador) }
    ])}

    ${dona(
      [
        { nombre: 'Neto', valor: r.neto, color: '#35d39a' },
        { nombre: 'Aportes', valor: r.totalAportes, color: '#2bb3ff' },
        { nombre: 'Ganancias', valor: r.ganancias, color: '#ffb648' },
        { nombre: 'Otras deducciones', valor: r.otrasDeducciones, color: '#8b6bff' }
      ],
      'NETO',
      compacto(r.neto)
    )}

    <div class="seccion-titulo">Remunerativos</div>
    <table class="tabla">
      <thead><tr><th>Concepto</th><th style="text-align:right">Importe</th></tr></thead>
      <tbody>
        ${filas(remunerativos)}
        <tr class="total"><td>Total bruto</td><td class="num">${pesos(r.bruto)}</td></tr>
      </tbody>
    </table>

    <div class="seccion-titulo">Descuentos</div>
    <table class="tabla">
      <thead><tr><th>Concepto</th><th style="text-align:right">Importe</th></tr></thead>
      <tbody>
        ${filas(descuentos, 'negativo')}
        <tr class="total"><td>Total descuentos</td>
          <td class="num negativo">${pesos(-(r.totalAportes + r.ganancias + r.otrasDeducciones))}</td></tr>
      </tbody>
    </table>

    <div class="seccion-titulo">Costo del empleador</div>
    <table class="tabla">
      <tbody>
        ${filas(contribuciones, 'contribucion')}
        <tr class="total"><td>Bruto + contribuciones</td><td class="num">${pesos(r.costoEmpleador)}</td></tr>
      </tbody>
    </table>

    <p class="nota">
      Base imponible de ganancias: <strong>${pesos(r.baseImponibleGanancias)}</strong>
      · alícuota marginal: <strong>${pct(r.aliquotaMarginal)}</strong>
      · mínimo no imponible + deducción especial del juego cargado.
    </p>`;
}

/* ---------------- SAC ---------------- */
document.getElementById('form-sac').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  const datos = datosDelFormulario(evento.target);
  const [anio, mes] = (datos.periodo || '2026-06').split('-');

  try {
    const r = await pedir('/api/sac', {
      nombre: 'SAC',
      sueldoBasico: Number(datos.mejor || 0),
      mejorRemuneracionSemestre: Number(datos.mejor || 0),
      fechaIngreso: '2016-01-01',
      anio: Number(anio),
      mes: Number(mes)
    });

    document.getElementById('resultado-sac').innerHTML = `
      ${tarjetas([
        { rotulo: 'Mejor remuneración', valor: pesos(r.mejorRemuneracion) },
        { rotulo: 'Días computados', valor: `${r.diasTrabajados} / ${r.diasDelSemestre}` },
        { rotulo: 'SAC a pagar', valor: pesos(r.importe), destacada: true }
      ])}
      ${dona(
        [
          { nombre: 'SAC', valor: r.importe, color: '#35d39a' },
          { nombre: 'Resto del semestre', valor: Math.max(0, r.mejorRemuneracion / 2 - r.importe), color: '#22303f' }
        ],
        'SAC',
        compacto(r.importe)
      )}
      <p class="nota">
        ${r.proporcional
          ? 'Es proporcional: no se trabajó el semestre completo.'
          : 'Semestre completo: corresponde la mitad de la mejor remuneración.'}
        Base legal: Ley 23.041 y art. 121 LCT.
      </p>`;
  } catch (error) {
    mostrarError('resultado-sac', error.message);
  }
});

/* ---------------- vacaciones ---------------- */
document.getElementById('form-vacaciones').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  const datos = datosDelFormulario(evento.target);

  try {
    const r = await pedir('/api/vacaciones', {
      fechaIngreso: datos.fechaIngreso,
      anio: Number(datos.anio || 2026),
      sueldoBasico: Number(datos.sueldoBasico || 0),
      diasTomados: datos.diasTomados ? Number(datos.diasTomados) : null
    });

    document.getElementById('resultado-vacaciones').innerHTML = `
      ${tarjetas([
        { rotulo: 'Antigüedad', valor: `${r.aniosAntiguedad} años` },
        { rotulo: 'Días que corresponden', valor: `${r.diasCorresponden}` },
        { rotulo: 'Valor día', valor: pesos(r.valorDia) },
        { rotulo: 'A cobrar', valor: pesos(r.importe), destacada: true }
      ])}
      <p class="nota">
        ${r.diasTomados} de ${r.diasCorresponden} días corridos, sobre un sueldo dividido 25.
        Base legal: arts. 150 y 155 LCT.
      </p>`;
  } catch (error) {
    mostrarError('resultado-vacaciones', error.message);
  }
});

/* ---------------- indemnización ---------------- */
document.getElementById('form-indemnizacion').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  const datos = datosDelFormulario(evento.target);

  try {
    const r = await pedir('/api/indemnizacion', {
      sueldoBasico: Number(datos.sueldoBasico || 0),
      fechaIngreso: datos.fechaIngreso,
      fechaDespido: datos.fechaDespido,
      mejorRemuneracion: datos.mejorRemuneracion ? Number(datos.mejorRemuneracion) : null
    });

    const avisos = [
      r.topeAplicado ? '<div class="advertencia">Se aplicó el tope del art. 245 configurado en los parámetros.</div>' : '',
      r.pisoAplicado ? '<div class="advertencia">Se aplicó el piso indemnizatorio configurado.</div>' : ''
    ].join('');

    document.getElementById('resultado-indemnizacion').innerHTML = `
      ${avisos}
      ${tarjetas([
        { rotulo: 'Años computados', valor: `${r.aniosComputados}` },
        { rotulo: 'Antigüedad (art. 245)', valor: pesos(r.antiguedad) },
        { rotulo: 'Preaviso', valor: pesos(r.preaviso) },
        { rotulo: 'Total', valor: pesos(r.total), destacada: true }
      ])}
      ${dona(
        [
          { nombre: 'Antigüedad', valor: r.antiguedad, color: '#35d39a' },
          { nombre: 'Preaviso', valor: r.preaviso, color: '#2bb3ff' },
          { nombre: 'Integración mes', valor: r.integracionMesDespido, color: '#ffb648' },
          { nombre: 'SAC s/ indemnización', valor: r.sacSobreIndemnizacion, color: '#8b6bff' }
        ],
        'TOTAL',
        compacto(r.total)
      )}
      <table class="tabla">
        <tbody>
          <tr><td>Mejor remuneración mensual</td><td class="num">${pesos(r.mejorRemuneracion)}</td></tr>
          <tr><td>Antigüedad (${r.aniosComputados} años, art. 245)</td><td class="num">${pesos(r.antiguedad)}</td></tr>
          <tr><td>Preaviso (${r.mesesPreaviso} ${r.mesesPreaviso === 1 ? 'mes' : 'meses'}, art. 232)</td><td class="num">${pesos(r.preaviso)}</td></tr>
          <tr><td>Integración del mes de despido (art. 233)</td><td class="num">${pesos(r.integracionMesDespido)}</td></tr>
          <tr><td>SAC proporcional (art. 123)</td><td class="num">${pesos(r.sacSobreIndemnizacion)}</td></tr>
          <tr class="total"><td>Total indemnizatorio</td><td class="num">${pesos(r.total)}</td></tr>
        </tbody>
      </table>`;
  } catch (error) {
    mostrarError('resultado-indemnizacion', error.message);
  }
});

/* ---------------- arranque ---------------- */
cargarParametros();

document.querySelector('#form-sueldo').dispatchEvent(new Event('submit'));
