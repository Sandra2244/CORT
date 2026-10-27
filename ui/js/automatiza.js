/* ===== AUTOMATIZA — «cuando X, entonces Y» (ronda 2.4) =====
 *
 * Lo que ella pidió: «la automatización como es JARVIS o Cortana». En esos
 * asistentes eso son *reglas*: una condición que se dispara sola y una lista de
 * cosas que hacer. Aquí es exactamente ésto, y **sin tocar Java**: la cara ya
 * tiene todas las manos que hacen falta (`accion`, `mente`, `memoria`,
 * `Reproductor`), lo que faltaba era el sitio donde se juntan.
 *
 * Dos decisiones que gobiernan el fichero entero:
 *
 * · **Este módulo es puro.** Ni `document`, ni `window`, ni `localStorage` a pelo:
 *   el almacén y el reloj entran por parámetros. Es lo que permite comprobar las
 *   reglas con `node scripts/prueba-automatiza.mjs` en el portátil, sin teléfono y
 *   sin WebView — igual que `Avisos.linea()` es la mitad comprobable de esa clase.
 *
 * · **Nada se dispara si no hay quien lo ejecute.** `ejecuta(accion, args)` lo
 *   pone `telefono.js`, y si una acción no está en el puente ese `ejecuta`
 *   devuelve `false` y la regla lo cuenta. Una automatización muda sería peor que
 *   ninguna: la dueña creería que CORT ya se ocupa de lo que dijo.
 *
 * La limitación honesta, y va escrita en la hoja: **las reglas se evalúan mientras
 * CORT está vivo en pantalla**. La cara es una página; un `WebView` cerrado no
 * escucha. Lo que sí funciona con la pantalla apagada es lo que Java hace solo
 * (leer avisos en voz alta, la música, el oído del auricular).
 */

export const CLAVE_ALMACEN = 'cort.autos.v1';

/* El pliegue de texto vive en `texto.js` desde la refactorización: aquí se importa
   y se re-exporta, porque `scripts/prueba-automatiza.mjs` lo comprueba desde esta
   hoja y las reglas lo usan por dentro. Es el mismo `normaliza` del resto de la
   cara — tener dos copias era justamente lo que se quería quitar. */
import { normaliza } from './texto.js';
export { normaliza };

/* ─────────────── los disparadores que de verdad tienen señal ───────────────
   Cada uno lista el evento que lo alimenta, y ese evento está MEDIDO en este
   repo: `stt-final` lo emite `CortNative.java` con el texto, `auricular` sale de
   `escuchaDelAuricular()`, `pause`/`resume` de `pausa()`/`reanuda()`, y `aviso`
   es nuevo en la 2.4 — Java lo manda desde `Avisos.onNotificationPosted`.
   Un disparador sin evento que lo alimente no se ofrece: es un botón roto. */
export const DISPARADORES = [
  { id: 'frase', nombre: 'cuando yo diga o escriba', campo: 'texto',
    pista: 'modo noche', senal: 'stt-final / terminal',
    nota: 'vale cualquier palabra suya; la regla gana a la orden de siempre' },
  { id: 'aviso', nombre: 'cuando llegue un aviso', campo: 'texto', campo2: 'de',
    pista2: 'whatsapp', pista: 'la palabra del mensaje', senal: 'aviso',
    nota: 'de quien sea y qué diga; se puede poner sólo una de las dos cosas' },
  { id: 'auricular', nombre: 'cuando pulse el auricular', campo: 'estado',
    opciones: ['suena', 'deja de sonar'], senal: 'auricular' },
  { id: 'cargador', nombre: 'cuando cambie la batería', campo: 'estado',
    opciones: ['conecta', 'desconecta', 'baje de'], senal: 'aparato',
    nota: 'se mide con la batería que ya lee el teléfono, sin permiso nuevo' },
  { id: 'hora', nombre: 'a una hora del día', campo: 'hora', opciones: null,
    senal: 'reloj', nota: 'una sola vez cada día' },
];

/* ─────────────── las acciones: todas con su mano en el puente ───────────────
   Cada `id` tiene que estar atendido en `ejecuta()` de `telefono.js`. La hoja de
   abajo es la lista que se pinta en el `<select>`, y `prueba-costura.py` comprueba
   que lo que se ofrece existe. */
export const ACCIONES = [
  { id: 'habla', nombre: 'que CORT diga', campo: 'texto', pista: 'ya está listo' },
  { id: 'volumen', nombre: 'poner el volumen', campo: 'como',
    opciones: ['callar', 'mínimo', 'máximo', 'subir', 'bajar'] },
  { id: 'linterna', nombre: 'la linterna', campo: 'como', opciones: ['encender', 'apagar'] },
  { id: 'abrir', nombre: 'abrir una app', campo: 'app', pista: 'whatsapp' },
  { id: 'musica', nombre: 'la música', campo: 'como',
    opciones: ['parar', 'seguir', 'pausa', 'siguiente'] },
  { id: 'piensa', nombre: 'que piense una cosa (su cerebro)', campo: 'texto',
    pista: '¿qué tengo hoy?' },
  { id: 'recuerdo', nombre: 'apuntar un recuerdo', campo: 'texto',
    pista: 'bajar la leche del súper' },
  { id: 'alarma', nombre: 'poner una alarma', campo: 'hora', pista: '07:30' },
];

/* Las tres que se dejan hechas, para que la función no sea una hoja en blanco. */
export function preajustes() {
  return [
    { id: 'auto-noche', nombre: 'modo noche', activo: true,
      disparador: { tipo: 'frase', texto: 'modo noche' },
      hacen: [{ que: 'volumen', como: 'callar' }, { que: 'linterna', como: 'apagar' },
              { que: 'habla', texto: 'Modo noche: silencio y a dormir.' }] },
    { id: 'auto-manana', nombre: 'el aviso de la mañana', activo: false,
      disparador: { tipo: 'hora', hora: '07:30' },
      hacen: [{ que: 'piensa', texto: '¿qué tengo hoy?' }] },
    { id: 'auto-cargador', nombre: 'cuando desconecte el cargador', activo: false,
      disparador: { tipo: 'cargador', estado: 'desconecta' },
      hacen: [{ que: 'habla', texto: 'Ya sin cable: mira cuánta batería queda.' }] },
  ];
}

let contador = 0;
const idNuevo = () => 'auto-' + Date.now().toString(36) + '-' + (++contador);

/* ───────────────────────── el motor ───────────────────────── */
export function creaMotor({ ejecuta, term, almacen, reloj } = {}) {
  const ahora = () => (reloj ? reloj() : Date.now());
  const di = (t, c) => { try { term && term(t, c || 'autos'); } catch { /* consola cerrada */ } };

  const store = almacen || ((typeof localStorage !== 'undefined') ? localStorage : null);
  let reglas = [];

  function lee() {
    if (!store) return [];
    let crudo = null;
    try { crudo = store.getItem(CLAVE_ALMACEN); } catch { return []; }
    if (!crudo) return [];
    try {
      const s = JSON.parse(crudo);
      return Array.isArray(s.reglas) ? s.reglas : (Array.isArray(s) ? s : []);
    } catch { di('las reglas estaban guardadas rotas; se empiezan de cero', 'aviso'); return []; }
  }
  function salva() {
    if (!store) return false;
    try { store.setItem(CLAVE_ALMACEN, JSON.stringify({ v: 1, reglas })); return true; }
    catch { di('el teléfono no dejó guardar las reglas', 'aviso'); return false; }
  }
  reglas = lee();

  /* La hora se guarda como «2026-10-22» para que «a las 7:30» no se repita al
     volver a abrir la app dos minutos después. */
  const dia = ms => new Date(ms).toISOString().slice(0, 10);

  /* Reglas con nombre legible para la hoja. */
  function resume(r) {
    const d = DISPARADORES.find(x => x.id === r.disparador.tipo) || { nombre: r.disparador.tipo };
    const con = r.disparador.texto || r.disparador.hora || r.disparador.estado || r.disparador.de || '';
    const hace = (r.hacen || []).map(a => {
      const x = ACCIONES.find(y => y.id === a.que) || { nombre: a.que };
      return x.nombre + (a.texto || a.como || a.app || a.hora ? ' · ' + (a.texto || a.como || a.app || a.hora) : '');
    });
    return { id: r.id, nombre: r.nombre || d.nombre, activo: r.activo !== false,
             cuando: d.nombre + (con ? ' → «' + con + '»' : ''), hacen: hace,
             veces: r.veces || 0, ultima: r.ultima || 0 };
  }

  /* ¿La señal le viene a esta regla? Toda la comparación está aquí, y es pura:
     es la función que se prueba en el portátil. */
  function coincide(r, senal) {
    if (!r || !senal || r.disparador.tipo !== senal.tipo) return false;
    const d = r.disparador;
    if (d.tipo === 'frase') {
      const busca = normaliza(d.texto);
      if (!busca) return false;
      return normaliza(senal.texto).includes(busca);
    }
    if (d.tipo === 'aviso') {
      const de = normaliza(d.de || ''), texto = normaliza(d.texto || '');
      if (!de && !texto) return false;
      if (de && !normaliza(senal.de || '').includes(de)) return false;
      if (texto) {
        const cuerpo = normaliza((senal.dice || '') + ' ' + (senal.texto || ''));
        if (!cuerpo.includes(texto)) return false;
      }
      return true;
    }
    if (d.tipo === 'auricular') return d.estado === (senal.escuchando ? 'suena' : 'deja de sonar');
    if (d.tipo === 'cargador') {
      if (d.estado === 'conecta') return senal.cargando === 1 || senal.cargando === true;
      if (d.estado === 'desconecta') return senal.cargando === 0 || senal.cargando === false;
      if (d.estado === 'baje de') {
        const tope = Number(d.hasta);
        return Number.isFinite(tope) && Number(senal.bateria) >= 0 && Number(senal.bateria) <= tope;
      }
      return false;
    }
    if (d.tipo === 'hora') return !!d.hora && senal.hora === d.hora;
    return false;
  }

  /* El freno: una regla de «aviso» con la palabra «hola» no puede sonar veinte
     veces en un minuto. 60 s por defecto; `hora` usa el día entero. */
  function puede(r, ms) {
    if (r.disparador && r.disparador.tipo === 'hora') return r.ultimaDia !== dia(ms);
    const tope = Number.isFinite(r.refrenar) ? r.refrenar : 60000;
    return !r.ultima || ms - r.ultima >= tope;
  }

  async function corre(r, senal) {
    const hechos = [];
    const fallidas = [];
    for (const a of (r.hacen || [])) {
      let ok = false;
      try { ok = await ejecuta(a.que, a); } catch (e) { ok = false; di('la acción «' + a.que + '» dio error: ' + e, 'aviso'); }
      (ok ? hechos : fallidas).push(a);
    }
    r.ultima = ahora();
    r.ultimaDia = dia(r.ultima);
    r.veces = (r.veces || 0) + 1;
    salva();
    const nombre = r.nombre || r.id;
    if (hechos.length) di('automatización «' + nombre + '»: '
      + hechos.map(a => a.que).join(' + ') + (senal && senal.texto ? ' (por «' + String(senal.texto).slice(0, 30) + '»)' : ''), 'autos');
    if (fallidas.length) di('«' + nombre + '» no pudo: ' + fallidas.map(a => a.que).join(', ')
      + ' — ese APK no tiene esa mano, o falta un permiso.', 'aviso');
    return { hechos, fallidas };
  }

  /* La boca por donde entra todo: `dispara(senal)`. Devuelve las reglas que
     sonaron (cero = nadie tenía nada apuntado, y la cara sigue con lo suyo). */
  function dispara(senal) {
    const ms = ahora();
    const apuntadas = reglas.filter(r => r.activo !== false && coincide(r, senal));
    const vivas = apuntadas.filter(r => puede(r, ms));
    // Que se frenó tiene que decirse: si no, la dueña repite su frase dos veces, no
    // pasa nada a la segunda y piensa que la regla se rompió.
    apuntadas.filter(r => !vivas.includes(r)).forEach(r =>
      di('«' + (r.nombre || r.id) + '» acaba de sonar: la freno un minuto para que no se repita.', 'aviso'));
    const resultados = vivas.map(r => corre(r, senal));
    return vivas.length ? resultados : [];
  }

  return {
    lista: () => reglas.map(resume),
    crudas: () => reglas,
    total: () => reglas.length,
    guardadas: () => !!store,
    agrega(r) {
      const nueva = { id: r.id || idNuevo(), nombre: (r.nombre || '').trim(), activo: true,
                      disparador: { ...(r.disparador || {}) }, hacen: (r.hacen || []).map(a => ({ ...a })),
                      refrenar: r.refrenar, ultima: 0, veces: 0 };
      reglas.push(nueva); salva(); return resume(nueva);
    },
    quita(id) { const n = reglas.length; reglas = reglas.filter(r => r.id !== id); salva(); return n !== reglas.length; },
    cambia(id, activo) {
      const r = reglas.find(x => x.id === id); if (!r) return false;
      r.activo = !!activo; if (r.activo) { r.ultima = 0; r.ultimaDia = ''; }
      salva(); return true;
    },
    vacia() { reglas = []; salva(); },
    arranca() { reglas = preajustes(); salva(); return reglas.map(resume); },
    dispara, coincide, puede, resume,
  };
}

/* ─────────────── el reloj, la parte molesta ───────────────
   «A las 7:30» y «baje del 20%» no tienen evento que los empuje: hacen falta dos
   miradas por minuto. `marcapasos` es UN temporizador para todas las reglas, y
   sólo se enciende si algo lo pide (`necesita`), así que una cara sin reglas de
   hora no gasta ni una alarma. */
export function necesitaReloj(reglas) {
  return (reglas || []).some(r => r.activo !== false
    && r.disparador && r.disparador.tipo === 'hora')
    || (reglas || []).some(r => r.activo !== false
      && r.disparador && r.disparador.tipo === 'cargador');
}

export function marcapasos({ motor, aparato, ahora = () => new Date(), cadaMs = 30000 }) {
  let vivo = null;
  const latido = {
    pisa() {
      const d = ahora();
      const hhmm = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
      motor.dispara({ tipo: 'hora', hora: hhmm });
      // La batería sólo se pregunta si hay una regla que la mire.
      const lee = aparato && aparato();
      if (lee && (lee.bateria !== undefined || lee.cargando !== undefined)) {
        motor.dispara({ tipo: 'cargador', cargando: lee.cargando, bateria: lee.bateria });
      }
    },
    arranca() { if (!vivo) vivo = setInterval(() => latido.pisa(), cadaMs); return latido; },
    para() { if (vivo) { clearInterval(vivo); vivo = null; } return latido; },
    viva: () => !!vivo,
  };
  return latido;
}
