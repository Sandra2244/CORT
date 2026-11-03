# PROCEDENCIA de `cort-web/` — de dónde viene cada archivo

**Leé esto antes de publicar, modificar o borrar cualquier cosa de esta carpeta.**

**Autoría:** CORT es de Askher Vargas y Sandra Lopez; soporte y permisos en
`Sandrasofialopezgomez3@gmail.com` y `Carlosa3325@gmail.com` (ver `../LICENSE` y
`../AVISO_LEGAL.md`). Lo que sigue describe de dónde salió la plantilla, no quién
dueño del proyecto.

---

## 1. Qué es esta carpeta

`cort-web/` es la interfaz de CORT. Está construida **sobre la demo web de J.A.R.V.I.S
de TechEnClair**, no sobre código propio desde cero. La copia física de esa demo se
descargó el **2026-11-02** y está en:

```
/home/Sandra/Escritorio/JARVIS-FUENTES/01_jarvis-web_techenclair/   (5,1 MB, espejo de techenclair.fr/jarvis-demo)
```

Esa carpeta de fuentes es la referencia intocada. `cort-web/` es lo mismo, rediseñado.

## 2. Estado legal — la parte importante

La demo de TechEnClair **no trae archivo LICENSE**. En el repo de GitHub que enlaza su
página ("Open source") sólo hay recursos de Home Assistant, **no el código de la app**.
Sin licencia declarada, el código es *all rights reserved* por defecto.

Consecuencia práctica, y es dura:

> **Esta carpeta NO se publica en GitHub ni en ningún sitio público hasta que
> TechEnClair responda por escrito.** Publicar sin permiso sería redistribuir código
> ajeno sin licencia, y eso no se arregla cambiando el nombre y los colores.

Lo que sí está hecho para pedir el permiso:

- Borrador de carta: `/home/Sandra/Escritorio/JARVIS-FUENTES/PERMISO_TECHENCLAIR.md`
  (destinatario publicado: `jean@domotique.fr`, también tienen Discord).
- **Estado a 2026-11-02: escrita, no enviada.** Enviarla le toca a Sandra.
- Si no responden en 15 días, se trata como «sin permiso»: la demo queda sólo como
  referencia documentada y hay que reescribir la interfaz desde cero.

El `LICENSE` de la raíz del repo (MIT, © 2026 Sandra Sofia Lopez) protege **el trabajo
propio** (`cort-bridge/`, `cort/cort-*.js`, `cort/cort-style.css`), no el código ajeno
que está debajo. Eso hay que separarlo antes de publicar: o se licencia la base, o se
sube sólo lo propio.

## 3. Archivo por archivo — quién lo escribió

| Ruta | Origen | Estado |
|---|---|---|
| `index.html` | Demo TechEnClair | Modificado (56 líneas) |
| `index.html.orig` | Demo TechEnClair | **Intacto** — respaldo del original |
| `assets/main-s6G6kMTO.js` | Demo TechEnClair | Modificado (3 líneas) |
| `assets/main-s6G6kMTO.js.orig` | Demo TechEnClair | **Intacto** |
| `assets/main-CLjAaHak.css` | Demo TechEnClair | Intacto |
| `assets/three.module-*.js` | Demo TechEnClair (three.js empaquetado) | Intacto |
| `wallpapers/*` | Demo TechEnClair | Intactos |
| `demo/mock-ws.js` | Demo TechEnClair | Descargado del index; sigue en disco por si se vuelve atrás |
| `demo/demo-banner.js` | Demo TechEnClair | Modificado (2 líneas) y fuera del index |
| `demo/demo-banner.js.orig` | Demo TechEnClair | **Intacto** |
| `cort/cort-ui.js` | **Código propio de CORT** | 100 % nuestro |
| `cort/cort-mock.js` | **Código propio de CORT** | 100 % nuestro |
| `cort/cort-style.css` | **Código propio de CORT** | 100 % nuestro |
| `cort/sin-servicio.html` | **Código propio de CORT** | Página honesta "sin servicio" |
| `cort/vendor/leaflet/*` | Leaflet 1.9.4, BSD-3 | Espejo local (era CDN unpkg) |

## 4. Qué se cambió exactamente en la base

**`index.html`** (56 líneas tocadas sobre 5.900):

- `<html lang="fr">` → `lang="es"`; `<title>J.A.R.V.I.S</title>` → `<title>CORT</title>`.
- Logo de arranque: `J.A.R.V.I.S` / `JUST A RATHER VERY INTELLIGENT SYSTEM` →
  `CORT` / `COGNITIVA · OMNIPRESENTE · RAPSODIA · TERMINAL`; `BUILD TECHENCLAIR` →
  `PROYECTO CORT — SANDRA LÓPEZ`.
- `www.techenclair.fr` en la barra de arranque y en la etiqueta del asistente → textos
  propios. La pantalla del "sistema de navegación" con su marca de agua y su TikTok → CORT.
- Link de Leaflet: `unpkg.com` → `cort/vendor/leaflet/` (**sin CDN**).
- `<script src="demo/mock-ws.js">` y `demo-banner.js` fuera; entran `cort/cort-mock.js`,
  `cort/cort-ui.js` y `cort/cort-style.css`.
- Botón `MISE À JOUR JARVIS` → `ACTUALIZAR CORT` (sin enlace externo).
- Comentario de procedencia en el `<head>`.
- **Los tres `<script defer src="https://cdn.jsdelivr.net/npm/@mediapipe/...">` fuera**
  (hands, camera_utils, drawing_utils). Pesaban ~2 MB desde un CDN y se cargaban en cada
  arranque. El bundle trae guardas `typeof Hands > "u"`, así que el modo holograma de
  gestos no arranca y el resto de la interfaz sigue igual (comprobado: consola limpia al
  cargar). Para volver a activarlos, restaurar las tres etiquetas desde `index.html.orig`.
- Selector "CEREBRO PREFERIDO (LLM)" y sus opciones, en español; los valores (`auto`,
  `local_uncensored`, …) no se tocan porque el bundle los compara.
- Las tres tarjetas de modelo local (`local_model_choice`) eran `dolphin3`, `phi3.5` y
  `llama3.1:8b`: **ninguno de los tres existe en este equipo**. Ahora son
  `smollm2:135m`, `qwen2.5:0.5b` y `qwen3:0.6b`, los tres medidos en disco, con su peso y
  la RAM que piden.

Tras estos cambios **no queda ninguna carga externa en el arranque**: `grep` de
`src="http…"` en el index sale vacío. Lo que sí sigue yendo a internet **al usar el panel
correspondiente** son losetas del mapa (`mt1.google.com`), las webcams de Windy, y el
reproductor HLS (`cdn.jsdelivr.net/npm/hls.js`) que el bundle inyecta bajo demanda.

**`assets/main-s6G6kMTO.js`** (3 líneas): las tres salidas a
`https://www.techenclair.fr/...` (actualizador, banner y botón del panel) apuntan ahora a
`cort/sin-servicio.html`. Nada más tocado del bundle.

**`demo/demo-banner.js`** (2 líneas): rutas relativas rotas del espejo (`../pages/jarvis.html`)
→ URL absoluta, para que el banner no apunte a la nada si algún día se vuelve a cargar.
Hoy **no se carga**.

## 5. Cómo volver atrás

Caminos de regreso, del más fino al más grueso:

```bash
# 1) Dejar la interfaz como el original de la demo (los .orig están versionados):
cd ~/Escritorio/CORT/cort-web
cp index.html.orig index.html
cp assets/main-s6G6kMTO.js.orig assets/main-s6G6kMTO.js
cp demo/demo-banner.js.orig demo/demo-banner.js

# 2) Quitar sólo la capa CORT sin tocar el resto: borrar las 3 líneas
#    <script src="cort/..."> y el <link ... cort-style.css> del index.

# 3) Todo el estado anterior al trabajo web, desde fuera del repo:
ls ~/Escritorio/"Respaldo Proyectos Programacion"/CORT_2026-11-02_pre-web/
#    contiene CORT/ copiado, CORT-fuentes-2026-11-02.tar.gz y manifesto_original.md5
#    (verificar con: md5sum -c manifesto_original.md5)
```

Rama de trabajo: **`web/cort-v0`**. `main` no se tocó. Nada está publicado en remoto.

## 6. Lo que NO viene de TechEnClair y es la parte de valor

`../cort-bridge/cort_server.py` (puente Python: clima real, auditoría real, medición real
de CPU/RAM/disco, protocolo con Ollama, gates de memoria) y los tres archivos de `cort/`.
Esa es la propiedad del proyecto. Si lo de la licencia no se resuelve, se puede reconstruir
una interfaz propia encima del mismo puente; el puente no depende de la demo.
