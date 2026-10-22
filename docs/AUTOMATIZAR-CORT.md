# Automatizar CORT — «cuando X, entonces Y»

Ronda **2.4.0**. Es lo que ella pidió con «la automatización como es JARVIS o
Cortana»: reglas que se cumplen solas, apuntadas por ella, sin programar nada.

Se puede hacer de dos maneras, y las dos llevan al mismo sitio (la hoja
**Equipo · 8 · Automatiza**): hablando o escribiendo en la pantalla **Código**.

---

## 1 · Qué es una regla

Una regla tiene dos mitades:

```
cuando  ⟨una cosa pase⟩        →   haz  ⟨una o varias cosas⟩
```

La parte de «cuando» (el **disparador**) es una señal que CORT ya recibe:

| disparador | qué tiene que pasar |
|---|---|
| **cuando yo diga o escriba** | cualquier palabra suya, con o sin tildes, dentro de una frase más larga |
| **cuando llegue un aviso** | un aviso nuevo de una app concreta (`whatsapp`, `gmail`…) y/o con una palabra dentro |
| **cuando pulse el auricular** | el doble toque del auricular (`suena` / `deja de sonar`) |
| **cuando cambie la batería** | `conecta`, `desconecta` o `baje de` un porcentaje |
| **a una hora del día** | `07:30`, una sola vez cada día |

La parte de «haz» (la **acción**) usa las manos que CORT ya tenía:

`que CORT diga` · `poner el volumen` · `la linterna` · `abrir una app` ·
`la música` (parar / seguir / pausa / siguiente) · `que piense una cosa` (su
cerebro, de casa o de la nube) · `apuntar un recuerdo` · `poner una alarma`.

No hay ninguna función nueva del puente detrás de esto: la automatización es la
capa que **junta** lo que ya existía.

---

## 2 · Crear una regla con la voz

Una frase, con la palabra `automatiza` delante:

```
automatiza cuando diga modo noche haz callar la música
automatiza cuando llegue un aviso de whatsapp haz que CORT diga «mensaje de Juan»
automatiza cuando desconecte el cargador haz poner el volumen al máximo
automatiza a las 7:30 haz que piense «¿qué tengo hoy?»
```

Y para ver las que hay:

```
mis automatizaciones
```

Se pueden decir desde el micrófono o escribir en la pantalla **Código** (la
terminal ampliada de esta ronda). La hoja se abre sola para que vea lo que quedó
apuntado.

---

## 3 · Crearla con los botones

Hoja **Equipo · 8 · Automatiza**: un nombre, el disparador (lo que se ofrece en el
desplegable cambia los campos: si el disparador tiene estados, sale una lista en vez
de un campo de texto), la acción y su dato. `＋ apuntar la regla`.

Cada regla pintada trae tres botones:

- `●` / `○` — encenderla o apagarla (las apagadas se ven en gris, para que no haya
  duda).
- `▶` — **probarla ahora**. Ejecuta sus acciones de una vez: es la forma de saber si
  ese APK tiene la mano que hace falta sin esperar a que suene el aviso de verdad.
- `✕` — borrarla.

`las tres de muestra` deja apuntadas:

| regla | cuando | haz |
|---|---|---|
| modo noche | diga «modo noche» | callar el volumen + apagar la linterna + decírtelo |
| el aviso de la mañana (apagada) | 07:30 | pensar «¿qué tengo hoy?» |
| cuando desconecte el cargador (apagada) | quite el cable | decírtelo |

---

## 4 · Tres cosas que conviene saber

**Las suyas mandan.** Las reglas se consultan **antes** que la boca de CORT. Si ella
apuntó que «modo noche» hace tres cosas, eso es lo que pasa, no lo que la cara
entiende siempre por esas palabras.

**Un minuto de freno.** Una regla que acaba de sonar no vuelve a sonar durante un
minuto, y se avisa en la consola («acaba de sonar: la freno un minuto para que no se
repita»). Sin esto, una regla de avisos con la palabra «hola» sonaría veinte veces en
un minuto. Las de hora no se repiten en todo el día.

**Mientras CORT esté en pantalla.** La cara es una página web dentro del teléfono;
una página cerrada no escucha. Lo que sí sigue funcionando con la pantalla apagada
es lo que hace Java solo: leer tus avisos en voz alta, el reproductor con su
notificación y el oído del auricular. Esto no es una disculpa, es el diseño:
convertir las reglas en algo de segundo plano pediría un servicio propio en Java, y
esa pieza va en una ronda aparte, no a medias.

---

## 5 · Dónde se mira que esto funcione

- `scripts/prueba-automatiza.mjs` — 45 comprobaciones del motor con node, sin
  teléfono: los acentos, el freno, «una vez al día», la señal del aviso, la batería,
  la regla apagada, el almacén roto y lo que pasa cuando una acción no existe.
- `scripts/prueba-costura.py`, sector `[11]` — que las 8 acciones del desplegable
  tienen su `case` en las manos, que las 5 señales existen de verdad, que `.Avisos`
  manda el aviso, que el bloque está montado y que el CSS no falta.
- Las dos cosas corren en GitHub Actions **antes** de firmar el APK.
