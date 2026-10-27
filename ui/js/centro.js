/* ===== Centro de mando · todo lo que CORT sabe hacer, en una sola lista =====
 *
 * La dueña lo dijo así: «las funciones están regadas, les falta orden
 * profesional». Tenía razón: las 91 intenciones vivían en el diccionario, las
 * pantallas en `pantallas.js`, las herramientas en `#dock`, los ajustes en
 * `#cj-ajustes` y las órdenes de voz sólo se descubrían diciéndolas. Aquí se
 * juntan las cuatro familias con su nombre, su ejemplo y una búsqueda.
 *
 * Dos reglas que hacen que esto no mienta:
 *
 * · El catálogo sale del **diccionario generado** (`saber.py` → `habilidades.py`
 *   → `diccionario.js`), la misma fuente que atiende `Cerebro`. No hay una
 *   segunda lista escrita a mano que pueda quedarse vieja.
 * · Al tocar una orden se manda **la frase de ejemplo** por `cort:orden`; el
 *   `send()` de la cara la procesa igual que si la hubiera dicho. Si una orden
 *   no funcionara, fallaría igual aquí y en voz alta — no hay un camino de
 *   mentira sólo para la demostración.
 *
 * Es un módulo de pintado, sin estado global: recibe la raíz, `ir` y las
 * pantallas visibles. Así se puede montar en la sonda con el puente de mentira.
 */
import { DICCIONARIO, TOTALES } from './diccionario.js';
import { esc, sinTilde } from './texto.js';

const CAPAS = {
  mando:  { nombre: 'Órdenes del aparato', icono: '⚙' },
  razon:  { nombre: 'Razón y cuentas',     icono: '∑' },
  casa:   { nombre: 'Tu casa y tu equipo', icono: '⌂' },
  nube:   { nombre: 'La nube',             icono: '☁' },
  app:    { nombre: 'Pantallas de CORT',   icono: '▣' },
  herr:   { nombre: 'Herramientas',        icono: '▤' },
  ajuste: { nombre: 'Ajustes y permisos',  icono: '☰' },
};

/** Las cuatro familias, ya planas, para pintar y filtrar. */
function junta(apps) {
  const items = [];

  DICCIONARIO.forEach(d => {
    items.push({
      tipo: 'orden', capa: d.capa || 'mando', grupo: (CAPAS[d.capa] || CAPAS.mando).nombre,
      icono: (CAPAS[d.capa] || CAPAS.mando).icono,
      titulo: d.titulo || d.id,
      ejemplo: d.ejemplo || (d.frases && d.frases[0]) || d.titulo,
      busca: sinTilde([d.titulo, d.ejemplo, d.accion, ...(d.frases || [])].join(' ')),
    });
  });

  (apps || []).forEach(p => items.push({
    tipo: 'app', capa: 'app', grupo: CAPAS.app.nombre, icono: p.ic || '▣',
    titulo: p.titulo, ejemplo: p.sub, busca: sinTilde(p.titulo + ' ' + p.sub + ' ' + p.id),
  }));

  const movil = document.documentElement.classList.contains('mobile');
  document.querySelectorAll('#dock [data-win], #dock [data-act]').forEach(b => {
    // En el teléfono no se ofrece lo que sólo existe en el PC: un botón que
    // lleva a una ventana de escritorio es peor que no ofrecerlo.
    if (movil && b.hasAttribute('data-pc')) return;
    const nombre = (b.textContent || '').trim();
    const titulo = b.getAttribute('title') || nombre;
    items.push({
      tipo: b.hasAttribute('data-win') ? 'win' : 'act',
      capa: 'herr', grupo: CAPAS.herr.nombre, icono: (b.querySelector('i') || {}).textContent || '▤',
      titulo: nombre || titulo.split('·').pop().trim(),
      ejemplo: titulo,
      valor: b.dataset.win || b.dataset.act,
      busca: sinTilde(nombre + ' ' + titulo),
    });
  });

  document.querySelectorAll('#cj-ajustes [data-aj], #cj-ajustes [data-nombre]').forEach(b => {
    // El nombre legible está en `data-nombre` (wake/hand) o en el nodo de texto
    // que sigue al icono (`<i>A</i>Letra más grande`). Nunca se usa `textContent`
    // entero: arrastraría la «A» del icono al título.
    const texto = (b.lastChild && b.lastChild.textContent || '').trim();
    const titulo = b.dataset.nombre || texto || (b.textContent || '').trim();
    items.push({
      tipo: 'aj', capa: 'ajuste', grupo: CAPAS.ajuste.nombre,
      icono: (b.querySelector('i') || {}).textContent || '☰',
      titulo, ejemplo: 'enciende o apaga desde aquí',
      valor: b.dataset.aj || b.id, busca: sinTilde(titulo + ' ' + (b.dataset.aj || b.id)),
    });
  });

  return items;
}

/** Pinta el Centro dentro de `raiz`. Devuelve cuántas filas quedan a la vista
    (lo usa la sonda para comprobar la búsqueda, no para adorno). */
export function montaCentro(raiz, { ir, apps } = {}) {
  if (!raiz) return 0;
  const items = junta(apps);
  const capas = ['', 'mando', 'razon', 'casa', 'nube', 'app', 'herr', 'ajuste'];

  raiz.innerHTML = `
    <div class="cen-cabeza">
      <input id="cen-busca" type="search" autocomplete="off" spellcheck="false"
             placeholder="busca: volumen, alarma, música, permiso…"
             aria-label="Buscar en todo CORT">
      <p id="cen-cuenta">
        ${TOTALES.intents} intenciones · ${TOTALES.frases} frases, sacadas del
        mismo diccionario que las atiende. Toca una y CORT la ejecuta.
      </p>
    </div>
    <div class="cen-chips">${capas.map(c => {
      const n = c ? items.filter(i => i.capa === c).length : items.length;
      return `<button data-capa="${c}"${c ? '' : ' class="on"'}>${c ? esc(CAPAS[c].nombre) : 'Todo'} <b>${n}</b></button>`;
    }).join('')}</div>
    <div id="cen-lista" role="list"></div>
    <p id="cen-nada" hidden>No hay nada con esas palabras. Prueba «volumen», «alarma», «música» o «permiso».</p>`;

  const lista = raiz.querySelector('#cen-lista');
  const nada = raiz.querySelector('#cen-nada');
  const cuenta = raiz.querySelector('#cen-cuenta');
  const busca = raiz.querySelector('#cen-busca');
  let capa = '';

  function pinta() {
    const palabras = sinTilde(busca.value).split(/\s+/).filter(Boolean);
    const vistas = items.filter(i =>
      (!capa || i.capa === capa) && palabras.every(p => i.busca.includes(p)));
    let html = '', grupo = '';
    vistas.forEach(i => {
      if (i.grupo !== grupo) {
        grupo = i.grupo;
        html += `<div class="cen-grupo">${esc(grupo)} <span>${vistas.filter(x => x.grupo === grupo).length}</span></div>`;
      }
      const accion = i.tipo === 'orden' ? `data-frase="${esc(i.ejemplo)}"`
        : `data-valor="${esc(i.valor || '')}"`;
      html += `<button class="cen-fila" role="listitem" data-tipo="${i.tipo}" ${accion}
          data-capa="${i.capa}" title="${esc(i.ejemplo)}">
        <i>${esc(i.icono)}</i>
        <span class="cen-txt"><b>${esc(i.titulo)}</b><small>${i.tipo === 'orden' ? '“' + esc(i.ejemplo) + '”' : esc(i.ejemplo)}</small></span>
        <em>${i.tipo === 'orden' ? 'decir' : 'abrir'}</em>
      </button>`;
    });
    lista.innerHTML = html;
    nada.hidden = vistas.length > 0;
    cuenta.textContent = palabras.length || capa
      ? `${vistas.length} de ${items.length} · ${TOTALES.intents} intenciones y ${TOTALES.frases} frases en total`
      : `${TOTALES.intents} intenciones · ${TOTALES.frases} frases, sacadas del mismo diccionario que las atiende. Toca una y CORT la ejecuta.`;
    return vistas.length;
  }

  busca.oninput = pinta;
  busca.onkeydown = ev => {
    if (ev.key !== 'Enter') return;
    const primera = lista.querySelector('.cen-fila');
    if (primera) primera.click();
  };
  raiz.querySelectorAll('.cen-chips [data-capa]').forEach(b => {
    b.onclick = () => {
      capa = b.dataset.capa;
      raiz.querySelectorAll('.cen-chips button').forEach(x => x.classList.toggle('on', x === b));
      pinta();
    };
  });

  lista.onclick = ev => {
    const b = ev.target.closest('button.cen-fila');
    if (!b) return;
    const tipo = b.dataset.tipo;
    if (tipo === 'orden') {
      // Primero la cara, luego la frase: `activate()` del orbe se ve mientras
      // el cerebro responde, igual que si la hubiera dicho en voz alta.
      ir?.('orbe');
      window.dispatchEvent(new CustomEvent('cort:orden', { detail: { texto: b.dataset.frase } }));
      return;
    }
    if (tipo === 'app') { ir?.(b.dataset.valor); return; }
    if (tipo === 'aj') {
      const v = b.dataset.valor;
      (document.querySelector(`#cj-ajustes [data-aj="${v}"]`)
        || document.getElementById(v))?.click();
      return;
    }
    // Herramientas: son ventanas del orbe, con su manejador ya enganchado. Se
    // pulsa el botón de verdad en vez de duplicar aquí lo que hace `windows.js`.
    ir?.('orbe');
    setTimeout(() => {
      const sel = tipo === 'win' ? `#dock [data-win="${b.dataset.valor}"]` : `#dock [data-act="${b.dataset.valor}"]`;
      document.querySelector(sel)?.click();
    }, 70);
  };

  return pinta();
}
