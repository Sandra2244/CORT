/* ===== el orbe del video, montado en la cara real =====
   La cara habla con ONCE métodos (`speak`, `burst`, `activate`, `stop`, `listen`,
   `setDisc`, `setAudio`, `pausa`, `vestir`, `colores`, `estado`) y los esperaba de
   `orb.js`. Este archivo no dibuja nada nuevo: mete el orbe que se construyó y se midió
   en el paso 1.1 (`orbe-plexo.js`, 340 puntos, 1.057 líneas y 160 estrellas de polvo,
   medido en el portátil de la dueña) dentro de esos once
   métodos, para que la dueña pueda poner el de la referencia sin desmontar la cara.

   Por qué es un ADAPTADOR y no una reescritura: el otro orbe sigue existiendo y se
   elige con `cort-orbe` en `localStorage` (por defecto `plexo`, que es el que ella
   pidió). Si WebGL o Three se caen, `ui/index.html` vuelve al orbe de siempre sin
   cortar la cara, igual que hacía con el doble de palo.

   Lo que NO hace este archivo, a propósito:
   · no copia geometría ni colores — los pide a `orbe-plexo.js` y a `traje.js`, que son
     los que miden `prueba-orbe.mjs` (121) y `prueba-colores.mjs` (51);
   · no arranca su bucle si el host no se lo pide, y lo congela con `pausa(true)` (el
     presupuesto de batería del teléfono: un WebGL que nadie ve es CPU, RAM y batería);
   · no inventa estados: los cinco nombres son los de la tabla del módulo.
*/
import * as THREE from 'three';
import { N_PUNTOS, VECINOS, RADIOS, DISTANCIA, creaOrbe } from './orbe-plexo.js';
import { POR_DEFECTO } from './traje.js';

export const CLAVE_ORBE = 'cort-orbe';

/** Qué orbe quiere la dueña. Por defecto el del video; `viejo` es la salida. */
export function orbeElegido() {
  try { return localStorage.getItem(CLAVE_ORBE) === 'viejo' ? 'viejo' : 'plexo'; }
  catch { return 'plexo'; }              // modo privado del WebView: queda el nuevo
}

/** El nivel de suelo de cada estado: lo que se mueve aunque el micrófono esté callado. */
const SUELO = Object.freeze({ reposo: .06, escucha: .35, piensa: .18, habla: 1, error: .10 });

/** Los dos colores del atuendo puesto, leídos de la cara (no de una copia). */
function trajeDeLaCara() {
  try {
    const st = getComputedStyle(document.documentElement);
    return [st.getPropertyValue('--primario').trim(), st.getPropertyValue('--secundario').trim()];
  } catch { return [POR_DEFECTO.primario, POR_DEFECTO.secundario]; }
}

export function initOrbeCara(mount, opciones = {}) {
  if (!mount) throw new Error('initOrbeCara: falta el sitio donde montar el orbe (#scene)');

  /* El pixelRatio es el grifo del coste: 2 multiplica por 4 los píxeles del shader. En
     la referencia el orbe no necesita más de 1,5, y en 1,8 GiB de RAM se agradece. */
  const dpr = Math.min(opciones.pixelRatio || (typeof devicePixelRatio === 'number' ? devicePixelRatio : 1), 1.5);
  const ren = new THREE.WebGLRenderer({ antialias: false, alpha: true, powerPreference: 'low-power' });
  ren.setPixelRatio(dpr);
  ren.setSize(innerWidth, innerHeight);
  mount.appendChild(ren.domElement);

  const escena = new THREE.Scene();
  const camara = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, .1, 100);
  /* 5,8 de cámara con una esfera de radio 1 y objetivo de 55°: el alto visible de la
     escena vale 2·tan(27,5°)·5,8 = 6,04 unidades, así que la esfera de 2 unidades ocupa
     el **33 % del alto**. Ese tercio es lo que mide el reposo del video
     (`docs/REFERENCIAS-VIDEOS-JARVIS.md` §5.2, fila t=0,0: «plexus pequeño, ~1/3 de la
     altura de la pantalla»). Estaba en 7,2, que da el 27 % —un cuarto— y era la mitad del
     motivo por el que la dueña decía «se ve muy simple»: el orbe era correcto pero chico,
     y el anillo del vórtice se quedaba en el 61 % del alto cuando el video llega al 82 %.
     A 5,8 el toro (radio mayor 1,95 + tubo) ocupa el 76 %. La fórmula del tamaño de los
     puntos lleva la misma distancia dentro como referencia, así que al acercar la cámara
     cada punto crece 1,24 veces sin tocar `uTamano`. El número no está escrito aquí: es
     `DISTANCIA`, exportado por `orbe-plexo.js`, para que la lente y el shader no puedan
     separarse jamás. */
  camara.position.set(0, .25, DISTANCIA);

  /* `tamano` en píxeles del aparato: `gl_PointSize` no conoce el pixel ratio y a 2x
     saldrían de la mitad de lo pedido (lo que midió la sonda del paso 1.1). */
  const orbe = creaOrbe(THREE, {
    modo: opciones.modo || 'pleno',
    puntos: opciones.puntos || N_PUNTOS,
    vecinos: opciones.vecinos || VECINOS,
    tamano: 2.8 * dpr,
    traje: opciones.traje || trajeDeLaCara(),
  });
  escena.add(orbe.objeto);

  /* ── las tres manos que mueven el nivel ───────────────────────────────────────
     `suelo` es lo que pide el estado, `audio` lo que mide el micrófono o la música, y
     `chispa` el empujón de un estallido. Eran una sola variable en el orbe viejo y por
     eso se pisaban: `stopMeter()` manda `setAudio(0,0)` y apagaba el nivel que había
     puesto `listen(true)`. Separadas, cada una manda en lo suyo y gana la mayor. */
  let suelo = SUELO.reposo, audio = 0, chispa = 0, nivel = 0;
  let estado = 'reposo', turnoVoz = 0, turnoAct = 0;
  let disco = 0;                                  // el vinilo de Música: 0 quieto, 1 girando

  const quiere = () => Math.min(1, Math.max(suelo, audio) + chispa);

  /** Pide un estado de la tabla. Un nombre inventado cae a `reposo` en vez de tumba cara. */
  function ponEstado(nombre) {
    const n = String(nombre || '').toLowerCase();
    if (!orbe.setEstado(SUELO[n] !== undefined ? n : 'reposo')) return 'reposo';
    estado = orbe.estado();
    suelo = SUELO[estado];
    return estado;
  }

  function burst() { chispa = .9; }

  /* El vórtice de activación del orbe viejo SÍ cabe ahora, y con el nombre que usa la
     cara: `dispara`. El orbe viejo lo hacía reescribiendo los vértices en la CPU; el
     plexo lo mezcla en el vertex shader con tres uniforms (`orbe-plexo.js`, MORFO), así
     que el gesto —estalla, se abre en anillo, se mantiene mientras ejecuta y se cierra—
     está en la referencia y no cuesta un bucle más. `piensa` sigue siendo el estado que
     dura hasta que la cara dice otra cosa: la animación y el color son dos cosas
     distintas y las dos mandan por su cuenta. */
  function activate() {
    const mio = ++turnoAct;
    burst();
    ponEstado('piensa');
    orbe.dispara('activa');
    setTimeout(() => {
      if (mio !== turnoAct) return;               // la voz o un estado nuevo ya mandaron
      if (orbe.estado() === 'piensa') ponEstado('reposo');
    }, 1600);
  }

  /* Al responder se dispara la versión CORTA (`responde`: 4,6 s en vez de 8). Es la
     animación que ella pidió «cuando responde CORT o ejecuta una respuesta», y si fuera
     la larga taparía la charla media frase.
     El `ms > 100` no es un adorno: `hud.js:1963` usa `speak(1)` para avisar de que la
     voz TERMINÓ (`onSpeak(false)`). Sin esa guarda, cada frase de CORT acabaría con una
     explosión nueva de 4,6 s encima de la pantalla —justo al revés de lo que significa.
     Un `ms` de 1 es una señal de apagado, no una duración. */
  function speak(ms = 2600) {
    const mio = ++turnoVoz;
    ponEstado('habla');
    if (ms > 100) orbe.dispara('responde');
    if (ms > 0) setTimeout(() => {
      if (mio !== turnoVoz) return;               // otra frase ya tomó el turno
      ponEstado('reposo');
    }, ms);
  }

  function listen(on) { ponEstado(on ? 'escucha' : 'reposo'); }

  function stop() {
    turnoVoz++; turnoAct++;                      // corta la voz y la activación en vuelo
    chispa = 0; audio = 0;
    orbe.corta();                                // «para» también vale para el vórtice
    ponEstado('reposo');
  }

  /* `setDisc` era el modo vinilo del reproductor: el orbe viejo le ponía un disco girando.
     Aquí el equivalente honesto es que el conjunto se incline y ruede despacio mientras
     suena, con el nivel siguiendo la música (que es lo que ya hace `setAudio`). */
  function setDisc(on) { disco = on ? 1 : 0; }

  function setAudio(level = 0, bass = 0) {
    audio = Math.max(Math.min(1, level), Math.min(1, bass) * .8);
  }

  function estadoGetSet(nombre) {
    if (nombre === undefined) return estado;
    return ponEstado(nombre);
  }

  /* ── el bucle: 30 fps de techo, y 15 con «sin animaciones» ────────────────────
     No es un adorno: a 60 fps el navegador paga el doble de sombras y en el teléfono
     de gama media se come la batería. El `requestAnimationFrame` se PARA del todo con
     `pausa(true)` — lo que hace la cara al cambiar de pantalla y al quitar el manto. */
  const FPS = 30;
  let enBucle = false, congelado = false, antes = 0, acum = 0;
  function cuadro(ahora) {
    if (congelado) { enBucle = false; return; }
    requestAnimationFrame(cuadro);
    const dt = Math.max(0, Math.min(.25, (ahora - antes) / 1000 || 0));
    antes = ahora;
    acum += dt;
    const quieto = typeof document !== 'undefined'
      && document.documentElement.classList.contains('sin-movimiento');
    const paso = 1 / (quieto ? 15 : FPS);
    if (acum < paso) return;
    const dtP = acum; acum = 0;
    nivel += (quiere() - nivel) * Math.min(1, dtP * 9);
    chispa = Math.max(0, chispa - dtP * 2.2);
    if (disco) {
      orbe.objeto.rotation.z += dtP * .5;         // el vinilo rueda
      orbe.objeto.rotation.x = .35;               // y se ve como un plato, no como esfera
    } else {
      orbe.objeto.rotation.z *= Math.max(0, 1 - dtP * 3);   // y vuelve a su sitio
      orbe.objeto.rotation.x = 0;
    }
    orbe.pinta(dtP, nivel);
    ren.render(escena, camara);
  }
  function arranca() {
    if (enBucle || congelado) return;
    enBucle = true; antes = performance.now();
    requestAnimationFrame(cuadro);
  }
  function pausa(on) { congelado = !!on; if (!congelado) arranca(); }

  const redimensiona = () => {
    camara.aspect = innerWidth / innerHeight;
    camara.updateProjectionMatrix();
    ren.setSize(innerWidth, innerHeight);
  };
  addEventListener('resize', redimensiona);

  /**
   * Vestir con el atuendo puesto: reescribe la tabla y el color SE ACERCA, no salta.
   * Devuelve la tabla VIVA (`orbe.estados()`), no lo que regresa `vestir` del módulo:
   * ése es el booleano de `setEstado`, y envolverlo con `{...}` daba un objeto vacío.
   * Se descubrió en el navegador, no en la prueba: `prueba-manto.mjs` sólo miraba que
   * el método existiera.
   */
  function vestir(primario, secundario) {
    orbe.vestir(primario, secundario);
    return { ...orbe.estados() };
  }

  /** Cambiar de orbe sin recargar: suelta geometría, texturas y el `canvas`. */
  function destruir() {
    congelado = true; enBucle = false;
    turnoVoz++; turnoAct++;
    removeEventListener('resize', redimensiona);
    orbe.borrar();
    escena.remove?.(orbe.objeto);
    ren.dispose?.();
    ren.domElement?.parentNode?.removeChild(ren.domElement);
  }

  arranca();

  return {
    speak, burst, activate, stop, listen, setDisc, setAudio, pausa, vestir,
    estado: estadoGetSet,
    /** Los cinco colores vivos del atuendo puesto, para la consola y las sondas. */
    colores: () => ({ ...orbe.estados() }),
    /** Lo que cuesta: puntos, líneas y dibujos por frame. No es una promesa, es cuenta. */
    cifras: () => ({ ...orbe.cifras(), fps: FPS, pixelRatio: dpr, radio: RADIOS.esfera }),
    /** En qué punto del baile está la animación dispersiva (`null` si no hay). */
    vortice: () => orbe.vortice(),
    /** El objeto vivo, para `ui/sonda-orbe.html` y para depurar sin adivinar. */
    orbe: () => orbe,
    destruir,
  };
}
