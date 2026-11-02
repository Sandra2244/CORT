# PLAN DE FASES — CORT

Del 2026-11-02. Cada fase tiene **5 tareas exactas** y una **salida medible**: si la
salida no se puede medir, la fase no está cerrada. Los números vienen del censo de
`INFORME_FUNCIONES.md` (mismo día): 155 botones, 34 órdenes sondeadas de las que
contestan 6, 138 comandos anunciados de los que responden bien 4, 10 paneles que se
abren vacíos.

La base de la demo de TechEnClair **se conserva como andamio** (menú, botones,
ventanas, HUD) y se rediseña por encima. Se acredita como referencia visual en el
README y en el repo. No se piden permisos y no se publican los `.orig` ni el espejo
descargado: ahí está la línea que protege tu autoría sin frenar nada.

---

## F1 — Que nada mienta (cimientos del puente)

1. Cola de escritura por conexión con candado: CORT habla y sigue leyendo órdenes a la
   vez. Hoy hay ~9 s de sordera medida en una respuesta larga.
2. `enviar_seguro()`: envíos que toleran pestaña cerrada y limpieza de conexiones
   muertas. Elimina la traza `Cannot write to closing transport` al recargar.
3. `update_settings` y `get_settings` atendidos: el botón GUARDAR de Ajustes guarda de
   verdad y Ajustes recupera ciudad, idioma y modelo al abrir.
4. Clima y temperatura reales en pantalla: la página pide clima al cargar y cada 10 min;
   el panel térmico lee `/sys/class/thermal` (medido: thermal_zone2 = 49,0 °C).
5. Sello de estado en los 10 paneles zombis: si no hay datos dicen «sin datos: falta X»
   con botón de reintento, en vez de un indicador de carga infinito.

**Salida:** al sondear las 34 órdenes, ninguna queda muda (contesta dato o contesta
motivo); 0 trazas en `/tmp/cort_bridge.log` tras recargar tres veces a media frase.

---

## F2 — El orbe y el arranque, ya de CORT

1. Capa `cort/cort-orbe.js` al lado del Three.js vendorizado: 7 estados con color
   propio (reposo, escucha, pensando, hablando, ejecutando, alerta, descarga).
2. Ráfaga tipo **vórtice** al ejecutar una orden: dispersión de partículas y
   reensamblado, disparada por un mensaje nuevo `estado: ejecutando` del puente.
3. Anillo de progreso mientras baja un modelo o corre la auditoría antivirus
   (el puente ya emite `ollama_pull_progress` y `av_progress` reales).
4. Pantalla de arranque con el nombre y el logo de CORT: fuera «JARVIS» y fuera los
   rótulos en francés del `boot-overlay`.
5. Medición en el navegador integrado: capturas de los 7 estados y FPS con 2 núcleos,
   para fijar el mínimo de partículas que no congela el equipo.

**Salida:** 7 estados visibles, dispersión en menos de 400 ms, FPS ≥ 24 medido, y el
orbe se ve distinto del original sin tocar el JS minificado.

---

## F3 — Cerebro encendido y voz

1. Turno de noche real: cargar `smollm2:135m` con `CORT_RAM_MIN=900 MODELO=smollm2:135m
./cort_cerebro.sh` y verificar con `cort_probe.py cerebro` (hoy: 210–320 MB libres, el
   modelo pide ~511 MB).
2. Historial persistente y resumen de sesión en `cort_state.json` (ahora el historial
   vive en memoria y se pierde al reiniciar).
3. Reglas locales corregidas: coincidencia por palabra completa y orden de prioridad,
   para que «Inspírame» no suelte estadísticas de RAM.
4. Motor de voz de salida elegido e instalado (espeak-ng, Piper local o Web Audio) con
   lectura larga sin cortes ni desbordes de memoria.
5. Micrófono en zona de pruebas, con el orbe marcando el estado de escucha.

**Salida:** conversación de 5 turnos con un modelo real nombrado en pantalla, y CORT
diciendo en voz alta una respuesta de más de 300 caracteres sin congelar el equipo.

---

## F4 — Vida diaria (17 comandos del censo)

1. Temporizadores y alarmas de verdad en el puente: cuenta atrás al HUD y aviso hablado.
2. Notas y recordatorios persistentes («anota que…», «muéstrame mis notas»).
3. Lista de tareas y de compras persistentes, sustituyendo los 3 artículos de ejemplo
   que trae la plantilla.
4. Modo «léeme la selección»: leer en voz alta el texto seleccionado (su estudio del
   suelo pelviano en el libro, sin capturar pantalla).
5. Escenas «modo estudio» y «modo madrugada»: silencian avisos, cambian color del orbe
   y ajustan el volumen.

**Salida:** los 17 comandos de esta familia responden con datos que **sobreviven a un
reinicio** del puente.

---

## F5 — Acciones sobre el equipo (35 comandos del censo)

1. Capa `acciones.py` con lista blanca cerrada de verbos Linux: abrir carpeta, abrir
   app, volumen, brillo, captura de pantalla, apagar el salvapantallas.
2. Zona de pruebas con `CORT_HOME` separado del resto del disco y registro de cada
   comando ejecutado con su hora.
3. Confirmación en pantalla antes de cualquier acción que escriba o cierre algo.
4. Prohibiciones duras escritas en el código: apagar, formatear, matar procesos, borrar
   fuera de su home. El antivirus ya funciona así (informa, no borra).
5. Prueba real medida en la Canaima: abrir el gestor de archivos, bajar el volumen,
   tomar una captura.

**Salida:** 10 acciones funcionando con su registro auditable y 0 ejecuciones fuera de
la lista blanca.

---

## F6 — Mapa propio y CORT OS de escenas

1. Quitar el `<iframe>` de ArcGIS y montar el mapa con el **Leaflet ya vendorizado**
   (`cort/vendor/leaflet/`): funciona sin internet si se añaden teselas locales.
2. Vuelo a ciudad, marcador y rutas desde el puente, usando la lat/lon que ya guarda
   `cort_state.json` (hoy el globo arranca en 0,0 frente a África).
3. Capa de clima sobre el mapa con los datos de open-meteo que el puente ya calcula.
4. **CORT OS** como lanzador propio de escenas y accesos directos dentro de la
   interfaz, no como sistema operativo: se queda el panel, se va la instalación.
5. Inventario final de dependencias externas (hoy quedan teselas de Google, Windy con
   clave y `hls.js` bajo demanda) y decisión de cada una.

**Salida:** globo y mapa funcionando sin conexión, centrados en tu posición real, con
vuelos pedidos por voz.

---

## F7 — Teléfono: app de asistente y puente con la Canaima

1. Elegir linaje y montar su proyecto fuente: `2.11.0-nucleo` (47,5 MB, con Vosk
   español sin internet y su propia `assets/ui`) o `bolsillo` (1 MB, fuente en
   `Sandra2244/CORT-nuevo` con `apps/bolsillo/compilar.sh`).
2. Añadir el `VoiceInteractionService` con su `xml/pre-services` para que el A16 te la
   liste en **Ajustes › Aplicación de asistente** (ahora sólo aparece Google).
3. Lectura en voz alta de lo que hay en pantalla y dictado: lo que uses para estudiar.
4. Conexión por red local al puente de la Canaima con token pareado y QR **generado en
   local** (fuera `api.qrserver.com`).
5. Compilación por GitHub Actions con el método que ya funciona: `aapt2` + `d8` +
   `zipalign 4` + `apksigner` v2/v3 con `CORT_APK_KEYSTORE_B64`, y prueba instalada en
   el teléfono sin avisos de Play Protect.

**Salida:** APK instalada, seleccionada como asistente del teléfono y respondiendo con
el puente de la Canaima por Wi-Fi.

---

## F8 — Presentación y publicación

1. Rótulos definitivos: cero «JARVIS» a la vista y cero francés (hoy quedan 3 cadenas
   visibles, medido con el propio detector de la página).
2. README en español con arquitectura y su instructivo de instalación paso a paso.
3. `LICENSE` MIT a tu nombre y nota clara: *interfaz inspirada en el proyecto JARVIS
   web de TechEnClair (referencia visual, con capturas; algunas cosas se replicaron
   como base); puente Python, rediseño, traducción y funciones, propios*.
4. Limpieza del repo antes de publicar: sin `.orig`, sin espejo descargado, sin estado
   personal, con `PROCEDENCIA.md` y `LEEME.md` revisados.
5. Empujar a `Sandra2244/CORT`, etiqueta de versión y release con el APK.

**Salida:** repo público que se defiende solo: se entiende qué es tuyo, qué es
referencia y cómo se instala.

---

## Lo que no entra en el plan (y por qué)

* Servicios con clave de pago y tarjeta (Spotify, YouTube API, Gmail, ElevenLabs): no
  tienes Visa/Mastercard y cada uno abre una llave que hay que mantener.
* Instalar Jarvis OS como sistema operativo: pide el disco entero y borraría MX Linux.
* Visión por cámara y gestos al mando del ratón: media resolución de la Canaima y
  MediaPipe; se decide después de tener F1 a F4 cerrados.
* Compilar el APK en la Canaima: no hay SDK y el Actions ya lo hace mejor.
