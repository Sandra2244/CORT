/*
 * El puente entre la cara de la PC y el Java del teléfono.
 *
 * Este archivo se carga ANTES que `cort/cort-mock.js` (Java lo inyecta justo
 * detrás de `<head>` cuando sirve `index.html` desde los `assets` del APK), y la
 * razón es una sola línea del mock:
 *
 *     const WS_NATIVA = window.WebSocket;   // hay que capturarla antes de sustituir el global
 *
 * Si nosotros llegamos tarde, el mock guarda el WebSocket de Chromium, intenta
 * `ws://cort.local:8765/ws`, no hay nada escuchando y la cara se queda en modo
 * simulación: bonita, pero muda. Si llegamos primero, guarda ESTE WebSocket, que
 * no abre sockets ni puertos: empuja el JSON a `CortNative.recibir()` y espera
 * la respuesta por `window.__cortNative.emit()`.
 *
 * Qué NO hace este archivo: no reimplementa el mock, no toca `cort-ui.js` y no
 * simula ningún dato. Todo lo que la interfaz pregunta viaja a Java, y Java
 * contesta con lo que midió el teléfono o con un `puente_aviso` que dice el
 * motivo. Un panel simulado en el teléfono sería mentir dos veces.
 */
(function () {
  "use strict";

  const N = window.CortNative;
  if (!N || typeof N.recibir !== "function") {
    // No estamos dentro del APK (alguien abrió `cort-web` en un navegador de
    // verdad): no se sustituye nada y la página habla con su puente de siempre.
    return;
  }

  /* ---------------------------------------------------------------- embudo */
  /* El único camino de vuelta. Java llama a `window.__cortNative.emit(objeto)`
   * con `evaluateJavascript`. Los eventos que llegan antes de que nadie escuche
   * se guardan: en un teléfono lento el orbe se monta después del primer
   * `system_stats`, y perder ese cuadro era quedarse con el HUD vacío. */
  const escuchas = [];
  const cola = [];
  const canales = new Set();

  window.__cortNative = {
    emit(ev) {
      // 1. A los que oigan el embudo crudo (diagnóstico, y el puente Java puede
      //    mandar cosas que la interfaz de la PC no conoce: permisos, pantalla
      //    leída, estado del servicio de escucha).
      if (!escuchas.length) {
        cola.push(ev);
        // El `cola` sólo sirve para lo que llegue antes de que nadie se suscriba.
        // Sin techo sería un crecimiento lento y permanente: Java empuja
        // `system_stats` cada cuatro segundos y un teléfono abierto toda la tarde
        // acumularía 900 cuadros por hora que nadie va a leer nunca.
        while (cola.length > 64) { cola.shift(); }
      } else { for (const f of escuchas) { try { f(ev); } catch (e) { console.warn("[cort-puente]", e); } } }
      // 2. Y al WebSocket que el mock tiene montado, que es lo que la interfaz
      //    de la PC espera: un mensaje con `data` en texto y su `JSON.parse`.
      const texto = JSON.stringify(ev);
      for (const c of canales) {
        if (c.readyState === ABIERTO) { c._recibe(texto); }
      }
    },
    on(f) {
      escuchas.push(f);
      for (const pendiente of cola.splice(0)) { try { f(pendiente); } catch (e) { console.warn("[cort-puente]", e); } }
    },
    off(f) {
      const i = escuchas.indexOf(f);
      if (i >= 0) { escuchas.splice(i, 1); }
    }
  };

  /* ------------------------------------------------------------ WebSocket */
  const CONECTANDO = 0, ABIERTO = 1, CERRANDO = 2, CERRADO = 3;

  function PuenteWS(url) {
    this.url = String(url || "");
    // ABIERTO desde el `new`, no desde el turno siguiente. Medido en la primera
    // prueba de esta fase: `cort-mock.js` decide en `handleClientMessage` si la
    // orden viaja o se simula mirando `PUENTE.vivo()`, que es
    // `ws.readyState === 1`. Con el `readyState` en 0 durante un tick, la primera
    // orden de la tarde (`check_ollama_status`, que la propia interfaz pide a los
    // 1,2 s de abrir) rebotaba en el simulador y el panel del cerebro salía con
    // números de mentira. Lo que sí va aplazado es el aviso `open`: el mock
    // instala sus manejadores justo después del `new`.
    this.readyState = ABIERTO;
    this.onopen = null;
    this.onmessage = null;
    this.onerror = null;
    this.onclose = null;
    this.binaryType = "arraybuffer";
    this._oidos = { open: [], message: [], error: [], close: [] };
    canales.add(this);
    setTimeout(() => {
      if (this.readyState !== ABIERTO) { return; }
      this._dispara("open", { type: "open" });
    }, 0);
  }

  PuenteWS.prototype.send = function (dato) {
    if (this.readyState !== ABIERTO) { throw new Error("el puente no está abierto"); }
    N.recibir(String(dato));
  };

  PuenteWS.prototype.close = function () {
    // Sin `onclose` a propósito. El mock reacciona a un cierre con tres reintentos
    // y luego uno cada 30 segundos; aquí no hay red que se caiga, y un lazo de
    // reconexión contra un canal que siempre está vivo sería CPU y batería por
    // nada. Si Java se muere, la cara sigue abierta y el próximo cuadro no llega:
    // eso ya lo cuenta el reloj del HUD.
    canales.delete(this);
    this.readyState = CERRADO;
  };

  PuenteWS.prototype._recibe = function (texto) {
    const ev = { type: "message", data: texto };
    if (typeof this.onmessage === "function") { this.onmessage(ev); }
    for (const f of this._oidos.message) { try { f(ev); } catch (e) { console.warn("[cort-puente]", e); } }
  };

  PuenteWS.prototype._dispara = function (tipo, ev) {
    const manijero = this["on" + tipo];
    if (typeof manijero === "function") { manijero.call(this, ev); }
    for (const f of this._oidos[tipo] || []) { try { f(ev); } catch (e) { console.warn("[cort-puente]", e); } }
  };

  PuenteWS.prototype.addEventListener = function (tipo, f) {
    if (this._oidos[tipo]) { this._oidos[tipo].push(f); }
  };

  PuenteWS.prototype.removeEventListener = function (tipo, f) {
    const lista = this._oidos[tipo];
    if (lista) { const i = lista.indexOf(f); if (i >= 0) { lista.splice(i, 1); } }
  };

  // La interfaz compara `readyState === WebSocket.OPEN`; sin las constantes aquí,
  // `undefined` y el puente parecería caído para siempre.
  PuenteWS.CONNECTING = CONECTANDO;
  PuenteWS.OPEN = ABIERTO;
  PuenteWS.CLOSING = CERRANDO;
  PuenteWS.CLOSED = CERRADO;

  window.WebSocket = PuenteWS;

  /* --------------------------------------------------- el service worker */
  /* `index.html` pregunta por los registros para limpiar los viejos. En el APK no
   * hay origen real ni red que cachear: se contesta en falso pero sin tirar un
   * error sin atrapar, que es lo que rompe una página en Chromium. */
  try {
    Object.defineProperty(navigator, "serviceWorker", {
      configurable: true,
      value: {
        controller: null,
        ready: Promise.reject(new Error("sin service worker dentro de la APK")),
        register: () => Promise.reject(new Error("sin service worker dentro de la APK")),
        getRegistration: () => Promise.resolve(undefined),
        getRegistrations: () => Promise.resolve([])
      }
    });
  } catch (noSePudo) {
    // Si el WebView no deja reescribir la propiedad, la página intentará registrar
    // y fallará sola; no es motivo para dejar de sustituir el WebSocket.
  }

  /* ------------------------------------------------------ capacidades */
  /* Lo mismo que regía en el APK viejo: se pregunta al aparato, y lo que no se
   * puede medir no se finge. Java responde un JSON con puertas; una puerta en
   * `false` es un panel que no debe ofrecer botones muertos. */
  let puertas = null;
  window.CORTcapaz = function (puerta) {
    if (puertas === null) {
      try { puertas = JSON.parse(N.capacidades() || "{}") || {}; }
      catch (e) { puertas = {}; }
    }
    return puertas[puerta] !== false;
  };

  window.CORT_esAndroid = true;
})();
