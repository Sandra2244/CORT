package com.cort.ia

import android.content.Context
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.StatFs
import java.io.File
import java.util.zip.ZipInputStream
import org.json.JSONObject
import org.vosk.Model
import org.vosk.Recognizer

/**
 * El OÍDO PROPIO de CORT: reconocimiento de español que vive dentro del APK y
 * no necesita ni internet ni los servicios de voz de Google.
 *
 * Está escrito en **Kotlin a propósito**. El `CORT IA_1.1.0.apk` que la dueña
 * tiene en el teléfono (1.815.389 B, medidos) es un build Kotlin: sus cuatro
 * `classes….dex` y sus `builtins` de Kotlin suman 919.207 B comprimidos.
 * La petición fue «usa el método de compilación del original», pues este archivo
 * se compila con `kotlinc`, se dexa con `d8` y va al mismo `classes.dex` que el
 * resto, igual que entonces. El cuerpo de siempre (`Cerebro`, `Mente`,
 * `Reproductor`…) sigue en Java: está probado contra `javac` y contra las 283
 * frases de la tabla, y cambiarlo de idioma no habría añadido ni una función.
 *
 * ### El motor, y por qué este (todo medido el 2026-10-21)
 *
 * **Vosk** (`com.alphacephei:vosk-android:0.3.47`, Apache-2.0):
 *
 * · AAR de 12.297.565 B con UN `libvosk.so` por ABI (arm64 8.862.928 B,
 *   armeabi-v7a 8.279.808 B) y 14 clases Java de 16.721 B. Modelo
 *   `vosk-model-small-es-0.42`: 39.817.833 B comprimidos, 60.286.598 B en 14
 *   archivos al descomprimirse.
 * · `sherpa-onnx` hace el mismo trabajo con 27.021.320 B de `.so` por ABI y un
 *   modelo de español continuo de 155.838.792 B: un APK de más de 200 MB.
 * · `whisper.cpp` y `Piper` no publican binarios de Android ya hechos; hay que
 *   cruzar-compilarlos con NDK. Quedan para la VOZ propia de la próxima ronda.
 *
 * ### Las firmas que se usan (verificadas con `javap` sobre el `classes.jar` del
 * AAR, no de memoria)
 *
 * ```
 * org.vosk.Model(String ruta)              throws IOException   ← SÓLO un directorio del disco
 * org.vosk.Recognizer(Model, float)        throws IOException
 *   boolean acceptWaveForm(short[], int)   String getResult()  String getPartialResult()  String getFinalResult()
 *   void reset()  void close()
 * ```
 *
 * Que `Model` sólo acepte un **directorio** (y no un `AssetManager`) es la razón
 * de que este archivo ocupe una tercera parte en desempacar: el ZIP del modelo
 * viaja dentro del APK en `assets/motor/` y la primera vez que CORT arranca se
 * copia a `filesDir/motor/`. Se hace a mano, sin `org.vosk.android.StorageService`,
 * porque ese servicio lee de `res/raw` con `AssetFileDescriptor` — y `aapt2`
 * comprime los assets, así que ese descriptor no existe: `openFd` lanza.
 *
 * Tampoco se usa `org.vosk.android.SpeechService`, aunque está en el AAR. Su
 * bucle (`RecognizerThread.run`, leído en el fuente oficial de Alpha Cephei)
 * termina en `if (nread < 0) throw new RuntimeException(...)` dentro de un hilo
 * sin `try/catch`: un `AudioRecord.read()` negativo —el caso exacto de cuando
 * otro juego le quita el micrófono a CORT, que es una queja real con Call of
 * Duty— **tumbaría el proceso**. Aquí esa misma lectura se corta, se avisa en
 * español y se suelta el micro.
 *
 * ### Contrato con la cara: idéntico al del reconocedor de Google
 *
 * `ui/js/voice.js` ya maneja la palabra de activación, el retroceso y los frenos;
 * sólo necesita `stt-start`, `stt-speech`, `stt-level` (0..1), `stt-partial`,
 * `stt-final` (`text` + `alts`), `stt-error` (`no-speech` | `busy` | `audio` |
 * `abort`) y `stt-end`. Nunca sale `not-allowed` de aquí: ese nombre apaga la
 * palabra de activación para siempre en la cara, y el permiso de micro lo
 * comprueba `CortNative` antes de llamar. Y `stt-end` sale **exactamente una vez**
 * por escucha —`cierra()` sobre un `AtomicBoolean`—, porque `voice.js` rearma el
 * «Oye CORT» en cada uno: dos finales serían dos micrófonos abiertos.
 */
class Oido(private val act: Context, private val salida: Oyente) {

    /** El único método que necesita la cara: un cuadro JSON ya con su `type`. */
    fun interface Oyente {
        fun cuadro(json: String)
    }

    companion object {
        /** Nombre del modelo, tal como lo escribe `apps/apk/motor.sh`. */
        const val MODELO = "vosk-model-small-es-0.42"

        /** Peso del ZIP que viaja en `assets/motor/`, medido en la fuente oficial. */
        const val PESO_ZIP = 39817833L

        /** Lo que ocupa en el disco del teléfono al descomprimirse (60 MB). */
        const val CRUDO_MODELO = 60286598L

        /** Colchón además del modelo: sin esto libre, ni se intenta extraer. */
        const val COLCHON = 20_000_000L

        /** Hz del oído de Vosk: 16 kHz mono, PCM 16. No es configurable. */
        const val MUESTRA = 16000

        /** Cuánto escucha como mucho cada vez, en ms. */
        const val MAX_WAKE = 5000
        const val MAX_CMD = 12000

        /** Marca del desempaque; su contenido es `MODELO:PESO_ZIP`, así que si el
         *  modelo cambia de versión se vuelve a extraer solo, sin tocar nada de la dueña. */
        const val MARCA = ".cort-listo"

        /** Por debajo de este nivel (0..1) se considera silencio. */
        private const val SILENCIO = 0.012
    }

    @Volatile private var estado = "sin-intentar"
    @Volatile private var motivo = ""
    @Volatile private var modelo: Model? = null
    @Volatile private var reconocedor: Recognizer? = null

    @Volatile private var vivo = false
    @Volatile private var cancelado = false
    /* `true` mientras hay UNA escucha abierta. Es la llave de que el `stt-end`
       salga exactamente una vez por escucha: lo cierra quien llega primero —el hilo
       que entregó su texto o se pasó de tiempo, o `cancela()`— y el que llega
       después no emite nada. `AtomicBoolean` en vez de un `var` con `@Volatile`
       porque las dos partes compiten de verdad: con un booleano normal los dos podían
       leer `true` a la vez. Medido en el run rojo de `v0.2.21-demo`, comprobación 5
       de `PruebaOido.kt`: la cara recibía DOS `stt-end` y `voice.js` rearmaba «Oye
       CORT» dos veces, o sea dos micrófonos abiertos sobre el mismo hilo. */
    private val abierta = java.util.concurrent.atomic.AtomicBoolean(false)

    /** Cierra la escucha entregando su `stt-end`, sólo si todavía estaba abierta. */
    private fun cierra() {
        if (abierta.compareAndSet(true, false)) cuadro("""{"type":"stt-end"}""")
    }
    private var hilo: Thread? = null

    /* ─────────────────────────── arranque ─────────────────────────── */

    /**
     * Extrae el modelo y carga la librería **en un hilo aparte**: `Model()` tarda
     * entre 1 y 3 s, y el `onCreate` de la actividad no puede pararse ahí, o el
     * teléfono muestra «CORT no responde» antes de tener oído ninguno.
     */
    fun prepara() {
        if (estado != "sin-intentar") return
        estado = "preparando"
        avisa()
        val carga = Thread { trabaja() }
        carga.name = "cort-oido"
        carga.isDaemon = true
        carga.start()
    }

    private fun trabaja() {
        try {
            val carpeta = extrae() ?: return        // ya avisó del porqué
            estado = "cargando"
            avisa()
            val m = Model(carpeta.absolutePath)
            modelo = m
            reconocedor = Recognizer(m, MUESTRA.toFloat())
            estado = "listo"
            avisa()
        } catch (enlaceRoto: UnsatisfiedLinkError) {
            // Sin `libvosk.so` o sin `libjnidispatch.so` dentro del APK: es un
            // fallo de EMPAQUETADO, no del teléfono. Se dice tal cual para no
            // culpar a la dueña de algo que rompió el pipeline.
            motivo = "las librerías del motor no están en el APK (${enlaceRoto.message ?: "sin detalle"})"
            estado = "sin-libreria"
            avisa()
        } catch (todoLoDemas: Throwable) {
            motivo = describe(todoLoDemas)
            estado = "roto"
            avisa()
        }
    }

    /**
     * Desempaca `assets/motor/<modelo>.zip` a `filesDir/motor/`. Devuelve el
     * directorio del modelo, o `null` habiendo avisado ya del motivo.
     */
    private fun extrae(): File? {
        val raiz = File(act.filesDir, "motor")
        val carpeta = File(raiz, MODELO)
        val marca = File(carpeta, MARCA)
        val etiqueta = "$MODELO:$PESO_ZIP"
        if (marca.exists() && etiqueta == runCatching { marca.readText() }.getOrDefault("")) {
            return carpeta
        }

        val disponible = libre(raiz)
        if (disponible != null && disponible < CRUDO_MODELO + COLCHON) {
            motivo = "no cabe: hacen falta ${(CRUDO_MODELO + COLCHON) / 1048576} MB libres y hay ${disponible / 1048576} MB"
            estado = "sin-sitio"
            avisa()
            return null
        }

        estado = "extrayendo"
        avisa()
        val temporal = File(raiz, ".${MODELO}.tmp")
        return try {
            temporal.deleteRecursively()
            temporal.mkdirs()
            var escrito = 0L
            var archivos = 0
            ZipInputStream(act.assets.open("motor/$MODELO.zip")).use { z ->
                var e = z.nextEntry
                while (e != null) {
                    if (!e.isDirectory) {
                        // El ZIP oficial viene con `vosk-model-small-es-0.42/` como
                        // carpeta de arriba en cada entrada, y `temporal` YA es esa
                        // carpeta: hay que quitarle el prefijo o `Model()` se encontraría
                        // `…/vosk-model-small-es-0.42/vosk-model-small-es-0.42` y diría
                        // «does not contain model files» (medido el 2026-10-21).
                        val nombre = e.name.removePrefix("$MODELO/")
                        if (nombre.isNotBlank()) {
                            val destino = File(temporal, nombre)
                            destino.parentFile?.mkdirs()
                            destino.outputStream().use { salidaArchivo -> z.copyTo(salidaArchivo) }
                            escrito += destino.length()
                            archivos++
                        }
                    }
                    z.closeEntry()
                    e = z.nextEntry
                }
            }
            if (archivos == 0 || escrito < CRUDO_MODELO * 9 / 10) {
                motivo = "el ZIP del modelo salió incompleto: $escrito bytes de $CRUDO_MODELO"
                estado = "roto"
                avisa()
                temporal.deleteRecursively()
                null
            } else {
                carpeta.deleteRecursively()
                raiz.mkdirs()
                if (!temporal.renameTo(carpeta)) {
                    motivo = "no se pudo colocar la carpeta del modelo en su sitio"
                    estado = "roto"
                    avisa()
                    null
                } else {
                    File(carpeta, MARCA).writeText(etiqueta)
                    carpeta
                }
            }
        } catch (sinZip: Exception) {
            motivo = "el modelo no está dentro del APK (${describe(sinZip)})"
            estado = "sin-modelo"
            avisa()
            temporal.deleteRecursively()
            null
        }
    }

    /** MB libres del sitio donde se escribe el modelo; `null` si no se puede medir. */
    private fun libre(directorio: File): Long? = try {
        val existente = directorio.parentFile ?: directorio
        StatFs(existente.absolutePath).availableBytes
    } catch (tampoco: Exception) {
        null
    }

    /* ─────────────────────────── escuchar ─────────────────────────── */

    fun listo(): Boolean = estado == "listo" && reconocedor != null

    fun ocupado(): Boolean = vivo

    fun estado(): String = estado

    /**
     * Abre el micro y escucha una orden. Devuelve `false` si el oído propio no
     * está listo: `CortNative` usa ese `false` para caer en el reconocedor del
     * sistema sin que la cara note la diferencia.
     */
    fun escucha(modo: String?, maximoMs: Int): Boolean {
        val r = reconocedor ?: return false
        if (vivo) return false

        val minimo = AudioRecord.getMinBufferSize(
            MUESTRA, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT
        )
        if (minimo <= 0) {
            sinOido("audio", "el teléfono no presta un micrófono de 16 kHz (código $minimo)")
            return false
        }
        val bocetoCorto = maxOf(minimo, MUESTRA / 5)          // muestras, nunca impar

        val graba = try {
            AudioRecord(
                MediaRecorder.AudioSource.VOICE_RECOGNITION, MUESTRA,
                AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT,
                bocetoCorto * 2
            )
        } catch (rechazado: Exception) {
            sinOido("audio", "no se pudo abrir el micrófono (${describe(rechazado)})")
            return false
        }
        if (graba.state != AudioRecord.STATE_INITIALIZED) {
            graba.release()
            sinOido("busy", "el micrófono lo tiene otra aplicación")
            return false
        }

        vivo = true
        cancelado = false
        abierta.set(true)
        val elHilo = Thread { escucha(r, graba, modo, maxOf(maximoMs, 1500)) }
        elHilo.name = "cort-oido-escuchando"
        elHilo.priority = Thread.MAX_PRIORITY
        hilo = elHilo
        elHilo.start()
        return true
    }

    private fun escucha(r: Recognizer, graba: AudioRecord, modo: String?, maximoMs: Int) {
        val boceto = ShortArray(maxOf(MUESTRA / 50, 160))     // 20 ms
        var ultimoAviso = 0L
        var topeDeNivel = 0.0
        var huboHabla = false
        var texto: String? = null
        var fallo: String? = null
        var detalle = ""

        try {
            graba.startRecording()
            if (graba.recordingState != AudioRecord.RECORDSTATE_RECORDING) {
                fallo = "audio"
                detalle = "el micrófono no llegó a grabar"
            } else {
                cuadro("""{"type":"stt-start","modo":${comilla(modo ?: "cmd")}}""")
                val inicio = System.currentTimeMillis()
                r.reset()
                while (!cancelado && vivo) {
                    if (System.currentTimeMillis() - inicio > maximoMs) {
                        if (huboHabla) texto = termina(r) else fallo = "no-speech"
                        break
                    }
                    val leido = graba.read(boceto, 0, boceto.size)
                    if (leido < 0) {
                        // ÉSTE era el `throw` de `SpeechService`. Aquí se corta,
                        // se avisa y se suelta el micro: no se muere la app.
                        fallo = "audio"
                        detalle = "la lectura del micrófono devolvió $leido (otro aparato se lo llevó)"
                        break
                    }
                    val nivel = nivelDe(boceto, leido)
                    if (nivel > SILENCIO) huboHabla = true
                    if (nivel > topeDeNivel + 0.2) {
                        topeDeNivel = nivel
                        cuadro("""{"type":"stt-speech"}""")
                    }
                    val ahora = System.currentTimeMillis()
                    if (ahora - ultimoAviso > 90) {
                        ultimoAviso = ahora
                        cuadro("""{"type":"stt-level","level":${fijo(nivel, 2)}}""")
                    }
                    if (r.acceptWaveForm(boceto, leido)) {
                        val cerrado = leEscribe(r.result, "text")
                        if (cerrado.isNotEmpty()) {
                            texto = cerrado
                            break
                        }
                    } else if (ahora - ultimoAviso > 150) {
                        val parcial = leEscribe(r.partialResult, "partial")
                        if (parcial.isNotEmpty()) {
                            ultimoAviso = ahora
                            cuadro("""{"type":"stt-partial","text":${comilla(parcial)}}""")
                        }
                    }
                }
            }
        } catch (revire: Exception) {
            fallo = "abort"
            detalle = describe(revire)
        } finally {
            try { graba.stop() } catch (yaNoGraba: Exception) { /* ya estaba parado */ }
            graba.release()
            try { r.reset() } catch (elMotorNoQuiere: Exception) { /* nada */ }
            vivo = false
        }

        // `cancela()` ya cerró su sesión (`cierra()` es idempotente por
        // `compareAndSet`): aquí no se entrega texto ni se repite el `stt-end`.
        if (cancelado) return
        if (texto == null && fallo == null) texto = termina(r)
        when {
            fallo != null -> {
                if (detalle.isNotEmpty()) {
                    motivo = detalle
                    cuadro("""{"type":"stt-error","error":${comilla(fallo)}}""")
                } else {
                    cuadro("""{"type":"stt-error","error":${comilla(fallo)}}""")
                }
                cierra()
            }
            texto.isNullOrEmpty() -> {
                cuadro("""{"type":"stt-error","error":"no-speech"}""")
                cierra()
            }
            else -> {
                cuadro("""{"type":"stt-final","text":${comilla(texto)},"alts":[${comilla(texto)}]}""")
                cierra()
            }
        }
    }

    /** `getFinalResult()` convertido a texto limpio; cadena vacía si el motor calla. */
    private fun termina(r: Recognizer): String =
        try { leEscribe(r.finalResult, "text") } catch (elMotorCalla: Exception) { "" }

    /** Cierra la escucha **entregando** lo que haya (el `stop()` de siempre). */
    fun para() {
        vivo = false
        hilo?.join(600)
    }

    /** Cierra la escucha **sin** entregar nada: el doble toque y el `pause` de la cara. */
    fun cancela() {
        cancelado = true
        vivo = false
        val elHilo = hilo
        hilo = null
        elHilo?.interrupt()
        // `cierra()` y no un `cuadro` directo: si la escucha ya se cerró sola —el
        // máximo de tiempo cumplido o un texto entregado antes de que la cara llamara
        // al botón— el `stt-end` YA salió, y un segundo rearma doble el bucle de
        // «Oye CORT» (`voice.js` llama a `scheduleWake()` en cada uno).
        cierra()
    }

    /** Freno del modo juego y de `MainActivity.onPause`: si estaba escuchando, lo cierra. */
    fun frena(congelado: Boolean) {
        if (congelado && vivo) cancela()
    }

    /** Se llama al destruir la actividad: el `Model` es nativo y trae ~50 MB detrás. */
    fun suelta() {
        cancela()
        try { reconocedor?.close() } catch (yaCerrado: Exception) { /* nada */ }
        reconocedor = null
        try { modelo?.close() } catch (yaCerrado: Exception) { /* nada */ }
        modelo = null
        estado = "cerrado"
    }

    /* ─────────────────────────── lo que ve la cara ─────────────────────────── */

    /** El estado completo, para la pantalla Equipo y para el diagnóstico por USB. */
    fun estadoJson(): String {
        val libre = libre(File(act.filesDir, "motor"))
        return StringBuilder("{\"type\":\"motor\"")
            .append(",\"oido\":").append(comilla(estado))
            .append(",\"listo\":").append(listo())
            .append(",\"motor\":\"vosk-0.3.47\"")
            .append(",\"modelo\":").append(comilla(MODELO))
            .append(",\"pesoModelo\":").append(CRUDO_MODELO)
            .append(",\"libresMB\":").append(if (libre == null) "\"?\"" else "${libre / 1048576}")
            .append(",\"motivo\":").append(comilla(motivo))
            .append(",\"escuchando\":").append(vivo)
            .append('}')
            .toString()
    }

    private fun avisa() {
        cuadro("""{"type":"motor","oido":${comilla(estado)},"motivo":${comilla(motivo)}}""")
    }

    private fun sinOido(nombre: String, detalle: String) {
        motivo = detalle
        avisa()
        cuadro("""{"type":"stt-error","error":${comilla(nombre)}}""")
        cuadro("""{"type":"stt-end"}""")
    }

    private fun cuadro(json: String) = salida.cuadro(json)

    /* ───────────────────── utilities sin sorpresas ───────────────────── */

    /** La energía de la boceta, normalizada 0..1 (es lo que espera `stt-level`). */
    private fun nivelDe(boceto: ShortArray, leido: Int): Double {
        if (leido <= 0) return 0.0
        var suma = 0.0
        for (n in 0 until leido) {
            val v = boceto[n] / 32768.0
            suma += v * v
        }
        return (kotlin.math.sqrt(suma / leido) * 3.2).coerceAtMost(1.0)
    }

    /** Vosk responde `{"text":"..."}` y `{"partial":"..."}`; si algo no sale, "". */
    private fun leEscribe(crudo: String, clave: String): String = try {
        JSONObject(crudo).optString(clave, "")
    } catch (noEsJson: Exception) {
        ""
    }

    private fun comilla(texto: String?): String {
        if (texto == null) return "\"\""
        val s = StringBuilder("\"")
        for (c in texto) {
            when (c) {
                '"' -> s.append("\\\"")
                '\\' -> s.append("\\\\")
                '\n' -> s.append("\\n")
                '\r' -> s.append("\\r")
                '\t' -> s.append("\\t")
                else -> if (c.code < 32) s.append(String.format("\\u%04x", c.code)) else s.append(c)
            }
        }
        return s.append('"').toString()
    }

    private fun fijo(valor: Double, decimales: Int): String =
        String.format(java.util.Locale.US, "%.${decimales}f", valor)

    private fun describe(e: Throwable): String =
        e.javaClass.simpleName + ": " + (e.message ?: "sin mensaje")
}
