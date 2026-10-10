# Notas de las Release

Texto listo para pegar en GitHub (*Releases → Draft a new release → la etiqueta ya creada*).
Las etiquetas `v0.7.0`, `v0.8.0`, `v0.9.0` y `v0.10.0` están publicadas en el remoto y cada una
resuelve a su commit; lo que falta es la página de Release, y eso necesita la sesión de la dueña
del repositorio — desde esta máquina no se crea por API (`gh` sin sesión iniciada, medido dos veces).

---

## `v0.10.0` — la cara se aparta cuando deja de hacer falta

Hasta ahora la pantalla de CORT tenía **un tirador que abría cinco paneles a la vez**. Esta
versión la rediseña contra los videos de referencia que la dueña del proyecto aportó, y el
resultado es **un riel de seis hilos en el borde derecho, uno por panel, y uno cada vez**.

- **`docs/REFERENCIAS.md`** — el análisis, por escrito y por primera vez: siete clips, seis
  fotogramas por clip en hojas de contacto, dos resultaron ser tutoriales de instalación y no
  interfaz, y de los demás salen **seis patrones** (el reactor es la pantalla; los paneles son
  hilos, no cajas; uno se abre y los demás se apartan; con el gesto la interfaz desaparece; la
  entrada es una línea; se llega con tres manos). **Cero assets, cero fotogramas, cero líneas de
  código de terceros en el repositorio**: lo que se copia es distribución, y está dicho en el doc.
- **`cort/paneles.ts`** — todo el estado de la cara en **lógica pura, sin DOM**: seis paneles con
  su etiqueta y su tecla en una sola lista, `alternar` que **sustituye** al panel abierto en vez
  de acumular, y un apagado por inactividad que no atenúa nada si hay un panel abierto, si la cara
  está apagada o si el sistema pide `prefers-reduced-motion`.
- **`ui/Riel.tsx`** — seis hilos de luz con el número de su tecla; el panel se monta y se desmonta,
  así que en reposo **no hay registro ni controles en el DOM**. El contador de mensajes sin leer
  vive ahora dentro del hilo de mensajes.
- **Se llega con tres manos**: el dedo toca el hilo; con el cursor basta pasar por encima
  (filtrado por `pointerType === 'mouse'`, porque en una pantalla táctil el `hover` no existe y
  fingirlo abriría paneles al deslizar); y el teclado es de primera clase — `1`–`6` abren cada
  panel, `/` salta al campo, `Esc` guarda, `h` apaga la cara y deja sólo el reactor, `?` abre la
  ayuda, que se genera de la misma lista que el riel, así que no puede desincronizarse.
  **Mientras se escribe en el campo ninguna tecla manda sobre la interfaz**: sólo `Escape`.
- **La interfaz se aparta sola**: doce segundos sin gesto y el riel con la barra de abajo bajan al
  26 % de opacidad; cualquier movimiento los despierta. Es **un `setTimeout` rearmado**, no un
  reloj contando, y el despertar por `pointermove` va recortado a 250 ms para no reconciliar el
  árbol a 60 Hz en dos núcleos.
- **Las primeras pruebas de JavaScript del repo, sin instalar nada**: `make test-web` transpira
  `paneles.ts` con el paquete `typescript` que **ya estaba** en `devDependencies` y lo ejecuta con
  `node --test`. **17 pruebas** que fijan lo que de verdad se rompe (atajos mientras se escribe,
  teclas con modificador, el segundo exacto del apagado). Van separadas de `make test` porque las
  316 de Python tienen que poder correr en una máquina sin Node.
- `ui/Bandeja.tsx` **se elimina**; `ui/Hud.tsx` queda en una sola línea abajo, y `Telemetry.tsx`
  pierde su prop `oculto` (si no hay panel abierto, no se monta).
- **Sin marco nuevo en el protocolo** (el riel no habla con el core) y **sin dependencias nuevas**.
- `make test` → **316 en verde**; `make test-web` → **17**; `npx tsc --noEmit` limpio;
  `npm run build` limpio (1 289,96 kB, gzip 358,00 kB).

**Sin verificar aquí**: el dedo sobre el teléfono físico (la pasada de navegador fue de cursor y
teclado), el teclado del Android con `1`–`6`, y **`Enter` para enviar** — el `<form onSubmit>` no
cambió con el riel y `form.requestSubmit()` envía y limpia el campo, pero con `press_key "Enter"`
del navegador automatizado no disparó, así que esa tecla no se afirma. La portada del README sigue
siendo la captura de `v0.6.0`, y el README lo dice: el tirador `⌃ mensajes` que se ve en ella ya no está.

**Zip**: `https://github.com/Sandra2244/CORT/archive/refs/tags/v0.10.0.zip`

---

## `v0.9.0` — CORT ya hace más de una cosa por mensaje

Un asistente reactivo contesta una orden. Éste ahora **encadena, ejecuta y comprueba**:
«sube el volumen, haz una captura y pausa la música» deja de resolverse con la primera frase
y se convierte en tres pasos ejecutados uno detrás de otro, cada uno con su verificación en
el mundo real.

- **`cort_core/planner.py` + `intents.match_all()`** (función 75): el mensaje se parte por
  `;`, `,`, `y`, `luego`, `después`, `entonces`, `además`; cada trozo pasa **por los mismos
  patrones de la lista cerrada de siempre** —lo que no está en ella no se convierte en paso—,
  se hereda el verbo del tramo anterior («abre la terminal y el gestor de archivos») y hay un
  tope de cuatro pasos por latencia, no por estética.
- **Nada de herramientas para el LLM** (regla 6 de `AGENTS.md`): `planner.py` no arma comandos
  ni tiene vía al shell, y hay una prueba que le lee el propio fuente para afirmarlo.
- **Sin marco nuevo en el protocolo**: los pasos viajan en los `intent` y `effect` que la
  interfaz ya entiende y el cierre es un `assistant_message`. Un cliente viejo no se rompe.
- **Medido en esta máquina**, con el ejecutor real, memoria en `/tmp` y sin Ollama ni navegador:
  8 marcos en **2,30 s** y este resumen saliendo del core —
  `2 de 3 pasos hechos: la captura de pantalla, pausar la reproducción. No pude: subir el
  volumen (el mando obedeció pero el nivel sigue en 100 % (¿salida de audio en Dummy?))`.
  La captura dejó un PNG de 161 KB en disco y el volumen **no se contó como hecho** aunque el
  mando respondiera 0: el comprobador sabe negar.
- **316 pruebas en verde** (66,6 s en esta máquina de dos núcleos; 27 nuevas en `test_planner.py`
  y 5 nuevas de protocolo).
- Documentación: sección nueva en `docs/ARCHITECTURE.md`, fila 75 en `docs/FUNCTIONS.md`
  (75 funciones: 24 hechas, 11 en curso, 40 pendientes) y `README.md` actualizado en el mismo commit.

**Sin verificar aquí**: la interfaz pintando los tres pasos en la ventana (se afirma por el
código del cliente, no por captura nueva), el teléfono físico y cualquier oída de la voz.

**Zip**: `https://github.com/Sandra2244/CORT/archive/refs/tags/v0.9.0.zip`

---

## `v0.8.0` — lo que se rechaza queda escrito

Primera pieza de la «base y proyección contra malware»: no bastaba con cerrar la puerta
(`v0.7.0`), hacía falta poder decir **qué** se pidió, desde dónde y que no pasó.

- **`cort_core/audit.py`** (función 74): una línea JSON por puerta cerrada en
  `services/core/data/rechazos.jsonl` (carpeta fuera de git), con seis motivos de **lista
  cerrada** y hora UTC.
- **El secreto nunca entra en el registro**: se guarda el *camino* pedido y no la URL, porque
  un `?token=` apuntado sería un archivo de claves; y si la llave aparece dentro de un nombre
  de archivo, se sustituye por `«llave»`. Comprobado con `grep` sobre el archivo crudo.
- **Un carácter de control no fabrica una segunda línea** (inyección clásica en log), un motivo
  inventado no se escribe, y un disco que no puede escribir devuelve `False` **sin lanzar
  excepción**: apuntar es secundario, cerrar la puerta no.
- **Leíble**: `make rechazos` o `python -m cort_core.audit [n]`.
- **Medido en vivo**: core publicado en `0.0.0.0`, cinco `curl` contra la IP de la Wi-Fi de
  esta máquina → `401 / 401 / 404 / 404 / 200`, cuatro líneas en la bitácora con su origen, y
  el apretón de manos del WebSocket sin llave cortado con `403`.
- **284 pruebas en verde** (20 nuevas en `test_audit.py`, 6 en `test_avatars.py`, más el
  aislamiento que impide que las pruebas de red escriban en la bitácora real).

**Zip**: `https://github.com/Sandra2244/CORT/archive/refs/tags/v0.8.0.zip`

---

## `v0.7.0` — la voz, y la red con llave

- **Voz en el navegador** (función 13): CORT lee cada respuesta con las voces del sistema,
  puntuando las *Natural* y la región; es la voz que se oye en el video del colaborador.
  **Escuchar** sigue en curso: el botón está escrito y montado, pero esta máquina no tiene
  ningún dispositivo de captura (`wpctl status` no lista *Source*, medido otra vez con
  auriculares Bluetooth delante).
- **Puerta de red** (función 73, `cort_core/security.py`): `--lan` **no abre el puerto** sin
  `CORT_LAN_TOKEN` —el lanzador y `python -m cort_core.server` se niegan y salen con código 1—;
  en `127.0.0.1` no se pide nada; la comparación es `hmac.compare_digest`; el `401` de un
  atuendo llega **antes** de tocar el disco y el WebSocket se cierra con **4401 antes de
  `accept()`**.
- **README público en español**: siete etiquetas de colores, índice, ocho pasos de instalación,
  tabla de «si algo no arranca» y el inventario de funciones contado sobre `docs/FUNCTIONS.md`.
- **257 pruebas en verde**.

**Sin verificar**: el teléfono físico (Samsung A16) abierto desde la red, y TLS —por `http://`
la llave viaja en claro y el navegador no da cámara ni micrófono fuera de `127.0.0.1`.

**Zip**: `https://github.com/Sandra2244/CORT/archive/refs/tags/v0.7.0.zip`
