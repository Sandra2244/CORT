/* ===== El orbe de la referencia: puntos y líneas, y barato =====
 *
 * Paso 1.1 de la Fase 1 nueva (ver `docs/PLAN-FASE-1.md`). NACE aparte: este módulo
 * no lo usa todavía `ui/index.html`. Se mide en `ui/sonda-orbe.html` y, si la dueña lo
 * aprueba, entonces sustituye al orbe de `js/orb.js`.
 *
 * Por qué existe en vez de retocar `orb.js`: el orbe actual paga ~5000 vértices, una
 * cáscara de 1280 triángulos con Fresnel y un recálculo de aristas cada 3 frames
 * (`orb.js:105-194`). La referencia del video es lo contrario: se ven puntos sueltos
 * unidos por líneas, con AIRE dentro de la esfera, y el color —no la forma— es lo que
 * cambia de estado. Con ~120 puntos y ~300 líneas estáticas se imita mejor y cuesta un
 * orden de magnitud menos en un portátil de 2 núcleos y 1,8 GiB.
 *
 * Las tres reglas de este módulo, que son las que lo hacen barato:
 *   1. La geometría se calcula UNA VEZ al nacer y no se toca más. Nada de reconstruir
 *      vértices en el bucle.
 *   2. El movimiento vive en el `vertex shader` y sale de `uniforms` (tiempo, nivel de
 *      audio, color). Un frame = escribir 4 números, no 360.
 *   3. Dibujos: 4 (puntos, líneas, polvo y halo). Con `modo:'bajo'`, 2 (puntos y halo).
 *
 * Es un módulo PURO en su parte de geometría: `puntosFibonacci` y `aristasCercanas` no
 * tocan THREE ni el DOM, así que `scripts/prueba-orbe.mjs` las mide en node sin WebGL,
 * igual que `traje.js` se mide con `prueba-colores.mjs`. `THREE` se INYECTA en
 * `creaOrbe` por el mismo motivo: sin WebGL no hay forma de probar el resto.
 */

/** Puntos sobre la esfera. 220 es lo que mide la bola de hilo del video (fotogramas
 *  vid-03/05/07: se ve como madeja, no como retícula); 2600 era el orbe viejo, y con
 *  120 —la primera medida de esta ronda— aún se leía como poliedro.
 *
 *  En la 2.19.0 sube a 340: la dueña pidió MÁS partículas («falta unas partículas en el
 *  orbe de referencia que debes agregarle al mio»). El número no se eligió por gusto ni
 *  por parecido al video: se MIDIO en `ui/sonda-orbe.html` sobre su portátil de 2 núcleos
 *  y gráficos integrados, que es el techo real. Con 220 la sonda marcaba
 *  15-22 cuadros por segundo y 0,05-0,07 ms de JavaScript por cuadro; 340 es el punto
 *  donde la madeja ya se ve cerrada sin que los cuadros por segundo caigan por debajo de
 *  los 220. Si el equipo afloja, se baja aquí y se vuelve a medir: lo que manda es la
 *  medida, no esta constante. */
export const N_PUNTOS = 340;

/** Vecinos más cercanos enlazados por punto. Con 6 salen ~640 líneas: el video tiene
 *  las vetas muy cruzadas. Pasando de 7 el brillo se suma tanto que el centro deja de
 *  tener aire y vuelve a parecer un disco (medido en la 2.12.0). */
export const VECINOS = 6;

/** El polvo de fondo, la otra mitad de lo que ella pidió. Son ESTRELLAS sueltas detrás
 *  del orbe, no más nudos de la esfera: el video tiene profundidad porque alrededor de la
 *  bola hay partículas que casi no se mueven, y aquí eso cuesta UN dibujo más con puntos
 *  de 1 a 3 px. En `modo:'bajo'` (el teléfono) no se dibujan. */
export const N_POLVO = 160;

/** Cuánto se sale cada punto del radio perfecto, de -GRANO/2 a +GRANO/2. El orbe del
 *  video NO es una esfera limpia: es un bulto. Sin este grano, por mucho que la onda
 *  empuje con el audio, en reposo se ve geométrico. */
export const GRANO = 0.14;

/** Radios de las cuatro piezas, en unidades del orbe. */
/** Radios de las cuatro piezas, en unidades del orbe. El halo va tan grande porque es
 *  un degradado casi transparente: con `RADIOS.halo` de 2,9 y su alfa viejo tapaba los
 *  puntos y la esfera se veía como un disco blanco (medido en el navegador).
 *
 *  `anillo` es el radio mayor del toro del vórtice, y se midió sobre el video
 *  `f7d16b9e…`: el anillo ocupa el 52 % del ancho de la pantalla y el agujero central
 *  es el 68 % de su diámetro exterior (§5.2 de REFERENCIAS-VIDEOS-JARVIS). Con el orbe
 *  en reposo ocupando ~22 %, el toro tiene que valer ~2,4 veces su diámetro. A 1,62
 *  se veía como un collar apretado alrededor de la esfera; a 1,95 el agujero queda
 *  limpio y el proporción se parece a la del video (re-medido en el navegador). */
export const RADIOS = Object.freeze({ esfera: 1, halo: 2.2, anillo: 1.95,
                                      polvoMin: 1.7, polvoMax: 3.4 });

/* ---------------- la geometría, en arrays planos (sin THREE) ---------------- */

/**
 * `n` puntos repartidos por la esfera SIN grumos (retícula de Fibonacci: el ángulo
 * áureo hace que ningún vecino quede apretado, cosa que un `Math.random()` no
 * garantiza). Devuelve `Float32Array` de `n*3` y, en el mismo orden, las fases
 * aleatorias pero **sembradas**: la misma semilla da el mismo orbe, y así la prueba
 * puede exigir que no cambie entre ejecuciones.
 */
export function puntosFibonacci(n = N_PUNTOS, radio = RADIOS.esfera, semilla = 7) {
  const pos = new Float32Array(n * 3);
  const fase = new Float32Array(n);
  const paso = Math.PI * (3 - Math.sqrt(5));   // ángulo áureo
  let s = semilla >>> 0;
  const rnd = () => {                          // xorshift32: determinista y barato
    s ^= s << 13; s >>>= 0; s ^= s >> 17; s ^= s << 5; s >>>= 0;
    return s / 4294967296;
  };
  for (let i = 0; i < n; i++) {
    const y = 1 - (i / (n - 1)) * 2;           // de +1 a -1
    const r = Math.sqrt(Math.max(0, 1 - y * y));
    const t = paso * i;
    // Un número por punto, sacado del MISMO xorshift sembrado: así la prueba puede
    // exigir que el bulto sea idéntico entre ejecuciones y que cambie con la semilla.
    const g = 1 + (rnd() - 0.5) * GRANO;
    pos[i * 3] = Math.cos(t) * r * radio * g;
    pos[i * 3 + 1] = y * radio * g;
    pos[i * 3 + 2] = Math.sin(t) * r * radio * g;
    fase[i] = rnd();
  }
  return { pos, fase };
}

/**
 * Aristas: para cada punto, sus `k` vecinos más cercanos. Devuelve pares
 * `[i,j,i,j,…]` **sin duplicados** (una línea por pareja, no dos) y sin bucles
 * propios. Se llama una sola vez, al nacer.
 *
 * Está escrito sin crear objetos dentro del bucle a propósito: la primera versión
 * empujaba `[distancia, j]` por cada pareja medida, y en el portátil de la dueña
 * (2 núcleos) eso eran ~14.000 mini-arrays y 73 ms de espera antes de ver el orbe.
 * Ahora reutiliza dos tablas y hace `k` barridos mínimos: mismo resultado, y la
 * medida está en `scripts/prueba-orbe.mjs`.
 */
export function aristasCercanas(pos, n = N_PUNTOS, k = VECINOS) {
  const dist = new Float64Array(n);      // distancia a cada candidato
  const usado = new Uint8Array(n);       // ya elegido como vecino
  const vistas = new Set();              // parejas ya enlazadas, en una sola dirección
  const pares = [];
  for (let i = 0; i < n; i++) {
    const ix = pos[i * 3], iy = pos[i * 3 + 1], iz = pos[i * 3 + 2];
    for (let j = 0; j < n; j++) {
      const dx = pos[j * 3] - ix, dy = pos[j * 3 + 1] - iy, dz = pos[j * 3 + 2] - iz;
      dist[j] = dx * dx + dy * dy + dz * dz;
      usado[j] = 0;
    }
    dist[i] = Infinity;                  // uno no es su propio vecino
    usado[i] = 1;
    for (let m = 0; m < k; m++) {
      let mejor = -1, menor = Infinity;
      for (let j = 0; j < n; j++) {
        if (!usado[j] && dist[j] < menor) { menor = dist[j]; mejor = j; }
      }
      if (mejor < 0) break;
      usado[mejor] = 1;
      const a = Math.min(i, mejor), b = Math.max(i, mejor);
      const clave = a * n + b;
      if (vistas.has(clave)) continue;
      vistas.add(clave);
      pares.push(a, b);
    }
  }
  return new Uint16Array(pares);
  /* `Uint16Array`, y no es un detalle de gusto: Three.js elige el tipo de índice que le
     dice a OpenGL mirando el array, y con un `Int32Array` pedía un tipo que no existe.
     Medido en el navegador de la dueña: `GL_INVALID_ENUM: glDrawElements` y las líneas
     no salían. Con 120 puntos sobran los 65.535 de un entero corto; si algún día
     `N_PUNTOS` pasara de eso, hay que cambiar a `Uint32Array` y comprobar que el WebGL
     del aparato soporte índices de 32 bits. Lo vigila `scripts/prueba-orbe.mjs` [2]. */
}

/**
 * El polvo de fondo: `n` estrellas sueltas entre `RADIOS.polvoMin` y `RADIOS.polvoMax`.
 * Es la otra mitad de lo que pidió la dueña en la 2.19.0 («falta unas partículas en el
 * orbe de referencia»): en el video hay profundidad porque ALREDEDOR de la bola hay
 * puntos que casi no se mueven, y eso aquí cuesta UN dibujo más con partículas de 1 a
 * 3 px — ni aristas, ni morph, ni Fresnel.
 *
 * Va en una CÁSCARA HUECA y no en el volumen entero a propósito: si una estrella cayera
 * dentro del orbe se leería como un nudo suelto de la madeja, que es justo lo que el
 * grano (`GRANO`) y la retícula de Fibonacci no quieren. El radio sale de la RAÍZ CÚBICA
 * de una uniforme, que es el sesgo que reparte parejo por VOLUMEN: sin él, un radio
 * uniforme amontona todo cerca de la superficie y el campo se ve como una cáscara pintada.
 *
 * Es la MISMA xorshift sembrada de `puntosFibonacci`, con la semilla revuelta
 * (`^ 0x9e3779b9`) para que las dos funciones no arranquen con el mismo valor. Dicho con
 * la honestidad de la batería de mutaciones (M21, 2026-10-27): QUITAR esa revuelta **no
 * se pone roja**, porque la esfera consume 2 valores por punto y el polvo 4 por estrella,
 * así que las dos corrientes se separan ya en el segundo número y ninguna estrella acaba
 * mirando hacia donde mira un nudo. El candado de la suite protege el RESULTADO —que el
 * campo no se parezca a la retícula—, que es como debe ser: sobrevive a un refactor. La
 * revuelta es higiene, no la que sostiene el resultado.
 */
export function polvoEstrella(n = N_POLVO, semilla = 7) {
  const pos = new Float32Array(n * 3);
  const fase = new Float32Array(n);
  let s = (semilla ^ 0x9e3779b9) >>> 0;
  const rnd = () => {
    s ^= s << 13; s >>>= 0; s ^= s >> 17; s ^= s << 5; s >>>= 0;
    return s / 4294967296;
  };
  for (let i = 0; i < n; i++) {
    const y = 1 - rnd() * 2;                    // latitud uniforme, sin grumos en los polos
    const r = Math.sqrt(Math.max(0, 1 - y * y));
    const t = rnd() * Math.PI * 2;
    const d = RADIOS.polvoMin + (RADIOS.polvoMax - RADIOS.polvoMin) * Math.cbrt(rnd());
    pos[i * 3] = Math.cos(t) * r * d;
    pos[i * 3 + 1] = y * d;
    pos[i * 3 + 2] = Math.sin(t) * r * d;
    fase[i] = rnd();
  }
  return { pos, fase };
}

/* ---------------- los estados, que son el color ---------------- */

import { estados as coloresDelTraje, POR_DEFECTO } from './traje.js';

/**
 * Lo que cada estado aporta ADEMÁS del color: `empuje` cuánto agranda la onda el
 * nivel de audio y `giro` radianes por segundo. Los colores NO están aquí — se
 * piden a `traje.js` (paso 1.2 de `docs/PLAN-FASE-1.md`), porque un color escrito a
 * mano en este archivo sería un orbe que no se viste con el atuendo de la dueña.
 */
const MOVIMIENTO = Object.freeze({
  reposo:  { opacidad: 0.82, empuje: 0.030, giro: 0.055 },
  escucha: { opacidad: 0.92, empuje: 0.075, giro: 0.160 },
  piensa:  { opacidad: 0.88, empuje: 0.055, giro: 0.620 },
  habla:   { opacidad: 0.98, empuje: 0.130, giro: 0.230 },
  error:   { opacidad: 0.88, empuje: 0.040, giro: 0.090 },
});

/** La tabla de un atuendo: el color de `traje.js` + el movimiento de arriba. */
export function estadosDelTraje(primario, secundario) {
  const c = coloresDelTraje(primario, secundario);
  const salida = {};
  for (const k of Object.keys(MOVIMIENTO)) {
    salida[k] = Object.freeze({ a: c[k].a, b: c[k].b, ...MOVIMIENTO[k] });
  }
  return Object.freeze(salida);
}

/**
 * Los cinco estados con el atuendo de fábrica (`Cortana` en `Paleta.java`). Con
 * éstos el orbe se ve como en los fotogramas de la referencia: blanco-frío en
 * reposo, cian al oír, turquesa al pensar, lima al hablar y rojo al fallar.
 * `creaOrbe(..., {traje})` y `vestir()` usan la misma función con otros colores.
 */
export const ESTADOS = estadosDelTraje(POR_DEFECTO.primario, POR_DEFECTO.secundario);

/** El estado con el que se enciende la cara: no llama la atención. */
export const ESTADO_INICIAL = 'reposo';

/* ---------------- los shaders ---------------- */

/* Una sola onda por vértice, a lo largo del radio. Se calcula en la GPU para todos los
   puntos y todas las líneas a la vez: el coste por frame es escribir los uniforms, no
   tocar vértices (regla 1 del archivo).
   Hay DOS vertex shader a propósito, no uno retocado con `replace()`: el de los puntos
   necesita el tamaño en pantalla y el de las líneas no, y una cadena que se parchea a
   mano es exactamente como se cayó la cara en la 2.10.0. El trozo común (`ONDA` +
   `MORFO`) se concatena en las DOS cadenas, que es lo que comprueba
   `scripts/prueba-orbe.mjs` [4]: si un día el de las líneas deja de llevar el vórtice,
   la explosión partiría los hilos en dos mundos distintos.
   `uTamano` se declara en la cabecera común y sólo lo lee el shader de los puntos: un
   uniform declarado y no usado es legal en GLSL (Three ni le busca ubicación), mientras
   que declararlo dos veces —como hacía la versión anterior— es lo que deja el parcheo
   de texto como único modo de mantener las dos copias sincronizadas.
   Lo mismo pasa con `vFondo`, la profundidad de cada vértice (de 0, lo más cerca de la
   lente, a 1, lo más lejos): se declara en ONDA porque es la cabecera de los TRES
   vertex, lo escribe sólo INCLINA —que el polvo no incluye— y lo leen los dos
   fragmentos del orbe. El del polvo no lo declara: en GLSL un `varying` que nadie lee
   no cuesta nada, y duplicar la declaración sí. */
/* La distancia de la cámara, UNA SOLA VEZ en el repo. No es un adorno de encuadre:
   §5.2 de `docs/REFERENCIAS-VIDEOS-JARVIS.md` mide el reposo del video en ~1/3 del alto
   de la pantalla, y con objetivo de 55° eso sale de 5,8 unidades (2 / (2·tan27,5°·5,8) =
   0,331). `orbe-cara.js` pone la cámara AQUÍ y este archivo usa el mismo número dos
   veces: como referencia del `gl_PointSize` y como centro del reparto de profundidad de
   `vFondo`. Por eso no puede quedar escrito a mano en los dos archivos. */
export const DISTANCIA = 5.8;

const ONDA = /* glsl */`
uniform float uTiempo;
uniform float uNivel;
uniform float uEmpuje;
uniform float uDispersa;
uniform float uVortice;
uniform float uPortal;
uniform float uTamano;
attribute float aFase;
varying float vBrillo;
varying float vCalor;
varying float vFondo;
void main() {
  float f = aFase * 6.2831853;
  float onda = sin(uTiempo * 1.7 + f + position.y * 3.1);
  float respira = 1.0 + (uEmpuje + uNivel * 0.16) * onda;
  vBrillo = clamp(0.45 + 0.55 * onda * (0.35 + uNivel), 0.0, 1.0);
  vec3 p = position * respira;`;

/* La ANIMACIÓN DISPERSIVA, que es lo que ella pidió del video `f7d16b9e…`: «cuando
   responde CORT o ejecuta una respuesta forma esa clase de vórtice, hazlo igual que en
   el video». Las medidas que están aquí dentro no se inventaron: son los píxeles del
   fotograma de 6,5 s y los segundos de cada fase, en
   `docs/REFERENCIAS-VIDEOS-JARVIS.md` §5.2.
     - `uDispersa`: cada punto sale disparado hacia fuera a SU distancia (depende de
       `aFase`, como en el video, donde la explosión no es una esfera que crece sino un
       abanico de estelas desiguales).
     - `uVortice`: torsión alrededor del eje Y, mayor en el ecuador que en los polos.
     - `uPortal`: mezcla esfera -> TORO. Radio mayor `RADIOS.anillo` (1,95) y tubo la
       quinta parte de ese radio (0,18 R, o sea 0,35), que deja el agujero central al
       0,70 del diámetro exterior; en el video medido es 0,68 (§5.2). El tubo va ATADO
       al radio en vez de ser un número suelto: si algún día se mueve `RADIOS.anillo`,
       la proporción del agujero se conserva sola. La INCLINACIÓN del anillo no está
       aquí: vive en `INCLINA`, al final del vertex shader, y el porqué está explicado
       allí (no es un detalle: la primera versión la puso en el espacio del objeto y el
       anillo se veía de canto).
   Por qué el `ph` del tubo depende de `position.y` y no sólo de `aFase`: los vecinos
   enlazados por una línea tienen fases aleatorias distintas, y con `ph` al azar cada
   hilo del plexo cruzaría el tubo de lado a lado. Atando `ph` a la latitud, los vecinos
   siguen siendo vecinos al formar el anillo y la corona se lee como madeja, no como
   telaraña.
   Y NADA de acentos graves dentro de estas cadenas: un acento grave cierra el literal,
   el módulo deja de parsear y la cara se queda en blanco sin decir nada. Pasó, y el
   `node --check` de la prueba no lo cazó porque el archivo seguía siendo JS válido.
   (Escribir aquí un cierre de comentario de bloque también rompe el archivo: es la misma
   familia de error, y por eso el candado está en `scripts/prueba-orbe.mjs` [4].) */
const MORFO = /* glsl */`
  // El anillo, una vez montado, AVANZA sobre si mismo: en el video la corona no es un toro
  // quieto, gira y los puntos calientes dan vueltas con el. El avance va MULTIPLICADO por
  // uPortal, asi que con el portal apagado el angulo es el de siempre y el reposo queda
  // identico al de la 2.16.0. (Aqui dentro solo ASCII: esto se manda a la GPU.)
  float th = atan(position.z, position.x) + uTiempo * 0.22 * uPortal;
  if (uDispersa > 0.001) {
    vec3 dir = normalize(position);
    // El abanico: cada punto sale a SU distancia y el recorrido es MAS largo (hasta
    // 2,4 radios en vez de 2,0) para que la nube se lea como estelas desiguales y no
    // como una esfera que crece. Medido sobre docs/referencias/f7-dispersa-030.jpg.
    p += dir * uDispersa * (0.35 + 2.05 * aFase);
    // Y el estallido se APLASTA en Y mientras se abre: en el fotograma la dispersion es
    // una CORONA con el centro vacio, no una bola de puercoespin. Medio radio vertical.
    p.y *= 1.0 - 0.55 * uDispersa;
    float tor = uVortice * (1.2 - abs(dir.y)) * 1.9;
    float cs = cos(tor), sn = sin(tor);
    p = vec3(p.x * cs - p.z * sn, p.y, p.x * sn + p.z * cs);
  }
  if (uPortal > 0.001) {
    float R = ${RADIOS.anillo};
    float rt = R * 0.18;
    float ph = position.y * 3.1 + f * 0.9 + uTiempo * 0.9;
    vec3 t = vec3((R + rt * cos(ph)) * cos(th), rt * sin(ph), (R + rt * cos(ph)) * sin(th));
    p = mix(p, t, clamp(uPortal, 0.0, 1.0));
  }
  // Los puntos calientes que recorren la corona. En el video son DOS O TRES manchas que
  // corren a distinta velocidad, no un aro uniforme: por eso hay aqui TRES viajeros de
  // coseno (uno a -1,6 rad/s, otro doblado y en sentido contrario, otro a +2,3) y se
  // guarda el MAS caliente con max, en vez de SUMARLOS. Sumarlos pintaba la corona entera
  // de blanco y el agujero volvia a desaparecer, el mismo fallo medido de las lineas.
  // vCalor es 0 en reposo: la cara se ve igual que en la 2.16.0 cuando no ejecuta nada.
  // (Solo ASCII aqui dentro: esto se manda a la GPU, y un acento grave cierra el literal.)
  float v1 = 0.5 + 0.5 * cos(th - uTiempo * 1.6);
  float v2 = 0.5 + 0.5 * cos(th * 2.0 + uTiempo * 1.1 - 2.1);
  float v3 = 0.5 + 0.5 * cos(th + uTiempo * 2.3 + 2.0);
  float calor = max(v1 * v1, max(v2 * v2 * v2, v3 * v3));
  // El foco vale tambien durante la explosion, no solo con el anillo montado: en el
  // fotograma de la dispersion hay manchas quemadas sueltas sobre la nube, no un flash
  // parejo. Por eso el termino base baja de 0.80 a 0.45 y los viajeros entran con max().
  float foco = max(uPortal, uDispersa);
  vCalor = clamp(uDispersa * 0.45 + calor * foco, 0.0, 1.0);`;

/* La inclinación del anillo se aplica en ESPACIO DE CÁMARA, no dentro del toro.
   Costó tres pantallazos y los tres están medidos:

   1) El toro nace en el plano XZ del objeto (su eje es Y) y la cámara está en +Z
      mirando al origen: SIN inclinar nada se ve EXACTAMENTE DE CANTO, una raya, y el
      agujero no existe. En el video el aro se ve casi de frente: medido sobre
      docs/referencias/f7-anillo-065.jpg (sección 5.2 de REFERENCIAS-VIDEOS-JARVIS) son
      215 x 206 px, una elipse de 0,96, o sea unos 16 grados de apertura. Se ha puesto
      20 (70 grados de giro = 1,2217 rad), que es el mismo aspecto con un dedo más de
      profundidad: proyecta 0,94 medido en el navegador.
   2) Ese giro NO puede hacerse en el espacio del objeto, porque el orbe entero rota
      en Y (el `giro` de la respiración). Rotar en Y no toca el eje Y, así que el
      plano del anillo parece a salvo... pero si lo inclinas ANTES de esa rotación,
      lo que inclinas es el eje sobre el que después gira la matriz: el aro barría la
      cámara y a los pocos segundos volvía a verse de canto. Medido en el navegador
      con la primera versión: caja proyectada 272 x 315 px, más ALTO que ancho.
      Aplicando el giro DESPUES de modelViewMatrix la inclinación es de pantalla y al
      spin del orbe le deja de importar: el anillo mira a la cámara siempre.
   3) Y el giro tiene que pivotar ALREDEDOR DEL CENTRO DEL OBJETO, no del origen del
      espacio de cámara. El origen de ese espacio es la LENTE, así que girar ahí barre
      la trayectoria: con el anillo a 7,2 de la cámara, inclinar 70 grados mandaba el
      orbe 6,8 unidades hacia arriba y la caja proyectada se quedaba en 93 x 93 px en
      una esquina (medido en el navegador, segunda versión). Se suma y se resta la
      columna de traslación de `modelViewMatrix`, que es lo mismo que pivotar sobre el
      propio orbe.

   El angulo va MULTIPLICADO por uPortal: con el portal apagado el orbe está donde
   siempre (reposo idéntico al de la 2.16.0), y al montarse el anillo todo el conjunto
   se gira hacia la cara, que es el gesto de "volverse a mirar" del video. */
/* Se exporta por el mismo motivo que `RADIOS`: es un número MEDIDO en el video, y la
   prueba tiene que poder exigir que el shader lo lleva dentro. Sin esto, cambiar el
   ángulo a 0 (que es quitar el anillo de la cara y dejarlo de canto) pasaba verde. */
export const GIRO = 1.2217;
/* ── EL AIRE: lo de atrás se apaga ──────────────────────────────────────────────
   Medido en pantalla el 27/10, el orbe se leía como una bola de alambre y no como la
   madeja con profundidad de la referencia. La cámara está a 5,8: el ecuador frontal
   queda a ~4,8 de la lente y el dorsal a ~6,8, y como el relleno es aditivo los ~1.057
   hilos de la cara de detrás se SUMABAN a los de delante. Apagar el fondo es lo único
   que separa las dos mitades sin borrar un vértice (regla 1 del archivo), y cuesta un
   `varying` y una resta por fragmento.
     El reparto se calcula sobre la distancia YA INCLINADA (`vis.z`), no sobre `mv.z`:
   con el anillo montado la corona se gira hacia la cara, y lo que tiene que apagarse es
   lo que en ese momento queda lejos de la lente. `vFondo` sale 0 a 4,8 de la lente y 1
   dos unidades y media más atrás.
     Y va DENTRO de `INCLINA`, no de `MORFO`, por la misma razón de siempre: MORFO se
   concatena también en el shader del polvo, que no se inclina ni tiene `vis`.
     Este bloque está FUERA de la cadena GLSL a propósito. El candado [4] de
   `scripts/prueba-orbe.mjs` no admite ni `/*` ni acentos graves dentro de los seis
   textos, y los dos tienen su historia: el 27/10 escribí uno de estos comentarios con
   backticks, el literal se cerró antes de tiempo, y la cara se quedó en blanco. */
const INCLINA = /* glsl */`
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  vec3 centro = modelViewMatrix[3].xyz;
  vec3 r = mv.xyz - centro;
  float ang = uPortal * ${GIRO};
  float ci = cos(ang), si = sin(ang);
  vec4 vis = vec4(r.x + centro.x,
                  r.y * ci - r.z * si + centro.y,
                  r.y * si + r.z * ci + centro.z, mv.w);
  vFondo = clamp((-vis.z - (${DISTANCIA} - 1.0)) / 2.6, 0.0, 1.0);
  gl_Position = projectionMatrix * vis;`;

const VERT_LINEAS = ONDA + MORFO + INCLINA + /* glsl */`
}`;

/* Por qué el tamaño del punto está topeado y lleva 7,2 dentro.
   `gl_PointSize` son PÍXELES DEL APARATO, no unidades del orbe, y crece al acercar la
   cámara. La primera versión usó `260.0 / -mv.z`, que a 4,4 de distancia daba puntos de
   190 px: en vez del encaje de hilos del video, una mancha blanca que tapaba el encaje.
   Ahora: el tamaño que pide el anfitrión, medido a la distancia de cámara de 7,2,
   corregido por la distancia real de cada punto y topeado entre 1 y 9 px. El pixel
   ratio ya viene dentro de `uTamano` porque GL no lo sabe.
   El `1.0 + vCalor * 0.5` de dentro: al dispersarse, los puntos del video se ven más
   gordos (son estelas quemadas por el obturador de la cámara). Medio punto de tamaño es
   lo que hay; el tope de 9 px sigue ahí para que la explosión no tape la cara. */
const VERT_PUNTOS = ONDA + MORFO + INCLINA + /* glsl */`
  // gl_PointSize son píxeles del aparato: ver el comentario de VERT_PUNTOS. Se mide
  // sobre vis.z, la profundidad YA inclinada, para que el tamaño acompañe al anillo.
  gl_PointSize = clamp(uTamano * (${DISTANCIA} / max(0.5, -vis.z)) * (1.0 + vCalor * 0.5), 1.0, 9.0);
}`;

/* Los puntos se dibujan como redondos suaves: `gl_PointCoord` evita una textura.
   El `mix` hacia `vec3(0.85, 0.97, 1.0)` es el núcleo blanco-cian de las estelas del
   video (`#90EFFF` medido sobre el fotograma de 1000 px): el color del traje manda en
   reposo, y el vórtice lo aclara sin pintarlo de un color propio.
   Lo que añade la pasada de los videos (27/10): **cada punto del video tiene un centro
   quemado**, no es un disco plano de un solo color. `nucleo` mide el quinto central de la
   mota y lo aclara hacia el mismo blanco-cian de siempre, así que la madeja deja de
   parecer un encaje de hilo pintado y pasa a parecer luz. Cuesta una `smoothstep` más por
   fragmento sobre ~340 motas de 3 px: nada. El `0.85` del brillo base sube desde `0.65`
   por el mismo motivo medido en pantalla —con la cámara más cerca los puntos se veían
   más grandes y más apagados a la vez—. */
const FRAG_PUNTOS = /* glsl */`
uniform vec3 uColorA;
uniform float uOpacidad;
varying float vBrillo;
varying float vCalor;
varying float vFondo;
void main() {
  float d = length(gl_PointCoord - vec2(0.5));
  float a = smoothstep(0.5, 0.06, d);
  if (a < 0.02) discard;
  float nucleo = smoothstep(0.20, 0.0, d);
  vec3 blanco = vec3(0.85, 0.97, 1.0);
  vec3 c = mix(uColorA, blanco, min(1.0, 0.75 * vCalor + 0.5 * nucleo));
  gl_FragColor = vec4(c * (0.85 + 0.7 * vBrillo + 0.55 * vCalor),
                      a * uOpacidad * (1.0 - 0.45 * vFondo));
}`;

/* El alfa de las líneas se apaga durante el morfeado. Con las aristas vivas la explosión
   y el anillo se tapaban con una tela blanca y el agujero del vórtice desaparecía; en el
   video la dispersión se hace con ESTRELLAS de partículas, no con una malla. El morfeado
   sigue dibujando líneas (el `modo bajo` no es la única excepción), pero al 7 % de su
   opacidad, que es lo que queda de 1 − 0,93·máx(dispersa, portal) con ambos a tope.
   En la 2.19.0 el factor sube de 0,85 a 0,93 porque con 1.057 líneas (antes 700) la tela
   volvía a ganar: medido en la sonda, el estallido seguía pareciendo una bola de alambre
   y no la corona de estelas del fotograma `f7-dispersa-030.jpg`.
   Y en la pasada de los videos (27/10) baja también el **piso** del alfa, de 0,42 a 0,26,
   subiendo a cambio lo que aporta `vBrillo` (0,55 → 0,62) y `vCalor` (0,3 → 0,34). La
   razón es una pantalla, no una opinión: con la cámara más cerca, el encaje de hilos se
   comía la bola y los puntos —que en la referencia son LO QUE SE VE— desaparecían detrás.
   Ahora la madeja es tenue y desigual, como en `f7-orbe-000.jpg`, y el brillo lo ponen
   los nudos. */
const FRAG_LINEAS = /* glsl */`
uniform vec3 uColorB;
uniform float uOpacidad;
uniform float uDispersa;
uniform float uPortal;
varying float vBrillo;
varying float vCalor;
varying float vFondo;
void main() {
  float tela = 1.0 - 0.93 * max(uDispersa, uPortal);
  vec3 c = mix(uColorB, vec3(0.85, 0.97, 1.0), 0.6 * vCalor);
  gl_FragColor = vec4(c * (0.5 + 0.9 * vBrillo + 0.5 * vCalor),
                      uOpacidad * (0.26 + 0.62 * vBrillo + 0.34 * vCalor) * tela
                      * (1.0 - 0.72 * vFondo));
}`;

/* ---------------- el polvo de fondo ---------------- */

/* Comparte la CABECERA (`ONDA`) con los puntos y las líneas: el tiempo, el nivel, la
   onda y el `vBrillo` salen de los mismos uniforms, que es la regla 2 del archivo (un
   frame = escribir los uniforms, no recalcular nada). Lo que NO comparte es el `MORFO`:
   el polvo no se mete en el toro ni se enlaza con nadie. Lo que sí hace durante la
   explosión es SALIR HACIA FUERA a su distancia, con menos alcance que los nudos de la
   esfera: en el video de referencia la dispersión se ve como un campo de estelas que se
   abre, y eso no se consigue con 340 puntos, se consigue con las partículas de atrás.
   Tampoco lleva `INCLINA`: la inclinación del anillo es un gesto del orbe, y el fondo
   tiene que quedarse donde estaba para que el conjunto siga teniendo profundidad.
   El tamaño va por fuera del tope de los puntos (1 a 3 px, no 1 a 9): una estrella gorda
   taparía la madeja. */
const VERT_POLVO = ONDA + /* glsl */`
  vec3 dir = normalize(position);
  p += dir * uDispersa * (0.35 + 1.15 * aFase);
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  gl_Position = projectionMatrix * mv;
  gl_PointSize = clamp(uTamano * 0.7 * (${DISTANCIA} / max(0.5, -mv.z)), 1.0, 3.0);
}`;

/* El alfa del polvo es MEDIA del del orbe: si brillara igual que los nudos, la bola se
   vería dentro de una niebla y el centro perdería el aire que se midió en la 2.12.0. El
   0,34 con el que nació esta capa en la 2.19.0 quedó DEMASIADO fino —medido en la sonda:
   se contaban con los dedos las estrellas del fotograma—, y subió a 0,55 sin que el orbe
   perdiera aire: sigue por debajo del brillo de un nudo cualquiera. */
const FRAG_POLVO = /* glsl */`
uniform vec3 uColorA;
uniform float uOpacidad;
varying float vBrillo;
void main() {
  float d = length(gl_PointCoord - vec2(0.5));
  float a = smoothstep(0.5, 0.10, d);
  if (a < 0.02) discard;
  gl_FragColor = vec4(uColorA * (0.34 + 0.62 * vBrillo), a * uOpacidad * 0.55);
}`;

/** Los seis textos GLSL, exportados sólo para que `prueba-orbe.mjs` los lea: en node
 *  no hay GPU, pero sí se puede exigir que un shader declare lo que usa. */
export const SHADERS = Object.freeze({
  puntos: VERT_PUNTOS, lineas: VERT_LINEAS,
  fragPuntos: FRAG_PUNTOS, fragLineas: FRAG_LINEAS,
  polvo: VERT_POLVO, fragPolvo: FRAG_POLVO,
});

/* ---------------- el ritmo de la animación dispersiva ---------------- */

/* Los cuatro tramos, en SEGUNDOS contados sobre el video `f7d16b9e…` (explosión 0,5 s,
   el anillo se establece en 2,0 s, se mantiene 4,0 s mientras ejecuta, y se cierra en
   1,5 s). Coinciden con lo que ya había calculado a ojo el orbe viejo en
   `orb.js:341-342` (1700 ms de vórtice, 3200 ms de portal), así que el tempo no se
   toca: lo que cambia es que aquí la forma la mezcla la GPU.
   `responde` es más corto a propósito: al contestar no hay ventana que enmarcar, y un
   anillo de 8 segundos taparía la charla. */
export const RITMOS = Object.freeze({
  activa:   Object.freeze({ estalla: 0.5, monta: 2.0, mantiene: 4.0, cierra: 1.5 }),
  responde: Object.freeze({ estalla: 0.4, monta: 1.2, mantiene: 1.8, cierra: 1.2 }),
});

const recorta = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);
const tramo = (t, a, b) => recorta((t - a) / Math.max(1e-6, b - a));
const suave = (x) => x * x * (3 - 2 * x);        // smoothstep, sin costuras en los bordes

/**
 * La forma de la explosión a los `t` segundos de haberla disparado: los tres valores que
 * quieren los uniforms. Es una FUNCIÓN PURA por el mismo motivo que `puntosFibonacci`:
 * en node no hay GPU, pero sí se puede exigir que a los 0,5 s esté toda dispersa, que a
 * los 2,5 s el portal esté al máximo y que al terminar vuelva a 0 sin saltos.
 * Devuelve `null` antes de empezar y pasados `total` segundos: el orbe vuelve solo.
 */
export function formaDelVortice(t, rit = RITMOS.activa) {
  const e = rit.estalla, m = e + rit.monta, k = m + rit.mantiene, f = k + rit.cierra;
  if (t < 0 || t >= f) return null;
  let d, p;
  if (t < e) { d = suave(tramo(t, 0, e)); p = 0; }
  else if (t < m) { const x = suave(tramo(t, e, m)); d = 1 - 0.75 * x; p = x; }
  else if (t < k) { d = 0.25; p = 1; }
  else { const x = suave(tramo(t, k, f)); d = 0.25 * (1 - x); p = 1 - x; }
  /* El vórtice (la torsión en espiral) manda mientras hay dispersión y deja de mandar
     cuando el anillo ya está montado: en el video la corona gira, pero no se retuerce. */
  return { dispersa: d, portal: p, vortice: Math.max(d, p * 0.35), total: f };
}

/* ---------------- el orbe ---------------- */

/**
 * Monta el orbe y devuelve su mando. `THREE` entra por parámetro (así node puede
 * importar este archivo sin WebGL). El bucle de animación NO vive aquí: quien llama
 * es el anfitrión con `pinta(segundos, nivel)`, para que el freno, el modo juego y una
 * pestaña oculta puedan parar el `requestAnimationFrame` desde fuera.
 */
export function creaOrbe(THREE, opciones = {}) {
  const n = opciones.puntos || N_PUNTOS;
  const k = opciones.vecinos || VECINOS;
  const modo = opciones.modo || 'pleno';           // 'pleno' | 'bajo' (sin líneas)
  // El atuendo con el que nace. Sin `traje`, el de fábrica: la tabla de `ESTADOS`.
  let tabla = opciones.traje && opciones.traje.length === 2
    ? estadosDelTraje(opciones.traje[0], opciones.traje[1]) : ESTADOS;
  const geo = puntosFibonacci(n, RADIOS.esfera, opciones.semilla || 7);
  const aristas = aristasCercanas(geo.pos, n, k);

  const colorA = new THREE.Color(tabla[ESTADO_INICIAL].a);
  const colorB = new THREE.Color(tabla[ESTADO_INICIAL].b);
  const comp = {
    uTiempo: { value: 0 },
    uNivel: { value: 0 },
    uEmpuje: { value: tabla[ESTADO_INICIAL].empuje },
    uOpacidad: { value: tabla[ESTADO_INICIAL].opacidad },
    uColorA: { value: colorA },
    uColorB: { value: colorB },
    uTamano: { value: opciones.tamano || 2.8 },   // píxeles lógicos a 7,2 de cámara
    /* Los tres mandos de la animación dispersiva. Nacen en 0: sin `dispara()`, el orbe
       se comporta exactamente como en la 2.16.0. */
    uDispersa: { value: 0 },
    uVortice: { value: 0 },
    uPortal: { value: 0 },
  };

  const objeto = new THREE.Group();

  const geomPuntos = new THREE.BufferGeometry();
  geomPuntos.setAttribute('position', new THREE.BufferAttribute(geo.pos, 3));
  geomPuntos.setAttribute('aFase', new THREE.BufferAttribute(geo.fase, 1));
  const puntos = new THREE.Points(geomPuntos, new THREE.ShaderMaterial({
    uniforms: comp, vertexShader: VERT_PUNTOS, fragmentShader: FRAG_PUNTOS,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  }));
  objeto.add(puntos);

  let lineas = null;
  if (modo !== 'bajo') {
    // Una sola geometría indexada: los mismos vértices de los puntos, enlazados.
    const geomLineas = new THREE.BufferGeometry();
    geomLineas.setAttribute('position', geomPuntos.getAttribute('position'));
    geomLineas.setAttribute('aFase', geomPuntos.getAttribute('aFase'));
    geomLineas.setIndex(new THREE.BufferAttribute(aristas, 1));
    lineas = new THREE.LineSegments(geomLineas, new THREE.ShaderMaterial({
      uniforms: comp, vertexShader: VERT_LINEAS, fragmentShader: FRAG_LINEAS,
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    }));
    objeto.add(lineas);
  }

  /* El polvo de fondo, SÓLO en `pleno`. Es el cuarto dibujo y el más barato de los
     cuatro (partículas de 1 a 3 px, sin aristas y sin morph), pero en el teléfono
     cuenta como relleno de pantalla y ahí no se paga: `modo:'bajo'` se queda en dos
     dibujos, que es lo que midió la sonda en el aparato de la dueña. */
  let polvo = null, nPolvo = 0;
  if (modo !== 'bajo') {
    const geoPolvo = polvoEstrella(opciones.polvo || N_POLVO, opciones.semilla || 7);
    nPolvo = geoPolvo.pos.length / 3;
    const geomPolvo = new THREE.BufferGeometry();
    geomPolvo.setAttribute('position', new THREE.BufferAttribute(geoPolvo.pos, 3));
    geomPolvo.setAttribute('aFase', new THREE.BufferAttribute(geoPolvo.fase, 1));
    polvo = new THREE.Points(geomPolvo, new THREE.ShaderMaterial({
      uniforms: comp, vertexShader: VERT_POLVO, fragmentShader: FRAG_POLVO,
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    }));
    objeto.add(polvo);
  }

  // El halo: un degradado radial dibujado a mano en un canvas de 128 px. Da el "glow"
  // de la referencia sin post-proceso, que en 2 núcleos no se paga.
  // En la 2.19.0 el centro es MÁS BRILLANTE y más CEÑIDO (los dos primeros tramos de la
  // escala). La dueña pidió el núcleo encendido del video: ahí la bola no es un cascarón
  // de hilo, tiene un fuego dentro. Cuesta CERO dibujos — es pintura sobre la misma
  // textura de 128 px —, y por eso se puede pagar aunque el aparato vaya justo.
  const cnv = document.createElement('canvas');
  cnv.width = cnv.height = 128;
  const g = cnv.getContext('2d');
  const rad = g.createRadialGradient(64, 64, 3, 64, 64, 62);
  rad.addColorStop(0, 'rgba(255,255,255,0.80)');
  rad.addColorStop(0.16, 'rgba(255,255,255,0.34)');
  rad.addColorStop(0.42, 'rgba(255,255,255,0.09)');
  rad.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = rad; g.fillRect(0, 0, 128, 128);
  /* LAS PÚAS del núcleo. En el fotograma de arranque del video
     (`docs/referencias/f7-orbe-000.jpg`, t = 0,0 s) el centro no es una bola difusa: es un
     punto quemado del que salen SEIS púas cortas. Se pintan en la MISMA textura de 128 px
     —tres trazos con degradado longitudinal, girados 60° cada uno—, así que cuestan CERO
     dibujos y CERO uniforms: es pintura, y por eso se puede pagar en un aparato de 2
     núcleos. `globalCompositeOperation = 'lighter'` para que las púas SUMEN sobre el
     degradado en vez de taparlo con su alfa. */
  g.save();
  g.translate(64, 64);
  g.globalCompositeOperation = 'lighter';
  g.lineWidth = 1.6;
  for (let i = 0; i < 3; i++) {
    g.rotate(Math.PI / 3);
    const pua = g.createLinearGradient(-58, 0, 58, 0);
    pua.addColorStop(0, 'rgba(255,255,255,0)');
    pua.addColorStop(0.5, 'rgba(255,255,255,0.85)');
    pua.addColorStop(1, 'rgba(255,255,255,0)');
    g.strokeStyle = pua;
    g.beginPath(); g.moveTo(-58, 0); g.lineTo(58, 0); g.stroke();
  }
  g.restore();
  const texHalo = new THREE.CanvasTexture(cnv);
  /* El color del halo es el **primario** del estado, no el secundario. Con `colorB` el
     núcleo quemado del video se convertía en un azulillo de fondo: en los fotogramas
     (los cuatro paneles de `docs/referencias` y los dos videos leídos el 27/10) lo más
     brillante de la bola ES el centro, y aquí eso era lo más apagado. */
  const halo = new THREE.Sprite(new THREE.SpriteMaterial({
    map: texHalo, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    opacity: 0.52, color: colorA.clone(),
  }));
  halo.scale.set(RADIOS.halo, RADIOS.halo, 1);
  objeto.add(halo);

  let estado = ESTADO_INICIAL;
  let giro = 0;
  const destino = { a: colorA.clone(), b: colorB.clone(), op: comp.uOpacidad.value,
                    empuje: comp.uEmpuje.value, vel: tabla[estado].giro };

  /** Pide un estado: el color NO salta, se interpola en `pinta`. */
  function setEstado(nombre) {
    const e = tabla[nombre];
    if (!e) return false;                    // un estado inventado no tumba la cara
    estado = nombre;
    destino.a.set(e.a); destino.b.set(e.b);
    destino.op = e.opacidad; destino.empuje = e.empuje; destino.vel = e.giro;
    return true;
  }

  /**
   * Cambio de atuendo en caliente, con los dos colores del contrato 2.1
   * (`--primario` / `--secundario`). No salta: reescribe el destino y `pinta` se
   * acerca en los siguientes frames, igual que cuando cambia el estado.
   */
  function vestir(primario, secundario) {
    tabla = estadosDelTraje(primario, secundario);
    return setEstado(estado);
  }

  /**
   * Dispara la animación dispersiva. No hace NADA con la geometría: guarda el reloj de
   * la coreografía y `pinta` escribe los tres uniforms en cada frame. `clase` es
   * `'activa'` (ejecuta algo: anillo largo, que enmarque la ventana) o `'responde'`
   * (contesta: explosión corta). Volver a disparar reinicia el baile, que es lo que
   * pasa cuando CORT ejecuta dos cosas seguidas.
   */
  let vort = null;
  function dispara(clase = 'activa') {
    vort = { t: 0, rit: RITMOS[clase] || RITMOS.activa };
  }

  /** Corta la explosión de golpe (la usa `stop()` de la cara: «para» es «para»). */
  function corta() {
    vort = null;
    comp.uDispersa.value = 0; comp.uVortice.value = 0; comp.uPortal.value = 0;
  }

  /** `dt` en segundos, `nivel` de 0 a 1 (micrófono o simulación). */
  function pinta(dt, nivel = 0) {
    const paso = Math.max(0, Math.min(0.1, dt));   // si el hilo estuvo dormido, no salta
    comp.uTiempo.value += paso;
    giro += paso * destino.vel * (0.5 + Math.min(1, nivel) * 1.2);
    objeto.rotation.y = giro;
    objeto.rotation.x = Math.sin(comp.uTiempo.value * 0.25) * 0.12;
    /* Profundidad barata: el polvo NO gira con el orbe, gira en contra. Restando medio
       `giro`, el campo de estrellas se queda a ~45 % de la velocidad de la madeja, que es
       lo que hace en el video —el fondo casi no se mueve y la bola sí—. Cuesta escribir
       UN número por frame y no añade ni un dibujo. */
    if (polvo) polvo.rotation.y = -giro * 0.55;
    // Interpolación suave: la misma idea del orbe viejo (`.055` por frame), en segundos.
    const mez = 1 - Math.pow(0.001, paso);
    colorA.lerp(destino.a, mez);
    colorB.lerp(destino.b, mez);
    comp.uOpacidad.value += (destino.op - comp.uOpacidad.value) * mez;
    comp.uEmpuje.value += (destino.empuje - comp.uEmpuje.value) * mez;
    comp.uNivel.value += (Math.min(1, Math.max(0, nivel)) - comp.uNivel.value) * mez;
    /* La coreografía, si está sonando. Se escribe DIRECTO y no interpolado: la curva ya
       es suave (nace en 0 y muere en 0), y añadirle un `lerp` encima le robaría los
       0,5 s de la explosión, que son justo lo que la hace parecer una explosión. */
    let portal = comp.uPortal.value;
    if (vort) {
      vort.t += paso;
      const f = formaDelVortice(vort.t, vort.rit);
      if (!f) { vort = null; }
      comp.uDispersa.value = f ? f.dispersa : 0;
      comp.uVortice.value = f ? f.vortice : 0;
      comp.uPortal.value = f ? f.portal : 0;
      portal = comp.uPortal.value;
    }
    halo.material.color.copy(colorA);
    /* El fogonazo: el `uDispersa` entra también en el brillo del halo. En el video la
       explosión no es sólo forma, es un portazo de luz que dura medio segundo, y aquí
       cuesta un multiplicador más en la misma línea (mismo dibujo, mismo relleno).
       Y el portal, en cambio, APAGA el núcleo, no lo enciende: medido sobre los dos
       fotogramas de la referencia, en `f7-orbe-000.jpg` (el estallido) el centro es una
       estrella con púas, y en `f7-anillo-065.jpg` (el anillo montado) el agujero está
       VACÍO. Con el término positivo de la 2.17.0 las púas se cruzaban sobre el agujero
       del vórtice, que es lo contrario de lo que se ve en el video.
       Los dos números del 27/10: la base sube de 0,15 a 0,52 y el portal resta 0,47 en vez
       de 0,11. No es un capricho de brillo —es lo que queda al leer los fotogramas con la
       bola ya grande (cámara a 5,8): con 0,15 el núcleo del video no existía en CORT, y el
       suelo de 0,06 mantiene el agujero del toro vacío, que es la medida que lo manda. */
    halo.material.opacity = Math.max(0.06, 0.52 + 0.26 * comp.uNivel.value
                                     + 0.20 * comp.uDispersa.value - 0.47 * portal);
    const s = RADIOS.halo * (1 + 0.10 * comp.uNivel.value + 0.75 * portal);
    halo.scale.set(s, s, 1);
  }

  /** Libera GPU. Con 1,8 GiB de RAM, un orbe que no se borra es una fuga. */
  function borrar() {
    puntos.geometry.dispose(); puntos.material.dispose();
    if (lineas) { lineas.geometry.dispose(); lineas.material.dispose(); }
    if (polvo) { polvo.geometry.dispose(); polvo.material.dispose(); }
    halo.material.map.dispose(); halo.material.dispose();
  }

  return {
    objeto, setEstado, pinta, borrar, vestir,
    dispara, corta,
    estado: () => estado,
    /** En qué punto del baile está: `null` si no hay ninguno. Para la sonda y la prueba. */
    vortice: () => (vort ? formaDelVortice(vort.t, vort.rit) : null),
    /** La tabla viva: lo que la sonda pinta en sus botones de estado. */
    estados: () => tabla,
    /** Lo que la sonda enseña para que el coste no sea una promesa. `polvo` es 0 en el
     *  `modo:'bajo'` del teléfono, y `dibujos` cuenta los cuatro de verdad: puntos,
     *  líneas, polvo y halo (o dos: puntos y halo, si el aparato va justo). */
    cifras: () => ({ puntos: n, lineas: aristas.length / 2,
                     polvo: nPolvo, dibujos: polvo ? 4 : 2 }),
  };
}
