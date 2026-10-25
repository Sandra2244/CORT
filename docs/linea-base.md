# Línea base de CORT — paso 0.3 de la Fase 0

**Medido:** 2026-10-25, de una tanda sola, en el portátil de la dueña.
**Rama:** `v0.2-demo`. Antes de la tanda el HEAD era `102eb39` (paso 0.2); durante el paso
se añadió `568acf3` (los comentarios del JDK) y esta tanda se repitió sobre él.
**APK publicado:** 2.11.0 / `versionCode` 21100 — **no cambia con este paso**: aquí no se
tocó nada que viaje dentro del APK.
**Paso de sólo medir y escribir:** no se arregló ningún rojo. Se documenta.

---

## 0. La máquina donde se midió (esto condiciona todas las cifras)

| dato | medido |
| --- | --- |
| núcleos | **2** (`nproc`) |
| memoria | 1.851 MB totales; **entre 312 y 363 MB disponibles** durante la tanda |
| sistema | Debian 13, bash 5, `python3 3.13.5`, `node v20.19.2` |
| Java | `openjdk 21.0.12.1` **sólo JRE** (`openjdk-21-jre` + `-jre-headless`); no hay `javac` como orden, **sí** el módulo `jdk.compiler@21.0.12.1` y `keytool` |
| qué más había abierto | Qoder (7 procesos, ~700 MB). **Sin Ollama y sin navegador de desarrollo al principio** |

Lo dice el propio sensor de CORT en la respuesta real de `/api/status` durante la tanda:
`"CPU 95 % · RAM 83 % (1.6 de 1.9 GB) · Disco 22 % usado."`. Con ese margen, **las medidas de
tiempo son de una máquina saturada**, y hay que leerlas como techo, no como suelo.

## 1. Las 12 suites que corren aquí: todas verdes

Corridas **en fila y a mano**, sin Ollama y sin navegador. `rc` es el código de salida real
de cada una (nada ocultado por una tubería).

| suite | rc | tiempo | comprobaciones |
| --- | --- | --- | --- |
| `prueba-costura.py` | 0 | 15 s | **314 `ok`**, 0 `NO` |
| `prueba-clima.py` | 0 | 4 s | 42 `ok` |
| `prueba-datos.py` | 0 | 2 s | 4 `ok` |
| `prueba-lectura.py` | 0 | 4 s | **0** — ver sección 4, fila 1 |
| `prueba-modelos.py` | 0 | 1 s | 53 `ok` |
| `prueba-organiza.py` | 0 | 1 s | 13 `ok` |
| `prueba-voz.py` | 0 | 2 s | 56 `ok` |
| `prueba-automatiza.mjs` | 0 | 4 s | 45 («motor de automatizaciones: 45 comprobaciones, todas en verde») |
| `prueba-colores.mjs` | 0 | 1 s | 28 |
| `prueba-mandos.mjs` | 0 | 1 s | 63 |
| `prueba-llave.sh` | 0 | 12 s | 7 `ok` |
| `prueba-mente.sh` | 0 | 60 s | 7 suites Java sobre las **336 frases** de la tabla: 43 + 45 + 58 + 18 + 21 = **185** con cifra, más `TABLA OK` y `DICCIONARIO OK` sin cifra |

**Suma con número: 810 comprobaciones en verde** (482 de python + 136 de node + 7 de llave +
185 de mente). **Tiempo de la tanda de pruebas: 108 s.**

Dos cosas de esta tabla son noticia: `prueba-mente.sh` pasó **en casa**, sin `javac` en el
`PATH`, porque el JRE trae el módulo del compilador (se corrigió el comentario que decía lo
contrario en `568acf3`); y su duración real aquí es **60 s**, no los ~25 s que decía su
cabecera.

## 2. Los 8 talleres de mutación: 7 verdes, 1 rojo

Un taller no prueba el producto: prueba que **la prueba puede caerse**. Cada uno rompe algo a propósito y exige que la suite se ponga roja **nombrando** la comprobación que
faltaba.

| taller | rc | tiempo | mutaciones |
| --- | --- | --- | --- |
| `taller-f15.sh` | **1** | 120 s | 8: **6 caen, 2 no se aplican** (`???`) |
| `taller-f16.sh` | 0 | 307 s | 18, todas caen nombrando lo que faltaba |
| `taller-f17.sh` | 0 | 220 s | 19, todas caen |
| `taller-f18.sh` | 0 | 200 s | 15, todas caen |
| `taller-f23.sh` | 0 | 157 s | 12 caen, 0 aguantan |
| `taller-mandos.sh` | 0 | 79 s | 11 caen y el árbol limpio vuelve a dar verde |
| `taller-modelos.sh` | 0 | 17 s | 17 caen, 0 aguantan |
| `taller-ollama.sh` | 0 | **767 s** | 12 caen, 0 aguantan |

**112 mutaciones en total: 110 caen, 2 están muertas. Tiempo de la tanda de talleres:
1.867 s (31 min 7 s).** Tanda completa del paso: **≈33 minutos** de 2 núcleos.

El rojo es el F15 y su diagnóstico está en la sección 5.

## 3. Lo que NO se pudo medir aquí, dicho en vez de fingido

| qué | por qué no | dónde sí |
| --- | --- | --- |
| `prueba-oido.sh` (`PruebaOido.kt` con Vosk real) | **no es la red**: `kotlinc` y el modelo ya están en `~/.cache` (96 MB + 77 MB, medidos). Es la RAM: el script pide `KOTLIN_MEM=320m` (`prueba-oido.sh:36`, donde `MEM_KOTLINC="${KOTLIN_MEM:-320m}"`) y en la tanda quedaron **312 MB disponibles** con Qoder abierto. Lanzarlo era cambiar un rojo por un portátil congelado | Actions (`build.yml:385`), donde corre después de `motor.sh` con la máquina entera libre |
| La sonda de la cara (`ui/sonda-carita.html`, **213** comprobaciones publicadas en `docs/CEREBRO-MAESTRO.md:881`) | El navegador del entorno de trabajo **no llegó a montar la página**: dos intentos de navegación devolvieron `Browser operation timed out after 250ms` y luego `The selected in-app browser page is blank`, con 322 MB libres. El backend **sí** la servía correcta y rápidamente (`200`, 78.151 B en 0,22 s), así que el fallo es del navegador en esta máquina, no de la cara | En el navegador de la casa, con el portátil despejado: `bash scripts/run.sh` y abrir `/sonda-carita.html` |
| Fluidez con y sin música (fotogramas por segundo del orbe) | Depende de la medida anterior. Sin página montada no hay `requestAnimationFrame` que contar | Igual: navegador en casa, y la burbuja/reproductor reales solo en su teléfono |
| Compilar el APK en casa | Faltan `aapt2`, `d8`, `zipalign` y `apksigner` del SDK de Android; **no** falta Java (`compilar.sh:162` muere sin `ANDROID_HOME`) | Actions, y ya: es el diseño del proyecto |

## 4. Agujeros de prueba encontrados midiendo (no son bugs del producto)

1. **`prueba-lectura.py` no comprueba nada.** Son 63 líneas que `print()` y nada más: no hay
   un solo `assert`, ni un contador de fallos, ni un `sys.exit(1)` (buscado en el archivo;
   su salida de hoy son 31 líneas de texto y `rc=0`). **Su verde es decorativo**: si mañana
   `leer_texto` devuelve basura, esta suite seguirá dando 0. Las demás no pueden decir lo mismo.
2. **Ninguna de las 12 suites mide rendimiento.** No hay comprobación de fluidez ni de memoria
   en la cara; las cifras de «va fluida» del mega prompt (regla A3) hoy **no tienen prueba**.
3. **El pipeline corre 9 de las 21.** Medido sobre `build.yml`: invoca `prueba-costura`,
   `prueba-clima`, `prueba-modelos`, `prueba-mente`, `prueba-voz`, `prueba-oido`,
   `prueba-automatiza`, `prueba-colores` y `prueba-mandos`. **No corren en ningún lugar
   continuo** `prueba-datos`, `prueba-organiza`, `prueba-lectura`, `prueba-llave` **ni ninguno
   de los 8 talleres**. Las cifras de talleres que aparecen en las notas de la Release
   («taller F23 12/12», `build.yml:661`) se escribieron a partir de tandas manuales como esta,
   no de un job.
4. **Los talleres y `prueba-mente.sh` comparten `/tmp/cort-mente` sin bloqueo.** El script no
   usa `trap`: borra y recrea el directorio al arrancar (`rm -rf "$T"` en `prueba-mente.sh:65`,
   con `T=/tmp/cort-mente` en `:62`), así que si dos procesos se lanzan a la vez el segundo
   desmonta el trabajo del primero. Es la razón de correrlos de uno en uno (`mapa` §8) y por qué
   la tanda de este paso fue en fila.

## 5. El rojo del taller F15, con nombre y línea

Las dos mutaciones marcadas `???` **no son código que aguante**: son mutaciones cuyo texto a
romper ya no existe, así que nunca llegaron a romper nada. El `rc=1` del taller es correcto:
una mutación que no se aplica no prueba nada.

| mutación | qué busca (`scripts/taller-f15.sh`) | qué hay hoy en `scripts/prueba-mente.sh` |
| --- | --- | --- |
| «el ecualizador entra en la suite de papel» (`:107-110`) | `"$E"/Elige.java "$T/src/com/cort/ia/"` | línea 67: `cp "$E"/Cerebro.java … "$E"/Elige.java "$T/src/com/cort/ia/"` — `Elige.java` **ya no es el último** de los 7; es el sexto |
| «Prueba6 fuera del bucle» (`:158-161`) | `for suite in Prueba Prueba2 Prueba3 Prueba4 Prueba5 Prueba6; do` | línea 100: el bucle lista **siete** suites, hasta `Prueba7` |

Las dos apuntan al mismo archivo y al mismo motivo: `prueba-mente.sh` **creció** (con
`Despertar.java` y `Prueba7` en rondas posteriores a F15) y sus anclas se quedaron atrás. La
comprobación de la costura que ambas deberían hacer caer **sí existe y es correcta**
(`prueba-costura.py:4084`, sector `[30]`: «`Ecualizador.java` se copia a la prueba de papel…
ese verde sería de cartón»); simplemente hoy es inalcanzable desde el taller.

**Arreglo propuesto (2 líneas, `scripts/taller-f15.sh:108` y `:159`):** re-anclar la primera a
`"$E"/Despertar.java "$T/src/com/cort/ia/"` y la segunda a la lista de siete. **No lo hice en
este paso** porque es tocar un script, y aquí vinimos a medir. Es un paso aparte de un minuto.

## 6. Arranque y latencias del núcleo de casa (esto sí se pudo medir)

Backend levantado con el propio `scripts/run.sh` por dentro
(`CORT_SERVE_UI=1 .venv/bin/uvicorn --app-dir backend app.main:app --host 127.0.0.1 --port 8000`):

| qué | medido |
| --- | --- |
| tiempo hasta el **primer** `200` en `/api/status` (proceso frío) | **11,94 s** |
| `/api/status` en su primera llamada después de levantado | 0,47 s |
| `/api/status` / `/api/port` / `/api/history` / `/` templados | 0,47 / **0,012** / **0,010** / **0,019** s |
| activos grandes servidos por el propio backend | `js/pantallas.js` 148.530 B en 0,014 s; `js/diccionario.js` 41.864 B en 0,014 s |
| memoria del proceso del backend | **62 MB** de RSS tras 3 min de vida |

**Y una cosa que explica un queja suya de antes.** La respuesta real de `/api/status` de hoy
empezaba así: `…"version":"0.2.0"`. El valor viene de `backend/app/main.py:74`
(`VERSION = "0.2.0"`, usado en `:139` y `:163`), y la cara lo pinta tal cual:
`ui/js/hud.js:93-96` pone `'v' + s.version` sobre el `v0.2` que ya viene escrito en
`ui/index.html:42`. Con el APK 2.11.0 instalado, la cara **muestra `v0.2.0`** porque el
backend del PC va por su propia cuenta y nunca se la subió. Es la prueba medida de que el
paso **T2** (Fase 1) es un asunto de honestidad de estado, no estético.

## 7. Cómo repetir esta tanda (no existe un runner; esta es la tanda)

`scripts/` no tiene ningún guion que corra todo (deuda fila 4 del mapa), así que la línea base
se arma así. Nota: el `rc` de cada línea es el de la suite, no el de un `tail` que lo tape.

```bash
cd ~/Documentos/CORT
for s in prueba-costura.py prueba-clima.py prueba-datos.py prueba-lectura.py \
         prueba-modelos.py prueba-organiza.py prueba-voz.py; do
    python3 "scripts/$s" > "/tmp/base03/$s.log" 2>&1 || echo "ROJO $s"
done
for s in prueba-automatiza.mjs prueba-colores.mjs prueba-mandos.mjs; do
    node "scripts/$s" > "/tmp/base03/$s.log" 2>&1 || echo "ROJO $s"
done
for s in prueba-llave.sh prueba-mente.sh; do
    bash "scripts/$s" > "/tmp/base03/$s.log" 2>&1 || echo "ROJO $s"
done
# Los talleres, UNO EN FILA (comparten /tmp/cort-mente):
for s in taller-f15.sh taller-f16.sh taller-f17.sh taller-f18.sh taller-f23.sh \
         taller-mandos.sh taller-modelos.sh taller-ollama.sh; do
    bash "scripts/$s" > "/tmp/base03/$s.log" 2>&1 || echo "ROJO $s"
done
```

Lo que **falta** en esa tanda y no se puede correr aquí: `prueba-oido.sh` (RAM) y la sonda de
la cara (navegador). Un runner futuro debería poder saltarse lo que no cabe y decir por qué.

## 8. Publicado antes de hoy vs medido hoy

| cifra publicada | medido hoy | veredicto |
| --- | --- | --- |
| costura **314 `ok`** (`docs/CEREBRO-MAESTRO.md:880`) | 314 `ok`, `rc=0` | exacto |
| mente **7 suites / 336 frases** | `MENTE OK: las 7 suites pasan sobre las 336 frases` | exacto |
| taller F16 **18/18**, F23 **12/12** (`build.yml:707`, `:661`) | 18 caen y 12 caen | exacto |
| colores **28/28**, mandos **63/63**, automatiza **45/45** (`build.yml:746`) | 28, 63, 45 | exacto |
| sonda de la cara **213 comprobaciones sin un rojo** | **no medible aquí** (sección 3) | sin verificar |
| «taller F15 verde» implícito en las notas de rondas anteriores | **rc=1**, 2 mutaciones muertas | **falso hoy** |

## 9. Lo que este documento deja como deuda nueva

1. `prueba-lectura.py` sin ni una comprobación (sección 4, fila 1).
2. Ninguna prueba de fluidez ni de memoria, que son dos reglas de la A3 (sección 4, fila 2).
3. 12 de 21 comprobaciones existen sólo cuando alguien las acuerda a mano (sección 4, fila 3).
4. Dos mutaciones del F15 ancladas a texto que ya no existe (sección 5).
5. `VERSION = "0.2.0"` en el backend, sin relación con la versión del APK (sección 6).

Las cinco se quedan escritas; **ninguna se arregla en este paso**.

## 10. Puerta de la Fase 0

Con `docs/referencia-openjarvis.md` (0.1), `docs/mapa-del-repo.md` (0.2) y este
`docs/linea-base.md` (0.3) los tres documentos están entregados. **La puerta la cierra ella,
aprobándolos**; hasta entonces no se abre la Fase 1.

Si al aprobarla quiere que el rojo del F15 se arregle antes de nada, es un micro-paso de dos
líneas y su verificación (volver a correr el taller: ~2 min).
