/* ===== 02 · CÓDIGO: la terminal del PC, el cuaderno y el modo copiloto =====
 *
 * Cuarto corte de la refactorización por tamaño (la regla de la dueña: «la interfaz
 * debe ser mil líneas máximo y si necesitas crear otros de otras líneas más conectas
 * y divides entre si pero que funcione correctamente»). Estos 388 líneas eran el
 * sector «02 · CÓDIGO» de `pantallas.js`, que baja de 2.184 a 1.795. Salen **tal
 * cual**: no se reescribe ni una coma de lo que hace; lo único nuevo son los `import`
 * de arriba y los `export` de abajo.
 *
 * Con quién habla y por qué no forma círculo:
 *  · `marco.js` —el puente con Java, `hayNucleo` con su cache, la pregunta honesta de
 *    «¿hay núcleo?» y el portapapeles—. Se importa; esta hoja ya no recibe el marco
 *    a mano.
 *  · `pasos.js` —los estados del hilo del copiloto (J2.3): `pendiente → corriendo →
 *    ok / falló`, y quién puede aceptar o rechazar un paso—.
 *  · `telefono.js` sólo `terminalTelefono`, la terminal de pega del teléfono.
 *  · `pantallas.js` importa DE aquí (`montaCodigo`, `pintaCodigo`), nunca al revés:
 *    la monta la carcasa y la registra con `alEntrar('codigo', pintaCodigo)`.
 *
 * Lo que sigue midiéndose aquí, sin cambio: que **quien ejecuta es el PC** (en la APK
 * no hay shell), el cuaderno con `localStorage`, el historial de comandos y el modo
 * copiloto de F11, cuyo veredicto de «sólo lectura» lo da `backend/app/copiloto.py` y
 * esta hoja se limita a acatar. La costura lo comprueba en su sector de la cara.
 */

import { esc } from './texto.js';
import { ESTADOS_PASO, puedeAceptar, puedeRechazar, arranca, rechaza, cierra } from './pasos.js';
import { terminalTelefono } from './telefono.js';
import {
  enTelefono, ctx, ir,
  hayNucleo, sinNucleoFrase, avisaSinNucleo,
  copia,
} from './marco.js';

/* ─────────────────────────── 02 · CÓDIGO ─────────────────────────── */
/*
 * Entorno de programación, terminal y **copiloto**. Dicho sin adornos y sin prometer
 * lo que Android no deja: **quien ejecuta es el PC**, porque dentro de una APK una app
 * normal no puede abrir una shell ni instalar paquetes (sandbox). Lo que hay aquí es
 * el terminal real del equipo (por `/api/command` y su ejecutor de acciones), un
 * cuaderno de código —escribes o pegas, pides que lo arregle, y lo guardas— y el modo
 * copiloto de F11: describes el objetivo, CORT piensa los comandos y ejecuta sólo los
 * que no pueden romper nada (`backend/app/copiloto.py`), dejando escritos los demás.
 */
const CLAVE_CODIGO = 'cort-codigo';
const CLAVE_COPILOTO = 'cort-copiloto';

/* ─────────────── el modo copiloto (F11 · el punto 4 de su lista) ───────────────
 * «CORT debe guiarte como copiloto y ejecutar los comandos él solo». La cara de
 * ese acuerdo es esta: escribes un OBJETIVO («cómo está el equipo», «qué ocupa
 * espacio») y CORT devuelve los PASOS con el comando exacto de cada uno. Cada paso
 * trae su ▶, y el ▶ sólo está encendido si el comando es de **sólo lectura** — el
 * veredicto no lo decide esta hoja, lo decide `backend/app/copiloto.py` con sus
 * tres listas (`LEE_SOLO`, `SUB_LECTURA`, `NUNCA`) y lo vuelve a comprobar en el
 * momento de ejecutar. Lo que escribe, borra o instalar se muestra con su motivo y
 * un botón de copiar: queda en tus manos, no en las de CORT.
 * Con el modo apagado la terminal sigue siendo la de siempre (`/api/command`), y
 * con el modo encendido se puede hacer una pausa del copiloto prefijando `> `.
 */
const copiloto = {
  activo: false, token: '', pasos: [], recetas: [], ocupado: false,
};
try { copiloto.activo = localStorage.getItem(CLAVE_COPILOTO) === '1'; } catch { /* sin localStorage */ }

function guardaCopiloto() {
  try { localStorage.setItem(CLAVE_COPILOTO, copiloto.activo ? '1' : '0'); } catch { /* nada */ }
}

/* Las sugerencias salen del propio backend (`recetas`), no escritas a mano aquí:
   si un día cambia una plantilla, la cara dice lo que de verdad sabe hacer. */
async function copilotoArranca() {
  const base = await hayNucleo();
  if (!base) return;
  if (copiloto.recetas.length) { pintaCopilotoChips(); return; }
  try {
    const r = await fetch(base + '/api/copiloto', { signal: AbortSignal.timeout(4000) });
    const j = await r.json();
    copiloto.recetas = Array.isArray(j.recetas) ? j.recetas : [];
    pintaCopilotoChips();
  } catch { /* sin catálogo: los chips simplemente no aparecen */ }
}

function pintaCopilotoChips() {
  const caja = document.getElementById('cod-cop-chips');
  if (!caja) return;
  if (!copiloto.activo) { caja.innerHTML = ''; return; }
  if (!copiloto.recetas.length) {
    caja.innerHTML = '<span class="cp-nota">pide el plan con tus palabras: «cómo está el equipo», '
      + '«qué ocupa espacio», «qué tengo instalado»…</span>';
    return;
  }
  caja.innerHTML = copiloto.recetas.map(t => '<button class="eq-chip" data-obj="'
    + esc(t) + '">' + esc(t) + '</button>').join('');
  caja.querySelectorAll('[data-obj]').forEach(b => {
    b.onclick = () => {
      const e = document.getElementById('cod-entrada');
      if (e) e.value = b.dataset.obj;
      codigo(b.dataset.obj);
    };
  });
}

async function copilotoPlan(objetivo) {
  const base = await hayNucleo();
  if (!base) {
    escribeCodigo(sinNucleoFrase(), 'aviso');
    return false;
  }
  copiloto.ocupado = true; pintaCopiloto();
  try {
    const r = await fetch(base + '/api/copiloto/plan', {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ objetivo }), signal: AbortSignal.timeout(30000),
    });
    const j = await r.json();
    if (!j.ok) {
      copiloto.token = ''; copiloto.pasos = [];
      escribeCodigo(j.dice || 'no pudo hacer un plan', 'aviso');
      return false;
    }
    copiloto.token = j.token || '';
    /* Cada paso nace con su estado (J2.3): los seguros quedan `pendiente` —con verde
       y rojo—, y los que el núcleo no ejecuta nacen `enseñado`, que es la palabra
       honesta: se enseñaron, no se hicieron. */
    copiloto.pasos = (j.pasos || []).map(p => ({ ...p, estado: p.seguro ? 'pendiente' : 'enseñado' }));
    escribeCodigo('plan (' + (j.origen || 'pasos') + '): ' + (j.dice || ''), 'hecho');
    return true;
  } catch (e) {
    escribeCodigo('el copiloto no respondió: ' + e, 'aviso');
    return false;
  } finally { copiloto.ocupado = false; pintaCopiloto(); }
}

async function copilotoEjecuta(indice) {
  const base = await hayNucleo();
  if (!base || !copiloto.token) return;
  const paso = (copiloto.pasos || [])[indice];
  if (!paso) return;
  /* El verde pasa por `pasos.js`: si el paso ya se corrió, se rechazó o no es seguro,
     `arranca` no hace nada y el comando no se ejecuta dos veces por un toque de más. */
  if (arranca(paso) !== 'corriendo') return;
  pintaCopiloto();
  try {
    const r = await fetch(base + '/api/copiloto/ejecuta', {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ token: copiloto.token, indice }),
      signal: AbortSignal.timeout(35000),
    });
    const j = await r.json();
    cierra(paso, j);
    escribeCodigo('▶ ' + paso.orden + ' — ' + (j.dice || ''), j.ejecutado && j.ok ? 'hecho' : 'aviso');
    if (j.salida) String(j.salida).split('\n').slice(0, 30)
      .forEach(l => escribeCodigo('  ' + l, 'cort'));
  } catch (e) {
    /* El núcleo no contestó: eso es un paso que FALLÓ, no uno que «se enseñó». Si se
       cerrara con `cierra`, la respuesta vacía lo dejaría en `enseñado` y la cara
       contaría como neutro un corte de red. */
    paso.estado = 'falló';
    paso.resultado = { ok: false, ejecutado: false, dice: 'no respondió: ' + e };
    escribeCodigo('▶ ' + paso.orden + ' — el copiloto no respondió: ' + e, 'aviso');
  } finally { pintaCopiloto(); }
}

/* Ejecuta en fila los pasos que el backend marcó como seguros, uno detrás de otro.
   Se para si uno falla de verdad: un copiloto que sigue andando después de un error
   no está guiando, está acumulando basura. */
async function copilotoEjecutaSeguros() {
  const seguros = copiloto.pasos.filter(p => p.seguro);
  for (const p of seguros) {
    await copilotoEjecuta(p.indice);
    if (p.resultado && p.resultado.ejecutado && !p.resultado.ok) {
      escribeCodigo('me paro aquí: el resto lo miras tú (' + (p.resultado.dice || '') + ')', 'aviso');
      break;
    }
  }
}

function pintaCopiloto() {
  const caja = document.getElementById('cod-cop-plan');
  if (!caja) return;
  if (!copiloto.activo) { caja.innerHTML = ''; return; }
  if (!copiloto.pasos.length) {
    caja.innerHTML = copiloto.ocupado ? '<div class="cp-nota">pensando los pasos…</div>' : '';
    return;
  }
  /* Los que «se ejecutan solos» son los seguros QUE AÚN no se tocaron: un paso ya
     corrido, rechazado o enseñado no vuelve a la cuenta, y así el botón `▶ ejecuta los
     N seguros` dice cuántos corren si lo pulsas ahora mismo. */
  const seguros = copiloto.pasos.filter(p => p.seguro && p.estado === 'pendiente').length;
  const hechos = copiloto.pasos.filter(p => p.estado === 'ok' || p.estado === 'falló'
    || p.estado === 'rechazado').length;
  caja.innerHTML = '<div class="cp-pie"><span class="cp-nota">'
    + copiloto.pasos.length + ' pasos · ' + seguros + ' se ejecutan solos · '
    + (copiloto.pasos.length - seguros - hechos) + ' sólo se enseñan'
    + (hechos ? ' · ' + hechos + ' ya decididos' : '') + '</span>'
    + '<button class="eq-b" id="cp-todos"' + (seguros && !copiloto.ocupado ? '' : ' disabled')
    + '>▶ ejecuta los ' + seguros + ' seguros</button>'
    + '<button class="eq-b" id="cp-cierra">cerrar el plan</button></div>'
    + copiloto.pasos.map(p => {
      const res = p.resultado || {};
      const est = ESTADOS_PASO[p.estado] || ESTADOS_PASO.pendiente;
      const corriendo = p.estado === 'corriendo';
      return '<div class="cp-paso' + (p.seguro ? '' : ' malo') + ' est-' + (p.estado || 'pendiente') + '">'
        + '<div class="cp-cabe"><span class="cp-tit">' + esc(p.paso || ('paso ' + (p.indice + 1)))
        + '</span><span class="cp-est" style="color:' + est.color + '">' + esc(est.dice) + '</span>'
        + '<button class="cp-b" data-copia="' + p.indice + '">copiar</button>'
        + (p.seguro ? '<button class="cp-b puesta" data-ejecuta="' + p.indice + '"'
          + (puedeAceptar(p) ? '' : ' disabled') + '>' + (corriendo ? '…' : '▶') + '</button>'
          : '<button class="cp-b" disabled>▶ no</button>')
        /* El rojo (J2.3): rechazar es siempre posible mientras el paso esté pendiente o
           enseñado, y es TERMINAL —después de decir «no» ya no hay verde que valga. */
        + (puedeRechazar(p) ? '<button class="cp-b rojo" data-rechaza="' + p.indice
            + '" title="no lo ejecutes, déjamelo escrito">✕</button>' : '')
        + '</div><div class="cp-orden">' + esc(p.orden || '') + '</div>'
        + (p.seguro ? '' : '<div class="cp-motivo">' + esc(p.motivo || 'no es de sólo lectura') + '</div>')
        + (p.permitido_por_ella ? '<div class="cp-nota">permitido por ti en copiloto.json</div>' : '')
        + (res.dice ? '<div class="cp-nota">' + esc(res.dice) + '</div>' : '')
        + (res.salida ? '<div class="cp-salida">' + esc(res.salida) + '</div>' : '')
        + '</div>';
    }).join('');
  caja.querySelectorAll('[data-ejecuta]').forEach(b => {
    b.onclick = () => copilotoEjecuta(Number(b.dataset.ejecuta));
  });
  caja.querySelectorAll('[data-rechaza]').forEach(b => {
    b.onclick = () => {
      const p = (copiloto.pasos || [])[Number(b.dataset.rechaza)];
      if (rechaza(p) !== 'rechazado') return;
      escribeCodigo('✕ ' + ((p && p.orden) || 'paso') + ' — no lo ejecuto: te lo dejo escrito', 'aviso');
      pintaCopiloto();
    };
  });
  caja.querySelectorAll('[data-copia]').forEach(b => {
    b.onclick = () => copia((copiloto.pasos[Number(b.dataset.copia)] || {}).orden || '', 'Comando copiado.');
  });
  const todos = caja.querySelector('#cp-todos');
  if (todos) todos.onclick = () => copilotoEjecutaSeguros();
  const cerrar = caja.querySelector('#cp-cierra');
  if (cerrar) cerrar.onclick = () => { copiloto.pasos = []; copiloto.token = ''; pintaCopiloto(); };
}


function montaCodigo() {
  const cuerpo = document.querySelector('#scr-codigo .scr-cuerpo');
  let guardado = '';
  try { guardado = localStorage.getItem(CLAVE_CODIGO) || ''; } catch { /* nada */ }
  cuerpo.innerHTML = `
    <div class="scr-lista cod-out" id="cod-out"></div>
    <label class="cp-cab">
      <input type="checkbox" id="cod-cop-on" ${copiloto.activo ? 'checked' : ''}>
      <b>modo copiloto</b>
      <small>piensa los comandos y ejecuta solo los de sólo lectura; lo que escribe o
      borra se queda escrito para que lo copies</small>
    </label>
    <div class="cp-chips" id="cod-cop-chips"></div>
    <div class="cp-plan" id="cod-cop-plan"></div>
    <div class="cod-fila">
      <span class="cod-prompt">cort@pc:~$</span>
      <input id="cod-entrada" placeholder=" Instala, arregla, actualiza… (escribe y Enter)" autocomplete="off">
      <button id="cod-enviar" title="Ejecutar">▲</button>
    </div>
    <details class="cod-nota" ${guardado ? 'open' : ''}>
      <summary>cuaderno de código (lo que escribas aquí no se pierde)</summary>
      <textarea id="cod-editor" spellcheck="false"
        placeholder="pega o escribe tu código…&#10;&#10;p.ej. un script de Python que ordene descargas"></textarea>
      <div class="cod-botones">
        <button id="cod-arregla">pide a CORT que lo arregle</button>
        <button id="cod-copia">copiar</button>
        <button id="cod-guarda">guardar en Notas</button>
      </div>
    </details>`;
  const editor = cuerpo.querySelector('#cod-editor');
  editor.value = guardado;
  editor.addEventListener('input', () => {
    try { localStorage.setItem(CLAVE_CODIGO, editor.value); } catch { /* nada */ }
  });
  cuerpo.querySelector('#cod-copia').onclick = () => copia(editor.value, 'Código copiado.');
  cuerpo.querySelector('#cod-guarda').onclick = async () => {
    if (!editor.value.trim()) return ctx?.say?.('El cuaderno está vacío.')
    try {
      const r = await fetch(ctx.api() + '/api/notes', {
        method: 'POST', headers: { 'content-type': 'application/json' },
        // `texto`, NO `text`: el modelo `Nota` del núcleo sólo tiene ese campo, y con
        // `text` FastAPI contesta 422 —el botón decía «el núcleo no dejó guardarlo»
        // sin que nadie hubiera probado a guardarlo de verdad (cazado al coser [18]).
        body: JSON.stringify({ texto: '[código] ' + editor.value }),
      });
      ctx?.say?.(r.ok ? 'Guardado en 04 · Notas.' : 'El núcleo no dejó guardarlo.');
    } catch { ctx?.say?.('Sin núcleo: no pude guardarlo.') }
  };
  cuerpo.querySelector('#cod-arregla').onclick = () => {
    const texto = editor.value.trim();
    if (!texto) return ctx?.say?.('Escribe o pega algo primero.')
    ir('charla');
    const entrada = document.getElementById('ch-entrada');
    if (entrada) {
      entrada.value = 'Revisa este código, dime qué está mal y devuélvemelo arreglado, comentado en español:\n\n' + texto;
      entrada.focus();
    }
  };
  const entrada = cuerpo.querySelector('#cod-entrada');
  cuerpo.querySelector('#cod-enviar').onclick = () => codigo(entrada.value);
  entrada.addEventListener('keydown', e => { if (e.key === 'Enter') codigo(entrada.value); });

  /* El interruptor del copiloto: cambia la pista de la línea, enseña las sugerencias
     que el backend de verdad sabe hacer y se recuerda en localStorage. */
  const interruptor = cuerpo.querySelector('#cod-cop-on');
  interruptor.onchange = () => {
    copiloto.activo = !!interruptor.checked;
    guardaCopiloto();
    pistaCopiloto(entrada);
    if (copiloto.activo) { copilotoArranca(); } else { copiloto.pasos = []; copiloto.token = ''; }
    pintaCopilotoChips(); pintaCopiloto();
    ctx?.say?.(copiloto.activo ? 'Modo copiloto: dime qué quieres averiguar y te digo los comandos.'
      : 'Modo copiloto apagado: la terminal es la de siempre.');
  };
  pistaCopiloto(entrada);
  pintaCopilotoChips(); pintaCopiloto();
  if (copiloto.activo) copilotoArranca();
}

/* La pista de la línea dice qué se espera escribir: un OBJETIVO con el copiloto
   encendido, la orden de siempre con él apagado. Prefijar `> ` salta el copiloto. */
function pistaCopiloto(entrada) {
  if (!entrada) return;
  entrada.placeholder = copiloto.activo
    ?' un objetivo: «cómo está el equipo», «qué ocupa espacio»… ( > para la orden de siempre)'
    :' Instala, arregla, actualiza… (escribe y Enter)';
}

const HISTORIAL_CODIGO = [];
async function codigo(texto) {
  const linea = String(texto || '').trim();
  if (!linea) return;
  const entrada = document.getElementById('cod-entrada');
  if (entrada) entrada.value = '';
  /* `> ` al principio salta el copiloto: es la salida de emergencia para pedir la
     orden de siempre («> reproduce música») sin apagar el interruptor. */
  const saltoCopiloto = /^>/.test(linea);
  const orden = linea.replace(/^>\s*/, '');
  if (!orden) return;
  HISTORIAL_CODIGO.push(orden);
  escribeCodigo('$ ' + orden, 'orden');
  const estado = document.querySelector('#scr-codigo .scr-estado');

  /* ── el copiloto (F11) ──
     Con el modo encendido, la línea se lee como un OBJETIVO y no como un comando:
     el plan lo hace el backend y aquí sólo se pintan los pasos y su ▶. En el
     teléfono, si no hay portátil localizado, el objetivo se contesta con el cerebro
     del teléfono — mejor eso que dejar la línea muerta. */
  if (copiloto.activo && !saltoCopiloto) {
    if (enTelefono() && terminalTelefono(orden, escribeCodigo)) return;
    const base = await hayNucleo();
    if (base) { await copilotoPlan(orden); return; }
    escribeCodigo('sin tu portátil no hay comandos que mirar: el copiloto trabaja sobre el PC. '
      + 'Esto lo contesto yo.', 'aviso');
  }

  /* ── la terminal AMPLIADA del teléfono (ronda 2.4) ──
     Hasta ahora, sin el portátil delante esta pantalla sólo sabía decir «sin
     núcleo». Ahora la línea se atiende en el propio aparato, en dos niveles:
     1) las órdenes del puente —volumen, linterna, alarma, apps, memoria, voz,
        atuendo, agenda y las de los cerebros de casa (`busca cerebros`, `modelos`,
        `usa el modelo …`, `descarga el modelo …`, `borra el modelo …`)—, y
     2) lo que no es orden: se le pregunta al cerebro del teléfono (`Mente`), que
        contesta con `Cerebro`/`Razon` sin red, o con el modelo local de Ollama si
        lo elegiste. La respuesta NO se espera aquí: llega por el evento `mente` y
        se escribe en esta misma terminal (el `espejo` de `telefono.js`), porque
        bloquear el hilo del puente es justo lo que traba el teléfono.
     Se necesita `CortNative.mente`: un instalador anterior lo echa de menos y cae
     en la frase honesta de siempre, no en un botón mudo. */
  if (enTelefono() && typeof (window.CortNative || {}).mente === 'function') {
    if (terminalTelefono(orden, escribeCodigo)) return;
    escribeCodigo('la contesto yo, sin el portátil…', 'aviso');
    try {
      window.CortNative.mente(JSON.stringify({ que: 'preguntar', texto: orden, eco: orden.slice(0, 40) }));
      return;
    } catch (e) { escribeCodigo('el cerebro del teléfono no respondió: ' + e, 'aviso'); return; }
  }

  if (!await avisaSinNucleo(estado)) {
    escribeCodigo(sinNucleoFrase(), 'aviso'); return;
  }
  try {
    const r = await fetch(ctx.api() + '/api/command', {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ message: orden }),
    });
    const j = await r.json();
    escribeCodigo(j.reply || j.error || 'sin respuesta', 'cort');
    (j.done || []).forEach(a => escribeCodigo('· hecho: ' + a, 'hecho'));
    ctx?.orb?.burst?.();
  } catch (e) {
    escribeCodigo('el núcleo no respondió: ' + e, 'aviso');
  }
}
function escribeCodigo(linea, clase) {
  const caja = document.getElementById('cod-out');
  if (!caja) return;
  const d = document.createElement('div');
  d.className = 'cod-linea ' + (clase || '');
  d.textContent = linea;
  caja.appendChild(d);
  caja.scrollTop = caja.scrollHeight;
}
function pintaCodigo() {
  if (!document.getElementById('cod-out')) montaCodigo();
  const caja = document.getElementById('cod-out');
  if (caja && !caja.childElementCount) {
    escribeCodigo('Terminal de CORT — las órdenes se ejecutan en tu PC: «crea la carpeta Apuntes en Documentos», '
      + '«instala ffmpeg», «arregla el permiso de la carpeta».', 'aviso');
    escribeCodigo('¿Prefieres que te lo piense yo? Enciende el «modo copiloto» de arriba y escribe un '
      + 'objetivo («cómo está el equipo», «qué ocupa espacio»): CORT te enseña los comandos y ejecuta '
      + 'sólo los que no pueden romper nada.', 'hecho');
    if (enTelefono()) escribeCodigo(
      'En el teléfono esta terminal manda SOBRE EL TELÉFONO: volumen, linterna, alarma, apps, '
      + 'memoria, voz, agenda y los cerebros de tu PC por Wi-Fi (`busca cerebros`, `modelos`, '
      + '`usa el modelo …`, `descarga el modelo …`). Lo que no sea orden lo piensa el cerebro '
      + 'del teléfono, con o sin internet. Instalar paquetes o tocar archivos del ordenador '
      + 'sigue necesitando el portátil: conecta (menú del botón «CORT · PC») y escribe ahí. '
      + 'Escribe `ayuda` para ver la lista.', 'aviso');
  }
}

/* Lo que la carcasa necesita: montar la hoja y pintarla al entrar. `codigo`,
   `escribeCodigo` y el estado del copiloto son de esta hoja — nada de fuera las
   llama, medido con `grep` sobre la cara entera. */
export { montaCodigo, pintaCodigo };
