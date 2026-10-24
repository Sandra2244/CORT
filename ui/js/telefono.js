/* ===== El Equipo: lo que CORT manda en el teléfono =====
 *
 * `docs/CONTRATO-PUENTE-2.1.md` es la LEY de los nombres. Aquí se traduce a algo
 * que la dueña pueda tocar con el dedo: seis bloques (Voz · Mando · Cerebro ·
 * Memoria · Atuendos · Agenda) dentro de la hoja `equipo` de `pantallas.js`.
 *
 * Tres reglas que gobiernan todo el fichero:
 *
 * · **Nada se ofrece si el puente no lo trae.** Cada llamada va por `llama()`
 *   (devuelve `null` si el método no existe en Java) y cada botón está detrás de
 *   `puede()`. Un APK viejo o sin permiso NO pinta un botón roto: pinta la frase
 *   honesta que viene en `dice`, que es lo que Java decide contar.
 *
 * · **En el PC no hay nada que mandar.** `montaTelefono()` no encuentra su hoja
 *   (no está en `visibles()` de `pantallas.js`) y sale con el objeto vacío: ni
 *   errores en consola ni llamadas raras. `telefonoPorVoz()` devuelve `false` y
 *   la frase sigue su camino de siempre por el núcleo.
 *
 * · **El estado vive aquí dentro.** Sin variables globales, sin `setInterval`
 *   preguntando: lo largo (red, cerebro, sincronizar) se resuelve en Java y
 *   vuelve como evento `{type:'mente'|'memoria'|'accion'}` que entra por
 *   `handleTelefonoEvento()`. Como el estado se guarda ANTES de pintar, un aviso
 *   que llega con la hoja cerrada no se pierde: sale cuando se abre.
 */

/* Las reglas «cuando X, entonces Y» (ronda 2.4). El motor es puro —sin `document`
   ni `localStorage` a pelo— y se prueba en el portátil con
   `node scripts/prueba-automatiza.mjs`; aquí sólo se le dan las manos (`ejecuta`),
   la consola y el DOM donde pintarse. */
import { creaMotor, marcapasos, necesitaReloj, DISPARADORES, ACCIONES, preajustes }
  from './automatiza.js';
/* El diccionario sale de `scripts/habilidades.py` + `scripts/saber.py`, la misma
   lista que vierte la tabla del APK y los casos de `Prueba5`. La ayuda de aquí no
   se escribe a mano: promete exactamente las intenciones que existen. */
import { AYUDA } from './diccionario.js';

const N = () => window.CortNative || null;const enTelefono = () => !!N();
const esc = s => String(s ?? '').replace(/[&<>"']/g,
  c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
// Para comparar por palabras: sin mayúsculas ni tildes, porque la dueña dice
// «mexicana», «Méxicana» o «la voz mexicana» y las tres son la misma idea.
const normaliza = s => String(s ?? '').toLowerCase()
  .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
  .replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim();

let ctx = null;              // { orb, term, say, api, ir } — se lo pasa `initPantallas`
let caja = null;             // el contenedor de los seis bloques
let montada = false;         // ¿está el DOM de la hoja montado?

/* Todo lo que la hoja sabe del aparato. Se pinta desde aquí y sólo desde aquí,
   para que el evento de Java y el golpe de dedo no puedan divergir. */
const estado = {
  voces: [], vozActual: '', velocidad: 1, tono: 1, faltanVoces: false, motor: '',
  nivel: null, max: null, linterna: false,
  mente: { proveedor: '', base: '', modelo: '', clavePuesta: false, conRed: false, motores: [] },
  ultimaMente: null,
  // Los cerebros de casa (Ollama en el PC, por Wi-Fi). `modelos` y `servidores` son
  // lo que vino de Java, sin retocar: la hoja se pinta sólo desde aquí.
  ollama: { servidor: '', origen: '', version: '', modelo: '', enCasa: false,
            modelos: [], servidorVisto: [], descargando: false, bajando: '',
            // F11 · el catálogo: con qué filtro está pintado y si está desplegado
            filtro: '', abierto: false },
  hechos: 0, conPortatil: false, direccion: '', recuerdos: [], quien: '', ultimaMemoria: null,
  atuendos: [], puesto: '', burbuja: false,
};
let preguntaVoz = false;     // la última pregunta/orden larga vino de la boca: hay que contestarla en voz

/* ─────────────────────────── el puente, con red ─────────────────────────── */

/* Igual que en `pantallas.js`: `typeof` antes de llamar. Un `TypeError` en el
   consola del WebView es un error técnico que la dueña no ve; lo que tiene que
   ver es una frase suya, en su pantalla.

   Desde la 2.5 la pregunta tiene dos mitades, y la segunda no se ve en el puente:
   el método `agenda` sigue existiendo en los dos perfiles del APK (el Kotlin se
   compila entero), pero en el `nucleo` el permiso `READ_CALENDAR` no está
   declarado en el manifiesto, así que el método existe y **no puede hacer nada** —
   y lo peor: `requestPermissions` de un permiso no declarado no abre cuadro,
   devuelve denegado en silencio. Por eso `puede()` consulta también
   `CORTcapaz()` (en `android-bridge.js`) para las cuatro puertas que el recorte
   cierra: con `nucleo` la cara pintará su frase de «este APK no puede», que ya
   estaba escrita y es la verdad. Sin puente (el PC) o con un APK anterior a la
   2.5, `CORTcapaz` devuelve `true` y nada de esto cambia. */
const PUERTAS = { agenda: 'agenda', contactos: 'llamadas', pedirContactos: 'llamadas' };
const puede = nombre => {
  const p = N();
  if (!p || typeof p[nombre] !== 'function') return false;
  const puerta = PUERTAS[nombre];
  return !puerta || (typeof window.CORTcapaz === 'function' ? window.CORTcapaz(puerta) : true);
};

const llama = (nombre, ...args) => {
  const p = N();
  if (!p || typeof p[nombre] !== 'function') return null;
  try { return p[nombre](...args); } catch (e) { ctx?.term?.('el puente dijo: ' + e, 'equipo'); return null; }
};

/* Java devuelve SIEMPRE una cadena JSON (`{"ok":true,…}` o `{"ok":false,"dice"}`).
   Aquí se convierte en objeto sin reventar con basura: un APK intermedio puede
   devolver un booleano, `null` o un texto a pelo, y ninguna de esas cosas debe
   tirar la hoja. Devuelve `null` si no hay nada que leer. */
function parsea(texto, c) {
  if (texto === null || typeof texto === 'undefined' || texto === '') return null;
  if (typeof texto === 'object') return texto;              // por si el puente ya da objeto
  if (typeof texto !== 'string') return texto;              // `true` / `false` / número
  try { return JSON.parse(texto); }
  catch { c?.term?.('el puente devolvió algo que no es JSON: ' + texto.slice(0, 60), 'equipo'); return null; }
}

/* La línea honesta de un bloque. Si `r` trae `dice`, se muestra LO QUE DIJO Java,
   no una paráfrasis nuestra: él sabe si falta un permiso y qué tocar en Ajustes. */
function avisa(donde, texto) {
  const l = el('eq-' + donde + '-dice');
  if (l) { l.textContent = String(texto || ''); l.classList.add('aviso'); }
}
function diceBien(donde, texto) {
  const l = el('eq-' + donde + '-dice');
  if (l) { l.textContent = String(texto || ''); l.classList.remove('aviso'); }
}
function linea(donde, texto) {
  const l = el('eq-' + donde + '-est');
  if (l) l.textContent = String(texto || '');
}
const el = id => (caja ? caja.querySelector('#' + id) : document.getElementById(id));

/* Una orden con su JSON dentro y su castigo si no existe. Devuelve el objeto con
   `ok:true` o `null` (ya habrá quedado la frase en el bloque). */
function envia(metodo, cuerpo, donde, sinPuente) {
  if (!puede(metodo)) { avisa(donde, sinPuente); ctx?.term?.(metodo + '() no está en este APK', 'equipo'); return null; }
  const crudo = llama(metodo, JSON.stringify(cuerpo));
  if (crudo === null) { avisa(donde, sinPuente); return null; }
  const r = parsea(crudo, ctx);
  if (r === null) { avisa(donde, 'El puente respondió algo que no sé leer; vuelve a intentarlo en un momento.'); return null; }
  if (r === false) { avisa(donde, 'El teléfono no hizo esa cosa.'); return null; }
  if (typeof r === 'object' && r.ok === false) { avisa(donde, r.dice || 'el teléfono no dejó hacerlo.'); return null; }
  return r;
}

/* Hablar y, de paso, dejar escrito en el bloque lo que se dijo. Desde la 2.4 se
   escribe TAMBIÉN en la consola: la dueña amplió la terminal del teléfono para
   escribir órdenes a mano, y una orden que sólo habla no deja rastro — parece que
   no hizo nada. */
function di(texto, donde) {
  if (donde) avisa(donde, texto);
  salida(texto);
  ctx?.say?.(texto);
  return true;
}

/* El sitio donde se lee lo que CORT acaba de decir. Dos, en el teléfono: la consola
   del orbe (`ctx.term`) y, si la dueña está en la pantalla **Código**, su terminal
   (`espejo`, que pone `terminalTelefono`). Un `try` alrededor porque el espejo es
   DOM ajeno: si la pantalla se desmontó entre la orden y la respuesta, la orden no
   se cae por un `null`. */
let espejo = null;
function salida(texto, clase) {
  ctx?.term?.(texto, 'equipo');
  if (espejo) { try { espejo(String(texto || ''), clase || 'cort'); } catch { /* pantalla cerrada */ } }
}

/* La terminal de la pantalla Código, ampliada para el teléfono (ronda 2.4): la
   misma boca que la voz, pero escribiendo. Devuelve `true` si la línea se atendió
   AQUÍ (puente del teléfono) y `false` si `pantallas.js` debe seguir intentando con
   el núcleo del PC. No inventa: si el puente no está, lo dice. */
export function terminalTelefono(orden, escribe) {
  if (!enTelefono()) return false;
  espejo = typeof escribe === 'function' ? escribe : null;
  const b = normaliza(orden);
  if (!b) return false;
  if (/^(ayuda|help|comandos|listado|que puedes hacer)\b/.test(b)) {
    CMD_TELEFONO.forEach(l => (escribe || salida)(l, 'aviso'));
    return true;
  }
  if (/^(olvida|cierra|limpia) (la )?terminal/.test(b)) {
    const caja = document.getElementById('cod-out');
    if (caja) caja.innerHTML = '';
    espejo = null;
    return true;
  }
  // `estado del telefono` / `sensores`: lo que mide el aparato, a pelo en la consola.
  if (/^(estado|que tal estas|como estas)\b/.test(b) && puede('aparato')) {
    const a = parsea(llama('aparato'), ctx);
    if (a) { Object.keys(a).forEach(k => (escribe || salida)(k + ': ' + fmt(a[k]), 'cort')); return true; }
  }
  return telefonoPorVoz(orden);
}
const fmt = v => (v && typeof v === 'object' ? JSON.stringify(v) : String(v));

/* Lo que `ayuda` enumera en la terminal del teléfono: las órdenes que se atienden
   AQUÍ, sin portátil. Se mantiene a mano, y `prueba-costura.py` comprueba que lo
   que se promete existe (una ayuda mentirosa es peor que ninguna). */
const CMD_TELEFONO = [
  '— órdenes que se atienden en el teléfono, sin PC:',
  '  sube el volumen · baja el volumen · callar · volumen max · volumen min',
  '  linterna · prende la linterna · apaga la linterna',
  '  pon una alarma a las 7:30 · temporizador de 10 minutos',
  '  abre whatsapp · busca en la red <algo> · busca la app <algo>',
  '  acuérdate de <algo> · ¿qué sabes de mí? · sincroniza con el pc',
  '  voz de siri · cambia la voz · ponte azul · atuendo Cortana · burbuja',
  '  piensa <pregunta>              (el cerebro del teléfono: casa o nube)',
  '  busca cerebros                  (barre tu Wi-Fi buscando Ollama)',
  '  modelos                         (qué modelos hay en tu PC)',
  '  usa el modelo qwen2.5:1.5b      (piensa con ése a partir de ahora)',
  '  descarga el modelo qwen2.5:0.5b (lo baja el PC; la barra se mueve aquí)',
  '  borra el modelo llama3',
  '  mis automatizaciones              (las reglas «cuando X, entonces Y»)',
  '  automatiza cuando diga modo noche haz callar la música',
  '  ¿qué tengo hoy? · revisa el correo · apunta cena con Samuel a las 9',
  '  estado                          (qué mide el teléfono ahora)',
  '  cronómetro · qué apps tengo      (el reloj y la rejilla de apps)',
  /* F14 · las cifras y los ejemplos salen del diccionario generado. Si una frase
     deja de existir, desaparece de la ayuda sola; no puede quedarse prometida. */
  ...AYUDA,
  '  ayuda · olvida la terminal',
];

/* ─────────────────────────── la carcasa de la hoja ─────────────────────────── */

const APPS = {
  'whatsapp business': 'whatsapp-business', whatsapp: 'whatsapp', watts: 'whatsapp',
  youtube: 'youtube', maps: 'maps', mapas: 'maps', spotify: 'spotify',
  gmail: 'gmail', correo: 'gmail', calendario: 'calendario', agenda: 'calendario',
  instagram: 'instagram', facebook: 'facebook', tiktok: 'tiktok',
  navegador: 'navegador', chrome: 'navegador', archivos: 'archivos',
  explorador: 'archivos', ajustes: 'ajustes', configuracion: 'ajustes', telefono: 'telefono',
};
const NOMBRES_APP = {
  whatsapp: 'WhatsApp', 'whatsapp-business': 'WhatsApp Business', youtube: 'YouTube', maps: 'Maps',
  spotify: 'Spotify', gmail: 'Gmail', calendario: 'Calendario', navegador: 'Navegador',
  archivos: 'Archivos', ajustes: 'Ajustes',
};
const PREAJUSTES = [
  ['siri', 'Siri'], ['alexa', 'Alexa'], ['cortana', 'Cortana'],
  ['española', 'Española'], ['mexicana', 'Mexicana'], ['neutra', 'Neutra'],
];
const PROVEEDORES = ['groq', 'openai', 'deepseek', 'mistral', 'qwen', 'ollama', 'anthropic'];

/* Un bloque = `<details>` con su título. Se abre por defecto: la consigna es que
   los seis sean **visibles y usables**, no un menú dentro de otro menú. */
function bloque(id, numero, titulo, sub, interior) {
  const d = document.createElement('details');
  d.className = 'eq-bloque'; d.id = 'eqb-' + id; d.open = true;
  const s = document.createElement('summary');
  s.innerHTML = `<b>${numero} · ${esc(titulo)}</b><span>${esc(sub)}</span>`;
  const c = document.createElement('div');
  c.className = 'eq-cuerpo';
  c.innerHTML = interior;
  d.appendChild(s); d.appendChild(c);
  return d;
}

/* ── las seis hojas de contenido ── */
const CARA_VOZ = `
  <div class="eq-estado" id="eq-voz-est">leyendo las voces del teléfono…</div>
  <div class="eq-tit">estilos que CORT imita</div>
  <div class="eq-fila" id="eq-voz-pre"></div>
  <div class="eq-tit">voces instaladas en tu teléfono</div>
  <div class="eq-nube" id="eq-voz-lista"></div>
  <div class="eq-doble">
    <label class="eq-slider">velocidad
      <input id="eq-voz-vel" type="range" min="0.5" max="2" step="0.05" value="1">
      <b id="eq-voz-vel-v">1.00</b></label>
    <label class="eq-slider">tono
      <input id="eq-voz-tono" type="range" min="0.5" max="2" step="0.05" value="1">
      <b id="eq-voz-tono-v">1.00</b></label>
  </div>
  <input id="eq-voz-texto" class="eq-lleno" placeholder="la frase de muestra"
    value="A sus órdenes. Soy CORT, tu asistente en el teléfono.">
  <div class="eq-fila">
    <button class="eq-b" id="eq-voz-prueba">▶ probar</button>
    <button class="eq-b" id="eq-voz-descarga">↻ descargar voces</button>
    <button class="eq-b" id="eq-voz-refresca">↺ volver a leer</button>
  </div>
  <div class="eq-dice" id="eq-voz-dice"></div>`;

const CARA_MANDO = `
  <div class="eq-estado" id="eq-mando-est">mirando qué hace tu teléfono…</div>
  <div class="eq-tit">volumen del aparato</div>
  <div class="eq-fila">
    <button class="eq-b eq-grande" data-vol="baja">−</button>
    <button class="eq-b eq-grande" data-vol="sube">+</button>
    <button class="eq-b" data-vol="min">mín</button>
    <button class="eq-b" data-vol="max">máx</button>
    <button class="eq-b" data-vol="callar">callar</button>
    <span class="eq-nivel" id="eq-mando-nivel"></span>
  </div>
  <div class="eq-fila"><button class="eq-b eq-grande" id="eq-linterna">🔦 linterna</button></div>
  <div class="eq-tit">despertar y contar</div>
  <div class="eq-fila">
    <input id="eq-alarma-hora" type="time" value="07:30">
    <input id="eq-alarma-cancion" placeholder="con qué canción">
    <input id="eq-alarma-nota" placeholder="de qué te aviso">
    <button class="eq-b" id="eq-alarma-pon">alarma</button>
  </div>
  <div class="eq-fila">
    <label class="eq-nota" for="eq-alarma-rutina">
      <input id="eq-alarma-rutina" type="checkbox"> rutina de la mañana</label>
    <button class="eq-b" id="eq-alarma-quita">quitar alarma</button>
  </div>
  <div class="eq-fila">
    <input id="eq-temp-min" type="number" min="0" max="600" step="1" value="10">
    <span class="eq-nota">minutos</span>
    <button class="eq-b" id="eq-temp-pon">temporizador</button>
  </div>
  <div class="eq-tit">tus apps</div>
  <div class="eq-rejilla" id="eq-apps"></div>
  <div class="eq-fila">
    <input id="eq-app-busca" placeholder="el nombre de una app…">
    <button class="eq-b" id="eq-app-ir">buscar app</button>
    <button class="eq-b" id="eq-app-todas">mis apps</button>
    <button class="eq-b" id="eq-red-ir">en la red</button>
  </div>
  <div class="eq-nube" id="eq-app-lista"></div>
  <div class="eq-dice" id="eq-mando-dice"></div>`;

const CARA_CEREBRO = `
  <div class="eq-estado" id="eq-men-est">preguntando al cerebro del teléfono…</div>
  <div class="eq-tit">con quién piensa CORT</div>
  <div class="eq-fila">
    <select id="eq-men-prov"></select>
    <input id="eq-men-modelo" placeholder="modelo" autocomplete="off" spellcheck="false">
  </div>
  <input id="eq-men-base" class="eq-lleno" placeholder="https://… (base del proveedor)"
    autocomplete="off" spellcheck="false">
  <input id="eq-men-clave" class="eq-lleno" type="password" placeholder="pegar clave aquí"
    autocomplete="off" spellcheck="false">
  <div class="eq-fila">
    <button class="eq-b" id="eq-men-guarda">guardar</button>
    <button class="eq-b" id="eq-men-prueba">probar</button>
    <span class="eq-nota" id="eq-men-clave-est"></span>
  </div>
  <div class="eq-tit">los cerebros gordos de tu casa (Ollama por Wi-Fi)</div>
  <div class="eq-estado" id="eq-oll-est">sin mirar la red todavía</div>
  <div class="eq-fila">
    <input id="eq-oll-serv" placeholder="http://192.168.1.20:11434"
      autocomplete="off" spellcheck="false">
    <button class="eq-b" id="eq-oll-fija">fijar</button>
  </div>
  <div class="eq-fila">
    <button class="eq-b" id="eq-oll-busca">🔍 buscar en tu Wi-Fi</button>
    <button class="eq-b" id="eq-oll-mis">↻ mis modelos</button>
  </div>
  <div class="eq-nube" id="eq-oll-lista"></div>
  <div class="eq-barra"><i id="eq-oll-barra"></i></div>
  <div class="eq-fila">
    <input id="eq-oll-nuevo" placeholder="bajar uno nuevo: qwen2.5:0.5b"
      autocomplete="off" spellcheck="false">
    <button class="eq-b" id="eq-oll-baja">↓ descargar</button>
    <button class="eq-b" id="eq-oll-cancela" hidden>✕ cancelar</button>
  </div>
  <div class="eq-tit">catálogo de modelos <small id="eq-cat-cuenta"></small></div>
  <div class="eq-fila">
    <input id="eq-cat-busca" placeholder="busca en el catálogo: qwen, 3b, código…"
      autocomplete="off" spellcheck="false">
    <button class="eq-b" id="eq-cat-abre">ver catálogo</button>
  </div>
  <div class="eq-fila" id="eq-cat-chips"></div>
  <div class="eq-nube" id="eq-cat-lista"></div>
  <div class="eq-nota">Ollama vive en tu PC, no dentro del teléfono: el APK no puede
    llevarse el servidor (es un programa de ordenador). Lo que hace CORT es hablar con
    él por Wi-Fi. Para que conteste hay que arrancarlo con <b>OLLAMA_HOST=0.0.0.0:11434</b>
    y tener los dos aparatos en la misma red.</div>
  <div class="eq-dice" id="eq-oll-dice"></div>
  <div class="eq-tit">preguntar sin el portátil delante</div>
  <div class="eq-fila">
    <input id="eq-men-pregunta" placeholder="piensa lo que sea…">
    <button class="eq-b" id="eq-men-ir">▲</button>
  </div>
  <div class="eq-res" id="eq-men-res"></div>
  <div class="eq-dice" id="eq-men-dice"></div>`;

const CARA_MEMORIA = `
  <div class="eq-estado" id="eq-mem-est">contando lo que recuerda el teléfono…</div>
  <div class="eq-fila">
    <input id="eq-mem-texto" placeholder="acuédate de…">
    <button class="eq-b" id="eq-mem-guarda">apuntar</button>
  </div>
  <div class="eq-fila">
    <button class="eq-b" id="eq-mem-quien">¿qué sabes de mí?</button>
    <button class="eq-b" id="eq-mem-sync">↺ sincronizar con el portátil</button>
    <button class="eq-b" id="eq-mem-refresca">↺ la lista</button>
  </div>
  <div class="eq-nube" id="eq-mem-lista"></div>
  <div class="eq-dice" id="eq-mem-dice"></div>`;

const CARA_ATUENDO = `
  <div class="eq-estado" id="eq-atu-est">mirando qué trajes hay…</div>
  <div class="eq-paletas" id="eq-atu-lista"></div>
  <div class="eq-fila">
    <button class="eq-b" id="eq-burb">● burbuja flotante</button>
    <span class="eq-nota" id="eq-burb-est">apagada</span>
  </div>
  <div class="eq-dice" id="eq-atu-dice"></div>`;

const CARA_AGENDA = `
  <div class="eq-estado" id="eq-ago-est">mirando tu calendario…</div>
  <div class="eq-fila">
    <button class="eq-b" id="eq-ago-hoy">hoy</button>
    <button class="eq-b" id="eq-ago-3">próximos 3</button>
    <button class="eq-b" id="eq-ago-7">próximos 7</button>
    <button class="eq-b" id="eq-ago-abrir">abrir calendario</button>
  </div>
  <div class="eq-nube" id="eq-ago-lista"></div>
  <div class="eq-tit">apuntar algo nuevo</div>
  <div class="eq-fila">
    <input id="eq-ago-titulo" placeholder="qué: cena con Samuel">
    <input id="eq-ago-hora" type="time" value="21:00">
    <button class="eq-b" id="eq-ago-pon">▲ apuntar</button>
  </div>
  <div class="eq-tit">el correo</div>
  <div class="eq-fila">
    <button class="eq-b" id="eq-ago-correo">✉ lo que llegó al correo</button>
    <span class="eq-nota" id="eq-ago-gmail"></span>
  </div>
  <div class="eq-dice" id="eq-ago-dice"></div>`;

/* ─────────────── 7 · OÍDO: el reconocimiento que vive dentro del APK ───────────────
   `Oido.kt` (Kotlin + Vosk) oye español sin internet y sin los servicios de voz de
   Google. No es un extra: es la respuesta a dos cosas que la dueña dijo —«no me
   entiende cuando estoy sin datos» y «en el juego se traba»—. La cara no pinta aquí
   una ilusión: cada fase la manda Java por el evento `motor` (`extrayendo`,
   `cargando`, `listo`, `sin-sitio`, `sin-modelo`, `roto`, `cerrado`) con su `motivo`
   en español, y el botón apaga o enciende el oído de verdad
   (`CortNative.oidoPropio`). Si el oído propio está apagado o aún no está listo,
   CORT sigue escuchando con el reconocedor de siempre: esta hoja lo dice, no lo
   esconde. */
const CARA_OIDOS = `
  <div class="eq-estado" id="eq-oido-est">preguntando al oído del teléfono…</div>
  <div class="eq-fila">
    <button class="eq-b eq-grande" id="eq-oido-btn">escucha sin internet: comprobando…</button>
  </div>
  <div class="eq-fila">
    <span class="eq-nota" id="eq-oido-motor"></span>
    <span class="eq-nota" id="eq-oido-sitio"></span>
  </div>
  <div class="eq-dice" id="eq-oido-dice"></div>
  <div class="eq-nota">el modelo de español ocupa 60 MB en tu teléfono y tarda unos
    segundos la primera vez; CORT te lo dice aquí mientras se copia.</div>`;

/* ── 8 · Automatiza: «cuando X, entonces Y» ──
   Lo de JARVIS: una condición y unas cosas que hacer, apuntadas por ella. Se ofrece
   aquí porque las manos ya están (volumen, linterna, apps, música, el cerebro, la
   memoria) y lo que faltaba era el sitio donde se juntan. La limitación va escrita
   en la propia hoja: las reglas se evalúan mientras CORT está vivo en pantalla. */
const CARA_AUTOS = `
  <div class="eq-estado" id="eq-aut-est">sin reglas todavía</div>
  <div class="eq-nube" id="eq-aut-lista"></div>
  <div class="eq-tit">crear una regla</div>
  <input id="eq-aut-nombre" class="eq-lleno" placeholder="cómo la llamas: modo noche">
  <div class="eq-fila">
    <select id="eq-aut-disp"></select>
  </div>
  <div class="eq-fila">
    <input id="eq-aut-de" placeholder="de quién (whatsapp, gmail…)" style="display:none">
    <select id="eq-aut-op" style="display:none"></select>
    <input id="eq-aut-texto" placeholder="la frase que tú dices">
  </div>
  <div class="eq-fila">
    <select id="eq-aut-acc"></select>
    <select id="eq-aut-opa" style="display:none"></select>
    <input id="eq-aut-arg" placeholder="el texto o el dato">
  </div>
  <div class="eq-fila">
    <button class="eq-b eq-grande" id="eq-aut-nueva">＋ apuntar la regla</button>
    <button class="eq-b" id="eq-aut-planta">las tres de muestra</button>
    <button class="eq-b" id="eq-aut-borra">borrar todas</button>
  </div>
  <div class="eq-dice" id="eq-aut-dice"></div>
  <div class="eq-nota">las reglas se cumplen <b>mientras CORT está abierto en pantalla</b>:
    la cara es una página y una página cerrada no escucha. Lo que sí funciona con la
    pantalla apagada es lo que hace Java solo (leer tus avisos en voz alta, la música,
    el oído del auricular). Ella lo dice en el contrato, no aquí de adorno.</div>`;

/* ─────────────────────────── montaje y pintura ─────────────────────────── */

export function montaTelefono(contexto) {
  ctx = contexto || ctx;
  const cuerpo = document.querySelector('#scr-equipo .scr-cuerpo');
  // En el PC esta hoja no se monta (no está en `visibles()`): se sale en silencio,
  // sin errores y sin llamadas al puente que no existe.
  if (!cuerpo) return { pinta: () => {}, abre: () => {}, viva: () => false };

  caja = document.createElement('div');
  caja.className = 'scr-lista eq-caja';
  caja.innerHTML = '<div class="eq-piego">lo que CORT puede hacer en tu teléfono '
    + 'sin tu portátil delante. Cada bloque dice en su propio sitio lo que este APK '
    + 'no dejó hacer: no hay botones que parezcan romper.</div>';
  caja.appendChild(bloque('voz', '1', 'Voz', 'la que sale por el altavoz', CARA_VOZ));
  caja.appendChild(bloque('mando', '2', 'Mando', 'volumen, linterna, alarmas y apps', CARA_MANDO));
  caja.appendChild(bloque('men', '3', 'Cerebro', 'quién piensa cuando no está el PC', CARA_CEREBRO));
  caja.appendChild(bloque('mem', '4', 'Memoria', 'lo que el teléfono recuerda', CARA_MEMORIA));
  caja.appendChild(bloque('atu', '5', 'Atuendos', 'los colores de CORT y su burbuja', CARA_ATUENDO));
  caja.appendChild(bloque('ago', '6', 'Agenda', 'tus citas y lo que llegó al correo', CARA_AGENDA));
  caja.appendChild(bloque('oido', '7', 'Oído', 'escuchar sin internet ni Google', CARA_OIDOS));
  caja.appendChild(bloque('autos', '8', 'Automatiza', 'cuando X, entonces Y', CARA_AUTOS));
  cuerpo.appendChild(caja);

  enganchaVoz();
  enganchaMando();
  enganchaCerebro();
  enganchaMemoria();
  enganchaAtuendo();
  enganchaAgenda();
  enganchaOido();
  enganchaAutos();

  montada = true;
  pinta();
  return { pinta, abre, viva: () => montada };
}

/* Todo lo que la pantalla puede preguntar al puente de golpe. Se llama al montar
   y cada vez que `pantallas.js` entra en `equipo` (igual que `arrancaMusica()`). */
function pinta() {
  if (!montada) return;
  pintaVoz(); pintaMando(); pintaCerebro(); pintaMemoria(); pintaAtuendo(); pintaOido();
  pintaAutos();
  const estadoBar = document.querySelector('#scr-equipo .scr-estado');
  if (estadoBar) {
    const cosas = [puede('accion') && 'mando', puede('ajusteVoz') && 'voz',
      puede('mente') && 'cerebro', puede('memoria') && 'memoria', puede('atuendo') && 'trajes',
      puede('oidoEstado') && 'oído propio', autos.total() && 'automatiza']
      .filter(Boolean);
    /* El perfil va al principio porque es la respuesta a «¿cuál de los dos APK de
       la Release tengo instalado?». `CORTperfil()` (en `android-bridge.js`) lee el
       `<meta-data>` del manifiesto **del archivo instalado**; en el PC sin puente
       dice `escritorio`, y en un APK anterior a la 2.5, `completo` — que es lo que
       era. Con `nucleo` hay cuatro puertas cerradas (asistente, avisos, marcar por
       nombre, baldosín) y la dueña tiene que poder verlo sin probar los botones. */
    const perfil = window.CORTperfil ? window.CORTperfil() : 'escritorio';
    estadoBar.textContent = 'envase ' + perfil + ' · '
      + (cosas.length ? 'puente 2.1 · ' + cosas.join(' · ') : 'puente viejo');
    estadoBar.classList.toggle('aviso', !cosas.length || perfil === 'nucleo');
  }
}

/* Llevar la vista de la dueña al bloque que acaba de contestar (por voz, p.ej.). */
function abre(id) {
  if (!montada) return;
  // Si estaba en el orbe (o en cualquier hoja sin video), la hoja del Equipo se
  // trae delante: «voz de siri» o «ponte azul» contestan enseñando el panel. Con
  // el MV, la música, la charla o el código abiertos NO se les roba la pantalla —
  // la dueña está mirando otra cosa y eso no se interrumpe a gritos.
  const raiz = document.documentElement;
  const clases = String((raiz && (raiz.className || '')) || '');
  if (typeof ctx?.ir === 'function' && !/\bp-equipo\b/.test(clases)
      && !/(?:^|\s)p-(?:mv|musica|charla|codigo)(?:\s|$)/.test(clases)) {
    ctx.ir('equipo');
  }
  const d = caja.querySelector('#eqb-' + id);
  if (!d) return;
  d.open = true;
  // El desplazamiento se calcula a mano (dentro de la propia hoja, sin
  // `scrollIntoView`, que movería la página entera). Si el aparato no da medidas,
  // el brillo del bloque avisa igual de dónde está la respuesta: nada de esto debe
  // tirar la hoja.
  try {
    const r = d.getBoundingClientRect(), c = caja.getBoundingClientRect();
    caja.scrollTop = Math.max(0, caja.scrollTop + (r.top - c.top) - 8);
  } catch { /* sin medidas: no pasa nada */ }
  d.classList.add('eq-brillo');
  setTimeout(() => d.classList.remove('eq-brillo'), 1400);
}

/* ── 1 · Voz ── */
function enganchaVoz() {
  const pre = el('eq-voz-pre');
  pre.innerHTML = PREAJUSTES.map(([k, n]) =>
    `<button class="eq-chip" data-pre="${esc(k)}">${esc(n)}</button>`).join('');
  pre.querySelectorAll('[data-pre]').forEach(b => b.onclick = () => preajuste(b.dataset.pre));
  el('eq-voz-vel').onchange = () => ponVoz(estado.vozActual);
  el('eq-voz-tono').onchange = () => ponVoz(estado.vozActual);
  ['eq-voz-vel', 'eq-voz-tono'].forEach(id => {
    const i = el(id);
    i.oninput = () => { const v = el(id + '-v'); if (v) v.textContent = (+i.value).toFixed(2); };
  });
  el('eq-voz-prueba').onclick = () => pruebaVoz();
  el('eq-voz-descarga').onclick = () => {
    const r = envia('ajusteVoz', { que: 'descargar' }, 'voz',
      'Lo de descargar las voces lo trae el APK nuevo de la Release: con este cuerpo no puedo abrir el instalador de voces de Android.');
    if (r) diceBien('voz', r.abre === 'ajustes'
      ? 'Ahí tienes Android: entra en Idiomas y voz ▸ Voz de Google ▸ Configurar voces y baja las que quieras.'
      : 'Pidiendo las voces al instalador de Android.');
  };
  el('eq-voz-refresca').onclick = () => pintaVoz();
}

function pintaVoz() {
  if (!montada) return;
  if (!puede('ajusteVoz')) {
    linea('voz', 'sin puente de voces');
    el('eq-voz-lista').innerHTML = '<span class="eq-nota">este APK todavía no me deja mirar '
      + 'tus voces: instala el APK nuevo de la Release y aquí sale la lista.</span>';
    return;
  }
  const r = envia('ajusteVoz', { que: 'lista' }, 'voz',
    'este APK no sabe mirar las voces.');
  if (!r) { linea('voz', 'voces: sin respuesta'); return; }
  estado.voces = Array.isArray(r.voces) ? r.voces : [];
  estado.vozActual = r.vozActual || '';
  estado.velocidad = typeof r.velocidad === 'number' ? r.velocidad : estado.velocidad;
  estado.tono = typeof r.tono === 'number' ? r.tono : estado.tono;
  estado.faltanVoces = !!r.faltanVoces;
  const lista = el('eq-voz-lista');
  lista.innerHTML = estado.voces.length
    ? estado.voces.map(v => `<button class="eq-chip${v.nombre === estado.vozActual ? ' puesta' : ''}" `
        + `data-v="${esc(v.nombre)}">${esc(v.nombre)}<small>`
        + `${esc(v.idioma || '')}${v.porDefecto ? ' · por defecto' : ''}</small></button>`).join('')
    : '<span class="eq-nota">no veo ninguna voz instalada. Pulsa «↻ descargar voces» y baja '
      + 'las de español en Android.</span>';
  lista.querySelectorAll('[data-v]').forEach(b => b.onclick = () => ponVoz(b.dataset.v));
  const vel = el('eq-voz-vel'), ton = el('eq-voz-tono');
  vel.value = estado.velocidad; ton.value = estado.tono;
  el('eq-voz-vel-v').textContent = (+estado.velocidad).toFixed(2);
  el('eq-voz-tono-v').textContent = (+estado.tono).toFixed(2);
  linea('voz', estado.voces.length + ' voces · ' + (estado.vozActual || 'sin voz elegida')
    + (estado.faltanVoces ? ' · faltan voces por descargar' : ''));
  const est = envia('ajusteVoz', { que: 'estado' }, 'voz', '');
  if (est) { estado.motor = est.motor || ''; linea('voz', lineaTexto(est)); }
}
const lineaTexto = est => (est.listo ? 'motor listo' : 'el motor de voz aún no está listo')
  + (est.motor ? ' · ' + est.motor : '') + (est.idioma ? ' · ' + est.idioma : '');

function ponVoz(nombre, alVoz) {
  if (!puede('ajusteVoz')) return di('Lo de cambiar de voz lo trae el APK nuevo de la Release; con este cuerpo no puedo tocar el motor de voz.', 'voz');
  const cuerpo = { que: 'poner', velocidad: +(el('eq-voz-vel')?.value || estado.velocidad),
    tono: +(el('eq-voz-tono')?.value || estado.tono) };
  if (nombre) cuerpo.nombre = nombre;
  const r = envia('ajusteVoz', cuerpo, 'voz', 'este APK no puede cambiar de voz.');
  if (!r) return false;
  if (nombre) estado.vozActual = nombre;
  diceBien('voz', (nombre ? 'Ya hablo con ' + nombre : 'Anotada la velocidad y el tono')
    + ' · velocidad ' + cuerpo.velocidad.toFixed(2) + ', tono ' + cuerpo.tono.toFixed(2) + '.');
  ctx?.orb?.burst?.();
  if (alVoz) ctx?.say?.('Listo, así sueno.');
  pintaVoz();
  return true;
}

function preajuste(nombre, alVoz) {
  if (!puede('ajusteVoz')) return di('Lo de los estilos de voz lo trae el APK nuevo: con este cuerpo no puedo imitar a nadie.', 'voz');
  const r = envia('ajusteVoz', { que: 'predefinida', nombre }, 'voz', 'este APK no tiene estilos de voz.');
  if (!r) return false;
  if (r.usada) estado.vozActual = r.usada;
  const dicho = 'Voz de estilo ' + nombre + ': ' + (r.usada || 'la que había')
    + (r.porQue ? ' — ' + r.porQue : '');
  diceBien('voz', dicho);
  if (alVoz) ctx?.say?.('Puesta: ' + (r.usada || nombre) + '. ' + (r.porQue || ''));
  pintaVoz();
  return true;
}

function pruebaVoz(alVoz) {
  if (!puede('ajusteVoz')) return di('Probar la voz lo trae el APK nuevo de la Release.', 'voz');
  const texto = (el('eq-voz-texto')?.value || 'A sus órdenes.').trim();
  const r = envia('ajusteVoz', { que: 'probar', texto }, 'voz', 'este APK no puede probar la voz.');
  if (!r) return false;
  diceBien('voz', 'Diciendo la muestra por el altavoz.');
  ctx?.term?.('muestra de voz: ' + texto.slice(0, 40), 'equipo');
  if (alVoz) ctx?.say?.('Ahí la tienes.');
  return true;
}

/* ── 2 · Mando ── */
function enganchaMando() {
  el('eq-apps').innerHTML = Object.keys(NOMBRES_APP).map(k =>
    `<button class="eq-app" data-app="${esc(k)}">${esc(NOMBRES_APP[k])}</button>`).join('');
  el('eq-apps').querySelectorAll('[data-app]').forEach(b =>
    b.onclick = () => accionAbrir(b.dataset.app, false));
  caja.querySelectorAll('#eqb-mando [data-vol]').forEach(b =>
    b.onclick = () => accionVolumen(b.dataset.vol, false));
  el('eq-linterna').onclick = () => accionLinterna('alterna', false);
  el('eq-alarma-pon').onclick = () => {
    const hora = (el('eq-alarma-hora')?.value || '').trim();
    if (!/^\d{1,2}:\d{2}$/.test(hora)) return avisa('mando', 'Dime la hora del despertar: 7:30, 06:15…');
    accionAlarma(hora, (el('eq-alarma-nota')?.value || '').trim(), false,
                 (el('eq-alarma-cancion')?.value || '').trim(),
                 !!el('eq-alarma-rutina')?.checked);
  };
  el('eq-alarma-quita').onclick = () => accionAlarmaQuita(false);
  el('eq-temp-pon').onclick = () => {
    const min = +(el('eq-temp-min')?.value || 0);
    if (!min) return avisa('mando', 'Pon primero cuántos minutos quieres contar.');
    accionTemporizador(min * 60, false);
  };
  el('eq-app-ir').onclick = () => buscaApp(el('eq-app-busca')?.value || '', false);
  el('eq-app-todas').onclick = () => misApps();
  el('eq-red-ir').onclick = () => buscaEnRed(el('eq-app-busca')?.value || '', false);
  const entrada = el('eq-app-busca');
  entrada.addEventListener('keydown', e => { if (e.key === 'Enter') buscaApp(entrada.value, false); });
}

function pintaMando() {
  if (!montada) return;
  if (!puede('accion')) {
    linea('mando', 'sin puente de mando');
    avisa('mando', 'Este APK todavía no obedece al teléfono: instala el APK nuevo de la Release '
      + 'y aquí salen el volumen, la linterna, las alarmas y tus apps.');
    return;
  }
  const r = envia('accion', { que: 'estado' }, 'mando', 'este APK no me cuenta su estado.');
  if (!r) { linea('mando', 'mando: sin respuesta'); return; }
  estado.nivel = typeof r.volumen === 'number' ? r.volumen : estado.nivel;
  estado.max = typeof r.max === 'number' ? r.max : estado.max;
  estado.linterna = !!r.linterna;
  pintaNivel();
  const lin = el('eq-linterna');
  lin.classList.toggle('puesta', estado.linterna);
  lin.textContent = '🔦 linterna ' + (estado.linterna ? 'encendida' : 'apagada');
  const av = puede('alarmaEstado') ? parsea(llama('alarmaEstado'), ctx) : null;
  const alarma = av?.puesta ? ' · alarma ' + (av.alarma || '') + ' (' + (av.en || '') + ')' : '';
  linea('mando', 'volumen ' + (estado.nivel ?? '—') + '/' + (estado.max ?? '—')
    + ' · linterna ' + (estado.linterna ? 'encendida' : 'apagada')
    + alarma
    + (r.sinMiedo ? ' · en modo juego' : ''));
}

function pintaNivel() {
  const n = el('eq-mando-nivel');
  if (!n) return;
  const pct = (estado.nivel != null && estado.max) ? Math.round(estado.nivel / estado.max * 100) : null;
  n.textContent = pct === null ? '' : pct + '%';
  n.style.setProperty('--eq-pct', (pct ?? 0) + '%');
}

const sinMando = 'Mandar sobre el teléfono (volumen, linterna, alarmas, apps) lo trae el APK nuevo de la Release; con este cuerpo no puedo tocar el aparato.';

function accionVolumen(como, alVoz) {
  if (!puede('accion')) return di(sinMando, 'mando');
  const r = envia('accion', { que: 'volumen', como }, 'mando', sinMando);
  if (!r) return false;
  if (typeof r.nivel === 'number') { estado.nivel = r.nivel; pintaNivel(); }
  const palabras = { sube: 'Subo el volumen.', baja: 'Lo bajo.', max: 'Volumen al máximo.',
    min: 'Volumen al mínimo.', callar: 'Callado el aparato.' };
  diceBien('mando', (palabras[como] || 'Volumen ajustado.')
    + (typeof r.nivel === 'number' ? ' Ahora en ' + r.nivel + (estado.max ? ' de ' + estado.max : '') + '.' : ''));
  if (alVoz) ctx?.say?.(palabras[como] || 'Volumen.');
  ctx?.orb?.burst?.();
  return true;
}

function accionLinterna(como, alVoz) {
  if (!puede('accion')) return di(sinMando, 'mando');
  const r = envia('accion', { que: 'linterna', como }, 'mando', sinMando);
  if (!r) return false;
  if (typeof r.linterna === 'boolean') estado.linterna = r.linterna;
  const lin = el('eq-linterna');
  if (lin) { lin.classList.toggle('puesta', estado.linterna);
    lin.textContent = '🔦 linterna ' + (estado.linterna ? 'encendida' : 'apagada'); }
  diceBien('mando', estado.linterna ? 'Linterna encendida.' : 'Linterna apagada.');
  if (alVoz) ctx?.say?.(estado.linterna ? 'Linterna encendida.' : 'Linterna apagada.');
  return true;
}

function accionAlarma(hora, nota, alVoz, cancion, rutina) {
  if (!puede('accion')) return di(sinMando, 'mando');
  const r = envia('accion', {
    que: 'alarma', hora, cancion: cancion || '', nota: nota || '', rutina: !!rutina,
  }, 'mando', sinMando);
  if (!r) return false;
  /* F16 · la frase la compone Java (hora, canción encontrada, si el minuto será
     exacto). La cara repite LO QUE DIJO, no una promesa propia: si el Android no
     da alarmas exactas, `dice` ya lo cuenta. */
  const dicho = r.dice || ('Despertador a las ' + (r.alarma || hora)
    + (nota ? ' — ' + nota : '') + '.');
  diceBien('mando', dicho);
  if (alVoz) ctx?.say?.(dicho);
  ctx?.term?.('alarma ' + (r.alarma || hora) + (r.exacta === false ? ' (sin minuto exacto)' : ''), 'equipo');
  return true;
}

/** «quitar la alarma»: el puente de F16 sabe desarmarla, no sólo ponerla. */
function accionAlarmaQuita(alVoz) {
  if (!puede('alarmaCancela')) return di(
    'Quitar la alarma lo trae el APK nuevo de la Release; este cuerpo sólo sabe ponerla.', 'mando');
  const r = parsea(llama('alarmaCancela'), ctx);
  if (!r) return false;
  const dicho = r.dice || 'Alarma quitada.';
  diceBien('mando', dicho);
  if (alVoz) ctx?.say?.(dicho);
  ctx?.term?.('alarma: ' + dicho, 'equipo');
  return true;
}

function accionTemporizador(segundos, alVoz) {
  if (!puede('accion')) return di(sinMando, 'mando');
  const r = envia('accion', { que: 'temporizador', segundos }, 'mando', sinMando);
  if (!r) return false;
  const puesto = typeof r.segundos === 'number' ? r.segundos : segundos;
  diceBien('mando', 'Contando ' + Math.round(puesto) + ' segundos. Te aviso al acabar.');
  if (alVoz) ctx?.say?.('Temporizador de ' + Math.round(puesto / 60) + ' minutos.');
  return true;
}

function accionAbrir(a, alVoz) {
  if (!puede('accion')) return di(sinMando, 'mando');
  const r = envia('accion', { que: 'abrir', a }, 'mando', sinMando);
  if (!r) return false;
  const nombre = NOMBRES_APP[a] || a;
  diceBien('mando', 'Abriendo ' + nombre + (r.abrio ? ' (' + r.abrio + ')' : '') + '.');
  if (alVoz) ctx?.say?.('Ahí tienes ' + nombre + '.');
  ctx?.orb?.burst?.();
  return true;
}

function buscaApp(nombre, alVoz) {
  const limpio = String(nombre || '').trim();
  if (!limpio) return di('Dime el nombre de la app que busco.', 'mando');
  if (!puede('accion')) return di(sinMando, 'mando');
  const r = envia('accion', { que: 'app', nombre: limpio }, 'mando', sinMando);
  if (!r) return false;
  diceBien('mando', 'Abriendo ' + (r.abrio || limpio)
    + (typeof r.parecido === 'number' ? ' (se parece un ' + r.parecido + '% a lo que dijiste).' : '.'));
  if (alVoz) ctx?.say?.('Abriendo ' + (r.abrio || limpio) + '.');
  return true;
}

function buscaEnRed(texto, alVoz) {
  const limpio = String(texto || '').trim();
  if (!limpio) return di('Dime qué busco.', 'mando');
  if (!puede('accion')) return di(sinMando, 'mando');
  const r = envia('accion', { que: 'buscar', texto: limpio }, 'mando', sinMando);
  if (!r) return false;
  diceBien('mando', 'Buscando «' + (r.busca || limpio) + '» en el teléfono.');
  if (alVoz) ctx?.say?.('Buscando ' + limpio + '.');
  return true;
}

/* `lanzadores` devuelve la lista larga; se pinta como nube de chips y cada uno
   abre con `{que:'app', nombre}` — Java es quien sabe emparejar nombre y paquete. */
function misApps() {
  if (!puede('accion')) return di(sinMando, 'mando');
  const r = envia('accion', { que: 'lanzadores' }, 'mando', sinMando);
  if (!r) return false;
  const apps = Array.isArray(r.apps) ? r.apps : [];
  const nube = el('eq-app-lista');
  if (!apps.length) {
    nube.innerHTML = '<span class="eq-nota">Android no me deja ver la lista de apps en este '
      + 'teléfono (pide el permiso de «todos los paquetes» en Ajustes). Escribe el nombre y la abro igual.</span>';
    return true;
  }
  nube.innerHTML = '<span class="eq-nota">' + apps.length + ' apps instaladas:</span>'
    + apps.slice(0, 80).map(a => `<button class="eq-chip" data-n="${esc(a.nombre || '')}">${esc(a.nombre || '')}</button>`).join('');
  nube.querySelectorAll('[data-n]').forEach(b => b.onclick = () => {
    const r2 = envia('accion', { que: 'app', nombre: b.dataset.n }, 'mando', sinMando);
    if (r2) diceBien('mando', 'Abriendo ' + (r2.abrio || b.dataset.n) + '.');
  });
  return true;
}

/* ── 3 · Cerebro ── */
function enganchaCerebro() {
  el('eq-men-prov').innerHTML = PROVEEDORES.map(p =>
    `<option value="${esc(p)}">${esc(p)}</option>`).join('');
  el('eq-men-guarda').onclick = () => guardaMente(false);
  el('eq-men-prueba').onclick = () => pruebaMente(false);
  el('eq-men-ir').onclick = () => preguntaMente(el('eq-men-pregunta')?.value || '', false);
  el('eq-men-pregunta').addEventListener('keydown', e => {
    if (e.key === 'Enter') preguntaMente(e.currentTarget.value, false);
  });
  enganchaOllama();
}

function pintaCerebro() {
  if (!montada) return;
  if (!puede('mente')) {
    linea('men', 'sin puente de cerebro');
    el('eq-men-res').innerHTML = '<span class="eq-nota">Pensar sin el portátil lo trae el APK nuevo '
      + 'de la Release. Con este cuerpo CORT sólo conversa cuando tu PC está encendido.</span>';
    return;
  }
  const r = envia('mente', { que: 'estado' }, 'men', 'este APK no tiene cerebro propio.');
  if (!r) { linea('men', 'cerebro: sin respuesta'); return; }
  estado.mente = { proveedor: r.proveedor || '', base: r.base || '', modelo: r.modelo || '',
    clavePuesta: !!r.clavePuesta, conRed: !!r.conRed, motores: Array.isArray(r.motores) ? r.motores : [] };
  const sel = el('eq-men-prov');
  // Los proveedores que el aparato no conoce se ofrecen igualmente (la lista es del
  // contrato): si Java no los trae, su `dice` lo cuenta.
  sel.innerHTML = PROVEEDORES.map(p => `<option value="${esc(p)}">${esc(p)}${estado.mente.motores.includes(p) ? '' : ' · sin probar'}</option>`).join('');
  if (estado.mente.proveedor) sel.value = estado.mente.proveedor;
  if (r.motores?.length) {
    const nuevos = r.motores.filter(m => !PROVEEDORES.includes(m));
    if (nuevos.length) sel.innerHTML += nuevos.map(m => `<option value="${esc(m)}">${esc(m)}</option>`).join('');
    if (estado.mente.proveedor) sel.value = estado.mente.proveedor;
  }
  const base = el('eq-men-base'), modelo = el('eq-men-modelo'), clave = el('eq-men-clave');
  // La clave NUNCA se rellena de vuelta: el contrato dice que esa cadena jamás sale
  // del teléfono hacia la cara. Aquí sólo se escribe, y se enseña si está puesta.
  base.value = estado.mente.base || '';
  modelo.value = estado.mente.modelo || '';
  if (clave) { clave.value = ''; clave.placeholder = estado.mente.clavePuesta ? 'puesta ✓ (vacío = no la toco)' : 'pegar clave aquí'; }
  el('eq-men-clave-est').textContent = estado.mente.clavePuesta ? 'clave: puesta ✓' : 'clave: ninguna';
  linea('men', (estado.mente.proveedor || 'sin proveedor') + ' · ' + (estado.mente.modelo || 'sin modelo')
    + ' · ' + (estado.mente.clavePuesta ? 'clave puesta ✓' : 'sin clave')
    + ' · red ' + (estado.mente.conRed ? 'hay' : 'no hay'));
  pintaUltimaMente();
  pintaOllama(false);
}

function guardaMente(alVoz) {
  if (!puede('mente')) return di('Ajustar el cerebro del teléfono lo trae el APK nuevo de la Release.', 'men');
  const clave = (el('eq-men-clave')?.value || '').trim();
  const r = envia('mente', {
    que: 'ajustar', proveedor: el('eq-men-prov')?.value || '',
    base: (el('eq-men-base')?.value || '').trim(), modelo: (el('eq-men-modelo')?.value || '').trim(),
    clave,                                        // vacío = «no la toques», dice el contrato
  }, 'men', 'este APK no deja ajustar su cerebro.');
  if (!r) return false;
  // Se vuelve a leer el estado: el contrato dice que `ajustar` contesta lo mismo
  // que `estado`, pero un APK intermedio puede devolver sólo `{"ok":true}`.
  diceBien('men', 'Anotado: ' + (r.proveedor || '') + ' con el modelo '
    + (r.modelo || 'que pusiste') + (r.clavePuesta ? ' · clave puesta ✓' : ' · sin clave todavía') + '.');
  if (alVoz) ctx?.say?.('Cerebro ajustado.');
  pintaCerebro();
  return true;
}

function pruebaMente(alVoz) {
  if (!puede('mente')) return di('Probar el cerebro del teléfono lo trae el APK nuevo de la Release.', 'men');
  const r = envia('mente', { que: 'probar' }, 'men', 'este APK no puede probar su cerebro.');
  if (!r) return false;
  diceBien('men', r.pendiente ? 'Probando: la respuesta larga llega en un momento.' : 'Aquí está la prueba.');
  ctx?.term?.('prueba de cerebro pedida', 'equipo');
  if (alVoz) ctx?.say?.('Mirando a ver quién responde.');
  return true;
}

function preguntaMente(texto, alVoz) {
  const pregunta = String(texto || '').trim();
  if (!pregunta) return di('Dime qué quieres que piense.', 'men');
  if (!puede('mente')) return di('Pensar sin el portátil lo trae el APK nuevo de la Release; con este cuerpo la pregunta se va a tu PC.', 'men');
  preguntaVoz = !!alVoz;
  const r = envia('mente', { que: 'preguntar', texto: pregunta }, 'men', 'este APK no puede pensar solo.');
  if (!r) { preguntaVoz = false; return false; }
  const res = el('eq-men-res');
  if (res) res.innerHTML = '<span class="eq-nota">Pensándolo…</span>';
  diceBien('men', '«' + pregunta.slice(0, 48) + '» ' + (r.pendiente ? 'se responde en un momento.' : '.'));
  ctx?.term?.('pregunta al cerebro del teléfono: ' + pregunta.slice(0, 40), 'equipo');
  return true;
}

function pintaUltimaMente() {
  const res = el('eq-men-res');
  if (!res) return;
  const e = estado.ultimaMente;
  if (!e) return;
  if (e.ok === false) {
    res.innerHTML = '<span class="eq-aviso-eq">' + esc(e.dice || 'el cerebro no respondió') + '</span>';
    return;
  }
  res.innerHTML = `<span class="eq-de ${esc(e.de || '')}">${esc(e.de === 'local' ? 'local' : 'nube')}</span>`
    + '<div class="eq-texto">' + esc(e.responde || '') + '</div>'
    + (e.eco ? '<div class="eq-nota">a propósito de: ' + esc(e.eco) + '</div>' : '');
}

/* ── 3b · los cerebros de casa: Ollama por Wi-Fi ──
   No hay método propio del puente: todo entra por `mente({que:'ollama',…})`, así
   que un APK anterior a la ronda 2.4 contesta `{"ok":false,"dice":…}` con su frase
   honesta en vez de reventar aquí. `estado` y `usa` vuelven en el mismo golpe;
   `fija`, `lista`, `descubre`, `borra` y `descarga` tardan (son red) y contestan
   después, por el evento `mente` con `de:'ollama'`. */

const giga = n => (n >= 1073741824 ? (n / 1073741824).toFixed(1) + ' GB'
  : n >= 1048576 ? Math.round(n / 1048576) + ' MB'
  : n >= 1024 ? Math.round(n / 1024) + ' KB' : n + ' B');

const barra = p => {
  const b = el('eq-oll-barra');
  if (b) b.style.width = Math.round(Math.max(0, Math.min(1, Number(p) || 0)) * 100) + '%';
};

/* El botón de cancelar sólo se enseña mientras hay una bajada abierta. No es adorno:
   Java no admite dos a la vez (el segundo `descarga` contesta «ya está bajando X»),
   así que cortar es lo único que queda cuando una se queda colgada, y la cara tiene
   que dar esa salida sin cerrar la hoja. */
const muestraCancela = si => {
  const b = el('eq-oll-cancela');
  if (b) b.hidden = !si;
};

/* ── F11 · el catálogo medido ──
   La dueña pidió «catálogo 1–100 con descarga en segundo plano, barra y aviso».
   Lo que NO se hizo: inventarse los pesos. Cada `b` de la tabla son los bytes de
   las capas del manifiesto que sirve `registry.ollama.ai` — o sea lo que
   `ollama pull` baja de verdad — medidos el 2026-10-23. La lista la lleva dentro
   la cara (no hace falta el portátil para mirarla), y el ↓ lanza la descarga por
   el puente de siempre (`mente`), que ya va en su hilo y ya manda su barra por el
   evento `mente`. */
/* Los bytes son la suma de las capas del manifiesto de
 * `registry.ollama.ai/v2/library/<modelo>/manifests/<etiqueta>` — lo que
 * `ollama pull` baja de verdad —, medidos desde este portátil el 2026-10-23.
 * Ordenados de menos a más. No hay ningún peso estimado en esta tabla. */
const CATALOGO_OLLAMA = [
  { m: 'all-minilm:22m', b: 45960589, d: 'embeddings: busca por sentido' },
  { m: 'all-minilm:33m', b: 67319501, d: 'embeddings: busca por sentido' },
  { m: 'smollm:135m', b: 91738925, d: 'los más chicos, para equipos flojos' },
  { m: 'smollm2:135m', b: 270898111, d: 'los más chicos, para equipos flojos' },
  { m: 'nomic-embed-text:latest', b: 274302030, d: 'embeddings: busca por sentido' },
  { m: 'gemma3:270m', b: 291554440, d: 'los más chicos, para equipos flojos' },
  { m: 'functiongemma:270m', b: 300806689, d: 'elige herramientas y funciones' },
  { m: 'qwen2.5:0.5b', b: 397820829, d: 'buen español' },
  { m: 'qwen3:0.6b', b: 522653277, d: 'buen español' },
  { m: 'paraphrase-multilingual:latest', b: 562777452, d: 'embeddings: busca por sentido' },
  { m: 'tinyllama:1.1b', b: 637699655, d: 'los más chicos, para equipos flojos' },
  { m: 'bge-large:335m', b: 670531692, d: 'embeddings: busca por sentido' },
  { m: 'smollm2:360m', b: 725565951, d: 'los más chicos, para equipos flojos' },
  { m: 'lfm2.5-thinking:1.2b', b: 731163420, d: 'razona paso a paso' },
  { m: 'gemma3:1b', b: 806067267, d: 'conversación general' },
  { m: 'qwen2.5:1.5b', b: 986061405, d: 'buen español' },
  { m: 'qwen2.5-coder:1.5b', b: 986061602, d: 'código' },
  { m: 'deepseek-r1:1.5b', b: 1117322281, d: 'razona paso a paso' },
  { m: 'deepcoder:1.5b', b: 1117323213, d: 'código' },
  { m: 'bge-m3:latest', b: 1157672268, d: 'embeddings: busca por sentido' },
  { m: 'snowflake-arctic-embed2:568m', b: 1160296381, d: 'embeddings: busca por sentido' },
  { m: 'llama3.2:1b', b: 1321097844, d: 'los más chicos, para equipos flojos' },
  { m: 'qwen3.5:0.8b', b: 1322069043, d: 'buen español' },
  { m: 'qwen3:1.7b', b: 1359292957, d: 'buen español' },
  { m: 'granite3.1-dense:2b', b: 1569689131, d: 'conversación general' },
  { m: 'llama-guard3:1b', b: 1600181360, d: 'filtra respuestas (guard)' },
  { m: 'gemma2:2b', b: 1629518008, d: 'conversación general' },
  { m: 'shieldgemma:2b', b: 1708595138, d: 'filtra respuestas (guard)' },
  { m: 'starcoder2:3b', b: 1709901383, d: 'código' },
  { m: 'moondream:1.8b', b: 1738450635, d: 'entiende imágenes' },
  { m: 'falcon3:1b', b: 1778722778, d: 'conversación general' },
  { m: 'smollm2:1.7b', b: 1820427974, d: 'los más chicos, para equipos flojos' },
  { m: 'qwen3-vl:2b', b: 1889519136, d: 'entiende imágenes' },
  { m: 'qwen2.5:3b', b: 1929911945, d: 'buen español' },
  { m: 'orca-mini:3b', b: 1979946988, d: 'conversación general' },
  { m: 'falcon3:3b', b: 2005696570, d: 'conversación general' },
  { m: 'hermes3:3b', b: 2019383881, d: 'conversación general' },
  { m: 'llama3.2:3b', b: 2019392628, d: 'conversación general' },
  { m: 'granite4:3b', b: 2099520968, d: 'conversación general' },
  { m: 'phi3:3.8b', b: 2176178430, d: 'conversación general' },
  { m: 'phi4-mini:3.8b', b: 2491876363, d: 'los más chicos, para equipos flojos' },
  { m: 'qwen3:4b', b: 2497293444, d: 'buen español' },
  { m: 'qwen3.5:2b', b: 2683396637, d: 'buen español' },
  { m: 'nemotron-mini:4b', b: 2697402127, d: 'conversación general' },
  { m: 'nemotron-3-nano:4b', b: 2837596648, d: 'los más chicos, para equipos flojos' },
  { m: 'ministral-3:3b', b: 2953840294, d: 'conversación general' },
  { m: 'granite4:1b', b: 3267419912, d: 'los más chicos, para equipos flojos' },
  { m: 'qwen3.5:4b', b: 3324173757, d: 'buen español' },
  { m: 'gemma3:4b', b: 3350272259, d: 'conversación general' },
  { m: 'deepscaler:1.5b', b: 3560419007, d: 'razona paso a paso' },
  { m: 'codellama:7b', b: 3825910133, d: 'código' },
  { m: 'llama2:7b', b: 3826793120, d: 'conversación general' },
  { m: 'deepseek-llm:7b', b: 4000473307, d: 'conversación general' },
  { m: 'starcoder2:7b', b: 4042812743, d: 'código' },
  { m: 'sqlcoder:7b', b: 4108916388, d: 'código' },
  { m: 'starling-lm:7b', b: 4108939803, d: 'conversación general' },
  { m: 'neural-chat:7b', b: 4109852830, d: 'conversación general' },
  { m: 'openchat:7b', b: 4109875903, d: 'conversación general' },
  { m: 'dolphincoder:7b', b: 4228620959, d: 'código' },
  { m: 'mistral:7b', b: 4372823897, d: 'conversación general' },
  { m: 'falcon3:7b', b: 4569738490, d: 'conversación general' },
  { m: 'llama3:8b', b: 4661224191, d: 'conversación general' },
  { m: 'hermes3:8b', b: 4661226758, d: 'conversación general' },
  { m: 'deepseek-r1:7b', b: 4683074953, d: 'razona paso a paso' },
  { m: 'qwen2.5:7b', b: 4683086845, d: 'buen español' },
  { m: 'qwen2.5-coder:7b', b: 4683087074, d: 'código' },
  { m: 'exaone-deep:7.8b', b: 4770664663, d: 'conversación general' },
  { m: 'aya:8b', b: 4797473531, d: 'buen español' },
  { m: 'cogito:8b', b: 4920747535, d: 'razona paso a paso' },
  { m: 'llama3.1:8b', b: 4920752841, d: 'conversación general' },
  { m: 'dolphin3:8b', b: 4920757165, d: 'conversación general' },
  { m: 'tulu3:8b', b: 4920788500, d: 'conversación general' },
  { m: 'granite3.3:8b', b: 4942891236, d: 'conversación general' },
  { m: 'granite3.1-dense:8b', b: 4991633323, d: 'conversación general' },
  { m: 'codegemma:7b', b: 5011852326, d: 'código' },
  { m: 'aya-expanse:8b', b: 5056999552, d: 'buen español' },
  { m: 'deepseek-r1:8b', b: 5225375560, d: 'razona paso a paso' },
  { m: 'qwen3:8b', b: 5225387677, d: 'buen español' },
  { m: 'glm4:9b', b: 5455325746, d: 'conversación general' },
  { m: 'minicpm-v:8b', b: 5473837900, d: 'entiende imágenes' },
  { m: 'ministral-3:8b', b: 6022236102, d: 'conversación general' },
  { m: 'solar:10.7b', b: 6072383801, d: 'conversación general' },
  { m: 'qwen3-vl:8b', b: 6190971493, d: 'entiende imágenes' },
  { m: 'qwen3.5:9b', b: 6550825373, d: 'buen español' },
  { m: 'mistral-nemo:12b', b: 7071712741, d: 'buen español' },
  { m: 'llama3.2-vision:11b', b: 7816588622, d: 'entiende imágenes' },
  { m: 'gemma3n:e2b', b: 7836324401, d: 'conversación general' },
  { m: 'gemma3:12b', b: 8164039587, d: 'conversación general' },
  { m: 'cogito:14b', b: 8985290822, d: 'razona paso a paso' },
  { m: 'deepseek-r1:14b', b: 8988111721, d: 'razona paso a paso' },
  { m: 'phi4:14b', b: 9053115905, d: 'conversación general' },
  { m: 'ministral-3:14b', b: 9082537031, d: 'conversación general' },
  { m: 'qwen3:14b', b: 9276198077, d: 'buen español' },
  { m: 'gemma3n:e4b', b: 9768581713, d: 'conversación general' },
  { m: 'phi4-reasoning:14b', b: 11117502673, d: 'razona paso a paso' },
  { m: 'mistral-small:24b', b: 14333921100, d: 'conversación general' },
  { m: 'devstral:24b', b: 14333927558, d: 'código' },
  { m: 'gemma3:27b', b: 17413409507, d: 'conversación general' },
  { m: 'qwen3.5:27b', b: 17478556413, d: 'buen español' },
  { m: 'qwen3-coder:30b', b: 18556700222, d: 'código' },
  { m: 'wizardcoder:33b', b: 18819451016, d: 'código' },
  { m: 'deepseek-r1:32b', b: 19851337321, d: 'razona paso a paso' },
  { m: 'qwq:32b', b: 19851349169, d: 'razona paso a paso' },
  { m: 'qwen2.5:32b', b: 19851349181, d: 'buen español' },
  { m: 'qwen2.5-coder:32b', b: 19851349410, d: 'código' },
  { m: 'qwen3.5:35b', b: 22069591997, d: 'buen español' },
  { m: 'llama3.3:70b', b: 42520413354, d: 'conversación general' },
];


const CAT_FILTROS = [
  ['', 'todos'],
  ['chico', '≤ 1 GB'],
  ['medio', '1–5 GB'],
  ['grande', '> 5 GB'],
  ['codigo', 'código'],
  ['razona', 'razona'],
  ['imagen', 'imágenes'],
  ['embed', 'embeddings'],
];

function catPasa(ficha) {
  const f = estado.ollama.filtro;
  if (!f) return true;
  if (f === 'chico') return ficha.b <= 1e9;
  if (f === 'medio') return ficha.b > 1e9 && ficha.b <= 5e9;
  if (f === 'grande') return ficha.b > 5e9;
  if (f === 'imagen') return /im|VL|visi/i.test(ficha.d + ficha.m);
  if (f === 'codigo') return /código/i.test(ficha.d);
  if (f === 'razona') return /razona/i.test(ficha.d);
  if (f === 'embed') return /embedding/i.test(ficha.d);
  return true;
}

/* Como el servidor de Ollama está en el PC, la cara sabe qué modelos ya están
   bajados (`estado.ollama.modelos`) y ése es el único criterio que puede pintar
   sin mentir: si no hay lista, no pinta ✓. */
function estaEnPC(nombre) {
  return (estado.ollama.modelos || []).some(m => (m.nombre || m) === nombre);
}

function pintaCatalogo() {
  const caja = el('eq-cat-lista'), chips = el('eq-cat-chips'), cuenta = el('eq-cat-cuenta');
  if (!caja || !chips || !cuenta) return;
  cuenta.textContent = CATALOGO_OLLAMA.length + ' medidos del registro';
  if (!estado.ollama.abierto) {
    chips.innerHTML = '';
    caja.innerHTML = '<span class="eq-nota">pulsa «ver catálogo» y se despliegan los '
      + CATALOGO_OLLAMA.length + ' modelos con el peso real de su descarga. Al tocar ↓ '
      + 'lo baja tu PC por Wi-Fi y la barra de arriba se mueve sola; puedes cerrar la '
      + 'hoja mientras baja.</span>';
    return;
  }
  chips.innerHTML = CAT_FILTROS.map(([clave, titulo]) =>
    `<button class="eq-chip${estado.ollama.filtro === clave ? ' puesta' : ''}" `
    + `data-filtro="${clave}">${titulo}</button>`).join('');
  chips.querySelectorAll('[data-filtro]').forEach(b => {
    b.onclick = () => { estado.ollama.filtro = b.dataset.filtro; pintaCatalogo(); };
  });

  const busca = plegarTexto(el('eq-cat-busca')?.value || '');
  const vale = CATALOGO_OLLAMA.filter(f => catPasa(f)
    && (!busca || plegarTexto(f.m + ' ' + f.d).includes(busca)));
  const tope = 40;
  caja.innerHTML = vale.length
    ? vale.slice(0, tope).map(f => {
        const enPC = estaEnPC(f.m);
        return `<div class="eq-mod"><b data-nombre="${esc(f.m)}">${esc(f.m)}`
          + (enPC ? ' ✓' : '') + `</b><small>${giga(f.b)}</small>`
          + `<button class="eq-b" data-baja="${esc(f.m)}">`
          + (enPC ? 'usa' : '↓') + `</button></div>`;
      }).join('')
      + (vale.length > tope
        ? `<span class="eq-nota">y ${vale.length - tope} más — afina la busca o el filtro</span>` : '')
    : '<span class="eq-nota">ni uno con esa busca. Prueba con «qwen», «3b» o «código».</span>';
  caja.querySelectorAll('[data-baja]').forEach(b => {
    b.onclick = () => {
      const nombre = b.dataset.baja;
      const input = el('eq-oll-nuevo');
      if (input) input.value = nombre;
      if (b.textContent.trim() === 'usa') ollamaOrden('usa', { modelo: nombre });
      else ollamaOrden('descarga', { modelo: nombre });
    };
  });
  caja.querySelectorAll('[data-nombre]').forEach(n => {
    n.onclick = () => {
      const input = el('eq-oll-nuevo');
      if (input) input.value = n.dataset.nombre;
      di('puesto «' + n.dataset.nombre + '» en el campo de descargar.', 'oll');
    };
  });
}

/* El catálogo no tiene acentos ni mayúsculas al filtrar: la dueña escribe «codigo»
   y quiere encontrar «código». Es el mismo arreglo que el buscador de Música, que
   en Java se llama `plegar`. */
function plegarTexto(s) {
  return String(s || '').toLowerCase().normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '').replace(/ñ/g, 'n');
}

function enganchaOllama() {
  el('eq-oll-busca').onclick = () => ollamaOrden('descubre');
  el('eq-oll-mis').onclick = () => ollamaOrden('lista');
  el('eq-oll-fija').onclick = () => ollamaOrden('fija', { servidor: (el('eq-oll-serv')?.value || '').trim() });
  el('eq-oll-baja').onclick = () => {
    const nombre = (el('eq-oll-nuevo')?.value || '').trim();
    if (!nombre) return di('Escribe el modelo que quieres bajar: qwen2.5:0.5b, qwen2.5:1.5b…', 'oll');
    ollamaOrden('descarga', { modelo: nombre });
  };
  el('eq-oll-nuevo').addEventListener('keydown', e => {
    if (e.key === 'Enter') el('eq-oll-baja').click();
  });
  el('eq-oll-cancela').onclick = () => ollamaOrden('cancela');
  el('eq-cat-abre').onclick = () => {
    estado.ollama.abierto = !estado.ollama.abierto;
    el('eq-cat-abre').textContent = estado.ollama.abierto ? 'cerrar catálogo' : 'ver catálogo';
    pintaCatalogo();
  };
  el('eq-cat-busca').addEventListener('input', () => {
    estado.ollama.abierto = true;
    el('eq-cat-abre').textContent = 'cerrar catálogo';
    pintaCatalogo();
  });
  pintaCatalogo();
}

/* La orden, con su frase de mientras. `envia` ya deja en el bloque el `dice` de
   Java cuando el APK no puede, así que aquí no se inventa nada. */
function ollamaOrden(accion, extra) {
  if (!puede('mente')) return di('Mirar a Ollama desde el teléfono lo trae el APK nuevo de la Release.', 'oll');
  const cuerpo = { que: 'ollama', accion };
  if (extra && typeof extra === 'object') Object.assign(cuerpo, extra);
  const r = envia('mente', cuerpo, 'oll', 'este APK todavía no habla con Ollama.');
  if (!r) return false;
  if (accion === 'usa') {                    // sincrónico: ya vino la respuesta
    estado.ollama.modelo = r.modelo || estado.ollama.modelo;
    estado.ollama.enCasa = true;
    diceBien('oll', r.dice || 'hecho.');
    ctx?.term?.('pienso con ' + (r.modelo || '') + ' (casa)', 'equipo');
    ctx?.say?.('Voy a pensar con el modelo de casa.');
    pintaOllama(false);
    return true;
  }
  if (!r.pendiente && r.que === 'fija') return manejaOllama(r);
  if (r.pendiente) {                          // llega en un momento, por el evento
    linea('oll', { descubre: 'mirando tu Wi-Fi… (dos o tres segundos)',
      lista: 'pidiendo la lista de modelos…',
      fija: 'llamando a ese PC…',
      borra: 'borrando ese modelo…',
      /* Lo de «te aviso» no es adorno: desde la ronda 2.8 el APK manda una
         notificación cuando la bajada termina o se corta (el aviso lo pone
         `Timbre.java`, por dentro), así que se puede cerrar la hoja y apagar la
         pantalla. Lo que no puede prometer es que el aviso llegue si Android mata
         la app por memoria. */
      descarga: 'bajando ' + (cuerpo.modelo || '') + ' · cierra la hoja si quieres, te aviso cuando termine',
      cancela: 'cortando la bajada… (el PC puede tardar unos segundos más)' }[accion] || 'mirando…');
  }
  return true;
}

/* La ✓ del catálogo depende de la lista que devuelve el PC: si llega tarde (el
   `lista` es red), el catálogo hay que repintarlo, si no se queda sin marcar y la
   dueña vuelve a bajar lo que ya tiene. */
function pintaOllama(pideLista) {
  if (!montada) return;
  if (!puede('mente')) {
    linea('oll', 'sin puente de cerebro');
    el('eq-oll-lista').innerHTML = '<span class="eq-nota">hablar con los cerebros de tu PC '
      + 'lo trae el APK nuevo de la Release.</span>';
    return;
  }
  const r = envia('mente', { que: 'ollama', accion: 'estado' }, 'oll',
    'este APK todavía no mira a Ollama.');
  if (!r) return;
  estado.ollama.servidor = r.servidor || '';
  estado.ollama.origen = r.origen || '';
  estado.ollama.modelo = r.modelo || '';
  estado.ollama.enCasa = !!r.eligeNube;
  const caja = el('eq-oll-serv');
  if (caja && !caja.value) caja.value = estado.ollama.servidor;
  pintaOllamaLinea();
  if (pideLista) ollamaOrden('lista');
}

function pintaOllamaLinea() {
  const o = estado.ollama;
  linea('oll', (o.servidor ? o.servidor + (o.version ? ' · Ollama ' + o.version : '')
        : 'sin PC señalado: pulsa «buscar en tu Wi-Fi»')
    + ' · ' + (o.enCasa ? 'pensando en casa ✓' : 'pensando con lo de siempre')
    + (o.modelo ? ' · ' + o.modelo : '')
    + (o.modelos.length ? ' · ' + o.modelos.length + ' modelos' : ''));
}

function pintaModelosOllama() {
  /* Con la lista nueva cambian las ✓ del catálogo: si no se repinta, la dueña
     vuelve a pedir un modelo que ya está bajado en su PC. */
  if (estado.ollama.abierto) pintaCatalogo();
  const cajaLista = el('eq-oll-lista');
  if (!cajaLista) return;
  const o = estado.ollama;
  cajaLista.innerHTML = o.modelos.length
    ? o.modelos.map(m => `<div class="eq-mod"><b${m.nombre === o.modelo ? ' class="puesta"' : ''}>`
        + `${esc(m.nombre)}${m.nombre === o.modelo ? ' ✓' : ''}</b>`
        + `<small>${esc(m.parametros || '?')} · ${esc(m.cuantizacion || '?')} · `
        + `${giga(Number(m.tamano) || 0)}</small>`
        + `<button class="eq-b" data-usa="${esc(m.nombre)}">usar</button>`
        + `<button class="eq-b" data-borra="${esc(m.nombre)}">borrar</button></div>`).join('')
    : '<span class="eq-nota">no veo modelos en ese PC. Escribe uno en «bajar uno nuevo»: '
      + 'para un teléfono de 4 GB van bien <b>qwen2.5:0.5b</b> y <b>qwen2.5:1.5b</b> '
      + '(se bajan en el PC, no en el teléfono).</span>';
  cajaLista.querySelectorAll('[data-usa]').forEach(b => {
    b.onclick = () => ollamaOrden('usa', { modelo: b.dataset.usa });
  });
  cajaLista.querySelectorAll('[data-borra]').forEach(b => {
    b.onclick = () => ollamaOrden('borra', { modelo: b.dataset.borra });
  });
}

/* Los PC que encontró `descubre`: si sólo hay uno se fija solo; con dos o más
   (varios ordenadores con Ollama en casa) se elige con un golpe. */
function pintaServidoresOllama(servidores) {
  const cajaLista = el('eq-oll-lista');
  if (!cajaLista) return;
  cajaLista.innerHTML = servidores.map(s => `<button class="eq-chip" data-serv="${esc(s.host)}">`
    + `${esc(s.host)}<small>Ollama ${esc(s.version || '?')}</small></button>`).join('')
    + '<span class="eq-nota">toca el PC donde están tus modelos</span>';
  cajaLista.querySelectorAll('[data-serv]').forEach(b => {
    b.onclick = () => { el('eq-oll-serv').value = b.dataset.serv; ollamaOrden('fija', { servidor: b.dataset.serv }); };
  });
}

/* El cuadro largo que manda Java. Devuelve `true` si era suyo (para que
   `handleTelefonoEvento` no lo tome por una respuesta del cerebro). */
function manejaOllama(ev) {
  const o = estado.ollama;
  if (ev.ok === false) {
    if (ev.que === 'descarga') { o.descargando = false; o.bajando = ''; barra(0); muestraCancela(false); }
    const dicho = ev.dice || 'el PC de casa no contestó.';
    /* Un corte pedido por ella misma no es un fallo, y tampoco es algo que CORT
       haya avisado: Java no manda notificación cuando la bajada la cancelas tú, así
       que aquí no se puede prometer el «te lo avisé». */
    if (ev.cancelado) {
      diceBien('oll', dicho);
      salida('bajada cancelada: ' + (ev.modelo || ''));
      return true;
    }
    avisa('oll', dicho + (ev.que === 'descarga' ? ' · CORT también te lo avisó' : ''));
    if (ev.que !== 'descarga') salida('ollama: ' + dicho);
    else salida('no pude bajar ' + (ev.modelo || 'el modelo') + ': ' + dicho);
    if (ev.que === 'lista') { o.modelos = []; pintaModelosOllama(); }
    return true;
  }
  switch (ev.que) {
    case 'cancela':
      // Java ya dijo `cancelado:true` por su lado; aquí sólo se suelta la barra.
      o.descargando = false; o.bajando = ''; barra(0); muestraCancela(false);
      diceBien('oll', ev.dice || 'bajada cortada.');
      salida('cancelado: ' + (ev.modelo || ''));
      return true;
    case 'fija':
      o.servidor = ev.servidor || o.servidor;
      o.version = ev.version || '';
      if (ev.contesta) { diceBien('oll', ev.dice || 'PC localizado.'); ollamaOrden('lista'); }
      else { avisa('oll', ev.dice || ''); }
      pintaOllamaLinea();
      return true;
    case 'descubre': {
      const servidores = Array.isArray(ev.servidores) ? ev.servidores : [];
      o.servidorVisto = servidores.map(s => s.host);
      const hallazgo = servidores.length === 1 ? 'Ollama en ' + servidores[0].host + ' (versión '
          + (servidores[0].version || '?') + ')'
        : servidores.length + ' PCs con Ollama: ' + servidores.map(s => s.host).join(', ');
      diceBien('oll', hallazgo + ' · ' + (ev.probados || '?') + ' direcciones miradas.');
      salida('buscando cerebros: ' + hallazgo);
      if (servidores.length === 1) { el('eq-oll-serv').value = servidores[0].host; ollamaOrden('fija', { servidor: servidores[0].host }); }
      else pintaServidoresOllama(servidores);
      return true;
    }
    case 'lista':
      o.modelos = Array.isArray(ev.modelos) ? ev.modelos : [];
      o.version = ev.version || o.version;
      o.servidor = ev.servidor || o.servidor;
      pintaModelosOllama();
      pintaOllamaLinea();
      const resumen = o.modelos.length
        ? o.modelos.map(m => m.nombre + ' (' + giga(Number(m.tamano) || 0) + ')').join(', ')
        : 'ninguno: pide «descarga el modelo qwen2.5:0.5b»';
      diceBien('oll', o.modelos.length + ' modelos listos en ' + (o.servidor || 'el PC')
        + (o.version ? ' · Ollama ' + o.version : '') + '.');
      salida('modelos en tu PC: ' + resumen);
      return true;
    case 'descarga': {
      if (ev.listo === undefined) {                 // va bajando: sólo la barra
        o.descargando = true;
        o.bajando = ev.modelo || o.bajando;
        barra(ev.porcentaje);
        muestraCancela(true);
        linea('oll', 'bajando ' + (ev.modelo || '') + ' · ' + (ev.estado || '')
          + (Number(ev.total) ? ' · ' + giga(Number(ev.hecho) || 0) + ' de ' + giga(Number(ev.total) || 0) : '')
          + (Number(ev.capas) > 1 ? ' · ' + ev.capas + ' capas' : ''));
        return true;
      }
      o.descargando = false; o.bajando = ''; barra(1); muestraCancela(false);
      if (ev.listo) {
        const dicho = 'ya está ' + (ev.modelo || 'el modelo') + ' en tu PC ('
          + giga(Number(ev.total) || 0) + '). Toca «usar» y CORT piensa con él.';
        diceBien('oll', dicho);
        salida(dicho);
        ctx?.say?.('Modelo bajado.');
        ollamaOrden('lista');
      } else { avisa('oll', ev.dice || 'no pude bajar ese modelo.'); }
      return true;
    }
    case 'borra':
      diceBien('oll', 'borrado ' + (ev.modelo || '') + ' de tu PC.');
      salida('borrado ' + (ev.modelo || '') + ' de tu PC');
      ollamaOrden('lista');
      return true;
    default:
      return true;
  }
}

/* ── 4 · Memoria ── */
function enganchaMemoria() {
  el('eq-mem-guarda').onclick = () => guardaRecuerdo(el('eq-mem-texto')?.value || '', false);
  el('eq-mem-quien').onclick = () => quienSoy(false);
  el('eq-mem-sync').onclick = () => sincroniza(false);
  el('eq-mem-refresca').onclick = () => pintaMemoria();
  el('eq-mem-texto').addEventListener('keydown', e => {
    if (e.key === 'Enter') guardaRecuerdo(e.currentTarget.value, false);
  });
}

function pintaMemoria() {
  if (!montada) return;
  if (!puede('memoria')) {
    linea('mem', 'sin puente de memoria');
    el('eq-mem-lista').innerHTML = '<span class="eq-nota">Recordar sin el portátil lo trae el APK '
      + 'nuevo de la Release: este cuerpo todavía apunta las cosas en tu PC.</span>';
    return;
  }
  const est = envia('memoria', { que: 'estado' }, 'mem', 'este APK no cuenta lo que recuerda.');
  if (est) {
    estado.hechos = typeof est.hechos === 'number' ? est.hechos : estado.hechos;
    estado.conPortatil = !!est.conPortatil;
    estado.direccion = est.direccion || '';
    linea('mem', estado.hechos + ' recuerdos · con el portátil: '
      + (estado.conPortatil ? 'sí (' + estado.direccion + ')' : 'todavía no'));
  }
  const lista = envia('memoria', { que: 'lista' }, 'mem', '');
  const recuerdos = (lista && Array.isArray(lista.recuerdos)) ? lista.recuerdos : [];
  estado.recuerdos = recuerdos;
  const nube = el('eq-mem-lista');
  if (!recuerdos.length) {
    nube.innerHTML = '<span class="eq-nota">la libreta está vacía: escribe arriba «acuédate de…».</span>';
    return;
  }
  nube.innerHTML = '<span class="eq-nota">lo último que apunté:</span>' + recuerdos.slice(0, 12)
    .map(r => `<div class="eq-rec"><span>${esc(r.contenido || '')}</span>`
      + `<small>${esc(String(r.cuando || '').slice(0, 10))}</small></div>`).join('');
}

function guardaRecuerdo(texto, alVoz) {
  const limpio = String(texto || '').trim();
  if (!limpio) return di('Dime qué quieres que recuerde.', 'mem');
  if (!puede('memoria')) return di('Guardar recuerdos en el teléfono lo trae el APK nuevo de la Release.', 'mem');
  const r = envia('memoria', { que: 'guardar', texto: limpio }, 'mem', 'este APK no puede apuntar nada.');
  if (!r) return false;
  diceBien('mem', 'Anotado' + (r.clave ? ' como «' + r.clave + '»' : '') + ': ' + limpio.slice(0, 60) + '.');
  if (alVoz) ctx?.say?.('Apuntado.');
  pintaMemoria();
  return true;
}

function quienSoy(alVoz) {
  if (!puede('memoria')) return di('Lo de saber quién eres en el teléfono lo trae el APK nuevo de la Release.', 'mem');
  const r = envia('memoria', { que: 'quien' }, 'mem', 'este APK no sabe qué recuerda.');
  if (!r) return false;
  estado.quien = r.dice || '';
  diceBien('mem', estado.quien || 'No encontré qué sé de ti.');
  if (alVoz) ctx?.say?.(estado.quien || 'Todavía no sé nada de ti.');
  return true;
}

function buscaRecuerdo(texto, alVoz) {
  const limpio = String(texto || '').trim();
  if (!limpio) return quienSoy(alVoz);
  if (!puede('memoria')) return di('Buscar en mi memoria del teléfono lo trae el APK nuevo de la Release.', 'mem');
  const r = envia('memoria', { que: 'buscar', texto: limpio }, 'mem', 'este APK no puede rebuscar.');
  if (!r) return false;
  diceBien('mem', 'De «' + limpio + '» sé: ' + (r.encuentra || 'nada por ahora') + '.');
  if (alVoz) ctx?.say?.(r.encuentra || 'Nada anotado sobre eso.');
  return true;
}

function sincroniza(alVoz) {
  if (!puede('memoria')) return di('Sincronizar con tu portátil lo trae el APK nuevo de la Release.', 'mem');
  const r = envia('memoria', { que: 'sincronizar' }, 'mem', 'este APK no puede cuadrar recuerdos.');
  if (!r) return false;
  preguntaVoz = preguntaVoz || !!alVoz;
  diceBien('mem', r.pendiente
    ? 'Cuadrando con tu portátil por el Wi-Fi: te digo el resultado en un momento.'
    : 'Cuadrado con el portátil.');
  if (alVoz) ctx?.say?.('Cuadrando con tu portátil.');
  return true;
}

/* ── 5 · Atuendos ── */
function enganchaAtuendo() {
  el('eq-burb').onclick = () => ponBurbuja(!estado.burbuja, false);
}

function pintaAtuendo() {
  if (!montada) return;
  if (!puede('atuendo')) {
    linea('atu', 'sin puente de trajes');
    el('eq-atu-lista').innerHTML = '<span class="eq-nota">Cambiar de traje lo trae el APK nuevo de la '
      + 'Release; con este cuerpo CORT viste siempre los colores de siempre.</span>';
  } else {
    const r = envia('atuendo', { que: 'lista' }, 'atu', 'este APK no tiene trajes.');
    if (r) {
      estado.atuendos = Array.isArray(r.atuendos) ? r.atuendos : [];
      estado.puesto = r.puesto || estado.puesto;
      const nube = el('eq-atu-lista');
      nube.innerHTML = (estado.atuendos.length
        ? estado.atuendos.map(a => `<button class="eq-palette${a.nombre === estado.puesto ? ' puesta' : ''}" `
            + `data-t="${esc(a.nombre || '')}" style="--p:${esc(a.primario || '#39c2ff')};--s:${esc(a.secundario || '#0a3d62')}">`
            + `<i></i><span>${esc(a.nombre || '')}</span></button>`).join('')
        : '<span class="eq-nota">no vine a traer ningún traje: escribe el nombre en la voz y lo intento.</span>')
        + (estado.puesto ? '<span class="eq-nota">puesto: ' + esc(estado.puesto) + '</span>' : '');
      nube.querySelectorAll('[data-t]').forEach(b => b.onclick = () => ponAtuendo(b.dataset.t, false));
      linea('atu', estado.atuendos.length + ' trajes · puesto: ' + (estado.puesto || 'el de siempre'));
    }
  }
  const bot = el('eq-burb');
  if (bot) {
    bot.classList.toggle('puesta', estado.burbuja);
    bot.textContent = '● burbuja ' + (estado.burbuja ? 'puesta' : 'apagada');
    const est = el('eq-burb-est');
    if (est) est.textContent = puede('burbuja')
      ? (estado.burbuja ? 'CORT flota encima de lo que estés usando' : 'un punto de CORT flotando, sin sacarte de nada')
      : 'la burbuja la trae el APK nuevo de la Release';
  }
}

/* El contrato pinta las variables CSS desde Java (`{"css":"--primario:#…;--secundario:#…"}`).
   Se leen con try/catch y se aplican a `<html>`; además `--cyan` lleva el primario
   para que el traje se note de verdad en el HUD de vidrio. */
function ponVariables(css) {
  const raiz = document.documentElement;
  String(css || '').split(';').forEach(parte => {
    const i = parte.indexOf(':');
    if (i < 0) return;
    const k = parte.slice(0, i).trim();
    const v = parte.slice(i + 1).trim();
    if (/^--[\w-]+$/.test(k) && /^#[0-9a-f]{3,8}$/i.test(v)) raiz.style.setProperty(k, v);
  });
  const p = raiz.style.getPropertyValue('--primario').trim();
  const s = raiz.style.getPropertyValue('--secundario').trim();
  if (/^#[0-9a-f]{3,8}$/i.test(p)) { raiz.style.setProperty('--cyan', p); raiz.style.setProperty('--text', p); }
  if (/^#[0-9a-f]{3,8}$/i.test(s)) raiz.style.setProperty('--glass-hi', s);
  raiz.classList.add('con-atuendo');
}

function ponAtuendo(nombre, alVoz) {
  const limpio = String(nombre || '').trim();
  if (!limpio) return di('Dime el traje que quiero ponerme.', 'atu');
  if (!puede('atuendo')) return di('Cambiar de traje lo trae el APK nuevo de la Release: con este cuerpo no puedo pintarme.', 'atu');
  const elegido = matchAtuendo(limpio);
  const r = envia('atuendo', { que: 'poner', nombre: elegido || limpio }, 'atu', 'este APK no me deja cambiarme.');
  if (!r) return false;
  ponVariables(r.css);
  estado.puesto = elegido || limpio;
  diceBien('atu', 'Ya visto de ' + estado.puesto + (r.css ? ' (' + r.css + ')' : '') + '.');
  if (alVoz) ctx?.say?.('Puesta de ' + estado.puesto + '.');
  ctx?.orb?.burst?.();
  pintaAtuendo();
  return true;
}

/* Si la lista del aparato tiene un traje con ese nombre (o con ese color dentro),
   se manda SU nombre exacto. Si no, se manda lo que dijo la dueña y Java contesta
   con su `dice`: no me invento un traje que no existe. */
function matchAtuendo(texto) {
  const b = normaliza(texto);
  const golpe = estado.atuendos.find(a => normaliza(a.nombre) === b)
    || estado.atuendos.find(a => normaliza(a.nombre).includes(b) || b.includes(normaliza(a.nombre)));
  return golpe ? golpe.nombre : '';
}

/* `burbuja(boolean)` NO lleva JSON dentro: es el único del contrato que recibe el
   booleano a pelo. Aun así, por puede() y sin fiarse de la forma de la respuesta. */
function ponBurbuja(on, alVoz) {
  if (!puede('burbuja')) return di('La burbuja flotante la trae el APK nuevo de la Release. Y aunque la tuviera: en modo juego nunca aparece.', 'atu');
  const crudo = llama('burbuja', !!on);
  const r = parsea(crudo, ctx);
  if (r && typeof r === 'object' && r.ok === false) {
    avisa('atu', r.dice || 'el teléfono no dejó poner la burbuja.');
    if (alVoz) ctx?.say?.(r.dice || 'Eso no lo puedo hacer ahora.');
    // «aparecer encima de otras apps» no es un cuadro de permiso: es un
    // interruptor de Ajustes, y Android se niega a pedirlo con
    // `requestPermissions`. Java ya lo sabe (`pidePermiso('burbuja')` abre la
    // pantalla), así que si falta eso es lo que hay que abrir, no repetir el
    // botón esperando que la segunda vez salga solo.
    if (/encima de otras apps|aparecer/.test(r.dice || '') && puede('requestPermission')) {
      llama('requestPermission', 'burbuja');
      avisa('atu', 'Te abro la pantalla de ese interruptor: actívalo y pídeme la burbuja otra vez.');
    }
    return true;
  }
  if (r === null && crudo === null) { avisa('atu', 'El puente no contesta a burbuja().'); return true; }
  // `Flotante` contesta con la clave `burbuja`, no `puesta`: leer la que no
  // existe hacía que APAGARLA se anunciara como «burbuja puesta».
  const puesta = (r && typeof r === 'object')
    ? (typeof r.burbuja === 'boolean' ? r.burbuja
       : (typeof r.puesta === 'boolean' ? r.puesta : true))
    : (r === undefined ? !!on : !!r);
  estado.burbuja = puesta;
  diceBien('atu', puesta
    ? 'Burbuja puesta: un punto mío flotando. Tócalo y abro CORT y te escucho.'
    : 'Burbuja quitada: vuelvo a estar dentro de la app.');
  if (alVoz) ctx?.say?.(puesta ? 'Burbuja puesta.' : 'Burbuja quitada.');
  pintaAtuendo();
  return true;
}

/* ── 6 · Agenda ──
   La cita se **lee**, nunca se escribe a escondidas: `apunta` rellena el
   formulario del calendario de Android y el dedo de la dueña lo guarda. Es la
   diferencia entre «te lo apunté» mentira y «te lo dejo listo» verdad, y por eso
   el manifiesto pide `READ_CALENDAR` y no `WRITE_CALENDAR`. */
function enganchaAgenda() {
  el('eq-ago-hoy').onclick = () => miraAgenda({ que: 'hoy' }, false);
  el('eq-ago-3').onclick = () => miraAgenda({ que: 'proximos', dias: 3 }, false);
  el('eq-ago-7').onclick = () => miraAgenda({ que: 'proximos', dias: 7 }, false);
  el('eq-ago-abrir').onclick = () => miraAgenda({ que: 'abrir' }, false);
  el('eq-ago-correo').onclick = () => correo(false);
  el('eq-ago-pon').onclick = () => apunta(null, null, false);
}

function pintaAgenda() {
  if (!montada) return;
  if (!puede('agenda')) {
    linea('ago', 'sin puente de agenda');
    el('eq-ago-lista').innerHTML = '<span class="eq-nota">«¿qué tengo hoy?» y el correo '
      + 'los trae el APK nuevo de la Release: con este cuerpo no miro tu calendario.</span>';
    return;
  }
  const r = envia('agenda', { que: 'proximos', dias: 3 }, 'ago',
                  'este APK no puede leer tu calendario.');
  if (!r) return;                       // `envia` ya dejó el `dice` de Java en la hoja
  const citas = Array.isArray(r.eventos) ? r.eventos : [];
  estado.citas = citas;
  linea('ago', r.dice || (citas.length + (citas.length === 1 ? ' cosa' : ' cosas')
    + ' en los próximos 3 días'));
  const nube = el('eq-ago-lista');
  if (!citas.length) {
    nube.innerHTML = '<span class="eq-nota">no hay nada apuntado estos días. Si acabo de '
      + 'pedir el permiso, pulsa «próximos 3» otra vez: la primera vez sólo servía para dártelo.</span>';
    return;
  }
  nube.innerHTML = citas.slice(0, 12).map(c => `<div class="eq-rec"><span>`
    + `${esc(c.titulo || 'sin título')}</span><small>${esc(c.dia || '')} · `
    + `${esc(c.cuando || '')}</small></div>`).join('');
}

function miraAgenda(peticion, alVoz) {
  if (!puede('agenda')) {
    return di('Ver tus citas en el teléfono lo trae el APK nuevo de la Release.', 'ago');
  }
  const r = envia('agenda', peticion, 'ago', 'este APK no puede abrir el calendario.');
  if (!r) return false;                 // ya lo cuenta `envia`, con la frase de Java
  const dicho = r.dice || (peticion.que === 'abrir' ? 'Te abro el calendario.' : 'Listo.');
  diceBien('ago', dicho);
  if (alVoz) ctx?.say?.(dicho);
  if (peticion.que === 'hoy' || peticion.que === 'proximos') pintaAgenda();
  return true;
}

/* El correo, dicho sin mentir: CORT no entra en Gmail (ese permiso no existe),
   cuenta los avisos que ya oyó en la barra y abre la app. Si el oído de los
   avisos está apagado, lo dice en la misma frase. */
function correo(alVoz) {
  if (!puede('agenda')) {
    return di('Mirar el correo en el teléfono lo trae el APK nuevo de la Release.', 'ago');
  }
  const r = envia('agenda', { que: 'correo' }, 'ago', 'este APK no puede ver el correo.');
  if (!r) return false;
  const dicho = r.dice || 'Te abro el correo.';
  diceBien('ago', dicho);
  const cuenta = el('eq-ago-gmail');
  if (cuenta) cuenta.textContent = typeof r.gmail === 'number' ? r.gmail + ' avisos' : '';
  if (alVoz) ctx?.say?.(dicho);
  return true;
}

/* «apunta cena el jueves a las 9»: se rellena el formulario, no se escribe. */
function apunta(titulo, hora, alVoz) {
  if (!puede('agenda')) {
    return di('Apuntar citas lo trae el APK nuevo de la Release.', 'ago');
  }
  const limpio = String(titulo || el('eq-ago-titulo')?.value || '').trim();
  if (!limpio) return di('Dime qué cita: «apunta cena con Samuel a las nueve».', 'ago');
  let ms = 0;
  const reloj = String(hora || el('eq-ago-hora')?.value || '').trim();
  if (/^\d{1,2}[:.]\d{2}$/.test(reloj)) {
    const [h, m] = reloj.split(/[:.]/).map(Number);
    const cuando = new Date();
    cuando.setHours(h, m, 0, 0);
    if (cuando.getTime() < Date.now()) cuando.setDate(cuando.getDate() + 1);
    ms = cuando.getTime();
  }
  const r = envia('agenda', { que: 'apunta', titulo: limpio, hora: ms }, 'ago',
                  'este APK no puede abrir el calendario.');
  if (!r) return false;
  const dicho = r.dice || 'Te lo abro listo para guardar.';
  diceBien('ago', dicho);
  if (alVoz) ctx?.say?.(dicho);
  return true;
}

/* ─────────────────────────── los avisos de Java ─────────────────────────── */
/* El puente empuja `{type:'mente'|'memoria'|'accion'}` cuando lo largo termina. Se
   guarda SIEMPRE en el estado (aunque la hoja esté cerrada) y se pinta si existe.
   Devuelve `true` si el evento era de estos. */
/* ─────────────────────── 7 · el oído propio, en la hoja ───────────────────────
   Java manda el estado por dos vías: el evento `motor` (cada vez que cambia de
   fase) y `oidoEstado()`, que se puede preguntar. La cara usa las dos: pinta con lo
   que llegue primero y no supone nunca lo que no le han dicho. */

/** Lo que se le dice a la dueña en cada fase. Sin inventar: si `Oido` no la nombra, se copia la palabra. */
const FASES_OID = {
  'sin-intentar': 'todavía no he intentado oír sin internet',
  'sin-arrancar': 'el oído sin nube no ha arrancado con CORT',
  'preparando': 'estoy preparando el oído sin nube…',
  'extrayendo': 'copiando el modelo de español a tu teléfono (60 MB, unos segundos)…',
  'cargando': 'cargando el modelo de español…',
  'listo': 'escucho sin internet ni Google ✓',
  'sin-sitio': 'no cabe el modelo: falta sitio libre en el teléfono',
  'sin-modelo': 'este APK es la variedad ligera: no lleva el motor dentro, oigo con el reconocedor de siempre',
  'sin-libreria': 'la librería del motor no cargó en este teléfono',
  'roto': 'el motor del oído se cayó',
  'cerrado': 'cerré el oído sin nube al salir de CORT',
  'apagado': 'el oído sin nube está apagado: uso el reconocedor de siempre',
};

function pintaOido(ev) {
  const e = ev || (() => {
    if (!puede('oidoEstado')) return { oido: 'apagado' };
    const r = parsea(llama('oidoEstado'), ctx);
    return r && typeof r === 'object' ? r : { oido: 'sin-arrancar' };
  })();
  estado.ultimoMotor = e;
  const fase = String(e.oido || 'sin-decir-fase');
  const lineaEl = el('eq-oido-est');
  if (lineaEl) {
    lineaEl.textContent = (FASES_OID[fase] || fase) + (e.motivo ? ' — ' + e.motivo : '');
    lineaEl.classList.toggle('aviso', !['listo'].includes(fase));
  }
  const motor = el('eq-oido-motor');
  if (motor) motor.textContent = e.motor ? 'motor: ' + e.motor + ' · ' + (e.modelo || '?') : '';
  const sitio = el('eq-oido-sitio');
  if (sitio) sitio.textContent = (e.libresMB !== undefined && e.libresMB !== '?' && e.pesoModelo)
    ? 'libres: ' + e.libresMB + ' MB · el modelo ocupa ' + Math.round((e.pesoModelo || 0) / 1048576) + ' MB'
    : '';
  const boton = el('eq-oido-btn');
  if (boton) boton.textContent = e.listo || fase === 'listo'
    ? 'escucha sin internet: activada'
    : (fase === 'apagado' ? 'escucha sin internet: apagada' : 'escucha sin internet: ' + fase);
  const dice = fase === 'listo' ? diceBien : avisa;
  if (e.listo) dice('oido', 'Ya oigo «CORT» sin datos ni wifi. Si Google no está, también.');
  else if (e.motivo) dice('oido', e.motivo);
}

/** «activa/quita el oído sin internet» y «¿me oyes sin wifi?», por voz. */
function accionOido(b) {
  if (!puede('oidoEstado') && !puede('oidoPropio')) {
    return di('Este APK todavía no trae el oído sin nube: empieza en el 2.3.0.', 'oido');
  }
  const enciende = /\b(activa|enciende|pon|quiero|quiero|on)\b/.test(b);
  const apaga = /\b(apaga|desactiva|quita|off|no quiero)\b/.test(b);
  if (!enciende && !apaga) {
    const e = parsea(llama('oidoEstado'), ctx) || estado.ultimoMotor || {};
    const fase = String(e.oido || 'sin-arrancar');
    return di((FASES_OID[fase] || fase) + (e.motivo ? ' — ' + e.motivo : ''), 'oido');
  }
  const r = parsea(llama('oidoPropio', enciende), ctx);
  if (!r || typeof r !== 'object') return di('El teléfono no me dejó mover el oído.', 'oido');
  setTimeout(() => pintaOido(), 400);
  return di(enciende
    ? 'Pongo el oído propio: te escucho sin internet ni servicios de voz.'
    : 'Apago el oído propio y vuelvo al reconocedor de Google.', 'oido');
}

function enganchaOido() {
  const boton = el('eq-oido-btn');
  if (!boton) return;
  boton.onclick = () => {
    const antes = estado.ultimoMotor || {};
    const quiero = !(antes.listo || antes.oido === 'listo') && antes.oido !== 'apagado';
    // `oidoPropio` es síncrono y dice lo que quedó puesto; si este APK no lo tiene
    // (un instalador anterior al 2.3.0) se avisa en el bloque, no en la consola.
    const r = puede('oidoPropio') ? parsea(llama('oidoPropio', quiero), ctx) : null;
    if (!r || typeof r !== 'object') { avisa('oido', 'este APK todavía no trae el oído sin nube.'); return; }
    ctx?.say?.(quiero ? 'Voy preparando el oído sin internet.' : 'Apago el oído propio y uso el de Google.');
    setTimeout(() => pintaOido(), 400);
  };
  pintaOido();
}

/* ════════════════════ 8 · AUTOMATIZA: «cuando X, entonces Y» ════════════════════
   Las reglas viven en `automatiza.js` (motor puro, comprobable en el portátil) y
   aquí reciben lo que ese motor no puede tener: **las manos** (`ejecutaAccion`), la
   consola, y el DOM donde pintarse. Tres cosas se sostienen con esto:

   · La orden de la dueña pasa por el motor ANTES que por la boca de CORT
     (`telefonoPorVoz`), así que si ella apuntó «modo noche», lo que pasa es LO SUYO,
     no lo que CORT siempre entiende por esa frase.
   · Las señales entran por donde ya entraban: `stt-final`/terminal (frase),
     `aviso` (nuevo en Java, ronda 2.4), `auricular`, y la batería, que se mira con
     el `aparato()` de siempre. Ninguna regla pide un permiso que el APK no tenga.
   · Si una acción no existe en este APK, `ejecutaAccion` devuelve `false` y el motor
     lo cuenta en la consola. Un «ya está» vacío es el fallo que se reprochó al 2.0.0.
*/

/* Las manos. Todo lo que una regla puede pedir, traducido a las funciones que YA
   estaban en esta hoja — no hay ni un puente nuevo que inventar. */
function ejecutaAccion(que, a) {
  const texto = String(a.texto ?? a.arg ?? a.app ?? a.hora ?? '').trim();
  switch (que) {
    case 'habla':
      if (!texto) return false;
      salida('la regla dice: ' + texto, 'autos');
      ctx?.say?.(texto);
      return true;
    case 'volumen': {
      const como = { callar: 'callar', mínimo: 'min', maximo: 'max', máximo: 'max',
                     subir: 'sube', bajar: 'baja', min: 'min', max: 'max' }[a.como || a.arg] || 'sube';
      return accionVolumen(como, true);
    }
    case 'linterna':
      return accionLinterna(/apag|off|quita/i.test(String(a.como || a.arg || '')) ? 'off' : 'on', true);
    case 'abrir':
      if (!texto) return false;
      return accionAbrir(texto.toLowerCase(), true);
    case 'musica': {
      const como = String(a.como || a.arg || 'parar').toLowerCase();
      const metodo = /para|stop/.test(como) ? 'musicaParar'
        : /siguiente|next/.test(como) ? 'musicaSiguiente'
        : /pausa/.test(como) ? 'musicaPausa'
        : /seguir|play|continua/.test(como) ? 'musicaPlay' : '';
      if (!metodo || !puede(metodo)) return false;
      llama(metodo);
      ctx?.term?.('la regla movió la música: ' + como, 'autos');
      return true;
    }
    case 'piensa':
      return texto ? preguntaMente(texto, true) : false;
    case 'recuerdo':
      return texto ? guardaRecuerdo(texto, true) : false;
    case 'alarma': {
      const hora = /^\d{1,2}:\d{2}$/.test(texto) ? texto : '';
      if (!hora) return false;
      return accionAlarma(hora, 'de tu automatización', true);
    }
    default:
      return false;
  }
}

/* El motor, una sola vez por carga de la página. `almacen` no se pasa: usa el
   `localStorage` del WebView, que es donde ya guarda CORT sus otras cosas, y si el
   aparato no lo deja escribir el motor lo dice en vez de callarse. */
const autos = creaMotor({
  ejecuta: ejecutaAccion,
  term: (t, c) => { ctx?.term?.(t, c || 'autos'); salida(t, 'autos'); },
});

/* El reloj sólo se enciende si hay una regla de hora o de batería: sin ella, cero
   temporizadores. Un latido cada 30 s, que es lo que tarda en notarse un «a las 7:30»
   y no martillea el `aparato()` de un teléfono modesto. */
let latido = null;
function revisaReloj() {
  const quiere = necesitaReloj(autos.crudas());
  if (quiere && !latido) {
    latido = marcapasos({ motor: autos, aparato: aparatoRapido, cadaMs: 30000 }).arranca();
  } else if (!quiere && latido) {
    latido.para(); latido = null;
  }
}

/* La batería se lee con lo que ya hay: `aparato()` cuesta un `Intent` pegajoso y no
   pide permiso. Se guarda el último número para no llamar al puente dos veces. */
let aparatoUltimo = null;
function aparatoRapido() {
  const r = puede('aparato') ? parsea(llama('aparato'), ctx) : null;
  if (r && typeof r === 'object') { aparatoUltimo = r; return r; }
  return aparatoUltimo;
}

/* Qué se muestra en el formulario según el disparador o la acción elegidos: los
   `<select>` con `opciones` sustituyen al campo de texto, para que no haya forma de
   escribir un estado que el motor no reconoce. */
function rellena(disparador, accion) {
  const d = DISPARADORES.find(x => x.id === disparador) || DISPARADORES[0];
  const a = ACCIONES.find(x => x.id === accion) || ACCIONES[0];
  const texto = el('eq-aut-texto'), op = el('eq-aut-op'), de = el('eq-aut-de');
  if (texto) {
    texto.style.display = d.campo === 'texto' || d.campo === 'hora' ? '' : 'none';
    texto.placeholder = d.tipo === 'hora' || d.campo === 'hora' ? '07:30'
      : (d.pista || 'la palabra');
  }
  if (op) {
    const hay = !!(d.opciones && d.opciones.length);
    op.style.display = hay ? '' : 'none';
    if (hay) op.innerHTML = d.opciones.map(o => `<option value="${esc(o)}">${esc(o)}</option>`).join('');
  }
  if (de) de.style.display = d.id === 'aviso' ? '' : 'none';
  const arg = el('eq-aut-arg'), opa = el('eq-aut-opa');
  if (arg) {
    arg.style.display = a.opciones && a.opciones.length ? 'none' : '';
    arg.placeholder = a.pista || (a.campo === 'hora' ? '07:30' : 'el texto');
  }
  if (opa) {
    const hay = !!(a.opciones && a.opciones.length);
    opa.style.display = hay ? '' : 'none';
    if (hay) opa.innerHTML = a.opciones.map(o => `<option value="${esc(o)}">${esc(o)}</option>`).join('');
  }
}

function leeFormulario() {
  const d = (el('eq-aut-disp') || {}).value || 'frase';
  const a = (el('eq-aut-acc') || {}).value || 'habla';
  const definicion = DISPARADORES.find(x => x.id === d) || {};
  const accion = ACCIONES.find(x => x.id === a) || {};
  const disparador = { tipo: d };
  if (definicion.opciones && definicion.opciones.length) disparador.estado = el('eq-aut-op').value;
  if (d === 'hora') {
    const hora = ((el('eq-aut-texto') || {}).value || '').trim();
    if (!/^\d{1,2}:\d{2}$/.test(hora)) { avisa('autos', 'la hora va en formato 07:30'); return null; }
    disparador.hora = hora.length === 4 ? '0' + hora : hora;
  } else if (d === 'cargador' && disparador.estado === 'baje de') {
    const hasta = Number(((el('eq-aut-texto') || {}).value || '').replace('%', ''));
    if (!Number.isFinite(hasta)) { avisa('autos', 'dime un porcentaje: «baje de 20»'); return null; }
    disparador.hasta = hasta;
  } else if (definicion.campo === 'texto') {
    disparador.texto = ((el('eq-aut-texto') || {}).value || '').trim();
  }
  if (d === 'aviso') disparador.de = ((el('eq-aut-de') || {}).value || '').trim();
  if (d === 'frase' && !disparador.texto) { avisa('autos', 'dime la frase que la dispara'); return null; }
  if (d === 'aviso' && !disparador.texto && !disparador.de) {
    avisa('autos', 'una regla de avisos necesita al menos «de quién» o «qué dice»'); return null;
  }

  const hacen = [{ que: a }];
  if (accion.opciones &&accion.opciones.length) hacen[0].como = el('eq-aut-opa').value;
  else hacen[0].texto = ((el('eq-aut-arg') || {}).value || '').trim();
  if (a === 'abrir') hacen[0].app = hacen[0].texto;
  if (a === 'alarma') hacen[0].hora = hacen[0].texto;
  if (!hacen[0].como && !hacen[0].texto) { avisa('autos', 'la acción necesita un dato'); return null; }
  return { nombre: ((el('eq-aut-nombre') || {}).value || '').trim(), disparador, hacen };
}

function enganchaAutos() {
  const disp = el('eq-aut-disp'), acc = el('eq-aut-acc');
  if (!disp || !acc) return;
  disp.innerHTML = DISPARADORES.map(d => `<option value="${esc(d.id)}">${esc(d.nombre)}</option>`).join('');
  acc.innerHTML = ACCIONES.map(a => `<option value="${esc(a.id)}">${esc(a.nombre)}</option>`).join('');
  disp.onchange = () => rellena(disp.value, acc.value);
  acc.onchange = () => rellena(disp.value, acc.value);
  rellena('frase', 'habla');

  el('eq-aut-nueva').onclick = () => {
    const r = leeFormulario();
    if (!r) return;
    const nueva = autos.agrega(r);
    diceBien('autos', 'apuntada: ' + nueva.nombre + ' — ' + nueva.cuando + ' → ' + nueva.hacen.join(' + '));
    ['eq-aut-nombre', 'eq-aut-texto', 'eq-aut-arg', 'eq-aut-de'].forEach(id => {
      const c = el(id); if (c) c.value = '';
    });
    pintaAutos();
    ctx?.say?.('Regla apuntada.');
  };
  el('eq-aut-planta').onclick = () => {
    autos.vacia();
    preajustes().forEach(r => autos.agrega(r));
    diceBien('autos', 'las tres de muestra puestas. Enciende la que quieras.');
    pintaAutos();
  };
  el('eq-aut-borra').onclick = () => {
    autos.vacia(); pintaAutos();
    diceBien('autos', 'borradas todas. La hoja queda limpia.');
  };
  pintaAutos();
}

function pintaAutos() {
  const cajaLista = el('eq-aut-lista');
  const lista = autos.lista();
  linea('autos', lista.length
    ? lista.length + ' regla(s) · ' + lista.filter(r => r.activo).length + ' encendidas'
      + (autos.guardadas() ? '' : ' (este teléfono no deja guardarlas: se pierden al cerrar)')
    : 'sin reglas todavía. «cuando diga modo noche, calla la música» — o las tres de muestra.');
  if (!cajaLista) return;
  cajaLista.innerHTML = lista.map(r => `
    <div class="eq-mod${r.activo ? '' : ' apagada'}" data-regla="${esc(r.id)}">
      <div class="eq-mod-n">
        <b>${esc(r.nombre)}</b>
        <span>${esc(r.cuando)}</span>
        <span class="eq-mod-t">${r.hacen.map(esc).join(' + ')}</span>
      </div>
      <div class="eq-mod-b">
        <button data-aut-pon="${esc(r.id)}" title="encender/apagar">${r.activo ? '●' : '○'}</button>
        <button data-aut-ya="${esc(r.id)}" title="probar ahora">▶</button>
        <button data-aut-fu="${esc(r.id)}" title="borrar">✕</button>
      </div>
      <div class="eq-mod-d">${r.veces ? 'sonó ' + r.veces + ' vez' + (r.veces > 1 ? 'es' : '') : 'sin sonar aún'}</div>
    </div>`).join('');
  cajaLista.querySelectorAll('[data-aut-pon]').forEach(b => {
    b.onclick = () => {
      const r = autos.lista().find(x => x.id === b.dataset.autPon);
      autos.cambia(b.dataset.autPon, !(r && r.activo));
      revisaReloj(); pintaAutos();
    };
  });
  cajaLista.querySelectorAll('[data-aut-ya]').forEach(b => {
    b.onclick = () => {
      // Probar es disparar la regla con una señal que la cumpla a la fuerza: así se
      // ve si SUS manos llegan, sin esperar a que suene el aviso de verdad.
      const r = autos.crudas().find(x => x.id === b.dataset.autYa);
      if (!r) return;
      diceBien('autos', 'probando «' + (r.nombre || r.id) + '»…');
      (r.hacen || []).forEach(a => {
        Promise.resolve(ejecutaAccion(a.que, a)).then(ok => {
          if (!ok) avisa('autos', '«' + a.que + '» no pudo hacerse en este APK.');
        });
      });
    };
  });
  cajaLista.querySelectorAll('[data-aut-fu]').forEach(b => {
    b.onclick = () => { autos.quita(b.dataset.autFu); revisaReloj(); pintaAutos(); };
  });
  revisaReloj();
}

/* «cuando diga modo noche haz callar la música» — la regla escrita de una frase.
   Sólo se atiende con la palabra `automatiza`/`regla`/`cuando … haz` claras, para no
   llevarse por delante un «cuando llueva avísame» que era una pregunta normal. */
function reglaDeVoz(texto, b) {
  const par = String(texto).match(/cuando\s+(.+?)\s+(?:haz|entonces|que|y)\s+(.+)/i);
  if (!par) return false;
  const condicion = par[1].replace(/^(diga|dice|diga|escriba|llegue|suene|pase)\b/i, '').trim();
  const obra = normaliza(par[2]);
  const hace = (() => {
    if (/volumen|sonido/.test(obra)) {
      const como = /call|silenc/.test(obra) ? 'callar' : /max|tope/.test(obra) ? 'máximo'
        : /baj|suave/.test(obra) ? 'bajar' : /sub|fuerte/.test(obra) ? 'subir' : 'mínimo';
      return { que: 'volumen', como };
    }
    if (/linterna|antorcha|luz/.test(obra)) return { que: 'linterna', como: /apag|quita/.test(obra) ? 'apagar' : 'encender' };
    if (/musica|cancion|reproduc/.test(obra)) {
      return { que: 'musica', como: /siguiente/.test(obra) ? 'siguiente'
        : /pausa/.test(obra) ? 'pausa' : /seguir|play/.test(obra) ? 'seguir' : 'parar' };
    }
    if (/abre|abrir/.test(obra)) {
      const app = obra.replace(/^abre\s+(?:la\s+|el\s+|una\s+)?/, '').replace(/\b(app|la app|el app)\b/g, '').trim();
      if (!app) return null;
      return { que: 'abrir', app, texto: app };
    }
    if (/recuerd|apunta|anota/.test(obra)) {
      return { que: 'recuerdo', texto: par[2].replace(/^\s*(?:apunta|anota|recuerda)\s*(?:que|de)?\s*/i, '').trim() };
    }
    if (/di|avisa|habla|dile/.test(obra)) {
      return { que: 'habla', texto: par[2].replace(/^\s*(?:di|dile|avisa(?:me)?|habla)\s*(?:que|me)?[:\s]*/i, '').trim() };
    }
    return { que: 'piensa', texto: par[2] };
  })();
  if (!hace) return di('No entendí qué hacer. Prueba: «automatiza cuando diga modo noche haz callar la música».', 'autos');
  const tipo = /aviso|mensaje|llegue/.test(normaliza(condicion)) ? 'aviso' : 'frase';
  const disparador = tipo === 'aviso'
    ? { tipo, texto: condicion.replace(/^(de|cuando|llegue|un)\b/ig, ' ').trim() }
    : { tipo: 'frase', texto: condicion };
  const nombre = ((texto.match(/llamad[oa]\s+["']?([^"'”]{2,30})/i) || [])[1] || '').trim();
  const r = autos.agrega({ nombre: nombre || condicion.slice(0, 28), disparador, hacen: [hace] });
  pintaAutos();
  abre('autos');
  return di('Regla apuntada: cuando ' + r.cuando.replace(/^cuando\s+/i, '') + ' → ' + r.hacen.join(' + ') + '.', 'autos');
}

export /* F14 · «nada ejecutado sin quien lo pida»: cada `accion` de la tabla tiene UNA
   boca, y aquí se nombran las tres. Las de aparato van a `Acciones.java` por
   `envia('accion')`; la música va a la tecla del sistema (`teclaMedia`, que llega
   al reproductor que sea) y, si el APK no la trae, al reproductor propio; y
   `saludo`, `llamar`, `avisos`, `juego` y `memoria` ya se atienden ANTES de
   llegar al cerebro (la cara intercepta esas frases). Antes se mandaba todo a
   `Acciones`: después de «Hola, te escucho.» salía «todavía no sé hacer saludo».
   La costura [29] comprueba que estos dos conjuntos y los `case` de
   `Acciones.java` cubran el vocabulario entero, sin sobras ni huecos. */
const ACCION_DE_APARATO = new Set(['volumen', 'linterna', 'alarma', 'temporizador',
  'cronometro', 'estado', 'lanzadores', 'abrir', 'poner', 'buscar']);
const ACCION_DE_CARA = new Set(['saludo', 'llamar', 'avisos', 'juego', 'memoria']);
function ejecutaLocal(accion, param) {
  if (ACCION_DE_APARATO.has(accion)) {
    return envia('accion', { que: accion, args: param }, 'mando',
      'sé lo que querías hacer, pero este APK no manda sobre el aparato.');
  }
  if (accion === 'musica') {
    // F15 · la tabla también puede pedir música por NOMBRE, listas y ecualizador:
    // el cerebro devuelve `musica` con `poner:X`, `lista:X`, `listas`,
    // `ecualiza:X` o `ecualizaestado`. Aquí se ejecuta con las manos de verdad.
    const dos = String(param).split(':');
    const verbo = dos[0].trim();
    const nombre = dos.slice(1).join(':').trim();
    if (verbo === 'poner' && nombre) return parsea(llama('musicaPonerNombre', nombre));
    if (verbo === 'lista' && nombre) {
      const puesta = llama('musicaPonerLista', nombre, 0);
      return puesta ? { ok: true, dice: 'Pongo la lista «' + nombre + '».' }
        : { ok: false, dice: 'No encuentro la lista «' + nombre + '» con canciones.' };
    }
    if (verbo === 'listas') {
      const listas = parsea(llama('musicaListas')) || [];
      return { ok: true, dice: listas.length
        ? 'Tus playlists: ' + listas.join(', ') + '.'
        : 'No tienes playlists guardadas en el teléfono.' };
    }
    if (verbo === 'ecualiza' && nombre) return parsea(llama('ecualiza', nombre));
    if (verbo === 'ecualizaestado') return parsea(llama('ecualizaEstado'));
    const tecla = { pausa: 'pausa', reanuda: 'play', siguiente: 'siguiente',
                    anterior: 'anterior' }[param];
    if (tecla && puede('teclaMedia') && llama('teclaMedia', tecla) !== false) return true;
    const propio = { pausa: 'musicaPausa', reanuda: 'musicaPlay',
                     siguiente: 'musicaSiguiente', anterior: 'musicaAnterior' }[param];
    if (propio && puede(propio)) { llama(propio); return true; }
    // `mueve` no dice hacia dónde: no se inventa un salto.
    return null;
  }
  return ACCION_DE_CARA.has(accion) ? true : null;
}

/* ─────────────────────────── la pantalla del despertador ──────────────────
   F16. Vive en el `body`, fuera de las hojas, porque a las siete de la mañana la
   dueña no tiene por qué estar en el Equipo: el despertador es lo que hay que
   ver, con la hora grande y dos botones —detener y cinco minutos—. No se cierra
   sola: una alarma que se va sin que nadie la oiga es peor que ninguna. */
function pintaAlarma(ev) {
  let caja = document.getElementById('cort-alarma-pantalla');
  if (!caja) {
    caja = document.createElement('div');
    caja.id = 'cort-alarma-pantalla';
    caja.setAttribute('role', 'dialog');
    caja.setAttribute('aria-label', 'despertador de CORT');
    caja.innerHTML = `
      <div class="ca-sello">despertador de CORT</div>
      <div class="ca-hora" id="ca-hora">—</div>
      <div class="ca-nota" id="ca-nota"></div>
      <div class="ca-rutina" id="ca-rutina"></div>
      <div class="ca-botones">
        <button type="button" id="ca-detener">detener</button>
        <button type="button" id="ca-posponer">5 minutos</button>
      </div>`;
    document.body.appendChild(caja);
    caja.querySelector('#ca-detener').onclick = () => {
      const r = puede('alarmaDetener') ? parsea(llama('alarmaDetener'), ctx) : null;
      cierraAlarma();
      ctx?.say?.(r?.dice || 'Despertador detenido.');
    };
    caja.querySelector('#ca-posponer').onclick = () => {
      const r = puede('alarmaPosponer') ? parsea(llama('alarmaPosponer'), ctx) : null;
      cierraAlarma();
      ctx?.say?.(r?.dice || 'Te despierto en cinco minutos.');
    };
  }
  caja.querySelector('#ca-hora').textContent = ev.hora || '—';
  const cosas = [];
  if (ev.nota) cosas.push(ev.nota);
  if (ev.titulo) cosas.push('canción: «' + ev.titulo + '»' + (ev.artista ? ' de ' + ev.artista : ''));
  caja.querySelector('#ca-nota').textContent = cosas.join(' · ') || 'Buenos días.';
  const rutina = caja.querySelector('#ca-rutina');
  rutina.textContent = ev.rutina ? (ev.dice || 'rutina de la mañana') : '';
  caja.classList.add('viva');
  ctx?.term?.('despertador · ' + (ev.hora || '—') + (ev.nota ? ' · ' + ev.nota : ''), 'mando');
  ctx?.orb?.burst?.();
}

function cierraAlarma() {
  const caja = document.getElementById('cort-alarma-pantalla');
  if (caja) caja.classList.remove('viva');
}

function handleTelefonoEvento(ev) {
  if (!ev || typeof ev.type !== 'string') return false;

  /* F16 · el despertador. Va lo primero: si suena a las 7, lo que importa es
     verlo y poder callarlo, no una regla de automatización. La pantalla no vive
     dentro de la hoja del Equipo —la dueña puede tener abierta otra—: se pega al
     `body` y se pinta con lo que Java mandó. */
  if (ev.type === 'alarma') { pintaAlarma(ev); return true; }

  /* Las automatizaciones se alimentan de los eventos EN CUANTO llegan, antes de que
     la hoja los interprete para pintar. `aviso` es nuevo en la 2.4 (Java lo manda
     desde `.Avisos`); el del auricular ya existía. Ninguno de los dos interrumpe lo
     de siempre: si ninguna regla sonó, el evento sigue su camino. */
  if (ev.type === 'aviso') {
    const sonaron = autos.dispara({ tipo: 'aviso', de: ev.de || '', dice: ev.dice || '' });
    if (montada) pintaAutos();
    if (sonaron.length) return true;
    // Sin regla que lo quiera, el aviso se cuenta igual que antes: en la consola.
    ctx?.term?.('aviso de ' + (ev.de || 'quién sabe') + ': ' + String(ev.dice || '').slice(0, 70), 'equipo');
    return false;
  }
  if (ev.type === 'auricular') {
    autos.dispara({ tipo: 'auricular', escuchando: !!ev.escuchando });
    if (montada) pintaAutos();
  }

  if (ev.type === 'mente') {
    // Los cuadros de Ollama usan el mismo evento que las respuestas, pero no son
    // una respuesta: son la lista, el progreso de una descarga o un aviso del PC.
    if (ev.de === 'ollama') return manejaOllama(ev);
    estado.ultimaMente = ev;
    if (montada) { pintaUltimaMente(); const d = el('eq-men-dice'); if (d) d.textContent = ''; }
    const dicho = ev.ok === false
      ? (ev.dice || 'El cerebro del teléfono no supo contestar.')
      : (ev.responde || 'Ya pensé lo mío, pero no volvió texto.');
    // Java dice de dónde salió la respuesta (`nube` o `local`); si no lo dice,
    // no se inventa ni se queda el paréntesis a medias.
    const de = ev.de === 'local' || ev.de === 'nube' ? ' (' + ev.de + ')' : '';
    salida('respuesta del cerebro' + de + ': ' + String(dicho).slice(0, 600));
    if (preguntaVoz) { preguntaVoz = false; ctx?.say?.(String(dicho).slice(0, 400)); ctx?.orb?.burst?.(); }
    // Y si la respuesta local TRAÍA una acción, se hace. `Mente.local()` nombra la
    // cosa (`{"de":"local","accion":"volumen","param":"sube"}`) y **no la ejecuta**:
    // quien la ejecuta es `Acciones`, desde la cara. Sin este reenvío, «sube el
    // volumen» sin PC contestaba «vale» y no subía nada.
    if (ev.de === 'local' && typeof ev.accion === 'string' && ev.accion) {
      const hecha = ejecutaLocal(ev.accion, ev.param || '');
      if (hecha) {
        ctx?.term?.('acción del cerebro local: ' + ev.accion, 'equipo');
        /* F14 · `estado` y `lanzadores` devuelven datos, no sólo `ok`. Antes la
           frase se decía y el número se quedaba dentro del JSON: la dueña oía
           «miro cómo va» y no veía nada. Aquí se cuenta lo que volvió, medido, y
           el cronómetro dice su propia limitación. */
        if (ev.accion === 'estado') {
          const partes = [];
          if (typeof hecha.volumen === 'number') {
            partes.push('volumen ' + hecha.volumen + ' de ' + (hecha.max ?? '—'));
          }
          if (hecha.red) partes.push('red ' + hecha.red);
          partes.push('linterna ' + (hecha.linterna ? 'encendida' : 'apagada'));
          partes.push(hecha.sinMiedo ? 'sin permisos pendientes'
            : 'faltan permisos' + (Array.isArray(hecha.faltan) && hecha.faltan.length
              ? ': ' + hecha.faltan.join(', ') : ''));
          const frase = 'El teléfono: ' + partes.join(' · ') + '.';
          diceBien('mando', frase); ctx?.say?.(frase);
        } else if (ev.accion === 'lanzadores') {
          const apps = Array.isArray(hecha.apps) ? hecha.apps : [];
          const nombres = apps.slice(0, 8).map(x => x.nombre).filter(Boolean);
          const frase = 'Veo ' + (hecha.total ?? apps.length) + ' apps'
            + (nombres.length ? ': ' + nombres.join(', ') + (apps.length > nombres.length ? '…' : '') : '')
            + '.';
          diceBien('mando', frase); ctx?.say?.(frase);
        } else if (ev.accion === 'cronometro' && hecha.dice) {
          diceBien('mando', hecha.dice); ctx?.say?.(hecha.dice);
        } else if (ev.accion === 'musica' && hecha.dice) {
          // F15 · el nombre de la canción, la lista o el preset que de verdad se
          // puso, y su motivo si no se pudo: la frase sale del aparato, no de aquí.
          diceBien('mando', hecha.dice); ctx?.say?.(hecha.dice);
        }
      }
    }
    return true;
  }
  if (ev.type === 'memoria') {
    estado.ultimaMemoria = ev;
    if (ev.ok === false) avisa('mem', ev.dice || 'no pude cuadrar con el portátil.');
    else {
      diceBien('mem', 'Cuadrado con el portátil: ' + (ev.subidos ?? 0) + ' subidos, '
        + (ev.bajados ?? 0) + ' bajados.');
      if (preguntaVoz) { preguntaVoz = false; ctx?.say?.('Cuadrado con tu portátil: '
        + (ev.subidos ?? 0) + ' subieron y ' + (ev.bajados ?? 0) + ' bajaron.'); }
    }
    pintaMemoria();
    return true;
  }
  if (ev.type === 'accion') {
    // Java avisa de lo que hizo (o no hizo) por su cuenta: alarma, linterna,
    // volumen desde el auricular. Se cuenta tal cual y se vuelve a leer el estado.
    const dicho = ev.dice || ev.resumen
      || (ev.ok === false ? 'El teléfono no dejó hacer esa cosa.' : 'El teléfono hizo una cosa que no me contó.');
    avisa('mando', dicho);
    ctx?.term?.('aviso de acción: ' + String(dicho).slice(0, 60), 'equipo');
    pintaMando();
    return true;
  }
  if (ev.type === 'motor') {
    // La fase del oído propio. Se guarda SIEMPRE, con la hoja montada o no: si
    // CORT está copiando los 60 MB del modelo y ella abre Equipo dos minutos
    // después, lo que tiene que ver es en qué punto está, no «preguntando…».
    estado.ultimoMotor = ev;
    if (montada) pintaOido(ev);
    if (ev.oido) ctx?.term?.('oído sin nube: ' + ev.oido
      + (ev.motivo ? ' — ' + String(ev.motivo).slice(0, 60) : ''), 'equipo');
    return true;
  }
  return false;
}

/* El estado resumido, para `hud.js` y para la consola: una foto, no una llamada. */
export function estadoTelefono() {
  return {
    enTelefono: enTelefono(), montada,
    puente: { accion: puede('accion'), voz: puede('ajusteVoz'), memoria: puede('memoria'),
      mente: puede('mente'), atuendo: puede('atuendo'), burbuja: puede('burbuja') },
    voces: estado.voces.length, vozActual: estado.vozActual,
    nivel: estado.nivel, max: estado.max, linterna: estado.linterna,
    proveedor: estado.mente.proveedor, modelo: estado.mente.modelo,
    clavePuesta: estado.mente.clavePuesta, conRed: estado.mente.conRed,
    recuerdos: estado.hechos, conPortatil: estado.conPortatil, direccion: estado.direccion,
    atuendos: estado.atuendos.length, puesto: estado.puesto, burbuja: estado.burbuja,
    reglas: autos.total(), reglasVivas: autos.lista().filter(r => r.activo).length,
  };
}

/* ─────────────────────────── la voz de la dueña ─────────────────────────── */

/* «sube el volumen», «linterna», «pon una alarma a las 7:30», «abre whatsapp»,
   «busca recetas», «qué sabes de mí», «acuédate de…», «voz de siri»,
   «ponte azul», «burbuja», «piensa…», «sincroniza con el pc».
   Devuelve `true` si la frase era suya (y ya la mandó o ya la contestó). */
export function telefonoPorVoz(texto) {
  if (!enTelefono()) return false;            // en PC: nada de esto, la frase sigue al núcleo
  const b = normaliza(texto);
  if (!b) return false;

  /* −1 · LAS REGLAS DE ELLA, antes que la boca de CORT. Si apuntó «modo noche», lo
         que tiene que pasar es LO SUYO, no lo que la cara siempre entiende por esa
         frase. Por eso va en el sitio −1, por encima del oído, el volumen y todo lo
         demás. Con la palabra `cuando … haz` delante, la frase además CREA la regla. */
  if (/\b(automatiza|automatizaciones|regla|reglas)\b/.test(b) && /\bcuando\b/.test(b)
      && /\b(haz|entonces)\b/.test(b)) {
    const creada = reglaDeVoz(texto, b);
    if (creada) return true;
  }
  // `automatiz` con sufijo: «mis automatizaciones» y «apaga la automatización de la
  // mañana» también entran por aquí. Se usa la raíz sin tilde porque `normaliza`
  // ya se la quitó.
  if (/automatiz|\breglas\b/.test(b) && !/\bcuando\b/.test(b)) {
    abre('autos'); pintaAutos();
    const n = autos.total();
    return di(n ? 'Tienes ' + n + ' regla(s): ' + autos.lista().map(r => r.nombre).join(', ')
                + '. Se cumplen mientras CORT esté en pantalla.'
                : 'Aún no hay reglas. Dime «automatiza cuando diga modo noche haz callar la música».', 'autos');
  }
  const disparadas = autos.dispara({ tipo: 'frase', texto });
  if (disparadas.length) {
    if (montada) { abre('autos'); pintaAutos(); }
    ctx?.orb?.burst?.();
    return true;
  }

  /* 0 · el oído sin nube: «activa el oído sin internet», «¿me oyes sin wifi?»,
         «quita el oído offline». Se contesta con la fase REAL que Java ha mandado,
         nunca con lo que la cara supone. */
  if (/\boido\b/.test(b) && /\b(internet|nube|offline|wifi|datos)\b/.test(b)) {
    return accionOido(b);
  }
  if (/\b(escucha|oye|oyeme)\b/.test(b) && /\bsin (internet|wifi|datos|nube)\b/.test(b)) {
    return accionOido(b);
  }

  /* 1 · volumen — sólo con la palabra «volumen/sonido» delante, para no pisar a
        «baja la persiana», que es de otro mundo. */
  if (/\b(volumen|sonido)\b/.test(b)) {
    const como = /\b(max|maximo|tope|full)\b/.test(b) ? 'max'
      : /\b(min|minimo|bajito)\b/.test(b) ? 'min'
      : /\b(callar|calla|callate|muted)\b/.test(b) ? 'callar'
      : /\b(sube|subir|subid|mas fuerte|mas alto)\b/.test(b) ? 'sube'
      : /\b(baja|bajar|bajad|suave|menos)\b/.test(b) ? 'baja' : '';
    if (como) return accionVolumen(como, true);
  }

  /* 2 · linterna */
  if (/\b(linterna|antorcha)\b/.test(b) || /\bluz del telefono\b/.test(b)) {
    const como = /\b(enciende|prende|prender|on|prendida)\b/.test(b) ? 'on'
      : /\b(apaga|apagar|off|quita|cesa|apagada)\b/.test(b) ? 'off' : 'alterna';
    return accionLinterna(como, true);
  }

  /* 3 · alarma con hora, canción y nota */
  if (/\b(alarma|despertador|despiertame|despierta)\b/.test(b)) {
    const hora = sacaHora(texto);
    if (!hora) return di('Dime la hora: «pon una alarma a las 7:30».', 'mando');
    /* F16 · la canción va detrás de «con» y la nota detrás de «para». Se saca
       primero la canción y se quita del texto: así «noche de synth» no pierde su
       «de synth» como si fuera una nota. */
    const cancion = sacaCancion(texto);
    const sinCancion = cancion ? String(texto).replace(cancion, ' ') : texto;
    const nota = sacaNota(sinCancion);
    const rutina = /\b(rutina|buenos dias)\b/.test(b);
    return accionAlarma(hora, nota, true, cancion, rutina);
  }

  /* 4 · temporizador */
  if (/\b(temporizador|cuenta atras|cuenta-regresiva|crono)\b/.test(b)) {
    const seg = sacaSegundos(b);
    if (!seg) return di('Dime cuánto cuenta: «temporizador de 10 minutos».', 'mando');
    return accionTemporizador(seg, true);
  }

  /* 4c · las apps instaladas. Va ANTES que la agenda porque «qué apps tengo»
        lleva «tengo», y la rama 12 se la llevaba a las citas. Es la intención
        `lanzadores` del diccionario, con su misma nube de chips. */
  if (/\b(apps|aplicaciones)\b/.test(b)
      && /^(que|dime|lista|muestra|muestrame|ensename|cuantas|mis)\b/.test(b)) {
    abre('mando');
    const hechas = misApps();
    if (hechas) ctx?.say?.('Te dejo la lista de apps en la hoja Equipo.');
    return hechas;
  }

  /* 4d · F15 · la música por NOMBRE, las listas y el ecualizador. Va antes que la
        agenda y que el cerebro porque aquí SÍ se puede hacer en el teléfono: se
        busca en su biblioteca (`musicaPonerNombre`, que decide con `Elige`) y sólo
        si no hay nada parecido la frase sigue su camino (el cerebro abre YouTube).
        Los transportes («pausa», «siguiente») NO entran aquí: los casa el oído y,
        si llegan al cerebro, `ejecutaLocal` los manda a `teclaMedia`. */
  if (puede('musicaPonerNombre')) {
    // 4d.1 · «qué playlists tengo», «mis listas»
    if (/\b(playlists|listas)\b/.test(b)
        && /^(que|dime|mis|listame|muestra|muestrame|cuantas)\b/.test(b)
        && !/\b(pon|ponme|reproduce|escucha|oir)\b/.test(b)) {
      const listas = parsea(llama('musicaListas'));
      const nombres = Array.isArray(listas) ? listas.filter(x => typeof x === 'string') : [];
      return di(nombres.length
        ? 'Tus playlists: ' + nombres.join(', ') + '.'
        : 'No tienes playlists guardadas. Guarda una desde Música con «guardar lista».', 'mando');
    }
    // 4d.2 · «pon la playlist para correr» / «ponme la lista X»
    const lista = texto.match(/^\s*(?:oye\s+cort[,\s]+)?(?:pon|ponme|reproduce|escucha|quiero oir)\s+(?:la\s+|mi\s+)?(?:playlist|lista)\s+(.+)$/i);
    if (lista) {
      const nombre = lista[1].trim();
      const puesta = llama('musicaPonerLista', nombre, 0);
      if (puesta) return di('Pongo la lista «' + nombre + '».', 'mando');
      return di('No encuentro la lista «' + nombre + '» con canciones. Dime «qué playlists tengo».', 'mando');
    }
    // 4d.3 · «qué ecualizador tengo» / «cómo suena el ecualizador»
    if (/\b(ecualizador|preset|ecualizacion)\b/.test(b)
        && /^(que|dime|como|en que|hay)\b/.test(b)) {
      const r = parsea(llama('ecualizaEstado'));
      return di(r && r.dice ? r.dice : 'El ecualizador se enciende con la música.', 'mando');
    }
    // 4d.4 · «pon el ecualizador en rock» / «cambia el sonido a clásica»
    const ec = texto.match(/^\s*(?:oye\s+cort[,\s]+)?(?:pon|cambia|ecualiza)\s+(?:el\s+)?(?:ecualizador|sonido|preset)\s+(?:(?:a|en|al)\s+)?(.+)$/i)
      || texto.match(/^\s*(?:oye\s+cort[,\s]+)?ecualiza\s+(?:a\s+)?(.+)$/i);
    if (ec) {
      const r = parsea(llama('ecualiza', ec[1].trim()));
      return di(r && r.dice ? r.dice : 'No pude cambiar el ecualizador.', 'mando');
    }
    // 4d.5 · «pon After Dark», «pon la canción a After Dark», «cámbialo a X»
    const cancion = texto.match(/^\s*(?:oye\s+cort[,\s]+)?(?:cambia|cambialo|cambiala|ponme|pon)\s+(?:la\s+|el\s+)?(?:cancion|tema|musica|video)\s+(?:a|al|por)\s+(.+)$/i)
      || texto.match(/^\s*(?:oye\s+cort[,\s]+)?cambia(?:lo|la)?\s+(?:a|al|por)\s+(.+)$/i)
      || texto.match(/^\s*(?:oye\s+cort[,\s]+)?(?:ponme|pon|reproduce|suena|escucha)\s+(?:(?:la|el)\s+(?:cancion|tema|musica|video)\s+)?(.+)$/i);
    if (cancion) {
      const pedida = cancion[1].trim();
      if (pedida && !/^(la |el |una |un )?(playlist|lista|alarma|temporizador|volumen|linterna|cronometro|modo juego|siguiente|anterior|musica|de |la de |otra vez|de nuevo)\b/.test(normaliza(pedida))) {
        const r = parsea(llama('musicaPonerNombre', pedida));
        if (r && r.ok) return di(r.dice || ('Pongo «' + pedida + '».'), 'mando');
        // «cámbialo a X» no cae a YouTube: estaba sonando algo y pidió cambiar.
        if (r && /^\s*cambia/i.test(texto)) return di(r.dice || ('No encuentro «' + pedida + '».'), 'mando');
        // «pon X» sin nada en la biblioteca sigue al cerebro (su `poner` abre YouTube).
      }
    }
  }

  /* 4b · los cerebros de casa (Ollama por Wi-Fi). Va ANTES que «abre una app» y
        que «busca …» a propósito: «busca en tu wifi» o «abre los modelos» sin este
        orden se los llevaban la app o el buscador. Sólo se atiende con palabras
        suyas (`cerebros`, `ollama`, `modelo(s)`), así que no pisa «muéstrame tu
        cerebro» (el muro de recuerdos) ni las frases normales. */
  if (/\b(ollama|modelo|modelos|cerebros|bajada)\b/.test(b)
      || (/\bwifi\b/.test(b) && /^(busca|buscar|buscame|localiza|encuentra)\b/.test(b))) {
    // El nombre del modelo se saca del TEXTO, no de `b`: lleva dos puntos, puntos y
    // a veces mayúsculas, y todo eso `normaliza()` lo estropea.
    const MODELO = (texto.match(/(?:modelo|cerebro)\s*(?:de|:)?\s*["']?([A-Za-z0-9._:@\/-]{2,42})/i) || [])[1]
      || (texto.match(/(?:descarga|baja|borra|usa|pon|elimina)\s+(?:el\s+|la\s+|un\s+)?["']?([A-Za-z0-9._:@\/-]{2,42})/i) || [])[1] || '';
    abre('men');
    // «cancela la bajada», «para la descarga»: lo pide ella porque la barra no se
    // mueve, así que la salida tiene que estar también en la voz, no sólo en el botón.
    if (/^(cancela|cancelar|para|para\s+la|alto|frena)\b/.test(b) && /\b(bajada|descarga|descargando)\b/.test(b)) {
      return ollamaOrden('cancela')
        ? di('Cortando la bajada' + (estado.ollama.bajando ? ' de ' + estado.ollama.bajando : '') + '.', 'oll')
        : false;
    }
    if (/^(busca|buscar|buscame|localiza|encuentra)\b/.test(b)) {
      return ollamaOrden('descubre') ? di('Mirando tu Wi-Fi a ver dónde está Ollama…') : false;
    }
    if (/^(usa|pon|ponme|cambia|cambiate|elige|usar)\b/.test(b)) {
      if (!MODELO) return di('Dime cuál: «usa el modelo qwen2.5:1.5b».', 'oll');
      return ollamaOrden('usa', { modelo: MODELO }) ? di('Voy a pensar con ' + MODELO + '.') : false;
    }
    if (/^(descarga|descargar|baja|bajar|instala|instalar|instalame|pull)\b/.test(b)) {
      if (!MODELO) return di('Dime el modelo: «descarga el modelo qwen2.5:0.5b».', 'oll');
      return ollamaOrden('descarga', { modelo: MODELO })
        ? di('Pidiéndoselo a tu PC: ' + MODELO + '. La barra se mueve en la hoja Equipo.') : false;
    }
    if (/^(borra|borrar|elimina|eliminar|quita|quitar)\b/.test(b)) {
      if (!MODELO) return di('Dime cuál borro: «borra el modelo llama3».', 'oll');
      return ollamaOrden('borra', { modelo: MODELO }) ? di('Borrándolo de tu PC.') : false;
    }
    // Sin verbo claro: «modelos», «muéstrame los modelos», «los cerebros».
    return ollamaOrden('lista') ? di('Mirando qué modelos hay en tu PC.') : false;
  }

  /* 5 · «abre whatsapp» y las demás. A propósito NO están `musica` ni
        `reproductor-mv`: ésas ya tienen su sitio en la hoja de Música y el
        reproductor, y se las dejo a ellos. */
  const app = sacaApp(b);
  if (app) return accionAbrir(app, true);

  /* 6 · «busca <texto>» (app o red) */
  if (/^(busca|buscar|buscame|googlea|investiga|encuentra)\b/.test(b)) {
    const limpio = texto.replace(/^\s*(?:busca(?:r|me)?|googlea|investiga|encuentra)\s*(?:en (?:la )?(?:red|internet|google)|de|el|la|los|las|un|una|por|a)?\b/ig, '').trim();
    if (!limpio) return di('Dime qué busco.', 'mando');
    if (/\b(app|aplicacion|programa)\b/.test(b) && !/\b(red|internet|google|web)\b/.test(b)) {
      return buscaApp(limpio.replace(/\b(?:la|el|una|un|de|app|aplicacion|que|tengo|mi)\b/ig, ' ').replace(/\s+/g, ' ').trim(), true);
    }
    return buscaEnRed(limpio, true);
  }

  /* 7 · memoria. Las tildes se quitan al RECONOCER (`b`), pero el texto que se le
        manda a Java es el suyo, con sus acentos: «mi hermano» no es lo mismo que
        «mí», y ahí es donde hay que mirar. «qué recuerdas» se queda fuera a
        propósito: eso ya abre la ventana 08 · Cerebro del PC en `hud.js`. */
  if (/^que sabes\b/.test(b)) {
    const tema = texto.replace(/^.*?qu[eé]\s+sabes\s*(?:de|sobre|acerca de)?\s*/i, ' ').trim();
    if (!tema || /^(mi|mim|yo|sobre mi|de mi)$/.test(normaliza(tema))) return quienSoy(true);
    return buscaRecuerdo(tema, true);
  }
  if (/^(acuedate|acuerdate|apuntame|apunta en la memoria|guarda en la memoria|recuerdame)\b/.test(b)
      && !/\b(agenda|calendario|cita|reunion|junta)\b/.test(b) && !sacaHora(texto)) {
    // «apúntame» es ambiguo a propósito: puede ser memoria («apúntame que Ana
    // cumple años») o agenda («apúntame la cena con Samuel a las nueve»). La
    // dueña lo distingue con una hora o con la palabra cita: si las trae, esto NO
    // es memoria y se deja caer al grupo 12, que es el del calendario.
    const limpio = texto.replace(/^\s*(?:acu[eé]r?date(?:\s+(?:de|que))?|ap[uú]ntame|apunta en la memoria|guarda en la memoria|recu[eé]rdame)\s*(?:que|de|lo que|:)?\s*/i, '').trim();
    if (!limpio) return di('Dime qué quiero que recuerde.', 'mem');
    return guardaRecuerdo(limpio, true);
  }
  if (/\b(sincroniza|sincronizar|sincronizate|cuadra|pasa los recuerdos)\b/.test(b)
      && /\b(pc|portatil|ordenador|memoria|recuerdos|con el pc)\b/.test(b)) {
    return sincroniza(true);
  }

  /* 8 · voz: «voz de siri», «cambia la voz», «qué voces hay». Se aceptan las dos
        palabras porque la dueña habla de la lista («voces»), no sólo de la suya. */
  if (/\b(voz|voces)\b/.test(b) || /\bcomo suenas?\b/.test(b)) {
    if (/\basistente\b/.test(b)) return false;        // ése ya lo atiende `ponAsistente()`
    const pre = PREAJUSTES.find(([k]) => new RegExp('\\b' + normaliza(k) + '\\b').test(b));
    if (pre) { abre('voz'); return preajuste(pre[0], true); }
    if (/^(que|cuantas) voces\b/.test(b) || /\b(cambia|cual|cuales|cuantas|lista|otras|pon|ponme|muestra)\b/.test(b)) {
      abre('voz');
      if (montada) pintaVoz();
      return di('Te enseño las voces que hay instaladas en la pantalla del Equipo. '
        + 'Dime «voz de siri», «voz mexicana» o la que tú quieras.');
    }
    if (/\bprobar|prueba\b/.test(b)) { abre('voz'); return pruebaVoz(true); }
  }

  /* 9 · atuendos: «ponte azul», «atuendo Cortana» */
  const COLOR = /\b(azul|verde|rojo|roja|morado|violeta|rosa|rosado|amarillo|dorado|ambar|naranja|gris|negro|blanco|turquesa|cian|magenta|fucsia|acero|noche|dia)\b/;
  if (/\b(atuendo|traje|vestuario)\b/.test(b) || (/\b(ponte|ponerte|vistete|cambia|camvia)\b/.test(b) && COLOR.test(b))) {
    const nombre = (/\b(?:atuendo|traje)\s+(?:de |del |: )?([a-záéíóúñ ]{2,24})/i.exec(texto) || [])[1]
      || (COLOR.exec(normaliza(texto)) || [])[1] || '';
    if (!nombre) return di('Dime el traje: «ponte azul» o «atuendo Cortana».', 'atu');
    abre('atu');
    return ponAtuendo(nombre, true);
  }

  /* 10 · burbuja */
  if (/\bburbuja\b/.test(b)) {
    const on = !/\b(quita|quitar|apaga|apagar|cesa|fuera|off|esconde)\b/.test(b);
    return ponBurbuja(on, true);
  }

  /* 11 · «piensa <pregunta>»: el cerebro del teléfono, sin el portátil */
  if (/^(piensa|piensalo|piensa en|medita|reflexiona|contesta|responde)\b/.test(b)) {
    const pregunta = texto.replace(/^\s*(?:piensa(?:r?|lo)?|piensa en|medita|reflexiona|contesta|responde)\s*(?:que|lo que|sobre|de|:)?\s*/i, '').trim();
    if (!pregunta) return di('Dime la pregunta: «piensa por qué está lloviendo».', 'men');
    abre('men');
    return preguntaMente(pregunta, true);
  }

  /* 12 · agenda y correo: «¿qué tengo hoy?», «mi agenda», «las citas de la
        semana», «revisa el correo», «apunta cena con Samuel a las nueve». Se abre
        la hoja para que la dueña vea la lista, y la cita se rellena en el
        calendario del sistema —no se escribe a escondidas—.
        El correo se mira ANTES: «qué hay en el correo» también casa con el «qué
        hay» de la agenda, y contestarle con las citas sería cambiarle la pregunta. */
  if (/\b(correo|gmail|mail)\b/.test(b)
      && /\b(revisa|mirar|mira|que|hay|llegado|llego|leer|lee|abre|abrir)\b/.test(b)) {
    abre('ago');
    return correo(true);
  }
  if (/\b(agenda|citas|cita|calendario)\b/.test(b)
      || (/^(que|qué)\b/.test(b) && /\b(tengo|hay|viene|espera)\b/.test(b))) {
    if (/\b(apunta|anota|guarda|mete|agrega|anade|add)\b/.test(b)) {
      const limpio = texto.replace(/^\s*(?:apunta|anota|guarda|agrega|mete|añade|anádeme)\s*(?:en (?:la |el )?(?:agenda|calendario)|una?|el|la|que|:)?\s*/i, '').trim();
      return apunta(limpio, sacaHora(texto), true);
    }
    abre('ago');
    if (/\b(semana|proximos|proximo|dias|vendidero|despues)\b/.test(b)) {
      return miraAgenda({ que: 'proximos', dias: 7 }, true);
    }
    if (/\b(calendario|abrir|abre)\b/.test(b)) return miraAgenda({ que: 'abrir' }, true);
    return miraAgenda({ que: 'hoy' }, true);
  }

  return false;
}

/* ── las palabras hechas números ── */

/* «a las 7:30», «a las 7 y media», «a las 7», «7 y cuarto», y la tarde/noche
   suman 12 horas porque la dueña dice «a las 7 de la tarde» y espera un despertador
   de después de cenar, no de antes de desayunar. */
function sacaHora(texto) {
  const b = normaliza(texto);
  let h = null, m = null;
  const dos = /(\d{1,2})\s*[:.]\s*(\d{2})/.exec(String(texto));
  if (dos) { h = +dos[1]; m = +dos[2]; }
  const media = /\b(\d{1,2})\s+y\s+media\b/.exec(b);
  const cuarto = /\b(\d{1,2})\s+y\s+(?:un\s+)?cuarto\b/.exec(b);
  if (h === null && media) { h = +media[1]; m = 30; }
  else if (h === null && cuarto) { h = +cuarto[1]; m = 15; }
  else if (h === null) {
    const suelta = /\b(?:a\s+las|las|a\s+la)\s+(\d{1,2})\b/.exec(b);
    if (suelta) { h = +suelta[1]; m = 0; }
  }
  if (h === null) return '';
  if (/\b(tarde|noche|pm)\b/.test(b) && h < 12) h += 12;
  if (/\b(madrugada|manana|am)\b/.test(b) && h === 12) h = 0;
  if (h > 23 || m > 59) return '';
  return String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0');
}

/* La etiqueta del despertador: «para el tren», «de la reunión», «y avísame del bus». */
function sacaNota(texto) {
  const m = /\b(?:para|de|por|sobre)\s+([a-záéíóúñ ,._0-9]{3,40})$/i.exec(String(texto).trim());
  return m ? m[1].replace(/[.:;]\s*$/, '').trim() : '';
}

/* F16 · la canción del despertar: «a las 7 con after dark para el examen» →
   «after dark». Se corta en «para»/«que dice» (eso ya es la nota) y se quita el
   relleno «la canción»/«la música». Sin nombre no se inventa una. */
function sacaCancion(texto) {
  const m = /\b(?:con|y suena|y pon|y ponme)\s+(.+?)(?=\s+(?:para|que dice|diciendo)\b|$)/i
    .exec(String(texto).trim());
  if (!m) return '';
  const cancion = m[1].replace(/^(?:la\s+|el\s+|una\s+|un\s+)?(?:cancion|canción|musica|música|tema)\s+/i, '')
    .replace(/[.:;]\s*$/, '').trim();
  if (/^(?:la\s+|el\s+|una\s+|un\s+)?(?:cancion|canción|musica|música|tema)$/i.test(cancion)) return '';
  return cancion;
}

/* «temporizador de 10 minutos» → 600; también «media hora», «un cuarto de hora»,
   «2 horas» y «45 segundos». La unidad se mira por su primera letra: h, m o s. */
function sacaSegundos(b) {
  const n = /(\d+(?:[.,]\d+)?)\s*(horas?|h|minutos?|min|segundos?|s)\b/.exec(b);
  if (n) {
    const val = +String(n[1]).replace(',', '.');
    const u = n[2][0];
    return Math.round(val * (u === 'h' ? 3600 : u === 'm' ? 60 : 1));
  }
  if (/\bmedia hora\b/.test(b)) return 1800;
  if (/\b(?:un )?cuarto de hora\b/.test(b)) return 900;
  if (/\buna hora\b/.test(b)) return 3600;
  return 0;
}

/* Qué app quiere abrir: la lista del contrato, con sus nombres de calle. */
function sacaApp(b) {
  if (!/\b(abre|abrir|abreme|abreel|lanza|lanzar|inicia|iniciar|arranca|arrancar|levanta|monta|activa)\b/.test(b)) return '';
  const claves = Object.keys(APPS).sort((a, c) => c.length - a.length);
  for (const k of claves) {
    if (new RegExp('\\b' + k.replace(/ /g, '\\s+') + '\\b').test(b)) return APPS[k];
  }
  return '';
}
