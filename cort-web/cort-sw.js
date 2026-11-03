/* CORT — service worker (fase F7)
 *
 * Regla de la fase F1 llevada al teléfono: lo que es programa se guarda, lo que es
 * medida no se toca. Las respuestas del puente (clima, temperatura, estado del equipo,
 * el WAV que CORT acaba de hablar) son datos de este instante: si el navegador los
 * cacheara, la pantalla mostraría un número viejo creyendo que es nuevo.
 */
const version = "cort-v1";
const programa = ["/", "/index.html", "/manifest.webmanifest",
  "/cort/cort-mock.js", "/cort/cort-orbe.js", "/cort/cort-ui.js", "/cort/cort-style.css",
  "/iconos/cort-192.png", "/iconos/cort-512.png"];

self.addEventListener("install", (ev) => {
  ev.waitUntil((async () => {
    const c = await caches.open(version);
    // Un archivo que falte no puede tumbar la instalación: se intenta uno por uno.
    for (const ruta of programa) {
      try { await c.add(new Request(ruta, { cache: "reload" })); } catch (e) {}
    }
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (ev) => {
  ev.waitUntil((async () => {
    const claves = await caches.keys();
    await Promise.all(claves.filter(k => k !== version).map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (ev) => {
  const req = ev.request;
  if (req.method !== "GET") return;
  const u = new URL(req.url);
  if (u.origin !== self.location.origin) return;
  // El puente manda datos vivos por WebSocket (no pasa por acá) y por /audio/*.wav.
  if (u.pathname.startsWith("/audio/")) return;              // nunca cachear voz
  if (u.pathname.startsWith("/api/")) return;

  ev.respondWith((async () => {
    const red = await fetch(req).catch(() => null);
    if (red && red.ok) {
      const c = await caches.open(version);
      if (programa.includes(u.pathname)) c.put(req, red.clone());
      return red;
    }
    const enCache = await caches.match(req);
    if (enCache) return enCache;
    // Sin red y sin copia: se devuelve la página con un aviso, no un error en blanco.
    const fuera = await caches.match("/index.html");
    if (fuera) return fuera;
    return new Response("CORT sin puente: la página está en caché pero no hay medidas.",
      { status: 503, headers: { "Content-Type": "text/plain; charset=utf-8" } });
  })());
});
