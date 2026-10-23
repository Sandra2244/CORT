# Los cerebros de casa: Ollama por Wi-Fi (ronda 2.4)

**Lo que CORT ya hace desde el teléfono**, sin pasar por internet ni por una factura:

- buscar el PC que tiene Ollama en tu Wi-Fi;
- listar los modelos instalados con su tamaño, sus parámetros y su cuantización;
- **bajar un modelo nuevo** desde el teléfono, viendo la barra moverse;
- borrar uno que ya no uses;
- elegir uno como cerebro, y que «piensa…» y el dictado se contesten **en casa**.

## Lo primero que hay que entender (y no es una excusa)

Ollama **no puede ir dentro del APK**. Es un servidor escrito en Go que necesita un
ordenador Linux/Windows/macOS y varios gigabytes de RAM; un APK de Android no puede
traerlo dentro. Lo que va dentro del APK es su **cliente**: `apps/apk/src/com/cort/ia/Ollama.java`,
que habla con el servidor de tu PC por la red de casa. Medido y comprobado con
`scripts/prueba-mente.sh` (`Prueba4`, 36 comprobaciones contra un Ollama de mentira
montado dentro del propio JDK).

Si algún día CORT piensa **sin PC delante**, eso será el otro camino: un motor GGUF
(los formatos `.so` de llama.cpp) metido en el APK. Esa parte es la ronda 2.4b y va a
parte porque necesita cruzar-compiler con el NDK dentro del pipeline.

## 1 · Deja Ollama a la vista de la Wi-Fi (una vez sola)

Por defecto Ollama escucha **sólo en su propia máquina** (`127.0.0.1:11434`), así que
el teléfono no lo ve aunque estén en la misma red. Hay que arrancarlo con
`OLLAMA_HOST=0.0.0.0:11434`.

**Linux con systemd**:

```bash
sudo systemctl edit ollama.service      # se abre el editor de la gota
# escribe dentro:
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

**Linux sin servicio** (lanzas `ollama serve` a mano):

```bash
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

**Windows**: Ajustes ▸ Sistema ▸ Acerca de ▸ Configuración de avanzado del sistema ▸
Variables de entorno ▸ Nueva… → nombre `OLLAMA_HOST`, valor `0.0.0.0:11434`. Luego
cierra Ollama de la bandeja (salir, no cerrar la ventana) y vuelve a abrirlo.

**Comprobación** desde el propio PC: `curl http://127.0.0.1:11434/api/version` debe
devolver `{"version":"…"}`. Desde el teléfono, si el firewall está activo, hay que
permitir el puerto 11434 en la red de casa (los firewalls de Windows suelen preguntar
la primera vez que Ollama escucha fuera).

## 2 · Dile a CORT dónde está

Hoja **Equipo ▸ 3 · Cerebro ▸ «los cerebros gordos de tu casa»**:

| botón | qué hace |
|---|---|
| 🔍 **buscar en tu Wi-Fi** | barre el rango `192.168.x.0/24` de tu teléfono buscando el puerto 11434. Tarda dos o tres segundos. Si encuentra uno solo, lo fija y lista sus modelos; si encuentra varios, toca elegir. **No pide ningún permiso nuevo**: la red propia se lee con `NetworkInterface`. |
| `fijar` (junto al campo de dirección) | guarda la dirección que escribiste y hace un ping corto. Guarda **siempre** —puede que el PC esté dormido— y dice si contestó o no. |
| ↻ **mis modelos** | la lista: nombre, tamaño, parámetros y cuantización. |
| **usar** (en cada modelo) | lo convierte en tu cerebro. A partir de ahí las preguntas se contestan con él y la respuesta sale marcada como `casa`, no como `nube`. |
| ↓ **descargar** | pide el modelo al PC y enseña la barra. El modelo se guarda en el PC, no en el teléfono. |
| **borrar** | quita ese modelo del PC. |

La dirección también se puede escribir a mano: valen `192.168.1.20`,
`192.168.1.20:11434`, `http://192.168.1.20:11434` e incluso la base con `/v1`.

## 3 · Qué modelo pedir con un teléfono de 4 GB

La RAM manda: un modelo grande se queda fuera y Android mata la conversación, no el
modelo. Lo que hay que mirar es el número de **parámetros** (0.5B, 1.5B, 7B…): CORT lo
lee del propio servidor (`/api/tags`) y lo pone en cada fila, junto al tamaño real en
disco y la cuantización.

Con un PC de 4 GB de RAM libre, pide de entrada `qwen2.5:0.5b` o `qwen2.5:1.5b` —son
los que caben sin apretar— y sube sólo si ves que responde bien y va sobrado. Un 7B,
aunque sea el que sale en los tutoriales, necesita varios gigabytes más y en esa
máquina se queda fuera.

**No copio tamaños de una web**: la lista que pinta CORT viene de `GET /api/tags` del
servidor que tengas delante, así que lo que ves ahí es lo que ocupa de verdad en tu PC.

## 4 · Cómo se ve que está pensando en casa

Con el modelo elegido, una pregunta larga (`piensa explícame qué eres`) contesta con
un cuadro marcado `de:"casa"` en vez de `de:"nube"`. Y con el corte de internet, o sin
clave de Groq, CORT sigue pensando: la red local no sale de casa.

Si el PC no está, la hoja lo dice con la frase de Java —«no llego a … por esta Wi-Fi»,
«el PC dejó de mandar trozos»— y CORT **no finge**: vuelve a `Cerebro` (las 283 frases
de la tabla) y a `Razon` (cuentas, unidades, fechas), que viven dentro del APK.

## 5 · Qué NO hace esta ronda

- No baja modelos al teléfono ni piensa sin el PC encendido (eso es 2.4b, el motor GGUF).
- No abre el puerto por ti ni toca el firewall del PC.
- No barre redes que no sean la tuya: el barrido completo sólo se hace en casa, y las
  pruebas del pipeline usan direcciones explícitas para no llamar a máquinas ajenas.

## 6 · El aviso cuando termina la bajada (ronda 2.8)

Bajar `qwen2.5:7b` son **4,7 GB medidos** y por la Wi-Fi de casa es media hora larga.
Desde la 2.8 el APK manda **una notificación al terminar** —y otra si la
bajada se corta, con el motivo que dio el servidor—, así que la hoja de Modelos se
puede cerrar y el teléfono se puede bloquear. Al pulsar ↓ la propia cara lo dice:
*«cierra la hoja si quieres, te aviso cuando termine»*.

El aviso lo pone un fichero nuevo, **`Timbre.java`**, y no el propio `Ollama.java`, que
es el que baja el modelo. No es un capricho de ordenación: `Ollama` es Java puro y se
compila **aquí, en el portátil, con el JDK** (`scripts/prueba-mente.sh`) para poder
probarlo sin teléfono, y un `NotificationManager` de Android ahí no existe. Lo que entra
en esa prueba es su **gemelo de papel**, `apps/apk/prueba/papeles/com/cort/ia/Timbre.java`,
que anota en `Timbre.PUESTOS` cada aviso que se habría puesto, y `Prueba4` lo cuenta: si
el día de mañana `Ollama` deja de avisar, la prueba del portátil se pone roja en casa,
sin encender nada. La firma de los dos `Timbre` es idéntica a propósito, y el sector [24]
de `scripts/prueba-costura.py` la cruza. El papel **no puede llamar a `Ollama`** (lleva su
propia copia de `peso`): `scripts/prueba-oido.sh` compila los gemelos de papel en soledad,
y allí la clase real no está delante — eso dio un rojo en el runner el 2026-10-23.

Es una notificación normal de `NotificationManager`, con su canal
**`CORT · modelos`**, no un servicio en primer plano: no añade ningún permiso ni ningún
`foregroundServiceType` al manifiesto, porque la superficie del manifiesto es justo lo
que hacía rechazar el APK (ver `BLOQUEO-PLAY-PROTECT.md`). `POST_NOTIFICATIONS` ya
estaba declarado desde el reproductor; si algún día lo quitas en Ajustes ▸ Notificaciones,
el aviso no sale y la descarga sigue igual.

El límite dicho en seco: el hilo que lee la descarga es de la app. Si Android la mata
por memoria, el aviso no llega —el modelo, en cambio, sí queda bajado en el PC, porque
quien lo baja es Ollama—.

## 7 · El catálogo: 107 modelos con su peso medido

La lista de modelos que ofrece la hoja ya no son cuatro de memoria: son **107 modelos
con el peso que ocupa su descarga**, leído trozo a trozo del registro público de Ollama
con `scripts/mede-catalogo.py`. Los **14** que aparecen en la hoja de modelos del
escritorio (`backend/app/models.py`) son un subconjunto de esos 107 y salen de **los
mismos bytes**; el sector **[23]** de la costura cruza los dos archivos, comprueba que
el `gb` declarado es la división de esos bytes y que ningún modelo de la cara está en
la lista sin haber sido medido. Si un peso no se puede medir, no sale.
