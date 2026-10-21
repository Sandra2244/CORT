# Contrato del puente `window.CortNative` — ronda 2.1.0

Éste es el **único documento que fija los nombres** de la ronda «el APK completo».
Java por un lado y la cara (`ui/`) por el otro se escriben a la vez, y la costura
sólo cierra si los dos lados respetan lo de abajo. `scripts/prueba-costura.py` [9]
comprueba que sea así.

Reglas que aplican a TODOS los métodos nuevos:

* Son síncronos y **devuelven una cadena JSON** (`String` en Java).
* Toda respuesta tiene la forma `{"ok":true, …}` o `{"ok":false,"dice":"…"}`,
  escrita con comillas escapadas. **Nunca** se lanza una excepción a la cara: un
  fallo devuelve `ok:false` con lo que hay que decir en voz alta.
* Lo largo (red, cerebro) se resuelve **en otro hilo** y vuelve como evento
  `window.__cortNative.emit({type:…})`; el método contesta enseguida
  `{"ok":true,"pendiente":true}`. La cara no se queda congelada esperando.
* Una clave de API **jamás** sale del teléfono hacia la cara: se dice
  `"clavePuesta": true` y nada más.

## 1 · `accion(que, args)` — mandar sobre el aparato

`accion` recibe un JSON y hace la cosa. `{"que":"…","args":"…"}` donde `args` es
otro JSON (string dentro de string) o campos sueltos. Métodos:

| `que` | argumentos | respuesta extra |
|---|---|---|
| `volumen` | `como`: `sube` `baja` `max` `min` `callar` | `{"nivel":63}` |
| `linterna` | `como`: `on` `off` `alterna` | `{"linterna":true}` |
| `alarma` | `hora`: `"07:30"`, `nota`: `"el tren"` | `{"alarma":"07:30"}` |
| `temporizador` | `segundos`: `90`, `nota` | `{"segundos":90}` |
| `cronometro` | `como` (se admite pero no hace falta) | `{"muestra":"reloj"}` — Android **no deja** arrancar el cronómetro desde fuera: CORT abre la pantalla del reloj y lo dice en `dice`; con API < 29 abre Ajustes ▸ fecha y hora, porque `ACTION_SHOW_TIMERS` es de API 29 y el suelo del APK es 26 |
| `abrir` | `a`: `whatsapp` `whatsapp-business` `youtube` `maps` `spotify` `gmail` `calendario` `instagram` `facebook` `tiktok` `navegador` `musica` `archivos` `ajustes` `telefono` `reproductor-mv` — y los atajos de Ajustes: `wifi` `bluetooth` `teclado` `avisos` `reloj` `mensajes` | `{"abrio":"com.whatsapp"}` |
| `app` | `nombre`: `"Lark player"` | `{"abrio":"…","parecido":72}` |
| `lanzadores` | — | `{"apps":[{"nombre":"…","paquete":"…"}]}` |
| `buscar` | `texto`: `"recetas con pollo"` | `{"busca":"…"}` |
| `estado` | — | `{"volumen":63,"max":100,"mudo":false,"linterna":false,"superficie":true,"permisoSonido":true,"avisos":true,"musica":true,"atuendo":"Cortana","juego":false,"faltan":[…],"sinMiedo":true}` — `sinMiedo` es «no falta ningún permiso para lo que la cara ofrece» |

Si Android no deja hacerlo (permiso que falta, app que no está) → `ok:false` con
`dice` explicándolo **y** qué tocar en Ajustes.

## 2 · `ajusteVoz(que, args)` — hablar y escuchar con la voz que gusta

| `que` | argumentos | respuesta extra |
|---|---|---|
| `lista` | — | `{"voces":[{"nombre":"…","idioma":"es_ES","porDefecto":true}],"vozActual":"…","velocidad":1.0,"tono":1.0,"faltanVoces":true}` |
| `poner` | `nombre`, `velocidad` (0,5–2,0), `tono` (0,5–2,0) | |
| `predefinida` | `nombre`: `siri` `alexa` `cortana` `española` `mexicana` `neutra` | `{"usada":"…","porQue":"…"}` — elige la mejor voz instalada parecida al estilo y, si no está, lo dice |
| `descargar` | — | abre el instalador de datos de TTS de Android; `{"abre":"ajustes"}` |
| `probar` | `texto` | dice la muestra en voz alta |
| `estado` | — | `{"listo":true,"motor":"…","idioma":"es_ES"}` |

## 3 · `memoria(que, args)` — el teléfono también recuerda

SQLite propio (`cort.db`), y `sincronizar` lo cuadra con el portátil por la LAN.

| `que` | argumentos | respuesta extra |
|---|---|---|
| `guardar` | `texto`: `"la clave del wifi es …"` | `{"clave":"wifi"}` |
| `buscar` | `texto`: `"qué sabes de mi hermano"` | `{"encuentra":"…"}` |
| `lista` | — | `{"recuerdos":[{"contenido":"…","cuando":"ISO"}]}` (hasta 40) |
| `quien` | — | `{"dice":"… cómo se llama la dueña, qué sabe"}` |
| `olvidar` | `texto` (vacío = todo) | `{"borrados":3}` — borra sólo lo que CORT guardó, nunca archivos |
| `sincronizar` | — | `{"pendiente":true}` → luego `{type:"memoria", ok, subidos, bajados}` |
| `estado` | — | `{"hechos":12,"conPortatil":true,"direccion":"http://192.168.1.30:8000"}` |

## 4 · `mente(que, args)` — pensar sin el portátil

| `que` | argumentos | respuesta extra |
|---|---|---|
| `estado` | — | `{"proveedor":"groq","base":"https://…","modelo":"…","clavePuesta":true,"conRed":true,"motores":["groq","openai","deepseek","mistral","qwen","ollama","anthropic"]}` — `ollama` es el motor local (`http://127.0.0.1:11434/v1`), y no lleva clave |
| `ajustar` | `proveedor`, `base`, `modelo`, `clave` (`clave:""` = no tocar) | lo mismo que `estado` |
| `preguntar` | `texto`, `eco` (primeros 40 caracteres) | `{"pendiente":true}` → evento `{type:"mente", ok, responde, de:"nube\|local", eco}`; si `de:"local"` y la frase era una orden del aparato, trae además `accion` y `param` |
| `probar` | — | `{"pendiente":true}` → evento igual, con `responde` corto |

`Mente` **reconoce** la orden pero no la ejecuta: la hace `Acciones` cuando la cara
le devuelve `accion`/`param`. Sin ese reenvío, «sube el volumen» sin portátil se
quedaba en un «vale» vacío.

## 5 · `atuendo(que, args)` — la cara cambia de traje

| `que` | argumentos | respuesta extra |
|---|---|---|
| `lista` | — | `{"atuendos":[{"nombre":"Cortana","primario":"#59d9ff","secundario":"#0a3d62"}],"puesto":"Cortana"}` |
| `poner` | `nombre` | `{"css":"--primario:#…;--secundario:#…"}` — la cara pinta esas variables |

## 6 · `burbuja(boolean)` — CORT flotando sin sacarte de nada

`CortNative.burbuja(true)` muestra un punto de 44 dp con `SYSTEM_ALERT_WINDOW`
(sólo si la dueña dio «aparecer encima de otras apps»; el botón de la hoja de
Atuendos lleva directo a esa pantalla de Ajustes); `false` lo quita.
En **modo juego nunca aparece**, ni aunque se le pida: devuelve
`{"ok":false,"dice":"estoy en modo juego: no me meto encima de tu partida"}`. Y al
poner el modo juego, la burbuja que estuviera puesta se quita sola. El toque en la
burbuja abre CORT y empieza a escuchar.

Es el **único** método del contrato que no lleva JSON dentro: recibe el booleano a
pelo (`llama('burbuja', !!on)`). Ojo con la clave de la respuesta: `Flotante` contesta
`{"ok":true,"burbuja":true|false,…}`, **no** `puesta` —leer `puesta` hacía que apagar
la burbuja se anunciara como «burbuja puesta»—. Y cuando falta el interruptor de
Android, la cara no se queda en el «no puedo»: llama a `requestPermission('burbuja')`,
que en `MainActivity.pidePermiso` abre la pantalla de «aparecer encima de otras apps».

## 6b · `bgStatus()` / `setBackground(on)` — el panel de segundo plano

`ui/js/hud.js` (07 · Perfil ▸ Segundo plano) pregunta siete claves y Java tiene que
medir las siete; antes devolvía sólo `bg` y `pc` y el panel estaba mudo (el
interruptor no se iluminaba, los permisos salían siempre sin marcar y apagarlo era
imposible). Lo que hay ahora:

| clave | de dónde sale |
|---|---|
| `enabled` | la preferencia `bg` (lo que la dueña pidió) |
| `running` | `MainActivity.avisoDeFondoPuesto()`: si el aviso fijo está puesto **ahora** |
| `mic` / `notif` | `RECORD_AUDIO` y los avisos de Android (`POST_NOTIFICATIONS`, que en 13+ es lo que deja publicar el aviso) |
| `overlay` | `Settings.canDrawOverlays` (la burbuja) |
| `battery` | `PowerManager.isIgnoringBatteryOptimizations` sobre su propio paquete |
| `maker` | `Build.MANUFACTURER` + `Build.BRAND`, para el aviso de los fabricantes que cierran procesos |
| `dice` | la frase honesta: con el aviso puesto siguen la música y el **doble toque del auricular**; el micrófono se queda cerrado y «Oye CORT» con la app cerrada **no** funciona |

`setBackground(true)` no abre el micrófono a escondidas: guarda la preferencia y, si
la cara ya se fue a segundo plano, pone o quita el aviso (`MainActivity.alAvisoDeFondo
LeGustaCambiar`). Sus tres botones «Dar» tienen a dónde ir: `overlay` abre la pantalla
de aparecer encima, `battery` la de excepciones de batería, y `autostart` los ajustes
de la app con la fila indicada en un aviso. Lo comprueba el sector [9] de
`scripts/prueba-costura.py` en las dos direcciones.


## 7 · `agenda(que, args)` — tus citas y lo que llegó al correo

`Agenda.java` lee el calendario del teléfono con `CalendarContract.Instances` y
**sólo** con `READ_CALENDAR`: nunca escribe. `apunta` abre el formulario del
calendario del sistema ya relleno, y el dedo de la dueña es el que guarda.

| `que` | argumentos | respuesta extra |
|---|---|---|
| `hoy` | — | `{"eventos":[{"titulo":"…","cuando":"09:30","dia":"21/10","empieza":millis,"termina":millis}],"total":2,"vacias":false,"dice":"Tienes 2 cosas hoy."}` |
| `proximos` | `dias` (1–60, por defecto 7) | lo mismo, con el plazo en `dice` |
| `estado` | — | `{"ok":true,"permiso":"calendario","avisosEscuchando":true}` |
| `abrir` | — | abre el calendario del sistema; `{"abre":"calendario"}` |
| `correo` | — | `{"gmail":3,"abre":true,"escuchando":true,"dice":"Tienes 3 avisos de Gmail."}` — cuenta lo que `Avisos` oyó del paquete de Gmail y abre la app; sin el interruptor de notificaciones lo dice en `dice` en vez de contar ceros |
| `apunta` | `titulo`, `hora` (milisegundos desde el epoch; `0` = sin hora) | abre `ACTION_INSERT` con la cita escrita; `{"abre":"calendario","dice":"Te lo abro listo para guardar."}` |

Sin permiso de calendario, `hoy`/`proximos` devuelven `ok:false` con
`"permiso":"calendario"` y **el puente lo pide en ese momento** —la dueña lo dio
justo cuando lo quería dar—. CORT no inventa citas: si no puede leer, lo dice.

## 8 · `comparte(ruta)` — «envíame ese archivo»

`CortNative.comparte("…")` acepta las dos formas que la cara tiene de nombrar un
archivo: el camino del disco (`/storage/emulated/0/Download/informe.pdf`, que sale
por `ArchivosProvider` → `content://com.cort.ia.files/…`) y el URI del índice de
Android (`content://media/external/audio/media/42`), que es lo único que sabe la
pantalla de Música. Sale por `ACTION_SEND` con `FLAG_GRANT_READ_URI_PERMISSION` y
Android enseña su cuadro de apps: la dueña elige WhatsApp, correo o Drive. Nunca
`file://`, que en Android 7+ corta el envío con `FileUriExposedException`.

Respuesta: `{"ok":true,"envia":"canción.mp3"}`, o `ok:false` con `dice` explicando
que el archivo no existe, que está fuera de las carpetas que Android deja compartir,
o que ninguna app de ese teléfono puede recibirlo.

## 9 · los eventos que vuelven

Además de los de siempre (`stt-*`, `tts-*`, `perm`, `music`), la ronda 2.1 empuja
cuatro a `window.__cortNative.emit({...})`:

| `type` | cuándo | payload |
|---|---|---|
| `mente` | termina una pregunta al cerebro de la nube (hilo aparte) | `{ok,responde,de:"nube\|local",eco}`; si `de` es `local` puede traer además `{accion,param}`, **y la cara tiene que reenviarlos a `accion()`** (`Mente` nombra la cosa, `Acciones` la hace) |
| `memoria` | termina una sincronía con el portátil | `{ok,subidos,bajados,dice}` |
| `auricular` | el **doble toque del auricular** abre el micro, y cuando se cierra | `{escuchando:true\|false}` |

`accion` **no** es un evento: es síncrono (`envia('accion', …)` trae la respuesta en
el mismo viaje), y no hay nada largo que Java haga por su cuenta en esta ronda. La
cara tiene una rama `ev.type === 'accion'` preparada para el día que lo haya; hoy
nadie la manda, y `scripts/prueba-costura.py` [9] lo comprueba para que la tabla de
eventos no mienta.

`auricular` es el que apaga la insignia: si Java abriera el micro y no lo dijera, la
cara quedaría pintando «escuchando» para siempre. Por eso los siete sitios que
cierran el oído pasan todos por la misma función (`oidoCerrado()`), y `mente`
`conTipo(json, "mente")` —el `type` se lo añade el puente al engancharse, porque la
clase devuelve la respuesta sin él—, mientras que `memoria` y los avisos llevan el
`type` ya escrito dentro de su propio JSON.

## Cómo lo llama la cara

Igual que todo lo que ya existe: `puede('accion')` antes de ofrecer el botón, y
`llama('accion', {que:'linterna', como:'alterna'})` para llamar, que devuelve
`null` si el método no está (cara vieja en APK nuevo, o APK viejo en cara nueva) y
entonces la cara manda un mensaje honesto en vez de reventar con un `TypeError`.
