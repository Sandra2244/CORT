/* ===== ORB de CORT — Three.js (estilo referencia azul) =====
   Capas visibles en el video: núcleo rojo-anaranjado brillante,
   cáscara de partículas azules, anillos orbitales, anillos de suelo
   concéntricos y estrellas. Al hablar se dispersa en círculo de estrellas. */
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

  /* ---- núcleo rojo-anaranjado (el "corazón" de la referencia azul) ---- */
  const nucleus = new THREE.Mesh(new THREE.SphereGeometry(.30, 24, 24),
    new THREE.MeshBasicMaterial({ color: 0xff6a2a }));
  group.add(nucleus);
  const glow = new THREE.Sprite(new THREE.SpriteMaterial({
    map: makeGlowTexture(), color: 0xff8f45, transparent: true, opacity: .85,
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
    gr.addColorStop(0, 'rgba(255,170,90,1)'); gr.addColorStop(.4, 'rgba(255,110,40,.35)');
    gr.addColorStop(1, 'rgba(255,80,20,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
    return new THREE.CanvasTexture(c);
  }

  /* ---- energía 0..1: 0 esfera compacta, 1 dispersión en anillo de estrellas ---- */
  let energy = 0, target = 0, spinBoost = 0;
  const RING_R = 2.6;

  /* ---- MODO DISCO (ejecutor de música): el orbe se dispersa y forma un
         círculo/vinilo que gira; la velocidad y el pulso los manda el audio ---- */
  let discMode = 0, discWant = 0, discAngle = 0, audioL = 0, audioB = 0;
  const discEdge = new THREE.Mesh(new THREE.TorusGeometry(2.38, .012, 8, 200),
    new THREE.MeshBasicMaterial({ color: 0x8fe4ff, transparent: true, opacity: 0,
      blending: THREE.AdditiveBlending, depthWrite: false }));
  discEdge.rotation.x = Math.PI / 2; group.add(discEdge);

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

  function frame(t) {
    requestAnimationFrame(frame);
    energy += (target - energy) * .05;
    spinBoost *= .96;
    discMode += (discWant - discMode) * .04;         // transición esfera ⇄ disco
    discAngle += .008 + audioL * .02 + audioB * .05; // ¡gira con la música!!
    audioB *= .92;                                    // el pulso del bajo decae
    const e = energy, dm = discMode, p = geo.attributes.position.array;
    for (let i = 0; i < N; i++) {
      const bx = base[i*3], by = base[i*3+1], bz = base[i*3+2], s = seed[i];
      const ang = Math.atan2(bz, bx) + e * (spinBoost * .06 + s * .35); // giro espiral al dispersar
      const rx = Math.cos(ang) * RING_R, rz = Math.sin(ang) * RING_R;
      const wob = 1 + e * .25 * Math.sin(t * .002 + s * 6);
      let x = (bx * (1 + e * 1.1) * wob) * (1 - e) + rx * e * wob;
      let z = (bz * (1 + e * 1.1) * wob) * (1 - e) + rz * e * wob;
      let y = by * (1 - e * .85) + Math.sin(t * .003 + s * 9) * .12 * e;
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
      p[i*3] = x; p[i*3+1] = y; p[i*3+2] = z;
    }
    geo.attributes.position.needsUpdate = true;
    core.rotation.y = t * .00022 + e * t * .0006 + spinBoost * .004;
    core.material.size = .028 + e * .016 + dm * .008;
    nucleus.scale.setScalar(1 + Math.sin(t * .004) * .08 + e * .5 + audioB * .9 * dm);
    glow.scale.setScalar(1.6 + Math.sin(t * .004) * .18 + e * 1.4 + audioB * 2.2 * dm);
    glow.material.opacity = .85 - e * .5;
    r1.rotation.z = t * .0004 + spinBoost * .01; r2.rotation.y = t * .0003;
    r1.material.opacity = .6 * (1 - dm * .8); r2.material.opacity = .6 * (1 - dm * .8);
    halo.scale.setScalar(1 + Math.sin(t * .003) * .03 + e * .5);
    halo.material.opacity = .14 * (1 - dm);
    discEdge.material.opacity = dm * (.5 + audioB * .5);
    discEdge.scale.setScalar(1 + audioB * .12 * dm);
    floor.rotation.y = t * .00012 + spinBoost * .002 + discAngle * .25 * dm;
    group.position.y = Math.sin(t * .0012) * .06;
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
    stop() { target = 0; },
    listen(on) { target = on ? .35 : 0; },
    /** activar/desactivar el modo vinilo del ejecutor de música */
    setDisc(on) { discWant = on ? 1 : 0; if (!on) target = 0; },
    /** nivel 0..1 (volumen) y bajo 0..1 (pulso) desde el AnalyserNode */
    setAudio(level = 0, bass = 0) { audioL = level; audioB = Math.max(audioB, bass); },
  };
}
