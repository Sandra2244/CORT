# Abrir CORT — el auricular, el gesto del asistente, la cortina y el icono

Ronda **2.4.1**. Es lo que ella pidió con «que hasta lo detecte como aplicación de
Asistente para colocarla como predeterminada en vez de Google y funcione con los
audífonos, con los mismos botones, sensores de doble toque, el hablar por audífonos,
CORT ejecute las acciones… inicie de otras formas».

Todo lo de abajo es **el mismo APK** (`CORT-IA-2.6.0.apk`): no hay que instalar nada
aparte ni dar ningún permiso nuevo. Lo que cambia es cuántas puertas tiene CORT y
cómo se abren.

---

## 1 · Las seis puertas, y qué hace cada una

| cómo se abre | qué pasa | desde qué versión |
|---|---|---|
| el **icono** del cajón | la cara, en el Orbe, sin micro | siempre |
| **mantener el icono** (atajos) | tres opciones: `Escucha` (cara + micro abierto), `Equipo`, `Charla` | 2.4.1 |
| el **baldosín** de la cortina rápida: «CORT escucha» | la cara + micro abierto, sin ser la app de asistencia | 2.4.1 |
| el **gesto del asistente** (mantener el botón de inicio, deslizar desde la esquina inferior, o el botón lateral según el teléfono) | la cara + micro abierto | 2.4.1 (antes sólo la sesión de voz) |
| **un toque** en el auricular | la música: play/pausa/siguiente. **No** es de CORT | siempre |
| **dos toques** en el auricular, en menos de medio segundo | la cara + micro abierto | 2.4.0 con la cara delante · **2.4.1 también con la cara cerrada** |
| **mantener pulsado** el botón del auricular (~500 ms o más) | la cara + micro abierto | 2.4.1, y hace falta ser la app de asistencia |

No hay ninguna de estas vías que abra un micrófono permanente: en ninguna. El micro
se abre cuando CORT se pone a escuchar y se cierra al terminar la frase, que es lo
que hace que el teléfono no se trabe (lo que la dueña notó en la 2.0).

---

## 2 · Poner CORT como «aplicación de asistencia»

Es el interruptor que decide a quién le llegan el gesto y el botón mantenido. La
manera corta está dentro de CORT:

1. Abre CORT y pulsa el botón **`CORT · PC`** (abajo a la izquierda, semi-transparente).
2. Elige **«Poner CORT como asistente (…)**». Lo que salga entre paréntesis es lo que
   CORT ha podido leer en el sistema: `ya elegido`, `pendiente` o `bloqueado por el
   fabricante`.
3. Android abre su cuadro de rol (`RoleManager`, API 29+) con la lista de apps de
   asistencia. Marca **CORT** y acepta el aviso («Google ahora no podrá responderte»).

La manera larga, si el cuadro no se abre: **Ajustes ▸ Sistema ▸ Aplicación de
asistencia predeterminada** (en Samsung: *Ajustes ▸ Aplicaciones ▸ Aplicaciones
predeterminadas ▸ Asistente de voz*; en Xiaomi: *Ajustes ▸ Aplicaciones ▸
Administrar aplicaciones ▸ Aplicación de asistencia*).

### Qué hay que saber antes de hacerlo, dicho sin adornos

* **El «OK Google» con la pantalla apagada se pierde.** Esa palabra la dice el
  servidor de Google, no viaja dentro de este APK, y Android sólo permite un
  asistente a la vez. Si la quieres de vuelta, se quita CORT del mismo cuadro.
* **La palabra «Oye CORT» no sustituye al «OK Google» con la pantalla apagada.** El
  oído propio de 2.3.0 (Vosk, dentro del APK, sin internet) funciona con la cara
  **abierta**: en segundo plano Android congela la app, y la única forma legal de
  tener un micro oyendo siempre es un servicio en primer plano con micrófono, que es
  lo que frozeó el teléfono una vez y no vuelve.
* **Algunos fabricantes no listan a nadie.** Huawei, Honor y capas viejas de Xiaomi
  traen el cuadro cerrado o se lo reservan a su asistente. Ahí el gesto y el botón
  mantenido no se pueden mover: usa el **baldosín** o el **atajo del icono**, que no
  necesitan ese permiso de nadie. `estadoAsistente()` lo dice con esas palabras, en
  vez de fingir que funcionará.
* **El teléfono puede preguntar dos veces** (una por el rol y otra por «permitir
  acceso a datos») y some capa de fabricante abre además su propio cuadro de
  «Confianza». Son diálogos del sistema, no de CORT, y los escribe Android en el
  idioma del teléfono.

---

## 3 · Los auriculares

### La voz de CORT sí sale por el auricular

El `TextToSpeech` del sistema habla por el **stream de multimedia**, y esto está
medido, no supuesto: la función `musicPlaying()` del puente tiene un detalle honesto
documentado — `AudioManager.isMusicActive()` también responde `true` mientras CORT
habla —, por eso la cara ignora el freno un segundo y medio después de cada frase.
Lo que significa para ti: cuando llevas los audífonos puestos, **CORT te responde
por los audífonos**, igual que la música.

### Los botones

Conectas los auriculares y el teléfono ve una «sesión de medios». Hay dos sesiones
en CORT y una sola a la vez está en primer plano:

* **con la cara delante**: manda la sesión `cort-auriculares` de `MainActivity`.
* **con la cara cerrada y CORT poniendo música**: manda la sesión `CORT` de
  `.Reproductor`, que es la que suena.
* **con la cara cerrada y sonando otra app** (Spotify, YouTube): la sesión activa es
  la de esa app y su doble toque es suyo. CORT no se lo quita a propósito:
  `setActive(false)` en `onPause()` es justamente «la música vuelve a su dono».

Y ahora lo que faltaba: desde el **2.4.1** el doble toque de la sesión del
reproductor **despierta a CORT**. Los dos primeros toques siguen siendo de la música
(el primero devuelve `false`, o sea «no lo consumo»), y el segundo dentro de 500 ms:

1. **pausa la canción** — el oído y el reconocedor del sistema oyen por el mismo
   micrófono que el auricular reporta; con la música sonando, CORT se transcribe a
   sí misma los tambores;
2. abre la cara con la orden de escuchar;
3. pinta la insignia del micro (`{type:"auricular",escuchando:true}`), porque no
   estás mirando la pantalla y algo te tiene que decir que ya te está oyendo.

Di la orden y CORT la ejecuta: es la misma boca de siempre — `Oido.kt` sin nube, o
el reconocedor si el oído no está listo — y las mismas manos (`Acciones.java`:
volumen, linterna, alarma, abrir apps, música, pensar, recordar).

**En modo juego el doble toque no es de CORT**: `soltarSesion()` cede la sesión y,
por si una capa de fabricante la trae de vuelta, `CortNative.enJuego()` corta el
toque antes de abrir el micro.

### El botón mantenido

Mantener pulsado el botón del auricular manda `ACTION_VOICE_COMMAND`. Desde el
2.4.1 CORT la declara, así que el sistema la trae a la cara y abre el micro. Esto
**sí** depende de que CORT sea la app de asistencia: si no lo es, se lo queda Google.

---

## 4 · El baldosín de la cortina rápida

Sirve para lo que más se repite: «quiero decirle algo a CORT ya, sin buscar el
icono», y funciona **aunque tu fabricante no deje cambiar el asistente**.

1. Baja la cortina dos veces (o desliza desde arriba dos veces).
2. **Editar** / el lápiz.
3. Busca en la bandeja de abajo **`CORT escucha`** y arrástralo a la zona de
   ajustes rápidos. Acepta.
4. Pulsa una vez: la cara aparece y ya está escuchando.

Está escrito en `apps/apk/src/com/cort/ia/Panel.java` (un `TileService`, Android 7+).
Dos decisiones honestas:

* El **icono** es el de «hablar» del sistema, no el anillo, porque Android tiñe los
  baldosines y un PNG con alpha sale como una mancha negra.
* El baldosín se queda **gris**, nunca azul encendido: el micro se cierra solo al
  terminar la frase y el baldosín no se entera desde su proceso. Un azul que no se
  apaga es mentira.

Con la pantalla bloqueada, Android no deja lanzar actividades desde un baldosín; en
Android 11+ CORT encarga el viaje para después del desbloqueo (`unlockAndRun`), así
que lo que haces es desbloquear y la cara aparece escuchando.

---

## 5 · Los atajos del icono

Mantén pulsado el icono de CORT en el cajón (o en la pantalla de bloqueo, si el
lanzador lo permite). Salen tres:

| atajo | qué hace |
|---|---|
| **Escucha** | abre la cara y pone el micro (`com.cort.ia.ESCUCHAR`) |
| **Equipo** | abre la cara y salta a la hoja **Equipo** (`com.cort.ia.EQUIPO`) |
| **Charla** | abre la cara y salta a la hoja **Charla** (`com.cort.ia.CHARLA`) |

Están en `apps/apk/res/xml/atajos.xml`, y las letras en `res/values/etiquetas.xml`.
Si a ti no te salen, son las dos razones de siempre: un lanzador que no soporta
atajos (algunos de Xiaomi/Samsung los ocultan) o que el teléfono aún tiene el APK
2.4.0. Se puede comprobar sin mirar la pantalla, desde un portátil con `adb`:

```bash
adb shell am start -a com.cort.ia.EQUIPO     # abre la cara en la hoja Equipo
```

Que ese comando funcione prueba que la otra mitad del viaje —Java traduce la acción,
el puente emite `{"type":"atajo","hoja":"equipo"}` y `pantallas.js` hace el
`ir('equipo')`— está cosida; lo demás es si tu lanzador pinta o no el menú.

---

## 6 · Qué se comprueba desde el repo y qué no

`scripts/prueba-costura.py`, sector **[12]**, comprueba sin teléfono las cinco dudas
que se rompen en silencio: que el manifiesto declare las acciones y el permiso del
baldosín; que `res/xml/atajos.xml` exista, apunte a `MainActivity` y use `@string/…`
(con la etiqueta escrita como literal, Android **no pinta el atajo**); que las hojas
que nombra Java (`equipo`, `charla`) existan de verdad en `pantallas.js`; que el
evento `atajo` lo emita Java y lo escuche la cara; y que `Reproductor` tenga su
`onMediaButtonEvent` con pausa incluida.

Lo que **no** se puede comprobar desde el repo: si tu fabricante lista a CORT en el
cuadro del asistente, si su lanzador pinta los atajos, y a qué app le da el botón del
auricular cuando suena otra. Eso son tres decisiones del teléfono, y las tres tienen
su plan B aquí arriba (baldosín y atajo de `Escucha`).
> **Si instalaste el envase `nucleo`** (`CORT-IA-2.6.0-nucleo.apk`, el que se prueba
> primero cuando Play Protect bloquea el completo): de las seis vías de esta guía
> quedan cuatro —la notificación del reproductor con su doble toque, los tres atajos
> del icono, el arranque normal y las acciones `com.cort.ia.{ESCUCHAR,EQUIPO,CHARLA}`—
> y no existen el gesto del asistente ni el baldosín de la cortina, porque ese envase
> no declara `BIND_VOICE_INTERACTION` ni `BIND_QUICK_SETTINGS_TILE`. La cara no se hace
> la loca: la hoja Equipo canta `envase nucleo` y si pides «pon CORT como asistente»
> contesta que ese envase no lo trae. Está explicado en
> [`docs/BLOQUEO-PLAY-PROTECT.md`](BLOQUEO-PLAY-PROTECT.md).

