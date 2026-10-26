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
 *   3. Dibujos: 3 (puntos, líneas, halo). Con `modo:'bajo'`, 2.
 *
 * Es un módulo PURO en su parte de geometría: `puntosFibonacci` y `aristasCercanas` no
 * tocan THREE ni el DOM, así que `scripts/prueba-orbe.mjs` las mide en node sin WebGL,
 * igual que `traje.js` se mide con `prueba-colores.mjs`. `THREE` se INYECTA en
 * `creaOrbe` por el mismo motivo: sin WebGL no hay forma de probar el resto.
 */

/** Puntos sobre la esfera. 120 se lee como el video; 2600 era el orbe viejo. */
export const N_PUNTOS = 120;

/** Vecinos más cercanos enlazados por punto. Con 5 salen ~300 líneas (cada una cuenta
 *  por dos mitades); más de 7 empieza a parecer una bola opaca y pierde el "aire". */
export const VECINOS = 5;

/** Radios de las cuatro piezas, en unidades del orbe. */
/** Radios de las cuatro piezas, en unidades del orbe. El halo va tan grande porque es
 *  un degradado casi transparente: con `RADIOS.halo` de 2,9 y su alfa viejo tapaba los
 *  puntos y la esfera se veía como un disco blanco (medido en el navegador). */
export const RADIOS = Object.freeze({ esfera: 1, halo: 2.2, anillo: 1.62 });

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
    pos[i * 3] = Math.cos(t) * r * radio;
    pos[i * 3 + 1] = y * radio;
    pos[i * 3 + 2] = Math.sin(t) * r * radio;
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

/* ---------------- los estados, que son el color ---------------- */

/**
 * Los cuatro estados de la cara, con los colores leídos en los fotogramas del video:
 * blanco-frío en reposo, cian al oír, y verde lima cuando trabaja o habla. `a` es el
 * color de los puntos y `b` el de las líneas; `empuje` cuánto agranda la onda el nivel
 * de audio; `giro` es radianes por segundo.
 *
 * En la integración (paso 1.2) `a` y `b` NO se quedan aquí escritos a mano: se piden
 * a `traje.js` (los canales `particula` y `hilos`) para que un atuendo siga pintando
 * todo el orbe, que es lo que vigila `prueba-colores.mjs`. Mientras el prototipo viva
 * aparte, la tabla propia es honesta.
 */
export const ESTADOS = Object.freeze({
  reposo:  { a: '#dff6ff', b: '#4a7f9e', opacidad: 0.62, empuje: 0.030, giro: 0.055 },
  escucha: { a: '#eafcff', b: '#39c2ff', opacidad: 0.90, empuje: 0.075, giro: 0.160 },
  piensa:  { a: '#c8fff0', b: '#25e0b8', opacidad: 0.86, empuje: 0.055, giro: 0.620 },
  habla:   { a: '#e8ffcf', b: '#8dff4a', opacidad: 0.96, empuje: 0.130, giro: 0.230 },
  error:   { a: '#ffe0e6', b: '#ff5b6e', opacidad: 0.88, empuje: 0.040, giro: 0.090 },
});

/** El estado con el que se enciende la cara: no llama la atención. */
export const ESTADO_INICIAL = 'reposo';

/* ---------------- los shaders ---------------- */

/* Una sola onda por vértice, a lo largo del radio. Se calcula en la GPU para todos los
   puntos y todas las líneas a la vez: el coste por frame es escribir 4 uniforms.
   Hay DOS vertex shader a propósito, no uno retocado con `replace()`: el de los puntos
   necesita el tamaño en pantalla y el de las líneas no, y una cadena que se parchea a
   mano es exactamente como se cayó la cara en la 2.10.0. */
const ONDA = /* glsl */`
uniform float uTiempo;
uniform float uNivel;
uniform float uEmpuje;
attribute float aFase;
varying float vBrillo;
void main() {
  float f = aFase * 6.2831853;
  float onda = sin(uTiempo * 1.7 + f + position.y * 3.1);
  float respira = 1.0 + (uEmpuje + uNivel * 0.16) * onda;
  vBrillo = clamp(0.45 + 0.55 * onda * (0.35 + uNivel), 0.0, 1.0);
  vec3 p = position * respira;`;

const VERT_LINEAS = ONDA + /* glsl */`
  gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
}`;

/* Por qué el tamaño del punto está topeado y lleva 7,2 dentro.
   `gl_PointSize` son PÍXELES DEL APARATO, no unidades del orbe, y crece al acercar la
   cámara. La primera versión usó `260.0 / -mv.z`, que a 4,4 de distancia daba puntos de
   190 px: en vez del encaje de hilos del video, una mancha blanca que tapaba el encaje.
   Ahora: el tamaño que pide el anfitrión, medido a la distancia de cámara de 7,2,
   corregido por la distancia real de cada punto y topeado entre 1 y 9 px. El pixel
   ratio ya viene dentro de `uTamano` porque GL no lo sabe.
   Y NADA de acentos graves dentro de estas cadenas: un acento grave cierra el literal,
   el módulo deja de parsear y la cara se queda en blanco sin decir nada. Pasó, y el
   `node --check` de la prueba no lo cazó porque el archivo seguía siendo JS válido.
   (Escribir aquí un cierre de comentario de bloque también rompe el archivo: es la misma
   familia de error, y por eso el candado está en `scripts/prueba-orbe.mjs` [4].) */
const VERT_PUNTOS = /* glsl */`
uniform float uTiempo;
uniform float uNivel;
uniform float uEmpuje;
uniform float uTamano;
attribute float aFase;
varying float vBrillo;
void main() {
  float f = aFase * 6.2831853;
  float onda = sin(uTiempo * 1.7 + f + position.y * 3.1);
  float respira = 1.0 + (uEmpuje + uNivel * 0.16) * onda;
  vBrillo = clamp(0.45 + 0.55 * onda * (0.35 + uNivel), 0.0, 1.0);
  vec3 p = position * respira;
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  // gl_PointSize son píxeles del aparato: ver el comentario sobre VERT_PUNTOS
  gl_PointSize = clamp(uTamano * (7.2 / max(0.5, -mv.z)), 1.0, 9.0);
  gl_Position = projectionMatrix * mv;
}`;

/* Los puntos se dibujan como redondos suaves: `gl_PointCoord` evita una textura. */
const FRAG_PUNTOS = /* glsl */`
uniform vec3 uColorA;
uniform float uOpacidad;
varying float vBrillo;
void main() {
  float d = length(gl_PointCoord - vec2(0.5));
  float a = smoothstep(0.5, 0.06, d);
  if (a < 0.02) discard;
  gl_FragColor = vec4(uColorA * (0.65 + 0.7 * vBrillo), a * uOpacidad);
}`;

const FRAG_LINEAS = /* glsl */`
uniform vec3 uColorB;
uniform float uOpacidad;
varying float vBrillo;
void main() {
  gl_FragColor = vec4(uColorB * (0.5 + 0.9 * vBrillo), uOpacidad * (0.42 + 0.55 * vBrillo));
}`;

/** Los cuatro textos GLSL, exportados sólo para que `prueba-orbe.mjs` los lea: en node
 *  no hay GPU, pero sí se puede exigir que un shader declare lo que usa. */
export const SHADERS = Object.freeze({
  puntos: VERT_PUNTOS, lineas: VERT_LINEAS,
  fragPuntos: FRAG_PUNTOS, fragLineas: FRAG_LINEAS,
});

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
  const geo = puntosFibonacci(n, RADIOS.esfera, opciones.semilla || 7);
  const aristas = aristasCercanas(geo.pos, n, k);

  const colorA = new THREE.Color(ESTADOS[ESTADO_INICIAL].a);
  const colorB = new THREE.Color(ESTADOS[ESTADO_INICIAL].b);
  const comp = {
    uTiempo: { value: 0 },
    uNivel: { value: 0 },
    uEmpuje: { value: ESTADOS[ESTADO_INICIAL].empuje },
    uOpacidad: { value: ESTADOS[ESTADO_INICIAL].opacidad },
    uColorA: { value: colorA },
    uColorB: { value: colorB },
    uTamano: { value: opciones.tamano || 2.8 },   // píxeles lógicos a 7,2 de cámara
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

  // El halo: un degradado radial dibujado a mano en un canvas de 128 px. Da el "glow"
  // de la referencia sin post-proceso, que en 2 núcleos no se paga.
  const cnv = document.createElement('canvas');
  cnv.width = cnv.height = 128;
  const g = cnv.getContext('2d');
  const rad = g.createRadialGradient(64, 64, 4, 64, 64, 62);
  rad.addColorStop(0, 'rgba(255,255,255,0.55)');
  rad.addColorStop(0.35, 'rgba(255,255,255,0.10)');
  rad.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = rad; g.fillRect(0, 0, 128, 128);
  const texHalo = new THREE.CanvasTexture(cnv);
  const halo = new THREE.Sprite(new THREE.SpriteMaterial({
    map: texHalo, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    opacity: 0.18, color: colorB.clone(),
  }));
  halo.scale.set(RADIOS.halo, RADIOS.halo, 1);
  objeto.add(halo);

  let estado = ESTADO_INICIAL;
  let giro = 0;
  const destino = { a: colorA.clone(), b: colorB.clone(), op: comp.uOpacidad.value,
                    empuje: comp.uEmpuje.value, vel: ESTADOS[estado].giro };

  /** Pide un estado: el color NO salta, se interpola en `pinta`. */
  function setEstado(nombre) {
    const e = ESTADOS[nombre];
    if (!e) return false;                    // un estado inventado no tumba la cara
    estado = nombre;
    destino.a.set(e.a); destino.b.set(e.b);
    destino.op = e.opacidad; destino.empuje = e.empuje; destino.vel = e.giro;
    return true;
  }

  /** `dt` en segundos, `nivel` de 0 a 1 (micrófono o simulación). */
  function pinta(dt, nivel = 0) {
    const paso = Math.max(0, Math.min(0.1, dt));   // si el hilo estuvo dormido, no salta
    comp.uTiempo.value += paso;
    giro += paso * destino.vel * (0.5 + Math.min(1, nivel) * 1.2);
    objeto.rotation.y = giro;
    objeto.rotation.x = Math.sin(comp.uTiempo.value * 0.25) * 0.12;
    // Interpolación suave: la misma idea del orbe viejo (`.055` por frame), en segundos.
    const mez = 1 - Math.pow(0.001, paso);
    colorA.lerp(destino.a, mez);
    colorB.lerp(destino.b, mez);
    comp.uOpacidad.value += (destino.op - comp.uOpacidad.value) * mez;
    comp.uEmpuje.value += (destino.empuje - comp.uEmpuje.value) * mez;
    comp.uNivel.value += (Math.min(1, Math.max(0, nivel)) - comp.uNivel.value) * mez;
    halo.material.color.copy(colorB);
    halo.material.opacity = 0.10 + 0.26 * comp.uNivel.value;
    const s = RADIOS.halo * (1 + 0.10 * comp.uNivel.value);
    halo.scale.set(s, s, 1);
  }

  /** Libera GPU. Con 1,8 GiB de RAM, un orbe que no se borra es una fuga. */
  function borrar() {
    puntos.geometry.dispose(); puntos.material.dispose();
    if (lineas) { lineas.geometry.dispose(); lineas.material.dispose(); }
    halo.material.map.dispose(); halo.material.dispose();
  }

  return {
    objeto, setEstado, pinta, borrar,
    estado: () => estado,
    /** Lo que la sonda enseña para que el coste no sea una promesa. */
    cifras: () => ({ puntos: n, lineas: aristas.length / 2,
                     dibujos: 2 + (lineas ? 1 : 0) }),
  };
}
