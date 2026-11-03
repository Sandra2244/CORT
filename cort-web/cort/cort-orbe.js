/**
 * CORT — capa del orbe: vórtice, ráfaga, anillos y núcleo
 *
 * Va en canvas 2D ENCIMA del WebGL de la demo (que no se toca y cuya instancia no
 * está expuesta). Por qué 2D y no Three.js: medido en la Canaima (2 núcleos, GPU
 * Bay Trail) la página entera corre a ~15 FPS con el orbe de la demo, y el único
 * gancho del motor ajeno que parece un vórtice —`triggerEchoConstruction`— esparce
 * las 2000 partículas por toda la pantalla y deja la CPU en 99 % (capturado el
 * 2026-11-02). Una capa 2D con ~260 puntos cuesta centésimas por fotograma y se
 * puede medir y recortar.
 *
 * Diseño sacado fotograma a fotograma de los dos videos de referencia
 * (DISENO_ORBE.md): el vórtice es esfera → recolección al plano → toroide girando
 * → dispersión, en ~900 ms; la ráfaga de ejecutar es un estiramiento vertical tipo
 * cometa en ~400 ms.
 *
 * Este archivo es código propio de CORT. No depende de la demo: si el orbe de la
 * demo no está, la capa sigue pintando su propia esfera.
 */
(function () {
  "use strict";

  const PALETA = {
    menta:   [0, 255, 200],
    cian:    [34, 229, 255],
    ambar:   [255, 170, 0],
    magenta: [255, 43, 214],
    violeta: [123, 92, 255],
    blanco:  [255, 255, 255]
  };

  // Estado → color y forma. La tabla está en DISENO_ORBE.md §3.
  const ESTADOS = {
    reposo:     { color: PALETA.cian,    nucleo: 0.55, anillos: 1.0 },
    escuchando: { color: PALETA.menta,   nucleo: 0.75, anillos: 0.75 },
    pensando:   { color: PALETA.violeta, nucleo: 0.9,  anillos: 1.3 },
    hablando:   { color: PALETA.menta,   nucleo: 1.0,  anillos: 1.0 },
    ejecutando: { color: PALETA.ambar,   nucleo: 1.0,  anillos: 0.6 },
    alerta:     { color: PALETA.magenta, nucleo: 1.0,  anillos: 1.6 },
    descarga:   { color: PALETA.ambar,    nucleo: 0.8,  anillos: 1.0 }
  };

  const N = 260;                 // partículas de la capa
  const lienzo = document.createElement("canvas");
  lienzo.id = "cort-orbe";
  lienzo.setAttribute("aria-hidden", "true");
  // El <script> vive en el <head>, donde document.body todavía no existe: se ancla al
  // nodo más alto disponible y, si acaso, se re-ancla en el primer fotograma.
  function anclar() {
    if (lienzo.parentNode) return;
    (document.body || document.documentElement).appendChild(lienzo);
  }
  anclar();
  const ctx = lienzo.getContext("2d", { alpha: true });

  let W = 0, H = 0, DPR = 1, cx = 0, cy = 0, R = 0, LADO = 0;
  let estado = "reposo";
  let volumen = 0;
  let anim = null;               // {modo, t0, dur}
  let progresoDescarga = null;   // 0..1 o null
  let corriendo = false;
  let particulas = [];
  let objetivoN = N;

  // Medición: la capa se recorta sola si la máquina no da, y lo dice con número.
  // Ojo: se juzga por su PROPIO costo por fotograma (msProm), nunca por el FPS de la
  // página. Medido el 2026-11-02 en la Canaima: ocultando la capa el FPS de la página
  // no cambiaba (8-19 FPS igual), porque el techo lo pone el CSS compuesto, no el
  // orbe. Recortarse por culpa del FPS ajeno dejaba la esfera en 88 puntos gratis.
  const cron = { fotos: 0, t0: 0, fps: 0, ms: 0, msProm: 0, acum: 0, malos: 0, ventanas: 0, recortes: 0, ultimoEfecto: null };

  function semilla(n) {
    const p = [];
    for (let i = 0; i < n; i++) {
      // esfera de Fibonacci: reparto parejo, sin parches vacíos
      const y = 1 - (i / (n - 1)) * 2;
      const r = Math.sqrt(Math.max(0, 1 - y * y));
      const th = i * 2.39996323;               // ángulo áureo
      p.push({
        x: Math.cos(th) * r, y: y, z: Math.sin(th) * r,
        a: th,               // ángulo para el anillo
        vel: 0.75 + Math.random() * 0.5,
        px: 0, py: 0,        // posición del fotograma anterior (filamento)
        visto: false
      });
    }
    return p;
  }

  const MINIMO = 96;               // por debajo de esta esfera el orbe se ve mudo
  let SEMILLA = [];                // las N completas; el recorte sólo las afina
  function afinar(base, n) {
    // toma n puntos REPARTIDOS, no los n primeros: los n primeros de una esfera de
    // Fibonacci son un casquete, y el orbe se quedaba a medias al recortar.
    if (!base.length || n >= base.length) return base.slice();
    const out = [];
    for (let i = 0; i < n; i++) out.push(base[Math.floor(i * base.length / n)]);
    return out;
  }

  function ajustar() {
    W = window.innerWidth; H = window.innerHeight;
    // En esta máquina el devicePixelRatio 2 cuesta el doble de relleno: se fija a 1.
    DPR = 1;
    // Centro y radio MEDIDOS sobre el orbe de la demo: (271,265) y ~104 px en una
    // ventana de 535×521. La caja del lienzo se recorta alrededor del orbe en vez de
    // cubrir toda la pantalla: menos píxeles que componer en una GPU Bay Trail.
    const vx = W * 0.506, vy = H * 0.508;
    R = Math.min(W, H) * 0.20;
    LADO = Math.round(Math.min(W, H) * 0.92);
    cx = LADO / 2; cy = LADO / 2;
    lienzo.width = Math.round(LADO * DPR);
    lienzo.height = Math.round(LADO * DPR);
    lienzo.style.cssText =
      "position:fixed;pointer-events:none;z-index:5;mix-blend-mode:screen;" +
      "left:" + Math.round(vx - cx) + "px;top:" + Math.round(vy - cy) + "px;" +
      "width:" + LADO + "px;height:" + LADO + "px;";
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  }

  function suave(t) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }
  function colorDe(base, alpha) { return "rgba(" + base[0] + "," + base[1] + "," + base[2] + "," + alpha + ")"; }

  // Proyección con inclinación: el toroide del video 2 se ve de frente y luego se
  // inclina; la misma fórmula sirve para la esfera de reposo.
  function proyectar(x, y, z, inclinacion) {
    const ci = Math.cos(inclinacion), si = Math.sin(inclinacion);
    return [cx + x * R, cy + (y * ci - z * si) * R];
  }

  function puntoReposo(p, tiempo) {
    // respiración lenta de la esfera: 3 % de radio, para que el reposo no esté muerto
    const br = 1 + 0.03 * Math.sin(tiempo * 0.0009 + p.a * 3);
    const rot = tiempo * 0.00012;
    const x = p.x * Math.cos(rot) - p.z * Math.sin(rot);
    const z = p.x * Math.sin(rot) + p.z * Math.cos(rot);
    return [x * br, p.y * br, z * br];
  }

  function dibujarNucleo(col, pulso) {
    const radio = R * (0.16 + 0.10 * pulso + 0.22 * volumen);
    const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, Math.max(2, radio));
    g.addColorStop(0, colorDe(PALETA.blanco, 0.85));
    g.addColorStop(0.35, colorDe(col, 0.55));
    g.addColorStop(1, colorDe(col, 0));
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(cx, cy, radio, 0, Math.PI * 2);
    ctx.fill();
  }

  function dibujarAnillos(col, tiempo, ganancia) {
    ctx.lineWidth = 1;
    for (let i = 0; i < 3; i++) {
      const incli = 0.35 + i * 0.55 + Math.sin(tiempo * 0.0002 + i) * 0.12;
      const radio = R * (1.12 + i * 0.16) * ganancia;
      ctx.strokeStyle = colorDe(col, 0.16 - i * 0.03);
      ctx.beginPath();
      for (let a = 0; a <= 64; a++) {
        const t = (a / 64) * Math.PI * 2;
        const [x, y] = proyectar(Math.cos(t) * radio / R, 0, Math.sin(t) * radio / R, incli);
        if (a === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }
  }

  function dibujarCuerdas(col, lista) {
    // ~70 cuerdas entre partículas vecinas: es lo que en la referencia dibuja la
    // esfera (líneas de gran círculo), no los puntos.
    ctx.strokeStyle = colorDe(col, 0.10);
    ctx.lineWidth = 1;
    ctx.beginPath();
    const paso = Math.max(1, Math.floor(lista.length / 70));
    for (let i = 0; i + paso < lista.length; i += paso) {
      const a = lista[i], b = lista[i + paso];
      if (!a.visto || !b.visto) continue;
      ctx.moveTo(a.px, a.py);
      ctx.lineTo(b.px, b.py);
    }
    ctx.stroke();
  }

  let ultimo = 0;
  let congelado = null;    // {modo, k} — pausa de laboratorio para fotografiar una fase
  const FPS_REPOSO = 20;   // en reposo la capa se limita sola; con efecto, va a tope
  let FPS_TOPE = 0;        // S1: tope que impone el escaneo del equipo (0 = no impone ninguno)

  function fotograma(tiempo) {
    if (!corriendo) return;
    // Con tope del escaneo, el tope manda incluso durante el efecto: es la diferencia
    // entre «el orbe se recorta cuando sufre» y «el orbe nunca promete 60 fps a un Celeron».
    // Sin tope se conserva lo de antes: ir a tope con efecto, 20 fps en reposo.
    const con_efecto = congelado || anim || progresoDescarga != null;
    const espera = FPS_TOPE ? 1000 / FPS_TOPE : (con_efecto ? 0 : 1000 / FPS_REPOSO);
    if (!congelado && tiempo - ultimo < espera) {
      requestAnimationFrame(fotograma);
      return;
    }
    ultimo = tiempo;
    const inicio = performance.now();
    const cfg = ESTADOS[estado] || ESTADOS.reposo;
    ctx.clearRect(0, 0, LADO, LADO);
    ctx.globalCompositeOperation = "lighter";

    let k = 0, modo = null;
    if (congelado) { modo = congelado.modo; k = congelado.k; }
    else if (anim) {
      const u = (tiempo - anim.t0) / anim.dur;
      if (u >= 1) {
        // El fotograma que cruza la meta PINTA k=1 y después se suelta el gesto.
        // Antes se descartaba ese fotograma: el último que se veía quedaba en k≈0,9
        // y el efecto moría a medias, con un fotograma de más en el reloj.
        cron.ultimoEfecto = {
          efecto: anim.modo,
          dur: anim.dur,
          msReal: Math.round(tiempo - anim.t0),
          fotos: anim.fotos + 1
        };
        anim.seacabo = true;
        modo = anim.modo; k = 1;
      }
      else { modo = anim.modo; k = u; anim.fotos++; }
    }

    // Con la pausa de laboratorio el reloj también se congela: la foto muestra una
    // fase exacta, no una esfera que sigue girando debajo del gesto.
    const reloj = congelado ? congelado.reloj : tiempo;

    dibujarAnillos(cfg.color, reloj, cfg.anillos);
    dibujarNucleo(cfg.color, modo ? 1 : 0.5 + 0.5 * Math.sin(reloj * 0.002));

    const lista = [];
    const estela = [];
    for (let i = 0; i < particulas.length; i++) {
      const p = particulas[i];
      let x, y, z, alfa = 0.55, tam = 1.1, base = null;

      if (modo === "vortice") {
        // 0–0.35 se recolecta al plano · 0.35–0.7 toroide girando · 0.7–1 se dispersa
        const a = p.a + (k > 0.3 ? (k - 0.3) * 9 * p.vel : 0);
        const enAnillo = k < 0.35 ? suave(k / 0.35)
                      : k < 0.70 ? 1
                      : 1 - suave((k - 0.70) / 0.30);
        const radioAnillo = k < 0.70 ? 0.92 : 0.92 + (k - 0.70) * 3.4;
        const [bx, by, bz] = puntoReposo(p, reloj);
        const rx = Math.cos(a) * radioAnillo, ry = 0, rz = Math.sin(a) * radioAnillo;
        x = bx + (rx - bx) * enAnillo;
        y = by + (ry - by) * enAnillo;
        z = bz + (rz - bz) * enAnillo;
        alfa = 0.5 + 0.5 * enAnillo;
        tam = 1.1 + enAnillo * 1.3;
      } else if (modo === "rafaga") {
        // estiramiento vertical tipo cometa (fotograma de los 9 s del video 1).
        // El tope de 0.95 es medido: con R=104 dentro de una caja de 479 px, un
        // estiramiento de 2.4 sacaba las partículas de arriba y abajo del lienzo.
        const e = k < 0.4 ? suave(k / 0.4) : 1 - suave((k - 0.4) / 0.6);
        const [bx, by, bz] = puntoReposo(p, reloj);
        base = [bx, by, bz];
        x = bx * (1 - 0.8 * e);
        y = by * (1 + 0.95 * e);
        z = bz * (1 - 0.8 * e);
        alfa = 0.55 + 0.45 * e;
        tam = 1.1 + e * 1.6;
      } else {
        [x, y, z] = puntoReposo(p, reloj);
        tam = 1 + volumen * 1.4;
      }

      const incli = modo === "vortice" ? 0.55 - k * 0.25 : 0.35;
      const [pxp, pyp] = proyectar(x, y, z, incli);
      if (modo === "rafaga" && i % 3 === 0) {
        // Estela de la ráfaga, pero CORTA y sólo en un tercio de las partículas: con
        // las 260 líneas largas (medido en la foto congelada) el orbe se tapaba con
        // una maraña y se leía como error, no como movimiento.
        let ax = p.px, ay = p.py;
        if (congelado && base) { const s = proyectar(base[0], base[1], base[2], incli); ax = s[0]; ay = s[1]; }
        let dx = pxp - ax, dy = pyp - ay;
        const largo = Math.hypot(dx, dy);
        const tope = 26;                                  // px: lo que dura un fotograma bueno
        if (largo > tope) { dx *= tope / largo; dy *= tope / largo; }
        estela.push(pxp - dx, pyp - dy, pxp, pyp);
      }
      ctx.fillStyle = colorDe(modo === "vortice" && k > 0.35 && k < 0.7 ? PALETA.blanco : cfg.color, alfa);
      ctx.beginPath();
      ctx.arc(pxp, pyp, tam, 0, Math.PI * 2);
      ctx.fill();
      lista.push({ px: pxp, py: pyp, visto: true });
      p.px = pxp; p.py = pyp;
    }
    if (estela.length) {
      // la estela de la ráfaga: en la Canaima un fotograma cae cada ~65 ms, así que
      // el salto entre posiciones es largo y se lee como cometa sin costo extra.
      ctx.strokeStyle = colorDe(cfg.color, 0.18);
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      for (let i = 0; i < estela.length; i += 4) {
        ctx.moveTo(estela[i], estela[i + 1]);
        ctx.lineTo(estela[i + 2], estela[i + 3]);
      }
      ctx.stroke();
    }
    if (!modo) dibujarCuerdas(cfg.color, lista);

    if (progresoDescarga != null) {
      // anillo de progreso: el % real de `pull_ollama_model`, no una rueda decorativa
      ctx.strokeStyle = colorDe(PALETA.ambar, 0.85);
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(cx, cy, R * 1.32, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * progresoDescarga);
      ctx.stroke();
    }

    ctx.globalCompositeOperation = "source-over";
    if (anim && anim.seacabo) anim = null;   // el fotograma final ya se pintó arriba

    // medición y recorte automático (por costo propio, con media móvil).
    // En pausa de laboratorio no se mide ni se recorta: una foto no es carga real.
    if (!congelado) {
      const costo = performance.now() - inicio;
      cron.ms = Math.round(costo * 100) / 100;
      cron.acum += costo;
      cron.fotos++;
      if (!cron.t0) cron.t0 = tiempo;
      if (tiempo - cron.t0 >= 1000) {
        cron.fps = Math.round(cron.fotos * 1000 / (tiempo - cron.t0));
        cron.msProm = Math.round(cron.acum / Math.max(1, cron.fotos) * 100) / 100;
        cron.fotos = 0; cron.acum = 0; cron.t0 = tiempo;
        // > 12 ms/fotograma durante TRES ventanas seguidas. El umbral alto y la espera
        // larga son medidas, no timidez: el costo propio del orbe es 1,9-4,9 ms y los
        // picos de 8-40 ms del arranque vienen de la máquina ocupada (en la prueba de
        // hoy el propio entorno del agente comía 63 %+52 % de los 2 núcleos y había
        // 1,3 GB en swap), no del lienzo. Recortar por eso dejaba la esfera a medias
        // sin aliviar nada: ocultar los lienzos WebGL no subió el FPS (9→11).
        if (cron.msProm > 12) cron.malos++; else cron.malos = 0;
        // Los cinco primeros segundos no cuentan: ahí la página está cargando y el
        // pico de 20-40 ms es del arranque, no del orbe (costo real medido en reposo:
        // 2,3 ms por fotograma con las 260 partículas puestas).
        cron.ventanas++;
        if (cron.ventanas > 5 && cron.malos >= 3 && particulas.length > MINIMO) {
          particulas = afinar(SEMILLA, Math.max(MINIMO, Math.floor(particulas.length * 0.75)));
          cron.recortes++;
        } else if (cron.msProm < 6 && particulas.length < objetivoN) {
          particulas = afinar(SEMILLA, Math.min(objetivoN, Math.floor(particulas.length / 0.75)));
        }
      }
    }
    requestAnimationFrame(fotograma);
  }

  function arrancar() {
    if (corriendo) return;
    anclar();
    corriendo = true;
    requestAnimationFrame(fotograma);
  }

  window.CORT_orbe = {
    estado: (e) => { if (ESTADOS[e]) estado = e; return estado; },
    volumen: (v) => { volumen = Math.max(0, Math.min(1, v || 0)); return volumen; },
    // S1: el escaneo del equipo pone el techo de fotogramas. 0 = sin techo.
    tope: (n) => { FPS_TOPE = Math.max(0, Math.min(60, parseInt(n, 10) || 0)); return FPS_TOPE; },
    // Duraciones elegidas para que la vara se cumpla en RELOJ DE PARED, no en la
    // línea de tiempo del gesto: un gesto sólo puede terminar en un fotograma, así
    // que la pared tarda `dur` + un fotograma. Con la página a 24-30 FPS (60 ms por
    // fotograma en la Canaima) 850 cierra en ~900 y 360 en ~400.
    vortice: (ms) => {
      const t = performance.now();
      anim = { modo: "vortice", t0: t, dur: Math.max(240, ms || 850), fotos: 0 };
      arrancar();
      return { efecto: "vortice", dur: anim.dur, desde: t };
    },
    rafaga: (ms) => {
      const t = performance.now();
      anim = { modo: "rafaga", t0: t, dur: Math.max(160, ms || 360), fotos: 0 };
      arrancar();
      return { efecto: "rafaga", dur: anim.dur, desde: t };
    },
    descarga: (p) => { progresoDescarga = p == null ? null : Math.max(0, Math.min(1, p)); return progresoDescarga; },
    // Pausa de laboratorio: pinta y deja quieta una fase exacta para fotografiarla.
    // CORT_orbe.congelar("vortice", 0.5) · CORT_orbe.congelar(null) para soltar.
    congelar: (modo, k) => {
      congelado = (modo === "vortice" || modo === "rafaga")
        ? { modo, k: Math.max(0, Math.min(1, k == null ? 0.5 : k)), reloj: performance.now() }
        : null;
      anim = null;
      arrancar();
      return congelado ? { modo: congelado.modo, k: congelado.k } : null;
    },
    fps: () => cron.fps,
    info: () => ({
      fps: cron.fps,
      tope: FPS_TOPE,
      msPorFotograma: cron.ms,
      msPromedio: cron.msProm,
      particulas: particulas.length,
      objetivo: objetivoN,
      recortes: cron.recortes,
      ventanasMalas: cron.malos,
      ultimoEfecto: cron.ultimoEfecto,
      estado, volumen: Math.round(volumen * 100) / 100,
      anim: anim ? anim.modo : null,
      congelado: congelado ? { modo: congelado.modo, k: congelado.k } : null,
      centro: [Math.round(cx), Math.round(cy)], radio: Math.round(R),
      caja: LADO + 'x' + LADO, lienzoReal: lienzo.width + 'x' + lienzo.height
    }),
    montar: () => { ajustar(); SEMILLA = semilla(N); objetivoN = N; particulas = afinar(SEMILLA, objetivoN); arrancar(); },
    desmontar: () => { corriendo = false; lienzo.remove(); }
  };

  // ---- traducción de mensajes del puente a gesto del orbe -------------------
  // La capa no decide nada por su cuenta: cada gesto responde a un mensaje real.
  // Así el orbe miente menos que la pantalla, que hojea estados que nadie ejecutó.
  window.CORT_orbe_alMensaje = (m) => {
    if (!m) return;
    const t = m.type || m.action || "";
    if (m.state === "thinking") { window.CORT_orbe.estado("pensando"); return; }
    if (m.state === "speaking") { window.CORT_orbe.estado("hablando"); return; }
    if (m.state === "listening") { window.CORT_orbe.estado("escuchando"); return; }
    if (m.state === "idle") { window.CORT_orbe.estado("reposo"); window.CORT_orbe.volumen(0); return; }
    if (t === "puente_conectado") {
      // arranque: un vórtice de saludo y reposo. Es el único gesto que no depende de
      // una orden; lo dispara la apertura real del WebSocket.
      window.CORT_orbe.estado("reposo");
      window.CORT_orbe.vortice(850);
      return;
    }
    if (t === "user_input") { window.CORT_orbe.estado("pensando"); return; }
    if (t === "live_subtitles") {
        // Desde F3 el volumen del orbe sale del analizador real del navegador
        // (cort-ui.js: AudioContext sobre el WAV que habla el puente). Aquí sólo se
        // marca el estado: un pulso con Math.random() era la mentira que sobraba.
        window.CORT_orbe.estado("hablando");
        return;
    }
    if (t === "mic_estado") {
      window.CORT_orbe.estado(m.estado === "escuchando" ? "escuchando" : "reposo");
      return;
    }
    if (t === "mic_texto") { window.CORT_orbe.estado("pensando"); window.CORT_orbe.rafaga(300); return; }
    if (t === "av_scan_start") { window.CORT_orbe.estado("ejecutando"); window.CORT_orbe.rafaga(400); return; }
    if (t === "av_progress") { window.CORT_orbe.estado("ejecutando"); return; }
    if (t === "av_threat_detected") { window.CORT_orbe.estado("alerta"); window.CORT_orbe.vortice(520); return; }
    if (t === "av_complete") {
      const hay = (m.threats || 0) > 0;
      window.CORT_orbe.estado(hay ? "alerta" : "reposo");
      if (!hay) window.CORT_orbe.vortice(700);
      return;
    }
    if (t === "ollama_pull_progress") {
      const pct = typeof m.pct === "number" ? m.pct / 100 : null;
      window.CORT_orbe.descarga(m.done ? null : pct);
      if (m.done && m.success === false) { window.CORT_orbe.estado("alerta"); window.CORT_orbe.rafaga(320); }
      else if (m.done) { window.CORT_orbe.estado("reposo"); }
      else window.CORT_orbe.estado("descarga");
      return;
    }
    if (t === "puente_aviso") { window.CORT_orbe.estado("alerta"); window.CORT_orbe.rafaga(300); return; }
    if (t === "brain_used") { window.CORT_orbe.vortice(600); return; }
  };

  ajustar();
  SEMILLA = semilla(N);
  particulas = SEMILLA.slice();
  window.addEventListener("resize", ajustar);
  arrancar();
})();
