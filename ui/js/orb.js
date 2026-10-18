/* ===== ORB de CORT — Three.js =====
   Núcleo de partículas + anillos + estrellas.
   Animación de la referencia: al escuchar/hablar el orbe SE DISPERSA
   formando un círculo de estrellas y luego se recompone. */
import * as THREE from 'three';

export function initORB(mount) {
  const scene = new THREE.Scene();
  const cam = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, .1, 100);
  cam.position.z = 6;
  const ren = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  ren.setSize(innerWidth, innerHeight);
  ren.setPixelRatio(Math.min(devicePixelRatio, 2));
  mount.appendChild(ren.domElement);

  /* ---- núcleo: 2600 puntos sobre una esfera ---- */
  const N = 2600;
  const pos = new Float32Array(N * 3), base = new Float32Array(N * 3),
        seed = new Float32Array(N);
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
  scene.add(core);

  const halo = new THREE.Mesh(new THREE.SphereGeometry(1.02, 32, 32),
    new THREE.MeshBasicMaterial({ color: 0x0a66aa, transparent: true, opacity: .16 }));
  scene.add(halo);

  function ring(rad, tilt, col) {
    const m = new THREE.Mesh(new THREE.TorusGeometry(rad, .004, 8, 160),
      new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: .6 }));
    m.rotation.x = tilt; scene.add(m); return m;
  }
  const r1 = ring(1.75, 1.35, 0x2fb9ff), r2 = ring(2.15, 1.9, 0x7f6bff);

  /* ---- estrellas de fondo ---- */
  const S = 900, sp = new Float32Array(S * 3);
  for (let i = 0; i < S * 3; i++) sp[i] = (Math.random() - .5) * 60;
  const starsG = new THREE.BufferGeometry();
  starsG.setAttribute('position', new THREE.BufferAttribute(sp, 3));
  scene.add(new THREE.Points(starsG, new THREE.PointsMaterial({
    color: 0x9fd8ff, size: .05, transparent: true, opacity: .5, depthWrite: false })));

  /* ---- energía 0..1: 0 esfera compacta, 1 dispersión en anillo de estrellas ---- */
  let energy = 0, target = 0;
  const RING_R = 2.6;

  function frame(t) {
    requestAnimationFrame(frame);
    energy += (target - energy) * .05;
    const e = energy, p = geo.attributes.position.array;
    for (let i = 0; i < N; i++) {
      const bx = base[i*3], by = base[i*3+1], bz = base[i*3+2], s = seed[i];
      // dirección angular del punto → al dispersar se desliza hacia el anillo ecuatorial
      const ang = Math.atan2(bz, bx);
      const rx = Math.cos(ang) * RING_R, rz = Math.sin(ang) * RING_R;
      const wob = 1 + e * .25 * Math.sin(t * .002 + s * 6);
      p[i*3]   = (bx * (1 + e * 1.1) * wob) * (1 - e) + rx * e * wob;
      p[i*3+2] = (bz * (1 + e * 1.1) * wob) * (1 - e) + rz * e * wob;
      p[i*3+1] = by * (1 - e * .85) + Math.sin(t * .003 + s * 9) * .12 * e;
    }
    geo.attributes.position.needsUpdate = true;
    core.rotation.y = t * .00022 + e * t * .0006;
    core.material.size = .028 + e * .014;
    r1.rotation.z = t * .0004; r2.rotation.y = t * .0003;
    r1.material.opacity = .6 + e * .4; r2.material.opacity = .6 + e * .4;
    halo.scale.setScalar(1 + Math.sin(t * .003) * .03 + e * .5);
    ren.render(scene, cam);
  }
  requestAnimationFrame(frame);

  addEventListener('resize', () => {
    cam.aspect = innerWidth / innerHeight; cam.updateProjectionMatrix();
    ren.setSize(innerWidth, innerHeight);
  });

  return {
    /** dispersa el orbe ms milisegundos y lo recompone (0 = hasta stop()) */
    speak(ms = 2600) { target = 1; if (ms > 0) setTimeout(() => target = 0, ms); },
    stop() { target = 0; },
    /** latido suave mientras escucha */
    listen(on) { target = on ? .35 : 0; },
  };
}
