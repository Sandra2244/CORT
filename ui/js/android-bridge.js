/* Puente con la app Android (se carga antes que todo).
   Android → JS:  window.__cortNative.emit({type, ...})
   JS → Android:  window.CortNative.listen(), .speak(), .requestPermission()…
   Los eventos que llegan antes de que la interfaz esté lista se guardan en cola. */
(function () {
  const subs = [], queue = [];
  window.__cortNative = {
    emit(ev) {
      if (!subs.length) { queue.push(ev); return; }
      for (const f of subs) { try { f(ev); } catch (e) { console.warn('cort-native', e); } }
    },
    on(f) { subs.push(f); queue.splice(0).forEach(ev => { try { f(ev); } catch (e) { console.warn(e); } }); },
  };
  const root = document.documentElement;
  if (window.CortNative) root.classList.add('android');
  const mq = matchMedia('(max-width: 760px), (max-height: 520px)');
  const setMobile = () => root.classList.toggle('mobile', mq.matches);
  setMobile(); mq.addEventListener ? mq.addEventListener('change', setMobile) : mq.addListener(setMobile);
  window.isMobileHUD = () => root.classList.contains('mobile');

  /* ── qué puertas trae EL APK instalado (ronda 2.5) ──────────────────────────
     Desde la 2.5.0 la Release publica dos perfiles del mismo cuerpo:
     `completo`, que declara el traje de asistente, el reconocedor, el lector de
     avisos, el baldosín de la cortina y las llamadas; y `nucleo`, que no declara
     ninguno de esos servicios `BIND_*` — es la superficie exacta del `1.1.4` que a
     la dueña se le instala — porque eso es lo único que, medido, separa lo que
     Play Protect deja abrir de lo que bloquea.

     El Kotlin de esas cuatro puertas está dentro en los dos casos; lo que no está
     en el `nucleo` es su declaración en el manifiesto, y un servicio no declarado
     no arranca. Dejar el botón pintado sería mentir: por eso la cara pregunta.

     Se lee con `CortNative.capacidades()`, que devuelve el `<meta-data>` del
     manifiesto **del archivo instalado** — no una constante compilada. Y la regla
     de oro de este helper: si no se puede mirar, `true`. En el PC no hay puente;
     en un APK anterior a la 2.5 no hay método; en los dos casos la conducta de
     siempre (todas las puertas abiertas) es la correcta, y una cara que se crea
     sin capacidades cerraría funciones que sí existen. */
  let caps = null;
  window.CORTcapaz = puerta => {
    const N = window.CortNative;
    if (!N || typeof N.capacidades !== 'function') return true;
    if (caps === null) {
      try { caps = JSON.parse(N.capacidades()) || {}; } catch { caps = {}; }
    }
    return caps[puerta] !== false;
  };
  window.CORTperfil = () => {
    const N = window.CortNative;
    if (!N || typeof N.capacidades !== 'function') return 'escritorio';
    if (caps === null) {
      try { caps = JSON.parse(N.capacidades()) || {}; } catch { caps = {}; }
    }
    return caps.perfil || 'completo';
  };
  if (window.CortNative) root.classList.add('perfil-' + window.CORTperfil());
})();
