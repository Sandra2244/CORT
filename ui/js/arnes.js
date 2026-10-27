/* ===== Arnés de CORT · la capa que une la voz con las herramientas =====
 *
 * La dueña pidió un arnés como los de OpenClaw y Hermes Agent: el sitio donde se
 * ve qué tiene CORT debajo —el puente, el núcleo, la memoria, las sesiones y las
 * herramientas— y si cada pieza está sana. No es un chat nuevo ni una promesa de
 * agentes autónomos: es el tablero de lo que ESTE aparato ya hace.
 *
 * Tres reglas para que no mienta:
 *
 * · Todo sale de una fuente real: `capacidades()`, `memoria('estado')`,
 *   `bgStatus()`, `musicaEstado()` del puente; `localStorage` de la Charla; y
 *   `/api/port`, `/api/status`, `/api/history` y `/api/memories` del núcleo.
 *   Si una fuente no contesta, la fila dice «no se pudo leer», no un cero bonito.
 * · Las 91 intenciones y sus 736 frases vienen del diccionario generado
 *   (`diccionario.js`), la misma tabla que atiende `Cerebro`. Aquí no se escribe
 *   una segunda lista que pueda quedarse vieja.
 * · El arnés no ejecuta nada por su cuenta: los ejemplos se mandan por
 *   `cort:orden`, igual que si se dijeran en voz alta, y «ver el Centro» cambia
 *   de hoja. Lo que no existe (varias sesiones simultáneas, agentes en segundo
 *   plano, nodos remotos) se dice como lo que es: todavía no.
 *
 * Vive aparte de `pantallas.js` y recibe `ir`, `api`, `pantallas` y el puente:
 * así la sonda lo puede montar con dobles sin tocar el teléfono.
 */
import { DICCIONARIO, TOTALES } from './diccionario.js';
import { esc } from './texto.js';

const CAPAS = {
  mando: { nombre: 'Aparato', icono: '⚙' },
  razon: { nombre: 'Razón', icono: '∑' },
  casa:  { nombre: 'Casa y equipo', icono: '⌂' },
  nube:  { nombre: 'Nube', icono: '☁' },
};

/** Objeto desde JSON, o `{}`. Nunca lanza: el arnés no se cae por un campo raro. */
function objeto(v) {
  if (!v) return {};
  if (typeof v === 'object') return Array.isArray(v) ? {} : v;
  try { const x = JSON.parse(v); return x && typeof x === 'object' && !Array.isArray(x) ? x : {}; }
  catch { return {}; }
}
function lista(v) {
  if (Array.isArray(v)) return v;
  try { const x = JSON.parse(v || '[]'); return Array.isArray(x) ? x : []; } catch { return []; }
}
const intenta = (f, porSi) => { try { return f(); } catch { return porSi; } };
const si = (v, siNo = '—') => v === 0 ? '0' : (v || siNo);

function fecha(ms) {
  const n = Number(ms);
  if (!n) return '';
  try {
    return new Date(n).toLocaleString('es-MX',
      { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  } catch { return new Date(n).toISOString().slice(0, 16).replace('T', ' '); }
}

/** Pide JSON al núcleo con un tope corto: si el portátil está dormido, no se espera. */
async function pide(url) {
  try {
    const r = await fetch(url, { signal: AbortSignal.timeout(1800) });
    if (!r.ok) return null;
    return await r.json();
  } catch { return null; }
}

/** Los datos del aparato. Puro: recibe el puente y el texto del historial. */
export function datosDelArnés({ N, historial }) {
  const caps = N && typeof N.capacidades === 'function'
    ? objeto(intenta(() => N.capacidades(), '')) : {};
  const mem = N && typeof N.memoria === 'function'
    ? objeto(intenta(() => N.memoria('{"que":"estado"}'), '')) : {};
  const bg = N && typeof N.bgStatus === 'function'
    ? objeto(intenta(() => N.bgStatus(), '')) : {};
  const musi = N && typeof N.musicaEstado === 'function'
    ? objeto(intenta(() => N.musicaEstado(), '')) : {};
  const camara = N && typeof N.hasPermission === 'function'
    ? intenta(() => !!N.hasPermission('camara'), null) : null;
  const sesion = lista(historial);
  const ultima = sesion.length ? sesion[sesion.length - 1].hora || 0 : 0;
  return { caps, mem, bg, musi, camara, sesion, ultima,
           puente: !!N, metodos: N ? Object.keys(N).length : 0 };
}

function vista(d) {
  const capas = Object.entries(TOTALES.porCapa || {}).map(([id, n]) => ({
    id, n, ...(CAPAS[id] || { nombre: id, icono: '·' }),
  }));
  const ejemplos = Object.keys(CAPAS)
    .map(id => DICCIONARIO.find(x => x.capa === id && x.ejemplo)).filter(Boolean);
  const perfil = d.caps.perfil || (d.puente ? 'APK sin capacidades' : 'navegador');
  const servicios = ['asistente', 'avisos', 'cortina', 'reconocedor', 'llamadas', 'agenda'];
  const nucleo = d.nucleo || {};
  const cerebro = nucleo.status && nucleo.status.brain ? nucleo.status.brain : null;
  const mirando = d.mirando === true;
  const coreSi = nucleo.core === true;
  const coreNo = nucleo.core === false;

  const luz = (estado, texto) =>
    `<span class="arn-luz ${estado}" title="${esc(texto)}"></span>`;

  const filasSalud = [
    { n: 'Puente Android', e: d.puente ? 'ok' : 'off',
      t: d.puente ? `${d.metodos} métodos nativos` : 'esta cara va sin puente (PC)' },
    { n: 'Núcleo del portátil', e: mirando ? 'warn' : coreSi ? 'ok' : coreNo ? 'warn' : 'off',
      t: mirando ? 'comprobando…' : coreSi ? nucleo.url : coreNo ? `no responde en ${nucleo.url}` : 'sin dirección' },
    { n: 'Micrófono', e: d.bg.mic ? 'ok' : d.puente ? 'warn' : 'off',
      t: d.bg.mic ? 'permiso concedido' : d.puente ? 'falta el permiso' : 'lo pone Android' },
    { n: 'Cámara', e: d.camara === true ? 'ok' : d.camara === false ? 'warn' : 'off',
      t: d.camara === true ? 'permiso concedido · la vista abre desde la mano'
        : d.camara === false ? 'falta el permiso' : 'no comprobable sin puente' },
    { n: 'Memoria del teléfono', e: d.mem.ok ? 'ok' : d.puente ? 'warn' : 'off',
      t: d.mem.ok ? `${si(d.mem.hechos)} hechos · ${si(d.mem.recuerdos)} recuerdos`
        : d.puente ? 'el puente no dio el estado' : 'vive en el teléfono' },
    { n: 'Sesión local', e: d.sesion.length ? 'ok' : 'off',
      t: d.sesion.length ? `${d.sesion.length} mensajes${d.ultima ? ' · ' + fecha(d.ultima) : ''}`
        : 'la Charla aún no tiene mensajes' },
    { n: 'Música', e: d.musi.suena ? 'ok' : 'off',
      t: d.musi.suena ? (d.musi.pista && d.musi.pista.titulo ? 'suena «' + d.musi.pista.titulo + '»' : 'reproduciendo')
        : 'en silencio' },
  ];

  return `
  <div class="arn-cabeza">
    <h2>ARNÉS</h2>
    <p>La capa que une la voz con las herramientas. Se lee del aparato cada vez que
       entras; lo que no contesta se dice, no se rellena.</p>
  </div>

  <div class="arn-rejilla">
    <section class="arn-caja">
      <h3>◈ Nodos</h3>
      <div class="arn-fila">${luz(d.puente ? 'ok' : 'off', 'puente')}
        <b>Este aparato</b><small>${esc(perfil)} · ${d.puente ? d.metodos + ' métodos' : 'sin puente'}</small></div>
      <div class="arn-chips">${servicios.map(s =>
        `<span class="arn-chip ${d.caps[s] ? 'on' : 'off'}">${esc(s)}</span>`).join('')}</div>
      <div class="arn-fila">${luz(mirando ? 'warn' : coreSi ? 'ok' : 'off', 'núcleo')}
        <b>Portátil</b><small>${mirando ? 'comprobando…'
          : coreSi ? esc(nucleo.url) : coreNo ? 'sin respuesta' : 'sin dirección'}</small></div>
      ${coreSi ? (cerebro ? `<div class="arn-fila"><b>Cerebro</b><small>${esc(cerebro.mode || '—')}
        · ${cerebro.ollama ? 'Ollama' : 'Ollama no'} · ${cerebro.groq ? 'Groq' : 'sin Groq'}
        · ${cerebro.gemini ? 'Gemini' : 'sin Gemini'}</small></div>
        ${nucleo.status.system ? `<p class="arn-suelto">${esc(nucleo.status.system)}</p>` : ''}`
        : `<p class="arn-suelto">El portátil contestó, pero no entregó su estado del cerebro:
           una consulta se pasó del tope. No se pone «Ollama no» cuando lo que hubo fue
           silencio.</p>`)
        : `<p class="arn-suelto">${coreNo ? 'El portátil no contestó: CORT sigue con lo que tiene en el teléfono.' : 'Se comprueba al entrar; esta cara no lleva la dirección.'}</p>`}
    </section>

    <section class="arn-caja">
      <h3>▤ Herramientas</h3>
      <p class="arn-suelto">${TOTALES.intents} intenciones y ${TOTALES.frases} frases del
         diccionario que atiende la voz. No hay una segunda lista.</p>
      <div class="arn-chips">${capas.map(c =>
        `<span class="arn-chip on">${esc(c.icono + ' ' + c.nombre)} <b>${c.n}</b></span>`).join('')}</div>
      ${ejemplos.map(x => `<button class="arn-ej" data-frase="${esc(x.ejemplo || x.titulo)}">
        <b>${esc(x.titulo || x.id)}</b><small>“${esc(x.ejemplo || x.titulo)}”</small></button>`).join('')}
      <button class="arn-ej arn-centro" data-centro="1"><b>Abrir el Centro</b>
        <small>las ${TOTALES.intents} órdenes, con búsqueda</small></button>
    </section>

    <section class="arn-caja">
      <h3>✦ Sesiones</h3>
      <div class="arn-fila">${luz(d.sesion.length ? 'ok' : 'off', 'sesión')}
        <b>Conversación local</b><small>${d.sesion.length} mensajes</small></div>
      ${d.ultima ? `<p class="arn-suelto">Último mensaje: ${esc(fecha(d.ultima))}</p>` : ''}
      <div class="arn-fila">${luz(coreSi ? (nucleo.historial ? 'ok' : 'warn') : 'off', 'historial')}
        <b>Historial del núcleo</b><small>${coreSi
          ? (nucleo.historial || 0) + ' respuestas guardadas' : 'sin núcleo'}</small></div>
      <p class="arn-suelto">CORT guarda <b>una</b> conversación local (los últimos 40
         mensajes) y el núcleo recuerda las últimas respuestas. No hay varias sesiones
         a la vez: esta fila no finge pestañas que no existen.</p>
    </section>

    <section class="arn-caja">
      <h3>◉ Memoria</h3>
      ${d.mem.ok ? `
        <div class="arn-fila">${luz('ok', 'memoria')}<b>Hechos</b><small>${si(d.mem.hechos)}</small></div>
        <div class="arn-fila">${luz('ok', 'memoria')}<b>Recuerdos</b><small>${si(d.mem.recuerdos)}</small></div>
        <div class="arn-fila">${luz('ok', 'memoria')}<b>Habilidades</b><small>${si(d.mem.habilidades)}</small></div>
        <div class="arn-fila">${luz(d.mem.conPortatil ? 'ok' : 'off', 'pc')}
          <b>Con portátil</b><small>${d.mem.conPortatil ? esc(d.mem.direccion || 'sí') : 'no'}</small></div>
        ${d.mem.sincronizando ? '<p class="arn-suelto">Sincronizando con el portátil ahora mismo.</p>' : ''}`
        : `<p class="arn-suelto">${d.puente
            ? 'El puente no entregó el estado de la memoria; no se pone un número de adorno.'
            : 'La memoria del teléfono existe cuando corre el APK; aquí no hay puente.'}</p>`}
      ${coreSi ? `<div class="arn-fila">${luz(nucleo.memorias ? 'ok' : 'off', 'memorias')}
        <b>Muro del núcleo</b><small>${nucleo.memorias || 0} recuerdos</small></div>` : ''}
    </section>

    <section class="arn-caja">
      <h3>✚ Salud</h3>
      ${filasSalud.map(f => `<div class="arn-fila">${luz(f.e, f.n)}<b>${esc(f.n)}</b>
        <small>${esc(f.t)}</small></div>`).join('')}
    </section>

    <section class="arn-caja">
      <h3>⌘ Puerta</h3>
      <p class="arn-suelto">Por donde se entra a CORT ahora mismo. Sólo se enciende lo
         que este aparato tiene de verdad.</p>
      <div class="arn-fila">${luz(d.caps.reconocedor ? 'ok' : 'off', 'voz')}
        <b>Voz</b><small>${d.puente ? (d.caps.reconocedor ? 'reconocedor del APK' : 'sin reconocedor')
          : 'lo pone el APK'}</small></div>
      <div class="arn-fila">${luz(d.caps.avisos ? 'ok' : 'off', 'avisos')}
        <b>Avisos</b><small>${d.puente ? (d.caps.avisos ? 'puede leerlos' : 'perfil sin avisos')
          : 'sólo en el teléfono'}</small></div>
      <div class="arn-fila">${luz(d.bg.bg ? 'ok' : 'off', 'fondo')}
        <b>Segundo plano</b><small>${d.puente
          ? (d.bg.bg ? (d.bg.running ? 'aviso puesto' : 'interruptor sí, aviso no') : 'se guarda al salir')
          : 'sólo en el teléfono'}</small></div>
      <div class="arn-fila">${luz(d.bg.overlay ? 'ok' : 'off', 'burbuja')}
        <b>Burbuja</b><small>${d.puente
          ? (d.bg.overlay ? 'permiso concedido' : 'falta «aparecer encima»')
          : 'sólo en el teléfono'}</small></div>
      <div class="arn-fila">${luz('ok', 'pantallas')}
        <b>Pantallas</b><small>${d.apps} hojas en este aparato</small></div>
      ${d.bg.maker ? `<p class="arn-suelto">Fabricante: ${esc(d.bg.maker)}</p>` : ''}
    </section>
  </div>
  <p class="arn-pie">Leído a las ${esc(new Date().toLocaleTimeString('es-MX'))}.
     El arnés enseña; no ejecuta nada por su cuenta.</p>`;
}

async function miraNucleo(base) {
  if (!base) return { mirando: false, nucleo: { core: false } };
  const puerto = await pide(base + '/api/port');
  if (!puerto) return { mirando: false, nucleo: { core: false, url: base } };
  const [status, hist, mems] = await Promise.all([
    pide(base + '/api/status'),
    pide(base + '/api/history?n=40'),
    pide(base + '/api/memories'),
  ]);
  return {
    mirando: false,
    nucleo: {
      core: true, url: base, status,
      historial: Array.isArray(hist) ? hist.length : 0,
      memorias: mems && Array.isArray(mems.recuerdos) ? mems.recuerdos.length : 0,
    },
  };
}

/**
 * Pinta el arnés dentro de `raiz`. Devuelve un resumen con las cuentas reales
 * (lo usa la sonda; no es decoración).
 */
export async function montaArnes(raiz, { ir, api, pantallas, puente } = {}) {
  if (!raiz) return null;
  const N = puente === undefined ? (window.CortNative || null) : puente;
  const base = intenta(() => (api ? api() : '') || '', '');
  const apps = Array.isArray(pantallas) ? pantallas.length : 0;
  const datos = datosDelArnés({
    N, historial: intenta(() => localStorage.getItem('cort-charla') || '[]', '[]'),
  });
  datos.apps = apps;

  const pinta = () => {
    raiz.innerHTML = vista(datos);
  };
  raiz.onclick = ev => {
    const frase = ev.target.closest('[data-frase]');
    if (frase) {
      ir?.('orbe');
      window.dispatchEvent(new CustomEvent('cort:orden', { detail: { texto: frase.dataset.frase } }));
      return;
    }
    if (ev.target.closest('[data-centro]')) ir?.('centro');
  };

  pinta();                              // primero lo del aparato, sin esperar al PC
  datos.mirando = true;
  const nube = await miraNucleo(base);
  Object.assign(datos, nube);
  pinta();                              // y después lo que contestó el núcleo

  return {
    mensajes: datos.sesion.length,
    historial: nube.nucleo.historial || 0,
    memorias: nube.nucleo.memorias || 0,
    nucleo: nube.nucleo.core === true,
    puente: datos.puente,
    capas: Object.keys(TOTALES.porCapa || {}).length,
    filas: raiz.querySelectorAll('.arn-caja').length,
  };
}
