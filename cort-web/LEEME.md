# CORT — cómo arrancarlo y qué hace de verdad

Asistente local en la laptop/Canaima. Nada sale del equipo salvo el clima.
Todo lo que responde está marcado: si un dato es **real** (`origen: "real"`) o
**simulado** (`origen: "simulado"`), y lo que no se puede medir se dice
"no disponible" en vez de inventarse.

---

## 1. Requisitos (verificados en este equipo)

| Cosa | Versión medida | Falta para otro equipo |
|---|---|---|
| Python | 3.13.5 | ≥ 3.10 |
| aiohttp | 3.11.16 | `pip install aiohttp` (única dependencia del puente) |
| Ollama | 0.34.2 en `/usr/local/bin/ollama` | opcional; sin él CORT sigue funcionando con las funciones locales |
| Navegador | cualquiera moderno, en `127.0.0.1` | — |
| Hardware medido | 2 núcleos · 1851 MB de RAM total | manda el número real de tu equipo |

## 2. Arrancar (dos pasos)

```bash
# 1) El cerebro (Python). Deja la ventana abierta; es el servidor.
cd ~/Escritorio/CORT/cort-bridge
python3 -u cort_server.py

# 2) Abre en el navegador:
#    http://127.0.0.1:8766/index.html
```

El puente sirve las dos cosas: la interfaz estática en **8766** y el websocket en **8765**.
Al arrancar imprime la RAM disponible medida y si Ollama está vivo, para que veas con qué
números empieza.

**Sin puente** (modo demo, todo simulado): `python3 -m http.server 8766` dentro de
`cort-web/` y abrir lo mismo. La interfaz avisa que el cerebro no está; no se hace la
ilusión de que responde sola.

## 3. Las dos puertas: disco y memoria

Son cosas distintas y confundirlas fue el error que dejó a CORT sin cerebro una temporada.

- **Descargar un modelo gasta DISCO.** Puerta: 500 MB de colchón además del tamaño del
  archivo, y 250 MB libres para tener el servidor de pie si hay que levantarlo. Con el
  servidor ya vivo, bajar es puro I/O y no congela nada.
- **Cargar un modelo y chatear gasta RAM.** Puerta: la RAM libre real, leída de
  `MemAvailable`. Si el modelo no cabe, **se dice el número** y se niega, no se prueba a
  ver qué pasa. Probar a ver qué pasa es como se congela un equipo de 1,8 GiB.

Con ~300 MB libres (Qoder + navegador abiertos) **ningún modelo cabe**. Por eso el turno de
noche: con el navegador y el editor cerrados quedan 900 MB o más.

## 4. Ya tienes 6 modelos descargados (medido en disco, 2026-11-02)

Leído de `~/.ollama/models/manifests` (4,7 GB de blobs), en MiB y tal como lo reporta el
puente. No hace falta descargar nada para empezar; hace falta **cargar** uno con memoria
suficiente:

| Modelo | Peso del archivo | RAM libre estimada para usarlo |
|---|---|---|
| `smollm2:135m` | 258 MB | ~511 MB |
| `gemma3:270m` | 278 MB | ~539 MB |
| `qwen2.5:0.5b` | 379 MB | ~680 MB |
| `qwen3:0.6b` | 498 MB | ~847 MB |
| `airaos-local:latest` | 718 MB | ~1 155 MB |
| `qwen3.5:2b` | 2 614 MB | ~3 809 MB (fuera del alcance de este equipo) |

El peso es medido. La RAM es **estimación** con la fórmula `peso × 1,4 + 150 MB` (pesos +
caché KV + contexto); está marcada como estimación en el código y se puede corregir midiendo.

## 5. El turno de noche (lo que sí desbloquea el cerebro)

```bash
# Con el navegador y el editor CERRADOS, antes de dormir:
cd ~/Escritorio/CORT/cort-bridge
CORT_RAM_MIN=900 MODELO=smollm2:135m ./cort_cerebro.sh
```

El guion mide la RAM libre antes de tocar nada; si no llega al mínimo, sale con código 2 y
dice el número ("hacen falta 900 MB libres y hay 312"). Si llega: levanta `ollama serve`,
baja o carga el modelo, lo anota en `cort_state.json` como modelo local y **apaga el
servidor para devolver la memoria**. No deja nada comiéndose el equipo.

## 6. Probar el protocolo sin abrir el navegador

```bash
cd ~/Escritorio/CORT/cort-bridge
python3 cort_probe.py                # estado del cerebro, sistema y clima
python3 cort_probe.py av             # auditoría: pasos y hallazgos por consola
python3 cort_probe.py modelos        # inventario del disco, catálogo y qué modelo cabe
python3 cort_probe.py clima          # por IP, por ciudad escrita y con ciudad falsa
python3 cort_probe.py cerebro "¿cómo va la RAM?"
```

Sirve para verificar el puente cuando el navegador no se puede abrir por falta de memoria.

## 7. Qué funciona con datos reales (medido el 2026-11-02)

| Función | Estado | Qué se midió |
|---|---|---|
| CPU / RAM / disco del HUD | **real** | 99-100 % CPU, 82-84 % RAM, 314 MB libres — ya no los 14-26 % inventados |
| Clima | **real** | open-meteo: Carora, 32,3 °C, llovizna. Con ciudad escrita a mano se resuelve con el geocodificador de open-meteo; si la ciudad no existe, avisa de que usa el último punto conocido en vez de cambiar de ciudad en silencio |
| Fila **CEREBRO** en Ajustes | **real** | lista los modelos leídos en disco con su peso, la RAM que piden y si caben con la memoria de este momento; los que no caben salen en punteado y un pie dice qué hacer |
| Elegir modelo desde la interfaz | **real** | el botón de la fila manda `set_local_model` al puente y se comprueba que queda escrito en `cort_state.json` |
| Auditoría de seguridad ("antivirus") | **real** | 4-5 hallazgos en 0,9-9 s en 4 pasos (arranque, procesos, archivos, permisos) |
| Estado de Ollama | **real** | responde aunque el servidor esté apagado, con la RAM medida |
| Descarga de modelos | **real con puertas** | si el modelo ya está en disco lo dice en vez de volver a bajarlo; si falta, mide disco (500 MB de colchón) antes de empezar y sigue el progreso del `/api/pull`. El protocolo se validó además contra un simulador etiquetado, sin tocar red |
| Chat con modelo | **cortado por RAM** | el puente se niega y dice el número; funciona en cuanto hay ~530 MB libres |
| Jarvis OS | **honesto** | nada en el puerto 3000; el puente se niega a instalarlo (pediría el disco entero) |
| Gestos con MediaPipe | **desactivados a propósito** | los tres `<script>` del CDN fuera del index: el arranque ya no descarga nada de internet. El bundle tiene guardas, así que sólo pierde el modo holograma de gestos |
| Guía de instalación de Ollama del panel | escrita para **Windows** | powerShell, "Windows 10 22H2", zona de notificaciones. En esta Canaima no aplica; hay que reescribirla para Linux (pendiente) |
| ~46 comandos del menú (winget, juegos, correo, OBS, VPN…) | no implementados | son de Windows; en Linux hace falta escribir cada uno |

## 8. La regla que no se rompe

El antivirus **informa, no borra ni mata nada**. Si le pides acción sobre un hallazgo
responde: *"No voy a borrar ni bloquear «X». Un falso positivo cuesta más que una amenaza
visible: dime tú qué hacer."* La auditoría recorre `~/.config/autostart`, procesos, permisos
SUID y archivos sensibles con tope de 2500 archivos y 8 s de presupuesto, y avisa cuando
trunca la lista en vez de callarse.

## 9. Idiomas

Español por defecto. Francés e inglés se cambian en **Ajustes** (fila "Idioma"). La
traducción se aplica al DOM (898+ entradas de diccionario más reglas para los textos que
el puente escribe), así que también traduce lo que llega por websocket. Cobertura medida
tras el trabajo: **100 %** de las 523 cadenas con firma francesa (queda un nombre propio,
"Éloïse — Francia").

## 10. Antes de publicar

Leer [`PROCEDENCIA.md`](PROCEDENCIA.md). Resumen: la base es la demo de TechEnClair **sin
licencia declarada**, la carta de permiso está escrita y **sin enviar**, y mientras no
respondan esto se queda en rama local.
