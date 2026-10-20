/* ===== Gestor de ventanas de vidrio de CORT =====
   Crear, arrastrar, enfocar, minimizar al dock y cerrar con animación. */

let zTop = 20;
const wins = new Map();
const isMobile = () => window.isMobileHUD && window.isMobileHUD();

const syncSheet = () => document.body.classList.toggle('sheet',
  [...wins.values()].some(w => w.open && !w.minimized));

export function createWin({ id, icon, title, x, y, w = 300, h, html = '', dockIcon, onShow }) {
  const el = document.createElement('div');
  el.className = 'win state-closed';
  el.id = 'win-' + id;
  el.style.left = x + 'px'; el.style.top = y + 'px'; el.style.width = w + 'px';
  if (h) el.style.height = h + 'px';
  el.innerHTML = `
    <div class="winbar"><span class="ico">${icon}</span><span class="ttl">${title}</span>
      <button class="bmin" title="Minimizar">─</button>
      <button class="bclose" title="Cerrar">✕</button></div>
    <div class="wcontent">${html}</div>`;
  document.body.appendChild(el);

  const dockBtn = document.querySelector(`#dock [data-win="${id}"]`);

  const win = {
    el, id, open: false, minimized: false,
    content: el.querySelector('.wcontent'),
    focus() {
      document.querySelectorAll('.win').forEach(w => w.classList.remove('focused'));
      el.classList.add('focused'); el.style.zIndex = ++zTop;
    },
    show() {
      // en el celular las ventanas son hojas a pantalla completa: una a la vez
      if (isMobile()) wins.forEach(o => { if (o !== win && o.open && !o.minimized) o.minimize(); });
      el.classList.remove('state-closed', 'state-min');
      win.open = true; win.minimized = false; win.focus();
      if (dockBtn) { dockBtn.classList.add('active'); dockBtn.classList.remove('minimized'); }
      syncSheet();
      if (onShow) try { onShow(); } catch (e) { console.warn(e); }
      if (isMobile() && dockBtn) dockBtn.scrollIntoView({ inline: 'center', block: 'nearest', behavior: 'smooth' });
    },
    minimize() {
      el.classList.add('state-min'); el.classList.remove('state-closed');
      win.minimized = true;
      if (dockBtn) { dockBtn.classList.add('minimized'); }
      syncSheet();
    },
    close() {
      el.classList.add('state-closed'); el.classList.remove('state-min');
      win.open = false; win.minimized = false;
      if (dockBtn) dockBtn.classList.remove('active', 'minimized');
      syncSheet();
    },
    toggle() { win.open && !win.minimized ? win.minimize() : win.show(); },
  };

  el.addEventListener('pointerdown', () => win.focus(), true);
  el.querySelector('.bclose').onclick = e => { e.stopPropagation(); win.close(); };
  el.querySelector('.bmin').onclick = e => { e.stopPropagation(); win.minimize(); };

  // arrastre con pointer capture (funciona con mouse, táctil y lápiz)
  const bar = el.querySelector('.winbar');
  let drag = null;
  bar.addEventListener('pointerdown', e => {
    if (e.target.tagName === 'BUTTON' || isMobile()) return;
    drag = { dx: e.clientX - el.offsetLeft, dy: e.clientY - el.offsetTop };
    bar.setPointerCapture(e.pointerId);
  });
  bar.addEventListener('pointermove', e => {
    if (!drag) return;
    el.style.left = Math.max(-40, Math.min(innerWidth - 80, e.clientX - drag.dx)) + 'px';
    el.style.top = Math.max(4, Math.min(innerHeight - 40, e.clientY - drag.dy)) + 'px';
  });
  bar.addEventListener('pointerup', () => drag = null);
  bar.addEventListener('dblclick', () => win.minimize());
  // celular: deslizar la barra hacia abajo minimiza la hoja
  let sy = null;
  bar.addEventListener('touchstart', e => { if (isMobile()) sy = e.touches[0].clientY; }, { passive: true });
  bar.addEventListener('touchend', e => {
    if (sy !== null && e.changedTouches[0].clientY - sy > 60) win.minimize();
    sy = null;
  });

  if (dockBtn) dockBtn.onclick = () => win.open && !win.minimized ? win.minimize() : win.show();

  wins.set(id, win);
  return win;
}

export const getWin = id => wins.get(id);
