/* ===== el `three` de pega para las pruebas de la cara =====
   `ui/vendor/three.module.js` pesa lo que pesa y en 2 núcleos no se puede montar un
   WebGL de verdad para comprobar una máquina de estados. Lo que se necesita para ejecutar
   `ui/js/orbe-cara.js` y `ui/js/orbe-plexo.js` fuera del navegador son catorce clases que
   se comporten como las de Three en lo que estos dos módulos usan: color, atributos,
   materiales, un `Group` con rotación y un renderer que cuente sus llamadas.

   NO es un sucedáneo del orbe: los módulos que se prueban son los del repo, copiados tal
   cual a `/tmp` con los tres `import` reescritos (el archivo de prueba lo comprueba). Lo
   que se mide aquí es el COMPORTAMIENTO del adaptador: a qué estado se pasa con cada
   orden de la cara, qué nivel se le da al shader, si el bucle se congela de verdad con
   `pausa()` y si el presupuesto del pixel ratio se respeta.
*/
const HEX = /^#([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$/i;

export class Color {
  constructor(valor) { this.set(valor); }
  set(valor) {
    if (valor instanceof Color) { this.r = valor.r; this.g = valor.g; this.b = valor.b; this.hex = valor.hex; }
    else if (typeof valor === 'number') { this.hex = valor; this.r = ((valor >> 16) & 255) / 255; this.g = ((valor >> 8) & 255) / 255; this.b = (valor & 255) / 255; }
    else {
      const t = String(valor || '').trim();
      if (!HEX.test(t)) throw new Error('Color de Three no admite «' + t + '»');
      let h = t.slice(1);
      if (h.length === 3) h = h.split('').map(c => c + c).join('');
      this.hex = '#' + h.toLowerCase();
      this.r = parseInt(h.slice(0, 2), 16) / 255;
      this.g = parseInt(h.slice(2, 4), 16) / 255;
      this.b = parseInt(h.slice(4, 6), 16) / 255;
    }
    return this;
  }
  copy(o) { return this.set(o); }
  lerp(o, t) {
    this.r += (o.r - this.r) * t; this.g += (o.g - this.g) * t; this.b += (o.b - this.b) * t;
    const dos = v => Math.round(Math.max(0, Math.min(255, v * 255))).toString(16).padStart(2, '0');
    this.hex = '#' + dos(this.r) + dos(this.g) + dos(this.b);
    return this;
  }
  clone() { return new Color(this); }
  /* Three no guarda el hex: lo deriva de r/g/b al pedirlo. El de pega hacía lo fácil
     (leer `this.hex`), y así un `lerp` que no moviera los componentes habría pasado por
     bueno. Ahora las dos cosas tienen que estar de acuerdo, como en el navegador. */
  getHexString() {
    const dos = v => Math.round(Math.max(0, Math.min(255, v * 255))).toString(16).padStart(2, '0');
    return dos(this.r) + dos(this.g) + dos(this.b);
  }
}

export class BufferAttribute {
  constructor(arrayo, itemSize) { this.array = arrayo; this.itemSize = itemSize; this.count = arrayo.length / itemSize; }
}
export class Float32BufferAttribute extends BufferAttribute {}
export class Uint16BufferAttribute extends BufferAttribute {}

export class BufferGeometry {
  constructor() { this.attributes = {}; this.index = null; this.disposed = false; }
  setAttribute(nombre, a) { this.attributes[nombre] = a; return this; }
  getAttribute(nombre) { return this.attributes[nombre]; }
  setIndex(a) { this.index = a; return this; }
  dispose() { this.disposed = true; }
}

class Material {
  constructor(opts = {}) { Object.assign(this, opts); this.disposed = false; }
  dispose() { this.disposed = true; }
}
export const ShaderMaterial = class extends Material {};
export const SpriteMaterial = class extends Material {};
export const MeshBasicMaterial = class extends Material {};

export class Points {
  constructor(geo, mat) { this.geometry = geo; this.material = mat; this.rotation = { x: 0, y: 0, z: 0 }; }
}
export class LineSegments extends Points {}
export class Mesh extends Points {}
export class Sprite {
  constructor(mat) { this.material = mat; this.scale = { x: 1, y: 1, z: 1, set(x, y, z) { this.x = x; this.y = y; this.z = z; } }; }
}
export class Group {
  constructor() {
    this.children = []; this.rotation = { x: 0, y: 0, z: 0 }; this.position = { x: 0, y: 0, z: 0 };
  }
  add(...hijos) { this.children.push(...hijos); return this; }
  remove(...hijos) { this.children = this.children.filter(h => !hijos.includes(h)); return this; }
}
export class Scene extends Group {}

export class PerspectiveCamera {
  constructor(fov, aspect, cerca, lejos) {
    this.fov = fov; this.aspect = aspect; this.near = cerca; this.far = lejos;
    this.position = { x: 0, y: 0, z: 0, set(x, y, z) { this.x = x; this.y = y; this.z = z; } };
    this.actualizaciones = 0;
  }
  lookAt() { return this; }
  updateProjectionMatrix() { this.actualizaciones++; return this; }
}

export class CanvasTexture {
  constructor(canvas) { this.image = canvas; this.disposed = false; }
  dispose() { this.disposed = true; }
}

export const AdditiveBlending = 2;
export const NormalBlending = 1;

/** El renderer de pega: guarda lo que se le pide y CUELGA de contar los `render`. */
export class WebGLRenderer {
  constructor(opts = {}) {
    Object.assign(this, opts);
    this.pixelRatio = 1; this.ancho = 0; this.alto = 0;
    this.renderiza = 0; this.disposed = false;
    this.domElement = { tagName: 'CANVAS', parentNode: null };
    // La prueba necesita saber CUÁNTAS veces se pintó: el conteo vive aquí, no en el
    // adaptador, para no ensuciar su API con un método de examen.
    WebGLRenderer.instancias.push(this);
    if (opts.falla) throw new Error('WebGL no arrancó (a propósito, para probar la caída)');
  }
  setPixelRatio(v) { this.pixelRatio = v; }
  getPixelRatio() { return this.pixelRatio; }
  setSize(w, h) { this.ancho = w; this.alto = h; }
  render(escena, camara) {
    if (!escena || !camara) throw new Error('render() sin escena o sin cámara');
    this.renderiza++;
    // Lo que mira la prueba: con qué cámara y con qué escena se pintó el último cuadro.
    this.ultimaEscena = escena; this.ultimaCamara = camara;
  }
  dispose() { this.disposed = true; }
}
WebGLRenderer.instancias = [];
export const renderers = WebGLRenderer.instancias;

export default {
  Color, BufferAttribute, Float32BufferAttribute, Uint16BufferAttribute, BufferGeometry,
  ShaderMaterial, SpriteMaterial, MeshBasicMaterial, Points, LineSegments, Mesh, Sprite,
  Group, Scene, PerspectiveCamera, CanvasTexture, WebGLRenderer,
  AdditiveBlending, NormalBlending,
};
