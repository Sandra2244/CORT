/* CORT — barrera de secretos antes del mock y del bundle heredado. */
(function () {
  "use strict";

  const CLAVE = "cort_web_v1";

  function sensible(nombre) {
    const n = String(nombre).toLowerCase();
    return n === "api_keys" || n === "clave" || n === "secret"
      || n.endsWith("_api_key") || n.endsWith("_token")
      || n.endsWith("_secret") || n.endsWith("_password");
  }

  function sanear(valor) {
    if (Array.isArray(valor)) return valor.map(sanear);
    if (!valor || typeof valor !== "object") return valor;
    const copia = {};
    for (const clave of Object.keys(valor)) {
      if (!sensible(clave)) copia[clave] = sanear(valor[clave]);
    }
    return copia;
  }

  function tieneSecretos(valor) {
    if (Array.isArray(valor)) return valor.some(tieneSecretos);
    if (!valor || typeof valor !== "object") return false;
    return Object.keys(valor).some(k => sensible(k) || tieneSecretos(valor[k]));
  }

  function purgarLegado() {
    try {
      const guardado = localStorage.getItem(CLAVE);
      if (!guardado) return;
      const datos = JSON.parse(guardado);
      const limpio = sanear(datos);
      if (JSON.stringify(datos) !== JSON.stringify(limpio)) {
        localStorage.setItem(CLAVE, JSON.stringify(limpio));
      }
    } catch (e) {
      try { localStorage.removeItem(CLAVE); } catch (noSePudo) {}
    }
  }

  function aviso() {
    return "CORT no guarda claves en el navegador. Usa el almacén seguro del dispositivo "
      + "cuando esa integración esté disponible.";
  }

  window.CORTsecretos = { sanear, tieneSecretos, purgarLegado, aviso };
  purgarLegado();
})();
