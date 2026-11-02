# DISEÑO DEL ORBE DE CORT — referencia sacada de los dos videos

**Fecha:** 2 de noviembre de 2026
**De dónde sale:** fotogramas extraídos de los dos videos que guardaste en
`~/Escritorio/Referencias IA CORT/`, sin ffmpeg: un servidorcito temporal
(`cort-bridge/cort_frames.py`, ya apagado) daba el MP4 con peticiones parciales y
el navegador pintaba cada segundo en un `<canvas>`. Los 43 fotogramas y los dos
mosaicos de revisión quedaron en:

```
~/Escritorio/Referencias IA CORT/fotogramas/
  montaje-1-orbe.png     ← VID-20261024-WA0034.mp4, 14 marcos (8 s … 242 s)
  montaje-2-vortice.png  ← f7d16b9e47ae45c813969bed77fedcf3.mp4, 14 marcos
  detalle-vortice.png    ← 1,5 s · 3 s · 4,5 s · 9 s  (el vórtice, en grande)
  detalle-orbe.png       ← 1 · 4 · 9 · 15 · 70 · 88 · 105 · 240 s
  VID-20261024-WA0034/   ← los .jpg sueltos, nombrados por segundo
  f7d16b9e-vortex/
```

**Estos archivos NO se commitean ni se publican:** son grabaciones de TikTok de
terceros (@techenclair y @teknomaster). Sirven como referencia visual privada, igual
que las capturas. De aquí solo sale diseño propio.

---

## 1. Qué se ve en cada video (lo que medí, no lo que supongo)

### Video 1 — `VID-20261024-WA0034.mp4` (255 s, 360×640, monitor + teléfono en soporte)

| Segundo | Qué hace el orbe | Para qué estado lo uso |
|---|---|---|
| 1 s | esfera de partículas **blancas** con arcos largos que la cruzan (líneas de gran círculo) y anillos orbitales finos | reposo |
| 4 s | la esfera **se contrae** y se vuelve una bola densa y brillante | volumen alto / hablando |
| 9 s | **dispersión**: todo colapsa a una ráfaga vertical tipo cometa, partículas estiradas en un eje | ejecutar una acción |
| 15 s | vuelve a formarse la esfera con sus arcos | fin de acción |
| 70 s | mismo esquema pero **verde-amarillo**, con un núcleo estelar y radios saliendo del centro | pensando |
| 88 s | verde, más pequeño y ordenado, núcleo brillante | escuchando |
| 105 s | verde **difuso y erizado**, sin arcos definidos | habla con volumen |
| 240 s | pantalla «CYBER SNAKE · RETRO EDITION» con rejilla neón | no es el orbe: es una **escena** (lo que aquí llamamos CORT OS) |

El teléfono que está al lado del monitor muestra **el mismo orbe, al mismo tiempo, en
los mismos colores** en todos los fotogramas: la interfaz del teléfono es la misma
página, no una versión aparte. Eso respalda la idea de la fase F7.

### Video 2 — `f7d16b9e47ae45c813969bed77fedcf3.mp4` (192 s, 576×1024)

| Segundo | Qué hace el orbe |
|---|---|
| 1,5 s | nube de partículas **cian** dispersas en esfera, con elípticas orbitales y un **núcleo estelar** pequeño y muy brillante |
| 3 s | la nube se **recolecta** hacia el plano del anillo: los brazos se curvan en espiral |
| 4,5 s | **anillo/vórtice formado**: toroide de partículas visto de frente, con filamentos que se salen del plano y un punto blanco incandescente girando en el borde |
| 9 s | el anillo se **inclinó** (ya se ve como elipse) mientras se abre una ventana encima: el vórtice sigue vivo detrás de la interfaz |

Del resto del video (60 s en adelante) lo que se ve son archivos `JARVIS_Setup_v1.exe`,
`.bat` y una guía de instalación en francés en el Bloc de notas: confirma lo ya sabido —
el backend de la demo es de Windows y aquí no aplica.

---

## 2. Lo que los dos videos enseñan y nuestra versión no tiene hoy

El orbe actual (Three.js vendorizado, 2000 partículas sobre una esfera, cámara en
z = 115) solo pone **puntos**. Los cinco rasgos que hacen que la referencia se vea bien
son estos, y ninguno está implementado:

1. **Arcos entre partículas.** Lo que dibuja la esfera no son los puntos: son cuerdas
   largas entre pares de partículas (líneas de gran círculo). Con `LineSegments` sobre
   ~120 cuerdas y opacidad baja se obtiene el calado sin coste.
2. **Núcleo estelar.** Un punto aditivo en el centro, con `sizeAttenuation` y tamaño
   ligado al volumen. Es lo que da el "brillo" en 1,5 s y en 70 s.
3. **Anillos orbitales.** 2–3 elipses inclinadas girando lento alrededor de la esfera
   (se ven en 1 s y en 1,5 s). Son `Line` de 128 puntos cada una, casi gratis.
4. **El vórtice, como transición y no como estado.** Los 3 segundos del video 2 son:
   esfera → recolección al plano → toroide → giro rápido → se queda de fondo inclinado.
   Eso es una **animación de 900 ms**, con curva de avance `easeInOutCubic`, y es lo que
   debe disparar cada acción ejecutada.
5. **La ráfaga de dispersión** (9 s del video 1) es distinta del vórtice: allí las
   partículas se **estiran a lo largo de un eje** y salen volando. Es el efecto de
   "se está haciendo", más corto (400 ms) y con retorno.

## 3. Paleta de CORT para los estados (nuestra, no la del video)

La referencia usa blanco y verde-amarillo. CORT tiene su propia paleta firma en
`cort-style.css` (`--cort-menta #00ffc8`, `--cort-cian #22e5ff`, `--cort-magenta #ff2bd6`,
`--cort-violeta #7b5cff`), así que los estados se mapean así:

| Estado | Color | Forma | Disparador real en el puente |
|---|---|---|---|
| reposo | cian apagado | esfera + arcos + anillos, giro lento | `state: idle` |
| escuchando | menta | anillos más juntos, núcleo fijo | `toggle_mic`/`user_speech` (F3) |
| pensando | violeta | núcleo pulsante, arcos temblorosos | `state: thinking` |
| hablando | menta→cian según volumen | radio ligado a `setVolume` | `live_subtitles` / TTS (F3) |
| **ejecutando** | ámbar | **ráfaga de dispersión 400 ms** | `av_scan_start`, `pull_ollama_model`, acciones F5 |
| alerta | magenta | vórtice lento + parpadeo | amenaza del antivirus, puerta de RAM/disco |
| descarga | ámbar con anillo de progreso | anillo que se llena | `pull_ollama_model` con % real |

## 4. Cómo se implementa sin tocar el bundle minificado

La instancia del orbe **no está expuesta** en el DOM (solo existe
`window.triggerEchoConstruction`), así que no se puede parchear desde fuera. La capa
propia es un módulo aparte que se monta encima del mismo `<canvas>`:

```
cort-web/cort/cort-orbe.js   ← código nuestro, 100 %
  · lee el estado desde los mensajes del puente (state, av_*, pull_*, live_subtitles)
  · dibuja arcos, núcleo y anillos con sus propios objetos Three.js
  · expone window.CORT_orbe = {setState, burst, vortex, fps}
```

El orbe de la demo sigue corriendo debajo y aporta las partículas; lo nuestro aporta
lo que en la referencia es lo que se nota. Si el WebGL de la Canaima no da, la capa se
desmonta y la pantalla sigue funcionando (el motor ya tiene un camino mudo de respaldo).

**Vara de salida de F2 (medible, no estética):** 7 estados distinguibles con el color de
la tabla, ráfaga en menos de 400 ms, vórtice en menos de 900 ms, **FPS ≥ 24 medidos con
`requestAnimationFrame`** en la pestaña real, y `window.CORT_orbe.fps()` devolviendo el
número. Nada de "se ve más bonito": se mide y se muestra.
