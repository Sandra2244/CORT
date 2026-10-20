/* Íconos de línea de CORT (SVG) — sustituyen a los emojis, que Android pinta a color.
   Uso en HTML: <i data-ic="mic"></i>   ·   en JS: ic('mic') */
(function () {
  const P = {
    mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3M9 21h6"/>',
    wake: '<circle cx="12" cy="12" r="1.6"/><path d="M8.6 8.6a4.8 4.8 0 0 0 0 6.8M15.4 8.6a4.8 4.8 0 0 1 0 6.8M5.6 5.6a9 9 0 0 0 0 12.8M18.4 5.6a9 9 0 0 1 0 12.8"/>',
    hand: '<path d="M8 13V6a1.5 1.5 0 0 1 3 0v5M11 10.5V4.5a1.5 1.5 0 0 1 3 0V11M14 11V6a1.5 1.5 0 0 1 3 0v6M17 11.5a1.5 1.5 0 0 1 3 0V15a6 6 0 0 1-6 6h-1.5a6 6 0 0 1-4.8-2.4L4.3 15.4a1.5 1.5 0 0 1 2.4-1.8L8 15.2"/>',
    folder: '<path d="M3 6.5A1.5 1.5 0 0 1 4.5 5H9l2 2h8.5A1.5 1.5 0 0 1 21 8.5v9a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 17.5z"/>',
    file: '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 12h6M9 16h6"/>',
    back: '<path d="M9 7 4 12l5 5M4 12h11a5 5 0 0 1 5 5"/>',
    lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    warn: '<path d="M12 3.5 2.5 20.5h19z"/><path d="M12 10v5M12 17.8v.4"/>',
    gear: '<circle cx="12" cy="12" r="3.2"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1"/>',
    play: '<path d="M8 5.5v13l10.5-6.5z" class="f"/>',
    pause: '<path d="M8.5 5.5v13M15.5 5.5v13" style="stroke-width:3"/>',
    prev: '<path d="M6 5.5v13"/><path d="M18.5 5.5 9 12l9.5 6.5z" class="f"/>',
    next: '<path d="M18 5.5v13"/><path d="M5.5 5.5 15 12l-9.5 6.5z" class="f"/>',
    refresh: '<path d="M20 12a8 8 0 1 1-2.4-5.7M20 4v5h-5"/>',
    grid: '<rect x="4" y="4" width="6.5" height="6.5" rx="1"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1"/><rect x="4" y="13.5" width="6.5" height="6.5" rx="1"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1"/>',
    list: '<path d="M4 6.5h16M4 12h16M4 17.5h16"/>',
    send: '<path d="M3.5 11.5 20.5 4 14 20.5l-3-6.5z"/><path d="M11 14 20.5 4"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    help: '<circle cx="12" cy="12" r="9"/><path d="M9.6 9.2a2.5 2.5 0 1 1 3.6 2.3c-.8.5-1.2.9-1.2 1.9"/><path d="M12 17.3v.4"/>',
    mail: '<rect x="3" y="5.5" width="18" height="13" rx="2"/><path d="M3.5 6.5 12 13l8.5-6.5"/>',
    open: '<path d="M3 7.5A1.5 1.5 0 0 1 4.5 6H9l2 2h8.5A1.5 1.5 0 0 1 21 9.5v9A1.5 1.5 0 0 1 19.5 20h-15A1.5 1.5 0 0 1 3 18.5z"/><path d="M12 17v-6M9.5 13 12 10.5 14.5 13"/>',
    brain: '<path d="M9 4a3 3 0 0 0-3 3 3 3 0 0 0-2 5 3 3 0 0 0 2 5 3 3 0 0 0 6 1V5a2 2 0 0 0-3-1zM15 4a3 3 0 0 1 3 3 3 3 0 0 1 2 5 3 3 0 0 1-2 5 3 3 0 0 1-6 1"/>',
  };
  window.ic = (name, cls = '') =>
    `<svg class="ic ${cls}" viewBox="0 0 24 24" aria-hidden="true">${P[name] || ''}</svg>`;
  const fill = (root = document) => root.querySelectorAll('[data-ic]').forEach(el => {
    if (!el.firstElementChild) el.innerHTML = window.ic(el.dataset.ic);
  });
  window.fillIcons = fill;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => fill());
  else fill();
})();
