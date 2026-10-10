# packaging/ — cómo se construyen los instaladores de una Release

Página de Release: https://github.com/Sandra2244/CORT/releases

## Lo que ya hace el pipeline solo (no hay que construir nada)

Al empujar una etiqueta `v*` (o `main`), `.github/workflows/publicar-release.yml` abre la página
de Release con la nota de `docs/RELEASE-NOTES.md` que corresponde a esa etiqueta
(`scripts/nota_release.py`). Y **GitHub adjunta solo** el código fuente en `.zip` y `.tar.gz` de
la etiqueta: eso es el «source.zip profesional», sin tocar nada.

## Setup de Windows — `cort-setup.exe`

Se construye **en un PC Windows** (aquí no: Inno Setup no corre en Linux, y está medido por qué
en `docs/PLATFORM.md`):

1. Bajar el árbol de la etiqueta: `https://github.com/Sandra2244/CORT/archive/refs/tags/v0.11.0.zip`,
   descomprimirlo donde se vaya a compilar.
2. Instalar [Inno Setup 6](https://jrsoftware.org/isinfo.php) (trae `ISCC.exe`).
3. Compilar: `"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\cort.iss`
   → sale `packaging\Output\cort-setup-0.11.0.exe`.
4. Adjuntarlo a la Release ya abierta:
   `gh release upload v0.11.0 packaging\Output\cort-setup-0.11.0.exe`

Qué hace el instalador y qué **no**: coloca el árbol (core + `dist` de la interfaz + scripts +
docs), crea el acceso doble-clic que llame a `cort.bat` —el mismo lanzador de siempre, no un
inventado aquí— y ofrece abrir un `cmd` en la carpeta para el paso 3 de `INSTALAR-WINDOWS.txt`
(crear el venv, `pip install`, `npm run build` la primera vez). **No empaqueta Python, Node ni
Ollama**: son instaladores oficiales, y sustituirlos sin medirlos sería justo lo que la regla 13
prohíbe. **No toca datos**: recuerdos, `.env` y modelos de la usuaria no entran en la lista de
archivos, y al desinstalar se avisa en pantalla de que no se borran.

**Estado honesto: `cort.iss` está escrito y revisado, sin compilar** — nadie lo ha pasado por
ISCC todavía. La primera vez que se compile, cualquier corrección vuelve a este repo; la Release
se actualiza con `gh release upload --clobber`.

## APK de Android

Tampoco se construye aquí: Gradle pide JDK completo (hay runtime, no `javac` —medido—), Android
SDK de varios GB y un pico de más de 1 GiB de RAM, y esta máquina se congela antes de terminar
(`docs/PLATFORM.md`). Las dos vías reales, en orden de honestidad:

1. **PWA (la vía de hoy, ya servida)**: con `cort.py --lan` y un HTTPS local, el Samsung A16
   puede «Añadir a pantalla de inicio» el manifiesto que ya existe. Es la interfaz completa; no
   es un `.apk`, y el README lo dice con esas letras.
2. **APK de verdad (necesita otra máquina o CI)**: empaquetar la misma web con Capacitor desde un
   PC con Android SDK — `npx cap add android` + `./gradlew assembleDebug` — y adjuntar el
   `app-debug.apk` con `gh release upload v0.11.0 <apk>`. **Decisión sin tomar** (está escrito en
   PLATFORM.md desde el principio): el APK o habla con el core de la laptop por la LAN (con llave,
   y cualquiera de la WiFi ve el puerto), o lleva su propio core en el teléfono, que hoy no cabe.

## Regla de oro para cualquier Release

Los instaladores son **artefactos nuevos junto a la etiqueta**: nunca reescriben historial, y los
datos personales de quien usa CORT (`data/`, `.env`, recuerdos, atuendos) viven fuera del árbol
que empaqueta `cort.iss`. Actualizar CORT no borra la memoria de la IA ni la tuya.
