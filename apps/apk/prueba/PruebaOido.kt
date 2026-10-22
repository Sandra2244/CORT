package com.cort.ia

import android.content.Context
import android.content.res.AssetManager
import android.media.AudioRecord
import android.os.StatFs
import java.io.File

/**
 * La prueba decisiva del oído propio, **en el portátil, sin teléfono**.
 *
 * `Oido.kt` llama a tres cosas que ningún `javac` del repo puede comprobar: las
 * firmas de `org.vosk.*`, el desempaque del modelo y el bucle de `AudioRecord`.
 * Aquí se le da el `Model` y el `Recognizer` **verdaderos** (el `vosk.jar` de
 * escritorio trae `libvosk.so` para linux-x86-64, que es el mismo código C que el
 * `libvosk.so` de Android) y los gemelos de papel de `apps/apk/prueba/papeles`
 * hacen de micrófono y de contexto. Se comprueba de una vez:
 *
 *   1 · que el ZIP de 39.817.833 B se desempaca y `Model(dir)` lo acepta;
 *   2 · que el estado llega a `listo` y se cuenta en JSON;
 *   3 · que con silencio sale `stt-error: no-speech` (y no un mudo infinito);
 *   4 · que con señal sale `stt-speech` y `stt-level` con número entre 0 y 1;
 *   5 · que `read()` negativo —el micrófono que le quitan a CORT en mitad de una
 *       partida— **no tumba el proceso**: termina en `stt-error: audio`;
 *   6 · que `cancela()` cierra con su `stt-end` y nada más;
 *   7 · que sin sitio libre no lo intenta ni destruye datos (`sin-sitio`).
 *
 * Uso (la monta `scripts/prueba-oido.sh`):
 *   java -cp … com.cort.ia.PruebaOido <carpeta-con-el-zip> <carpeta-de-archivos>
 */
object PruebaOido {

    private val avisos = ArrayList<String>()

    /**
     * El oído de las pruebas 2 a 5: **UN** `Model` cargado, no uno por comprobación.
     * Cargar el modelo de español cuesta entre 1 y 3 s en el teléfono y más de un
     * minuto en el portátil de 1,8 GiB de la dueña (medido 2026-10-21), y recargarlo
     * cinco veces no prueba nada nuevo. Lo que sí prueba compartirlo es lo que hace
     * CORT de verdad: el mismo oído escuchando varias veces seguidas, que es el
     * bucle de la palabra de activación.
     */
    private var guardado: Oido? = null

    @JvmStatic
    fun main(args: Array<String>) {
        val assets = File(if (args.size > 0) args[0] else "/tmp/cort-oido/activos")
        val archivos = File(if (args.size > 1) args[1] else "/tmp/cort-oido/archivos")
        val zip = File(assets, "motor/${Oido.MODELO}.zip")
        if (!zip.isFile) {
            println("FALLO: no está $zip (hay que copiar el modelo antes de la prueba)")
            kotlin.system.exitProcess(1)
        }

        var fallan = 0
        fallan += comprueba("desempaca y carga el modelo", {
            val ctx = contexto(assets, archivos, limpio = true)
            val o = Oido(ctx) { json -> synchronized(avisos) { avisos.add(json) } }
            o.prepara()
            esperaHasta { o.listo() } || fail("estado=" + o.estado() + " motivo=" + motivoDe(o))
            o.estadoJson().contains("\"listo\":true") || fail("estadoJson no dice listo")
            guardado = o                       // sigue vivo para las pruebas 2-5
        })

        fallan += comprueba("con silencio avisa no-speech", {
            val o = cargado(assets, archivos)
            AudioRecord.ALIMENTAR = null
            synchronized(avisos) { avisos.clear() }
            o.escucha("wake", 1200) || fail("escucha() dijo que no")
            esperaHasta { tiene("\"stt-end\"") } || fail("nunca cerró: " + ultimos())
            tiene("\"stt-error\",\"error\":\"no-speech\"") || fail("sin no-speech: " + ultimos())
            tiene("\"stt-start\"") || fail("no avisó de empezar")
        })

        fallan += comprueba("con señal manda nivel y habla", {
            val o = cargado(assets, archivos)
            AudioRecord.ALIMENTAR = tono(1000, 0.45)
            synchronized(avisos) { avisos.clear() }
            o.escucha("cmd", 1500) || fail("escucha() dijo que no")
            esperaHasta { tiene("\"stt-end\"") } || fail("nunca cerró: " + ultimos())
            tiene("\"stt-speech\"") || fail("no vio habla: " + ultimos())
            tiene("\"stt-level\"") || fail("no mandó nivel")
            nivelDentroDe0y1()
            AudioRecord.ALIMENTAR = null
        })

        fallan += comprueba("micrófono robado no tumba la app", {
            val o = cargado(assets, archivos)
            AudioRecord.CODIGO_DE_READ = -1
            synchronized(avisos) { avisos.clear() }
            o.escucha("cmd", 1500) || fail("escucha() dijo que no")
            esperaHasta { tiene("\"stt-end\"") } || fail("nunca cerró: " + ultimos())
            tiene("\"stt-error\",\"error\":\"audio\"") || fail("no dijo audio: " + ultimos())
            AudioRecord.CODIGO_DE_READ = 0
        })

        fallan += comprueba("cancela cierra con un solo stt-end", {
            val o = cargado(assets, archivos)
            AudioRecord.ALIMENTAR = tono(800, 0.3)
            synchronized(avisos) { avisos.clear() }
            o.escucha("wake", 8000) || fail("escucha() dijo que no")
            Thread.sleep(400)
            o.cancela()
            Thread.sleep(700)
            cuenta("\"stt-end\"") == 1 || fail("hubo ${cuenta("\"stt-end\"")} stt-end: " + ultimos())
            AudioRecord.ALIMENTAR = null
        })

        fallan += comprueba("sin sitio libre no lo intenta", {
            guardado?.suelta()          // se suelta el modelo ANTES de borrar su carpeta
            guardado = null
            File(archivos, "motor").deleteRecursively()
            StatFs.FALSO_LIBRE = 1_000L
            try {
                val ctx = contexto(assets, archivos, limpio = false)
                val o = Oido(ctx) { json -> synchronized(avisos) { avisos.add(json) } }
                o.prepara()
                esperaHasta { o.estado() == "sin-sitio" } || fail("estado=" + o.estado())
                !File(archivos, "motor/${Oido.MODELO}").exists() || fail("escribió igual")
                motivoDe(o).contains("no cabe") || fail("motivo raro: " + motivoDe(o))
            } finally {
                StatFs.FALSO_LIBRE = -1L
            }
        })

        if (fallan == 0) {
            println("OIDO OK: 6 comprobaciones sobre el motor Vosk de verdad.")
        } else {
            println("FALLO: $fallan de 6 comprobaciones del oído")
            kotlin.system.exitProcess(1)
        }
    }

    /* ────────────────────────── el andamiaje ────────────────────────── */

    private fun contexto(assets: File, archivos: File, limpio: Boolean): Context {
        if (limpio) {
            archivos.deleteRecursively()
            archivos.mkdirs()
        }
        val ctx = Context()
        // El gemelo de papel resuelve `new File(raíz, nombre)`, y `Oido` pide
        // `motor/<modelo>.zip`: con la raíz en `assets` la ruta sale exacta.
        ctx.assets = AssetManager(assets)
        ctx.filesDir = archivos
        return ctx
    }

    private fun cargado(assets: File, archivos: File): Oido {
        guardado?.let { if (it.listo()) return it }
        val o = Oido(contexto(assets, archivos, limpio = false)) { json ->
            synchronized(avisos) { avisos.add(json) }
        }
        o.prepara()
        esperaHasta { o.listo() } || fail("no llegó a listo: " + o.estado())
        guardado = o
        return o
    }

    private inline fun comprueba(nombre: String, bloque: () -> Unit): Int = try {
        bloque()
        println("  ok   · $nombre")
        0
    } catch (e: Throwable) {
        println("  FALLA· $nombre — ${e.message}")
        1
    }

    private class RazonDePrueba(msg: String) : RuntimeException(msg)
    private fun fail(msg: String): Nothing = throw RazonDePrueba(msg)

    private fun tiene(parte: String): Boolean = synchronized(avisos) { avisos.any { it.contains(parte) } }
    private fun cuenta(parte: String): Int = synchronized(avisos) { avisos.count { it.contains(parte) } }
    private fun ultimos(): String = synchronized(avisos) { avisos.takeLast(6).joinToString(" | ") }

    private fun nivelDentroDe0y1() {
        val niveles = synchronized(avisos) {
            avisos.mapNotNull { Regex("\"level\":([0-9.]+)").find(it)?.groupValues?.get(1)?.toDoubleOrNull() }
        }
        niveles.isNotEmpty() || fail("sin niveles")
        niveles.all { it in 0.0..1.0 } || fail("nivel fuera de 0..1: $niveles")
    }

    private fun motivoDe(o: Oido): String =
        Regex("\"motivo\":\"([^\"]*)\"").find(o.estadoJson())?.groupValues?.get(1) ?: ""

    private inline fun esperaHasta(corto: () -> Boolean): Boolean {
        var n = 0
        while (n < 600) {
            if (corto()) return true
            Thread.sleep(100)
            n++
        }
        return corto()
    }

    /** `leido` muestras de un seno: lo que oye el motor cuando alguien habla fuerte. */
    private fun tono(hz: Int, amplitud: Double): ShortArray {
        val n = 3200
        return ShortArray(n) { i ->
            (amplitud * 32767 * kotlin.math.sin(2.0 * Math.PI * hz * i / 16000.0)).toInt().toShort()
        }
    }
}
