/* ===== ORB de CORT — Three.js (azul puro estilo Cortana/BLACKBOX) =====
   Sin núcleo naranja: centro azul brillante, cáscara de partículas,
   plexus 3D (constelación con hilos de luz, video f7d16b9e), anillos
   orbitales, suelo concéntrico y estrellas, con mecimiento de
   profundidad. Al ACTIVAR una orden: estalla, gira en embudo espiral
   (vórtice francés), se comprime en un TORO 3D inclinado que gira
   (portal) y se recompone ejecutando la acción. */
import * as THREE from 'three';

export function initORB(mount) {
  const scene = new THREE.Scene();
  const cam = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, .1, 100);
  cam.position.set(0, .55, 6);
  cam.lookAt(0, -.1, 0);
  const ren = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  ren.setSize(innerWidth, innerHeight);
  ren.setPixelRatio(Math.min(devicePixelRatio, 2));
  mount.appendChild(ren.domElement);

  const group = new THREE.Group();      // todo el conjunto respira juntos
  scene.add(group);

  /* ---- núcleo azul brillante (sin naranja, como las referencias) ---- */
  const nucleus = new THREE.Mesh(new THREE.SphereGeometry(.24, 24, 24),
    new THREE.MeshBasicMaterial({ color: 0x8fdcff, transparent: true, opacity: .95 }));
  group.add(nucleus);
  const glow = new THREE.Sprite(new THREE.SpriteMaterial({
    map: makeGlowTexture(), color: 0x5fc8ff, transparent: true, opacity: .8,
    blending: THREE.AdditiveBlending, depthWrite: false }));
  glow.scale.setScalar(1.6);
  group.add(glow);

  /* ---- cáscara: 2600 partículas azules sobre esfera ---- */
  const N = 2600;
  const pos = new Float32Array(N * 3), base = new Float32Array(N * 3), seed = new Float32Array(N);
  for (let i = 0; i < N; i++) {
    const t = Math.acos(2 * Math.random() - 1), p = Math.random() * Math.PI * 2, r = 1.15;
    base[i*3] = pos[i*3] = r * Math.sin(t) * Math.cos(p);
    base[i*3+1] = pos[i*3+1] = r * Math.cos(t);
    base[i*3+2] = pos[i*3+2] = r * Math.sin(t) * Math.sin(p);
    seed[i] = Math.random() * Math.PI * 2;
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const core = new THREE.Points(geo, new THREE.PointsMaterial({
    color: 0x39c2ff, size: .028, transparent: true, opacity: .95,
    blending: THREE.AdditiveBlending, depthWrite: false }));
  group.add(core);

  const halo = new THREE.Mesh(new THREE.SphereGeometry(1.02, 32, 32),
    new THREE.MeshBasicMaterial({ color: 0x0a66aa, transparent: true, opacity: .14 }));
  group.add(halo);

  /* ---- PLEXUS 3D (video f7d16b9e): partículas ancla unidas por hilos de
         luz cuando están cerca → constelación que respira en 3D ---- */
  const ANCH = 160, MAXSEG = 700, D2 = .42 * .42;
  const anchors = new Uint16Array(ANCH);
  for (let i = 0; i < ANCH; i++) anchors[i] = (i * 1453) % N;
  const linePos = new Float32Array(MAXSEG * 6);
  const lineGeo = new THREE.BufferGeometry();
  lineGeo.setAttribute('position', new THREE.BufferAttribute(linePos, 3));
  const lines = new THREE.LineSegments(lineGeo, new THREE.LineBasicMaterial({
    color: 0x39c2ff, transparent: true, opacity: .18,
    blending: THREE.AdditiveBlending, depthWrite: false }));
  group.add(lines);
  function updatePlexus() {
    const p = geo.attributes.position.array;
    let seg = 0;
    for (let a = 0; a < ANCH && seg < MAXSEG; a++) {
      const ia = anchors[a] * 3;
      const ax = p[ia], ay = p[ia + 1], az = p[ia + 2];
      for (let b = a + 1; b < ANCH && seg < MAXSEG; b++) {
        const ib = anchors[b] * 3;
        const dx = p[ib] - ax, dy = p[ib + 1] - ay, dz = p[ib + 2] - az;
        if (dx * dx + dy * dy + dz * dz < D2) {
          const o = seg * 6;
          linePos[o] = ax; linePos[o + 1] = ay; linePos[o + 2] = az;
          linePos[o + 3] = p[ib]; linePos[o + 4] = p[ib + 1]; linePos[o + 5] = p[ib + 2];
          seg++;
        }
      }
    }
    for (let o = seg * 6; o < linePos.length; o++) linePos[o] = 0; // sin uso → invisibles
    lineGeo.attributes.position.needsUpdate = true;
  }

  /* ---- anillos orbitales inclinados ---- */
  function ring(rad, tilt, col) {
    const m = new THREE.Mesh(new THREE.TorusGeometry(rad, .004, 8, 160),
      new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: .6 }));
    m.rotation.x = tilt; group.add(m); return m;
  }
  const r1 = ring(1.75, 1.35, 0x2fb9ff), r2 = ring(2.15, 1.9, 0x7f6bff);

  /* ---- anillos de suelo concéntricos (el "plato" de la referencia) ---- */
  const floor = new THREE.Group();
  [1.3, 1.9, 2.55, 3.2].forEach((rad, i) => {
    const m = new THREE.Mesh(new THREE.TorusGeometry(rad, .006, 6, 180),
      new THREE.MeshBasicMaterial({ color: i % 2 ? 0x1f8fd6 : 0x39c2ff,
        transparent: true, opacity: .34 - i * .05 }));
    m.rotation.x = Math.PI / 2; floor.add(m);
  });
  floor.position.y = -1.75;
  /* rejilla en perspectiva bajo el plato (referencia azul) */
  const grid = new THREE.GridHelper(16, 26, 0x155a86, 0x0d3a5c);
  grid.material.transparent = true; grid.material.opacity = .32;
  grid.position.y = -.04; floor.add(grid);
  scene.add(floor);

  /* ---- haces de luz cayendo (ligeros, solo 4 planos aditivos) ---- */
  for (let i = 0; i < 4; i++) {
    const beam = new THREE.Mesh(new THREE.PlaneGeometry(.05, 3.4),
      new THREE.MeshBasicMaterial({ color: 0x2fb9ff, transparent: true, opacity: .07,
        blending: THREE.AdditiveBlending, depthWrite: false }));
    beam.position.set(Math.cos(i * 1.9) * 1.1, .3, Math.sin(i * 1.9) * 1.1);
    beam.rotation.y = i; scene.add(beam);
  }

  /* ---- estrellas de fondo ---- */
  const S = 900, sp = new Float32Array(S * 3);
  for (let i = 0; i < S * 3; i++) sp[i] = (Math.random() - .5) * 60;
  const starsG = new THREE.BufferGeometry();
  starsG.setAttribute('position', new THREE.BufferAttribute(sp, 3));
  scene.add(new THREE.Points(starsG, new THREE.PointsMaterial({
    color: 0x9fd8ff, size: .05, transparent: true, opacity: .5, depthWrite: false })));

  function makeGlowTexture() {
    const c = document.createElement('canvas'); c.width = c.height = 128;
    const g = c.getContext('2d'), gr = g.createRadialGradient(64, 64, 4, 64, 64, 64);
    gr.addColorStop(0, 'rgba(190,240,255,1)'); gr.addColorStop(.4, 'rgba(70,180,255,.35)');
    gr.addColorStop(1, 'rgba(20,110,220,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
    return new THREE.CanvasTexture(c);
  }

  /* ---- energía 0..1: 0 esfera compacta, 1 dispersión en anillo de estrellas ---- */
  let energy = 0, target = 0, spinBoost = 0;
  const RING_R = 2.6;

  /* ---- MODO DISCO (ejecutor de música): el orbe se dispersa y forma un
         círculo/vinilo que gira; la velocidad y el pulso los manda el audio ---- */
  let discMode = 0, discAngle = 0, audioL = 0, audioB = 0;
  const discEdge = new THREE.Mesh(new THREE.TorusGeometry(2.38, .012, 8, 200),
    new THREE.MeshBasicMaterial({ color: 0x8fe4ff, transparent: true, opacity: 0,
      blending: THREE.AdditiveBlending, depthWrite: false }));
  discEdge.rotation.x = Math.PI / 2; group.add(discEdge);

  /* ---- VÓRTICE DE ACTIVACIÓN (video francés): estalla → gira en embudo →
         se comprime en un TORO 3D inclinado (portal, video f7d16b9e) → esfera ---- */
  let vortex = 0, vortexWant = 0, vSpin = 0, musicOn = false;
  let po = 0, poWant = 0;                     // mezcla esfera ⇄ portal toroidal

  /* ---- onda de choque (shockwave) al ejecutar una acción ---- */
  const waves = [];
  function shockwave() {
    const w = new THREE.Mesh(new THREE.TorusGeometry(1.2, .02, 8, 120),
      new THREE.MeshBasicMaterial({ color: 0x8fe4ff, transparent: true, opacity: .9,
        blending: THREE.AdditiveBlending, depthWrite: false }));
    w.rotation.x = Math.PI / 2.4;
    group.add(w); waves.push({ m: w, t0: performance.now() });
  }

  /** ANIMACIÓN DE ACCIÓN de la referencia: el orbe estalla, gira disperso
      formando un círculo de estrellas y se recompone en espiral. */
  function burst() {
    shockwave(); spinBoost = 6; target = 1;
    setTimeout(() => { shockwave(); }, 260);
    setTimeout(() => { target = 0; }, 1500);   // se recompone solo
  }

  /** ACTIVACIÓN al recibir una orden (voz o chat): vórtice → portal tórico → esfera. */
  function activate() {
    shockwave(); spinBoost = 6; vortexWant = 1;
    setTimeout(() => { shockwave(); }, 300);
    setTimeout(() => { vortexWant = 0; poWant = 1; }, 1700);   // del vórtice al portal 3D
    setTimeout(() => { poWant = 0; }, musicOn ? 1700 : 3200);  // y de vuelta en esfera
  }

  /* depuración por URL: ?vortex / ?portal / ?disc congelan cada estado */
  if (/[?&]vortex/.test(location.search)) vortexWant = 1;
  if (/[?&]portal/.test(location.search)) { po = 1; poWant = 1; }
  if (/[?&]disc/.test(location.search)) musicOn = true;

  let frameNo = 0;
  function frame(t) {
    requestAnimationFrame(frame);
    energy += (target - energy) * .05;
    spinBoost *= .96;
    discMode += ((musicOn ? 1 : 0) - discMode) * .04; // esfera ⇄ disco
    discAngle += .008 + audioL * .02 + audioB * .05; // ¡gira con la música!!
    audioB *= .92;                                    // el pulso del bajo decae
    vortex += (vortexWant - vortex) * .06;
    vSpin += .04 + vortex * .16;                      // el vórtice arremolina
    po += (poWant - po) * .06;                        // esfera ⇄ portal tórico
    const e = energy, dm = discMode, vx = vortex, pox = po, p = geo.attributes.position.array;
    for (let i = 0; i < N; i++) {
      const bx = base[i*3], by = base[i*3+1], bz = base[i*3+2], s = seed[i];
      const ang = Math.atan2(bz, bx) + e * (spinBoost * .06 + s * .35); // giro espiral al dispersar
      const rx = Math.cos(ang) * RING_R, rz = Math.sin(ang) * RING_R;
      const wob = 1 + e * .25 * Math.sin(t * .002 + s * 6);
      let x = (bx * (1 + e * 1.1) * wob) * (1 - e) + rx * e * wob;
      let z = (bz * (1 + e * 1.1) * wob) * (1 - e) + rz * e * wob;
      let y = by * (1 - e * .85) + Math.sin(t * .003 + s * 9) * .12 * e;
      if (vx > .01) {
        // embudo/vórtice: radio crece con la altura, cada vuelta gira más
        const yv = by / 1.15;                        // -1..1
        const rv = .35 + (yv * .5 + .5) * 1.75;
        const a = ang + yv * 2.6 + vSpin;
        const jit = 1 + Math.sin(t * .006 + s * 8) * .06 * vx;
        x += (Math.cos(a) * rv * jit - x) * vx;
        z += (Math.sin(a) * rv * jit - z) * vx;
        y += (yv * 1.75 - y) * vx;
      }
      if (dm > .01) {
        // posición en el anillo: banda brillante hueca (el "círculo que gira"
        // de la referencia) + surcos interiores tipo vinilo en los bordes
        const band = (i * 7919) % 100;
        const ri = band < 78 ? 1.62 + (band / 100) * .52          // halo principal
                             : .55 + (band / 100) * 1.0;          // surcos internos
        const a0 = (i * 2.39996) % 6.28318;
        const spin = a0 + discAngle * (1.6 - ri * .35);
        const pump = 1 + audioB * .14;
        const dx = Math.cos(spin) * ri * pump;
        const dz = Math.sin(spin) * ri * pump;
        const dy = Math.sin(ri * 16 + t * .0025) * .03 + (s - 3.14) * .01;
        x += (dx - x) * dm; y += (dy - y) * dm; z += (dz - z) * dm;
      }
      if (pox > .01) {
        // PORTAL 3D: toro inclinado que gira — los partículas se enroscan en
        // el tubo del anillo (video f7d16b9e), con respiración del grosor
        const uu = (i * 2.39996) % 6.28318 + discAngle * 2;
        const vv = (i * 1.239) % 6.28318 + s;
        const rr = .30 + Math.sin(t * .002 + s * 7) * .06;
        const rad = 1.9 + rr * Math.cos(vv);
        const tx = Math.cos(uu) * rad, ty = rr * Math.sin(vv), tz = Math.sin(uu) * rad;
        const th = .55 + Math.sin(t * .0004) * .25;   // inclinación que cabecea
        const ct = Math.cos(th), sth = Math.sin(th);
        x += (tx - x) * pox;
        y += (ty * ct - tz * sth - y) * pox;
        z += (ty * sth + tz * ct - z) * pox;
      }
      p[i*3] = x; p[i*3+1] = y; p[i*3+2] = z;
    }
    geo.attributes.position.needsUpdate = true;
    if ((frameNo++ % 3) === 0) updatePlexus();   // hilos a 20 fps: barato y fluido
    lines.material.opacity = .18 * (1 - e * .55) * (1 - vx * .8) + pox * .10;
    core.rotation.y = t * .00022 + e * t * .0006 + spinBoost * .004;
    core.material.size = .028 + e * .016 + dm * .008;
    nucleus.scale.setScalar(1 + Math.sin(t * .004) * .08 + e * .5 + audioB * .9 * dm - vx * .7 - pox * .7);
    nucleus.material.opacity = .95 * (1 - vx * .8) * (1 - pox * .8);
    glow.scale.setScalar(1.6 + Math.sin(t * .004) * .18 + e * 1.4 + audioB * 2.2 * dm + vx * 1.2);
    glow.material.opacity = (.8 - e * .5) * (1 - vx * .6) * (1 - pox * .6);
    r1.rotation.z = t * .0004 + spinBoost * .01; r2.rotation.y = t * .0003;
    r1.material.opacity = .6 * (1 - dm * .8) * (1 - vx) * (1 - pox * .5);
    r2.material.opacity = .6 * (1 - dm * .8) * (1 - vx) * (1 - pox * .5);
    halo.scale.setScalar(1 + Math.sin(t * .003) * .03 + e * .5);
    halo.material.opacity = .14 * (1 - dm) * (1 - vx) * (1 - pox);
    discEdge.material.opacity = dm * (.5 + audioB * .5);
    discEdge.scale.setScalar(1 + audioB * .12 * dm);
    floor.rotation.y = t * .00012 + spinBoost * .002 + discAngle * .25 * dm;
    group.position.y = Math.sin(t * .0012) * .06;
    // profundidad 3D: todo el conjunto cabecea suavemente en el espacio
    group.rotation.x = Math.sin(t * .00035) * .18;
    group.rotation.z = Math.sin(t * .00027) * .10;
    // ondas: crecen y se desvanecen
    for (let i = waves.length - 1; i >= 0; i--) {
      const w = waves[i], dt = (t - w.t0) / 900;
      if (dt >= 1) { group.remove(w.m); w.m.geometry.dispose(); waves.splice(i, 1); continue; }
      w.m.scale.setScalar(1 + dt * 3.2);
      w.m.material.opacity = .9 * (1 - dt);
    }
    ren.render(scene, cam);
  }
  requestAnimationFrame(frame);

  addEventListener('resize', () => {
    cam.aspect = innerWidth / innerHeight; cam.updateProjectionMatrix();
    ren.setSize(innerWidth, innerHeight);
  });

  return {
    speak(ms = 2600) { target = 1; if (ms > 0) setTimeout(() => target = 0, ms); },
    burst,
    /** vórtice de activación: se dispersa, gira en embudo y forma un portal */
    activate,
    stop() { target = 0; vortexWant = 0; poWant = 0; },
    listen(on) { target = on ? .35 : 0; },
    /** activar/desactivar el modo vinilo del ejecutor de música */
    setDisc(on) { musicOn = !!on; if (!on) target = 0; },
    /** nivel 0..1 (volumen) y bajo 0..1 (pulso) desde el AnalyserNode */
    setAudio(level = 0, bass = 0) { audioL = level; audioB = Math.max(audioB, bass); },
  };
}
