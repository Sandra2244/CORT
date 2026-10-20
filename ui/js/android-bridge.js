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
})();
