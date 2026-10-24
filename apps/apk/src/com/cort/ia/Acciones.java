package com.cort.ia;

/*
 * Las manos de CORT sobre el aparato: volumen, linterna, alarma, temporizador,
 * cronómetro, abrir apps, buscar en la red y el estado del teléfono.
 *
 * Es la portación de `dev.sandra.cort.Acciones` (la línea hermana, la que sí
 * mandaba en el teléfono) al paquete de este APK, con las formas que fija la
 * sección 1 de `docs/CONTRATO-PUENTE-2.1.md`: entra el JSON `{"que":"…", …}` por
 * `accion(String)` y sale un JSON. Nunca sale una excepción: el puente llama
 * desde su propio hilo y un `throw` ahí arriba congela la cara.
 *
 * Lo que NO puede hacer, dicho sin adornos:
 *
 * · **No ejecuta comandos.** No hay `Runtime.exec`, ni shell, ni `sh -c`. Lo
 *   único que arranca son `Intent` con componentes que devolvió el propio
 *   `PackageManager` del sistema.
 * · **No marca sola.** Marcar y llamar es `Telefono.java`; aquí no se toca.
 * · **No abre la cámara ni graba vídeo ni imagen.** La linterna es
 *   `CameraManager.setTorchMode`, que no captura nada. Tampoco pide `CAMERA` en
 *   tiempo de ejecución: si no está concedida se dice, y la cara la pide por su
 *   lado (`CortNative.requestPermission('camara')`).
 * · **No sube el volumen sin `MODIFY_AUDIO_SETTINGS`.** Es un permiso normal
 *   (se concede al instalar), pero si la dueña lo revocó a mano, esto se para
 *   con `ok:false` en vez de quedarse a medias.
 * · **No puede iniciar ni parar un cronómetro de verdad**: Android no publica
 *   esa orden. Ver el comentario de `cronometro()`, que dice lo que sí hace.
 * · **No sabe de memoria qué apps existen ni ve todas las del teléfono.** Ve los
 *   lanzadores porque el manifiesto declara `<queries>` con `MAIN`/`LAUNCHER`, y
 *   los paquetes sueltos que ella nombra. Fuera de esa lista `PackageManager`
 *   contesta vacío, y aquí se dice en vez de fingir que la app no existe.
 * · **La red la mide `Aparato`, no esta clase.** Desde la ronda 2.2 el manifiesto
 *   declara `ACCESS_NETWORK_STATE`, así que `estado()` puede decir `wifi` o
 *   `celular` con un número real. Antes se callaba: sin ese permiso
 *   `ConnectivityManager` devuelve `null` y prometer «no hay Wi‑Fi» estando
 *   conectada era peor que callarlo.
 * · **No escribe nada en disco.** El único estado que recuerda es si ella misma
 *   mandó la linterna, en RAM y para poder alternarla.
 */

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.ActivityInfo;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.hardware.camera2.CameraAccessException;
import android.hardware.camera2.CameraManager;
import android.media.AudioManager;
import android.net.Uri;
import android.os.Build;
import android.provider.AlarmClock;
import android.provider.Settings;
import android.util.Log;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.UnsupportedEncodingException;
import java.net.URLEncoder;
import java.text.Normalizer;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class Acciones {

    private static final String LOG = "cort";

    /* ─────────────────────── el tiempo, dicho en español ─────────────────── */

    /** «5 minutos», «30 segundos», «2 horas». */
    private static final Pattern DURACION = Pattern.compile(
            "(\\d+)\\s*(hora|horas|minuto|minutos|min|segundo|segundos|s)");

    /** Cuánto sube o baja el volumen de una vez: tres pasos, no un salto brutal. */
    private static final int PASOS = 3;
    /** Por debajo de esta semejanza preferimos decir «no la encontré». */
    private static final int MINIMO_PORCENTAJE = 40;
    /** Tope de la rejilla de apps: cien iconos ya son un lista que nadie escucha. */
    private static final int TOPE_APPS = 120;

    /**
     * Lo que CORT mandó a la linterna, no lo que hace la linterna. Android sólo
     * deja leer el estado real de la linterna con un `TorchModeCallback`, y ese
     * callback vive mientras la cámara está abierta: para alternar con una orden
     * suelta la copia en RAM es lo honestamente posible. `volatile` porque la
     * escribe el hilo del puente.
     */
    private static volatile boolean linternaMandada = false;

    /**
     * Los nombres que la dueña usa de memoria y sus paquetes reales. Están en el
     * mismo orden que los `<package>` del `AndroidManifest.xml`: si aquí falta
     * uno, el manifiesto lo filtra y `PackageManager` responde vacío, que es
     * exactamente el fallo que se vio en la ronda 2.0.
     */
    private static final String[][] PAQUETES = {
        {"whatsapp", "com.whatsapp"},
        {"wpp", "com.whatsapp"},
        {"whatsappbusiness", "com.whatsapp.w4b"},
        {"youtube", "com.google.android.youtube"},
        {"maps", "com.google.android.apps.maps"},
        {"googlemaps", "com.google.android.apps.maps"},
        {"spotify", "com.spotify.music"},
        {"gmail", "com.google.android.gm"},
        {"calendario", "com.google.android.calendar"},
        {"googlecalendar", "com.google.android.calendar"},
        {"instagram", "com.instagram.android"},
        {"facebook", "com.facebook.katana"},
        {"tiktok", "com.ss.android.ugc.trill", "com.zhiliaoapp.musically"},
        {"archivos", "com.google.android.documentsui", "com.android.documentsui",
                "com.miui.filemanager", "com.huawei.filemanager", "com.sec.android.app.myfiles"},
        {"reproductormv", "com.xiaopl.mobileplayer", "com.ovovcx.fansclub"},
        {"mv", "com.xiaopl.mobileplayer", "com.ovovcx.fansclub"},
        {"lark", "com.xiaopl.mobileplayer", "com.ovovcx.fansclub"},
        {"larkplayer", "com.xiaopl.mobileplayer", "com.ovovcx.fansclub"},
    };

    private final Activity act;

    /**
     * Recibe la `Activity` (no sólo un `Context`) porque `startActivity` con
     * intentos que devuelven datos —alarma, búsqueda— se comporta mejor desde
     * ella. Todos los intentos llevan `FLAG_ACTIVITY_NEW_TASK` igualmente: el
     * puente llama desde su hilo y la cara puede estar ya en segundo plano.
     */
    public Acciones(Activity act) {
        this.act = act;
    }

    /* ────────────────────────────── la entrada ────────────────────────────── */

    /**
     * El único método público que llama la cara. `peticion` es el JSON del
     * contrato (`{"que":"volumen","como":"sube"}`, o `{"que":"…","args":"…"}`
     * con los campos metidos dentro de `args`, o el `que` a pelo en una cara
     * vieja). Devuelve siempre JSON.
     */
    public String accion(String peticion) {
        try {
            Petición p = Petición.de(peticion);
            if (p == null) {
                return error("no me ha llegado ninguna orden.");
            }
            String que = p.texto("que", "accion", "orden");
            if (que.isEmpty()) {
                return error("no sé qué hacer: falta el «que».");
            }
            // Se normaliza: la cara puede mandar «Volumen» o «linterna ON ».
            que = normaliza(que);
            switch (que) {
                case "volumen":      return volumen(p);
                case "linterna":     return linterna(p);
                case "alarma":       return alarma(p);
                case "temporizador": return temporizador(p);
                case "cronometro":   return cronometro(p);
                case "abrir":        return abrir(p);
                case "app":          return app(p);
                case "lanzadores":   return lanzadores(p);
                case "buscar":       return buscar(p);
                case "estado":       return estado();
                // `poner` viene portada de la línea hermana y está fuera de la
                // tabla del contrato 2.1: la cara no tiene por qué ofrecerla,
                // pero si la manda («pon After dark») responde. No toca el
                // reproductor propio: eso es `CortNative.musicaPoner`.
                case "poner":        return poner(p);
                default:
                    return error("todavía no sé hacer «" + que + "». Sé volumen, linterna, "
                            + "alarma, temporizador, cronómetro, abrir, app, lanzadores, "
                            + "buscar, poner y estado.");
            }
        } catch (Throwable todo) {
            // Nada de esto llega nunca a la cara como excepción.
            Log.e(LOG, "accion falló: " + peticion, todo);
            return error("algo se rompió dentro de CORT al hacer eso.");
        }
    }

    /* ─────────────────────────────── volumen ──────────────────────────────── */

    /**
     * `como`: `sube` `baja` `max` `min` `callar` (y `destapar`), o `nivel:3` para
     * un valor absoluto. Se usa `adjustStreamVolume` con paso antes que escribir
     * un número: el escalón de cada teléfono es distinto y la dueña no tiene por
     * qué perder su volumen de siempre.
     *
     * `MODIFY_AUDIO_SETTINGS` es un permiso normal, pero si no está concedido
     * esto se para y lo dice: media subida a medias es un chasquido en los oídos.
     */
    private String volumen(Petición p) {
        if (!tiene(android.Manifest.permission.MODIFY_AUDIO_SETTINGS)) {
            return error("no tengo permiso para cambiar el sonido: Ajustes ▸ Aplicaciones ▸ "
                    + "CORT ▸ Permisos ▸ «modificar los ajustes de sonido».");
        }
        AudioManager audio = audio();
        if (audio == null) {
            return error("no encontré el control de volumen de este teléfono.");
        }
        int tope = tope(audio);
        int pedido = p.enteroDef(-1, "nivel", "valor", "porcentaje");
        if (pedido >= 0) {
            int nuevo = Math.max(0, Math.min(tope, pedido));
            try {
                audio.setStreamVolume(AudioManager.STREAM_MUSIC, nuevo, AudioManager.FLAG_SHOW_UI);
                return Json.ok().p("nivel", nuevo).p("max", tope).fin();
            } catch (Throwable noDeja) {
                return error("Android no me dejó poner el volumen a " + nuevo + ".");
            }
        }
        String como = normaliza(p.texto("como", "modo", "direccion", "suelto"));
        if (como.isEmpty()) {
            return error("¿el volumen cómo? Puedo subirlo, bajarlo, ponerlo al máximo, "
                    + "al mínimo o callarlo.");
        }
        try {
            if (como.startsWith("callar") || como.startsWith("silenci") || como.equals("mute")
                    || como.equals("off")) {
                // `ADJUST_MUTE` no está permitido en todas las ramas de Android
                // (algunas exigen ser la app de notificaciones): si revienta, se
                // baja a cero, que es lo que la dueña quiere oír.
                try {
                    audio.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_MUTE,
                            AudioManager.FLAG_SHOW_UI);
                } catch (Throwable noDejaMute) {
                    audio.setStreamVolume(AudioManager.STREAM_MUSIC, 0, AudioManager.FLAG_SHOW_UI);
                }
            } else if (como.startsWith("destap") || como.equals("unmute") || como.equals("on")) {
                audio.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_UNMUTE,
                        AudioManager.FLAG_SHOW_UI);
            } else if (como.startsWith("max")) {
                for (int i = 0; i < 40 && nivel(audio) < tope; i++) {
                    audio.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_RAISE, 0);
                }
            } else if (como.startsWith("min")) {
                for (int i = 0; i < 40 && nivel(audio) > 0; i++) {
                    audio.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_LOWER, 0);
                }
            } else if (como.startsWith("sub") || como.startsWith("mas") || como.startsWith("subi")) {
                for (int i = 0; i < PASOS; i++) {
                    audio.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_RAISE,
                            AudioManager.FLAG_SHOW_UI);
                }
            } else if (como.startsWith("baj")) {
                for (int i = 0; i < PASOS; i++) {
                    audio.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_LOWER,
                            AudioManager.FLAG_SHOW_UI);
                }
            } else {
                return error("no conozco ese modo de volumen («" + como + "»).");
            }
            return Json.ok().p("nivel", nivel(audio)).p("max", tope).p("como", como).fin();
        } catch (Throwable raro) {
            Log.e(LOG, "volumen", raro);
            return error("este teléfono no me dejó mover el volumen.");
        }
    }

    /* ─────────────────────────────── linterna ─────────────────────────────── */

    /**
     * `CameraManager.setTorchMode` es API 23: la guarda de `SDK_INT` sobra en un
     * APK con suelo 26, pero se queda escrita porque el suelo se cambió una vez
     * y porque deja claro de qué versión viene cada cosa.
     *
     * No se pide `CAMERA` aquí en tiempo de ejecución: si no está concedida,
     * `ok:false` con el camino a mano y la cara la pide desde su pantalla.
     */
    private String linterna(Petición p) {
        if (Build.VERSION.SDK_INT < 23) {
            return error("este Android (API " + Build.VERSION.SDK_INT + ") no sabe de linternas "
                    + "controlables.");
        }
        if (!tiene(android.Manifest.permission.CAMERA)) {
            return error("la linterna va por el permiso de cámara y no lo tengo: "
                    + "Ajustes ▸ Aplicaciones ▸ CORT ▸ Permisos ▸ Cámara.");
        }
        String como = normaliza(p.texto("como", "modo", "estado", "suelto"));
        boolean encender;
        if (como.isEmpty() || como.equals("alterna") || como.startsWith("altern")) {
            encender = !linternaMandada;
        } else if (como.equals("on") || como.startsWith("enciend") || como.startsWith("prend")
                || como.startsWith("pon")) {
            encender = true;
        } else if (como.equals("off") || como.startsWith("apag")) {
            encender = false;
        } else {
            return error("no entiendo la linterna en ese modo («" + como + "»): vale on, off o "
                    + "alterna.");
        }
        CameraManager camara = camara();
        if (camara == null) {
            return error("este teléfono no tiene linterna controlable.");
        }
        try {
            String[] ids = camara.getCameraIdList();
            if (ids == null || ids.length == 0) {
                return error("no encuentro la cámara que manda la linterna.");
            }
            // La linterna suele colgar de la cámara trasera —la id «0» en casi
            // todos los teléfonos—, pero se recorre la lista entera: un
            // `IllegalArgumentException` significa «esta cámara no tiene flash»
            // y no es un fallo, es la siguiente.
            for (String id : ids) {
                try {
                    camara.setTorchMode(id, encender);
                    linternaMandada = encender;
                    return Json.ok().p("linterna", encender).p("camara", id).fin();
                } catch (IllegalArgumentException noTorch) {
                    /* sin flash en esta cámara: sigue */
                }
            }
            return error("las cámaras de este teléfono no traen linterna.");
        } catch (CameraAccessException noHayAccesso) {
            Log.e(LOG, "linterna", noHayAccesso);
            return error("no pude mirar las cámaras del teléfono.");
        } catch (SecurityException faltaPermiso) {
            return error("Android me negó la linterna pese al permiso de cámara; "
                    + "revisa Ajustes ▸ Aplicaciones ▸ CORT ▸ Permisos.");
        } catch (Throwable raro) {
            Log.e(LOG, "linterna", raro);
            return error("la linterna de este teléfono no se dejó mandar.");
        }
    }

    /* ─────────────────────────── alarma y relojes ─────────────────────────── */

    /**
     * La alarma de CORT: `Alarma.ponerDesde` con la frase entera.
     *
     * Desde F16 no se abre el reloj de otro: se arma la alarma de CORT, que sabe la
     * hora, la canción y la nota. La frase puede venir de tres sitios y los tres
     * tienen que entenderse igual:
     *
     * · de la tabla (`args` = «07:30 con after dark para el examen»), que es la
     *   que ya trae todo pegado;
     * · de la voz o del formulario, con los campos sueltos (`hora`, `cancion`,
     *   `nota`, `rutina`);
     * · de una automatización, que manda `hora` y una nota fija.
     *
     * La hora se compone con «a las» delante para que `Despertar` la lea como una
     * frase normal, pero sólo si `hora` es **sólo** una hora: si ya trae cola, se
     * usa tal cual y no se le pega una segunda nota que la cortaría.
     */
    private String alarma(Petición p) {
        String texto = p.texto("texto", "suelto");
        String hora = p.texto("hora", "a", "cuando");
        String cancion = p.texto("cancion", "musica");
        String nota = p.texto("nota", "mensaje", "etiqueta");
        String rutina = p.texto("rutina");

        String dicho;
        if (!texto.isEmpty()) {
            dicho = texto;
        } else if (!hora.isEmpty()) {
            dicho = hora;
            if (soloHora(hora)) {
                if (!cancion.isEmpty()) dicho += " con " + cancion;
                if (!nota.isEmpty()) dicho += " para " + nota;
            }
        } else {
            return error("no oí la hora. Dime «alarma a las 7:30» o «despiértame a las"
                    + " 7 con after dark para el examen».");
        }
        if ("true".equalsIgnoreCase(rutina) || "si".equalsIgnoreCase(rutina)
                || "sí".equalsIgnoreCase(rutina) || "1".equals(rutina)) {
            dicho += " buenos dias";
        }
        return Alarma.ponerDesde(act, dicho);
    }

    /** «7:30», «a las 7 y media», «7» — y nada más. */
    private static boolean soloHora(String s) {
        return s != null && s.trim().matches(
                "(?i)\\s*(a\\s+las\\s+|a\\s+la\\s+|las\\s+)?\\d{1,2}"
              + "(\\s*[:.h ]\\s*\\d{2})?(\\s+y\\s+(media|cuarto))?\\s*");
    }

    /**
     * `AlarmClock.SET_TIMER`. La longitud es `EXTRA_LENGTH` y son **enteros en
     * segundos, de 1 a 86 400**: `EXTRA_TIME_IN_MILLIS` y `EXTRA_COUNTDOWN` no
     * existen en Android (dos Runs rojos por confiar en la memoria en la línea
     * hermana; la lista verificada está en `simbolos-android.json`).
     */
    private String temporizador(Petición p) {
        String nota = p.texto("nota", "mensaje");
        int segundos = p.enteroDef(-1, "segundos", "seg", "duracion");
        if (segundos < 1) {
            segundos = p.enteroDef(-1, "minutos", "min");
            if (segundos > 0) {
                segundos = segundos * 60;
            }
        }
        if (segundos < 1) {
            String dicho = p.texto("para", "texto", "suelto", "nota");
            segundos = (int) Math.min(86400L, Math.max(0L, duracionAMillis(dicho) / 1000L));
        }
        if (segundos < 1) {
            return error("no oí cuánto tiempo. Di «temporizador de 90 segundos», "
                    + "«de 5 minutos» o «media hora».");
        }
        Intent intento = new Intent(AlarmClock.ACTION_SET_TIMER)
                .putExtra(AlarmClock.EXTRA_LENGTH, Math.min(86400, segundos))
                .putExtra(AlarmClock.EXTRA_MESSAGE, nota.isEmpty() ? "CORT" : nota)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            act.startActivity(intento);
            return Json.ok().p("segundos", Math.min(86400, segundos))
                    .p("nota", nota.isEmpty() ? "CORT" : nota).fin();
        } catch (ActivityNotFoundException noHayReloj) {
            return error("no encontré la app de reloj, así que no pude poner el temporizador.");
        } catch (Throwable raro) {
            Log.e(LOG, "temporizador", raro);
            return error("el reloj no me dejó poner el temporizador.");
        }
    }

    /**
     * El cronómetro, dicho sin adornos: **Android no publica ninguna orden para
     * iniciar o parar un cronómetro**. `docs/CONTRATO-PUENTE-2.1.md` pedía
     * `AlarmClock.SHOW_STOPWATCH` con `EXTRA_SHOW_HOME`, y esas dos constantes
     * **no existen** en `android.provider.AlarmClock` (verificado contra AOSP y
     * contra `simbolos-android.json` de la línea hermana): nombrarlas es un
     * `cannot find symbol` en el runner.
     *
     * Lo que sí existe desde API 29 es `ACTION_SHOW_TIMERS`, que abre la pantalla
     * del reloj donde vive el cronómetro; con eso la dueña llega en un toque y
     * esto lo dice en vez de prometer que ya está contando. Antes de API 29 se
     * cae a los ajustes de fecha y hora, que siempre existen.
     */
    private String cronometro(Petición p) {
        String como = normaliza(p.texto("como", "modo", "accion", "suelto"));
        Intent intento = new Intent();
        intento.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        String donde;
        if (Build.VERSION.SDK_INT >= 29) {
            intento.setAction(AlarmClock.ACTION_SHOW_TIMERS);
            donde = "reloj";
        } else {
            // `ACTION_SHOW_TIMERS` es de API 29 y el suelo del APK es 26: la
            // constante es una cadena que `javac` copia, pero la pantalla no
            // existía, así que se nombra otra cosa.
            intento.setAction(Settings.ACTION_DATE_SETTINGS);
            donde = "ajustes";
        }
        try {
            act.startActivity(intento);
            return Json.ok()
                    .p("muestra", donde)
                    .p("como", como.isEmpty() ? "ensena" : como)
                    .p("dice", "Te enseño la pantalla del reloj: ahí está el cronómetro, "
                            + "pero Android no deja que lo ponga en marcha yo sola.")
                    .fin();
        } catch (ActivityNotFoundException noHayReloj) {
            return error("no encontré la pantalla del reloj de este teléfono.");
        } catch (Throwable raro) {
            Log.e(LOG, "cronometro", raro);
            return error("el reloj no se dejó abrir.");
        }
    }

    /* ──────────────────────────────── abrir ───────────────────────────────── */

    /**
     * La mitad fija del «abre»: los nombres que ella usa de memoria van a un
     * paquete concreto y se comprueba que exista; lo demás se resuelve por las
     * categorías que Android ya expone (navegador, música, ajustes, marcador,
     * red, teclado, avisos). Si nada casa, se intenta por nombre de app (`app()`).
     *
     * `ok:false` honesto cuando la app no está: no se abre «algo que se le
     * parezca» sin decirlo.
     */
    private String abrir(Petición p) {
        String destino = p.texto("a", "destino", "app", "suelto");
        if (destino.isEmpty()) {
            return error("¿abro qué? Dime «abre WhatsApp» o «abre ajustes».");
        }
        String clave = sinSeparadores(normaliza(destino));

        for (String[] fila : PAQUETES) {
            if (!fila[0].equals(clave)) continue;
            String[] paquetes = new String[fila.length - 1];
            System.arraycopy(fila, 1, paquetes, 0, paquetes.length);
            String salida = porPaquetes(destino, paquetes);
            if (salida != null) return salida;
            // No la veo como paquete: a lo mejor el icono se llama distinto.
            String porNombre = app(destino);
            return porNombre != null ? porNombre : salidaNoVisible(destino);
        }

        Intent intento = new Intent();
        intento.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        String que_se_ve;
        switch (clave) {
            case "navegador":
            case "chrome":
            case "internet":
                intento.setAction(Intent.ACTION_MAIN);
                intento.addCategory(Intent.CATEGORY_APP_BROWSER);
                que_se_ve = "el navegador";
                break;
            case "musica":
            case "reproductor":
                intento.setAction(Intent.ACTION_MAIN);
                intento.addCategory(Intent.CATEGORY_APP_MUSIC);
                que_se_ve = "la música";
                break;
            case "ajustes":
            case "configuracion":
                intento.setAction(Settings.ACTION_SETTINGS);
                que_se_ve = "los ajustes";
                break;
            case "telefono":
            case "marcador":
                intento.setAction(Intent.ACTION_DIAL);
                que_se_ve = "el marcador";
                break;
            case "mensajes":
            case "mensajeria":
                // `CATEGORY_APP_MESSAGING` es de API 28 y el suelo es 26: en un
                // 26 o 27 no hay categoría que buscar, así que se dice.
                if (Build.VERSION.SDK_INT < 28) {
                    return error("esta versión de Android no expone la app de mensajes; "
                            + "dime «abre WhatsApp» y la abro por su nombre.");
                }
                intento.setAction(Intent.ACTION_MAIN);
                intento.addCategory(Intent.CATEGORY_APP_MESSAGING);
                que_se_ve = "los mensajes";
                break;
            case "reloj":
                // `ACTION_SHOW_ALARMS` es de API 29: mismo trato que arriba.
                if (Build.VERSION.SDK_INT >= 29) {
                    intento.setAction(AlarmClock.ACTION_SHOW_ALARMS);
                    que_se_ve = "el reloj";
                } else {
                    intento.setAction(Settings.ACTION_DATE_SETTINGS);
                    que_se_ve = "la fecha y la hora";
                }
                break;
            case "wifi":
            case "wi-fi":
            case "red":
                intento.setAction(Settings.ACTION_WIFI_SETTINGS);
                que_se_ve = "la Wi‑Fi";
                break;
            case "bluetooth":
                intento.setAction(Settings.ACTION_BLUETOOTH_SETTINGS);
                que_se_ve = "el Bluetooth";
                break;
            case "teclado":
                intento.setAction(Settings.ACTION_INPUT_METHOD_SETTINGS);
                que_se_ve = "los teclados";
                break;
            case "avisos":
            case "notificaciones":
                // La pantalla donde ella da el oído de `Avisos.java`. Es API 29.
                if (Build.VERSION.SDK_INT >= 29) {
                    intento.setAction(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS);
                    que_se_ve = "el acceso a tus avisos";
                } else {
                    intento.setAction(Settings.ACTION_SETTINGS);
                    que_se_ve = "los ajustes";
                }
                break;
            default:
                // No estaba en ninguna lista: puede ser el nombre de una app.
                String porNombre = app(destino);
                return porNombre != null ? porNombre : error(
                        "No conozco «" + destino + "». Puedo abrir WhatsApp, su Business, "
                        + "YouTube, Maps, Spotify, Gmail, el Calendario, Instagram, Facebook, "
                        + "TikTok, el navegador, la música, los archivos, los ajustes, el "
                        + "marcador, el reloj, la Wi‑Fi, el Bluetooth, el teclado y tus avisos. "
                        + "Y si me dices el nombre exacto de una app instalada, la abro también.");
        }
        try {
            act.startActivity(intento);
            return Json.ok().p("abrio", que_se_ve).p("nombre", que_se_ve).fin();
        } catch (ActivityNotFoundException noHay) {
            return error("Este teléfono no trae una app para " + que_se_ve + ".");
        } catch (Throwable raro) {
            Log.e(LOG, "abrir", raro);
            return error("no pude abrir " + que_se_ve + ".");
        }
    }

    /** `null` si ninguno de los paquetes está (o se ve). */
    private String porPaquetes(String destino, String[] paquetes) {
        PackageManager pm = act.getPackageManager();
        if (pm == null) {
            return error("este teléfono no me deja mirar sus aplicaciones.");
        }
        for (String paquete : paquetes) {
            Intent arranque = pm.getLaunchIntentForPackage(paquete);
            if (arranque == null) continue;
            arranque.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            try {
                act.startActivity(arranque);
                String nombre = etiquetaDe(pm, paquete);
                return Json.ok().p("abrio", paquete)
                        .p("nombre", nombre.isEmpty() ? destino : nombre).fin();
            } catch (ActivityNotFoundException noPuede) {
                return error("Encontré «" + destino + "» pero este teléfono no me deja abrirla.");
            } catch (SecurityException protegida) {
                return error("«" + destino + "» está protegida y no puedo abrirla.");
            } catch (Throwable raro) {
                Log.e(LOG, "abrir " + paquete, raro);
                return error("no pude abrir «" + destino + "».");
            }
        }
        return null;
    }

    private static String salidaNoVisible(String destino) {
        return error("«" + destino + "» no está en este teléfono, o Android no me deja verla. "
                + "Sólo veo los paquetes que el manifiesto declara en `<queries>`; si la app "
                + "existe, pruébalo con el nombre exacto que lees en su icono.");
    }

    /* ─────────────────────── cualquier app, por nombre ────────────────────── */

    /**
     * «Abre Lark player» con el nombre que ella dice, no con una tabla: CORT
     * mira **los lanzadores del teléfono** y arranca el que más se parezca. Es la
     * diferencia entre un menú de ocho categorías y un asistente, y se consigue
     * sin `QUERY_ALL_PACKAGES` —el permiso que Google castiga— gracias al
     * `<queries>` de `MAIN`/`LAUNCHER` del manifiesto.
     *
     * Con `nombre` vacío devuelve `null`: lo usa `abrir()` para no solapar su
     * propio mensaje.
     */
    private String app(String nombre) {
        String buscado = normaliza(nombre);
        if (buscado.isEmpty()) {
            return null;
        }
        PackageManager pm = act.getPackageManager();
        if (pm == null) {
            return error("este teléfono no me deja mirar sus aplicaciones.");
        }
        List<ResolveInfo> vistas = lanzadores();
        if (vistas.isEmpty()) {
            return error("no vi ninguna app en este teléfono. Sin el `<queries>` de "
                    + "`MAIN`/`LAUNCHER` en el manifiesto, Android no deja ver los lanzadores.");
        }
        ResolveInfo mejor = null;
        int puntos = 0;
        for (ResolveInfo vista : vistas) {
            int marcado = parecido(pm, vista, buscado);
            if (marcado > puntos) {
                puntos = marcado;
                mejor = vista;
            }
        }
        if (mejor == null || puntos < MINIMO_PORCENTAJE) {
            return error("No encontré «" + nombre + "» entre las apps de este teléfono. "
                    + "Pruébalo con el nombre exacto que ves en su icono.");
        }
        ActivityInfo quien = mejor.activityInfo;
        Intent arranque = new Intent(Intent.ACTION_MAIN);
        arranque.addCategory(Intent.CATEGORY_LAUNCHER);
        arranque.setClassName(quien.packageName, quien.name);
        arranque.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        String como_se_llama = texto(mejor.loadLabel(pm));
        try {
            act.startActivity(arranque);
            // `parecido` en porcentaje, como promete el contrato: 100 es el
            // nombre exacto del icono y 40 lo mínimo que CORT acepta sin preguntar.
            return Json.ok().p("abrio", quien.packageName)
                    .p("nombre", como_se_llama)
                    .p("componente", quien.name)
                    .p("parecido", puntos).fin();
        } catch (ActivityNotFoundException noPuede) {
            return error("Encontré " + como_se_llama + " pero este teléfono no me deja abrirla.");
        } catch (SecurityException protegida) {
            return error("Encontré " + como_se_llama + ", pero está protegida y no puedo abrirla.");
        } catch (Throwable raro) {
            Log.e(LOG, "app " + nombre, raro);
            return error("No pude abrir " + como_se_llama + ".");
        }
    }

    private String app(Petición p) {
        String nombre = p.texto("nombre", "app", "a", "suelto", "texto");
        if (nombre.isEmpty()) {
            return error("¿qué app? Di «abre Lark player» con el nombre del icono.");
        }
        return app(nombre);
    }

    /**
     * Cuánto se parece una app instalada a lo que la dueña nombró, en porcentaje
     * (la escala vieja de 0 a 5 de la línea hermana, llevada a 0…100 porque el
     * contrato devuelve `parecido:72`). Se compara **normalizado** —minúsculas,
     * sin tildes— porque el habla llega así y los iconos dicen «Música» o
     * «Configuración».
     */
    private static int parecido(PackageManager pm, ResolveInfo vista, String buscado) {
        if (vista == null || vista.activityInfo == null
                || vista.activityInfo.packageName == null || vista.activityInfo.name == null) {
            return 0;
        }
        String etiqueta = normaliza(texto(vista.loadLabel(pm)));
        if (etiqueta.isEmpty()) {
            return 0;
        }
        if (etiqueta.equals(buscado)) return 100;
        if (etiqueta.startsWith(buscado)) return 88;
        if (buscado.startsWith(etiqueta)) return 80;
        if (etiqueta.contains(buscado)) return 72;
        // Muchas apps se llaman distinto en el icono que en su paquete
        // («ajustes» → `com.android.settings`): el paquete rescata los nombres
        // en inglés que la dueña usa de memoria, como «spotify» o «lark».
        String paquete = normaliza(vista.activityInfo.packageName);
        if (paquete.equals(buscado)) return 76;
        if (paquete.contains(buscado)) return 60;
        for (String palabra : etiqueta.split(" ")) {
            if (palabra.length() > 3 && buscado.contains(palabra)) return 55;
        }
        for (String palabra : buscado.split(" ")) {
            if (palabra.length() > 3 && etiqueta.contains(palabra)) return 50;
        }
        return buscado.contains(etiqueta) ? 42 : 0;
    }

    /** Los lanzadores que CORT puede ver, sin sí misma y sin filas rotas. */
    private List<ResolveInfo> lanzadores() {
        List<ResolveInfo> salida = new ArrayList<>();
        PackageManager pm = act.getPackageManager();
        if (pm == null) return salida;
        Intent pregunta = new Intent(Intent.ACTION_MAIN);
        pregunta.addCategory(Intent.CATEGORY_LAUNCHER);
        List<ResolveInfo> vistas;
        try {
            vistas = pm.queryIntentActivities(pregunta, 0);
        } catch (Throwable raro) {
            Log.e(LOG, "queryIntentActivities", raro);
            return salida;
        }
        if (vistas == null) return salida;
        String mia = act.getPackageName();
        for (ResolveInfo vista : vistas) {
            if (vista == null || vista.activityInfo == null
                    || vista.activityInfo.packageName == null || vista.activityInfo.name == null) {
                continue;
            }
            // Abrirse a sí misma no es abrir una app.
            if (vista.activityInfo.packageName.equals(mia)) continue;
            salida.add(vista);
        }
        return salida;
    }

    /** La rejilla: `{"apps":[{"nombre":"…","paquete":"…"}]}`, ordenada por nombre. */
    private String lanzadores(Petición p) {
        int tope = p.enteroDef(TOPE_APPS, "cuantas", "tope", "max");
        if (tope < 1) tope = TOPE_APPS;
        if (tope > 400) tope = 400;
        PackageManager pm = act.getPackageManager();
        List<ResolveInfo> vistas = lanzadores();
        List<String[]> filas = new ArrayList<>();
        for (ResolveInfo vista : vistas) {
            String nombre = texto(vista.loadLabel(pm));
            filas.add(new String[] { nombre, vista.activityInfo.packageName, vista.activityInfo.name });
        }
        Collections.sort(filas, new Comparator<String[]>() {
            @Override public int compare(String[] x, String[] y) {
                return x[0].compareToIgnoreCase(y[0]);
            }
        });
        StringBuilder s = new StringBuilder("[");
        int contados = 0;
        for (String[] fila : filas) {
            if (contados >= tope) break;
            if (contados > 0) s.append(',');
            s.append("{\"nombre\":\"").append(esc(fila[0]))
             .append("\",\"paquete\":\"").append(esc(fila[1]))
             .append("\",\"actividad\":\"").append(esc(fila[2])).append("\"}");
            contados++;
        }
        s.append(']');
        return Json.ok().p("total", filas.size()).crudo("apps", s.toString()).fin();
    }

    /* ──────────────────────────── buscar y poner ──────────────────────────── */

    /**
     * `ACTION_WEB_SEARCH` con el extra `"query"` (el nombre literal que usa
     * `SearchManager.QUERY`: se escribe a mano porque la constante no está en la
     * lista verificada de símbolos). Si el teléfono no trae buscador —un tablet
     * sin Google— se cae a un enlace público, que cualquier navegador sabe abrir.
     */
    private String buscar(Petición p) {
        String texto = p.texto("texto", "q", "consulta", "suelto");
        if (texto.isEmpty()) {
            return error("¿busco qué?");
        }
        Intent intento = new Intent(Intent.ACTION_WEB_SEARCH)
                .putExtra("query", texto)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            act.startActivity(intento);
            return Json.ok().p("busca", texto).p("como", "buscador").fin();
        } catch (ActivityNotFoundException noHayBuscador) {
            Intent enlace = new Intent(Intent.ACTION_VIEW,
                    Uri.parse("https://www.google.com/search?q=" + codifica(texto)))
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            try {
                act.startActivity(enlace);
                return Json.ok().p("busca", texto).p("como", "enlace").fin();
            } catch (Throwable tampocoNavegador) {
                return error("Nada en este teléfono abre una búsqueda: ni buscador ni navegador.");
            }
        } catch (Throwable raro) {
            Log.e(LOG, "buscar", raro);
            return error("no pude lanzar la búsqueda de «" + texto + "».");
        }
    }

    /**
     * Portado de la línea hermana y **fuera de la tabla del contrato 2.1**:
     * «pon After dark» abre la búsqueda de ese tema en internet, que es lo máximo
     * que se puede hacer sin meterse dentro de la app de nadie. No pulsa el play
     * de un tercero ni finge que suena; para la música del teléfono está
     * `Reproductor.java` y `CortNative.musicaPoner`.
     */
    private String poner(Petición p) {
        String obra = p.texto("obra", "cancion", "texto", "suelto");
        if (obra.isEmpty()) {
            return error("¿pongo qué?");
        }
        Intent intento = new Intent(Intent.ACTION_VIEW,
                Uri.parse("https://www.youtube.com/results?search_query=" + codifica(obra)))
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            act.startActivity(intento);
            return Json.ok().p("pone", obra).p("abrio", "youtube").fin();
        } catch (ActivityNotFoundException noHayNavegador) {
            return error("Nada en este teléfono abre un enlace. Dime «busca " + obra + "».");
        } catch (Throwable raro) {
            Log.e(LOG, "poner", raro);
            return error("no pude abrir la búsqueda de «" + obra + "».");
        }
    }

    /* ─────────────────────────────── estado ───────────────────────────────── */

    /**
     * Lo que se puede leer sin ningún permiso de más. `sinMiedo` es la palabra del
     * contrato, que lo deja abierto con `…`: aquí significa **que no falta ninguno
     * de los permisos peligrosos que CORT usa**, y `faltan` los nombra en español
     * para que la cara los liste. `linterna` es lo que CORT mandó, no lo que hace
     * el flash (ver el comentario del campo).
     */
    private String estado() {
        Json j = Json.ok();
        AudioManager audio = audio();
        int tope = audio == null ? 0 : tope(audio);
        j.p("volumen", audio == null ? 0 : Math.max(0, nivel(audio)));
        j.p("max", tope);
        if (audio != null) {
            // `isMusicMute()` NO está en la lista pública del SDK (es de
            // `@SystemApi`, y `javac` la rechaza aunque el teléfono la tenga). Lo
            // que se puede medir con API pública es el nivel: silencio es cero.
            j.p("mudo", Math.max(0, nivel(audio)) == 0);
        }
        j.p("linterna", linternaMandada);
        j.p("superficie", aparece());
        j.p("permisoSonido", tiene(android.Manifest.permission.MODIFY_AUDIO_SETTINGS));
        try {
            j.p("avisos", Avisos.activado(app()));
        } catch (Throwable raro) {
            j.p("avisos", false);
        }
        try {
            j.p("musica", Musica.puedeLeer(app()));
        } catch (Throwable raro) {
            j.p("musica", false);
        }
        j.p("atuendo", Paleta.puesto(app()));
        j.p("juego", juego());
        // La red se puede medir desde la ronda 2.2, cuando el manifiesto declaró
        // `ACCESS_NETWORK_STATE`. Antes se callaba a propósito (`ConnectivityManager`
        // contesta `null` sin ese permiso) y callar seguía siendo mejor que mentir;
        // ahora hay un número de verdad, así que la mentira desaparece.
        try {
            String red = Aparato.de(app()).red(app());
            j.p("red", red.isEmpty() ? "sin conexion" : red);
        } catch (Throwable raro) {
            j.p("red", "sin medir");
        }

        List<String> faltan = new ArrayList<>();
        if (!tiene(android.Manifest.permission.RECORD_AUDIO)) faltan.add("el micrófono");
        if (!tiene(android.Manifest.permission.CAMERA)) faltan.add("la cámara (para la linterna)");
        if (!tiene(android.Manifest.permission.READ_CONTACTS)) faltan.add("los contactos");
        if (!tiene(android.Manifest.permission.CALL_PHONE)) faltan.add("marcar directo");
        if (Build.VERSION.SDK_INT >= 33
                && !tiene("android.permission.POST_NOTIFICATIONS")) {
            faltan.add("que te suenen los avisos");
        }
        j.p("sinMiedo", faltan.isEmpty());
        j.crudo("faltan", array(faltan));
        return j.fin();
    }

    /* ─────────────────────────────── el suelo ─────────────────────────────── */

    private Context app() {
        Context app = act.getApplicationContext();
        return app != null ? app : act;
    }

    private AudioManager audio() {
        try {
            Object servicio = app().getSystemService(Context.AUDIO_SERVICE);
            return servicio instanceof AudioManager ? (AudioManager) servicio : null;
        } catch (Throwable raro) {
            Log.e(LOG, "audio", raro);
            return null;
        }
    }

    /**
     * Lo mismo con la cámara, y por el mismo motivo: el cast directo sobre lo que
     * devuelva un fabricante con un `Context` raro es un `ClassCastException` que
     * subiría hasta `accion`. Aquí se contesta `null` y `linterna` lo dice.
     */
    private CameraManager camara() {
        try {
            Object servicio = app().getSystemService(Context.CAMERA_SERVICE);
            return servicio instanceof CameraManager ? (CameraManager) servicio : null;
        } catch (Throwable raro) {
            Log.e(LOG, "camera", raro);
            return null;
        }
    }

    private int nivel(AudioManager audio) {
        try {
            return audio.getStreamVolume(AudioManager.STREAM_MUSIC);
        } catch (Throwable raro) {
            return -1;
        }
    }

    private int tope(AudioManager audio) {
        try {
            return audio.getStreamMaxVolume(AudioManager.STREAM_MUSIC);
        } catch (Throwable raro) {
            return 0;
        }
    }

    private boolean tiene(String permiso) {
        try {
            return app().checkSelfPermission(permiso) == PackageManager.PERMISSION_GRANTED;
        } catch (Throwable raro) {
            return false;
        }
    }

    private boolean aparece() {
        try {
            return Settings.canDrawOverlays(app());
        } catch (Throwable raro) {
            return false;
        }
    }

    private boolean juego() {
        try {
            SharedPreferences p = app().getSharedPreferences("cort", Context.MODE_PRIVATE);
            return p.getBoolean("juego", false);
        } catch (Throwable raro) {
            return false;
        }
    }

    /** El nombre que ella ve en el icono, o cadena vacía si el sistema lo niega. */
    private static String etiquetaDe(PackageManager pm, String paquete) {
        try {
            ApplicationInfo info = pm.getApplicationInfo(paquete, 0);
            return texto(pm.getApplicationLabel(info));
        } catch (Throwable noSeVe) {
            return "";
        }
    }

    /* ───────────────────────────── parseo puro ────────────────────────────── */

    /** «5 minutos», «30 segundos», «2 horas» → milisegundos; 0 si no se entiende. */
    private static long duracionAMillis(String dicho) {
        Matcher m = DURACION.matcher(dicho == null ? "" : dicho);
        if (!m.find()) {
            return 0L;
        }
        long n = entero(m.group(1));
        String unidad = m.group(2);
        if (unidad.startsWith("h")) return n * 3600000L;
        if (unidad.startsWith("m")) return n * 60000L;
        return n * 1000L;
    }

    private static int entero(String texto) {
        try {
            return Integer.parseInt(texto);
        } catch (NumberFormatException noEs) {
            return 0;
        }
    }

    /**
     * Minúsculas, sin tildes y con la puntuación del habla convertida en espacio:
     * así se compara «¿Abre Lark Player?» con el icono «lark player». Es el mismo
     * criterio que `Cerebro.normaliza`; se repite aquí a propósito para que las
     * manos no dependan del oído: si `Cerebro` cambia o se cae, `accion` sigue
     * contestando.
     */
    private static String normaliza(String texto) {
        if (texto == null) {
            return "";
        }
        String bajo = Normalizer.normalize(texto, Normalizer.Form.NFD)
                .replaceAll("\\p{Mn}+", "").toLowerCase(Locale.ROOT);
        bajo = bajo.replaceAll("[¿?¡!.,;:\"“”'()]", " ");
        return bajo.replaceAll("\\s+", " ").trim();
    }

    /** «whatsapp-business» y «whatsapp business» y «WhatsApp.» son la misma clave. */
    private static String sinSeparadores(String bajo) {
        return bajo.replaceAll("[ ._\\-]", "");
    }

    /** `URLEncoder` con el charset por nombre: la variante de `Charset` es de API 29. */
    private static String codifica(String texto) {
        try {
            return URLEncoder.encode(texto.trim(), "UTF-8");
        } catch (UnsupportedEncodingException nuncaPasa) {
            return texto.trim().replace(" ", "+");
        }
    }

    private static String texto(CharSequence cosa) {
        return cosa == null ? "" : cosa.toString();
    }

    /* ───────────────────────────── JSON a mano ────────────────────────────── */

    private static String error(String dice) {
        return "{\"ok\":false,\"dice\":\"" + esc(dice) + "\"}";
    }

    private static String array(List<String> cosas) {
        StringBuilder s = new StringBuilder("[");
        for (int i = 0; i < cosas.size(); i++) {
            if (i > 0) s.append(',');
            s.append('"').append(esc(cosas.get(i))).append('"');
        }
        return s.append(']').toString();
    }

    /** Escapa lo que la dueña dictó antes de meterlo dentro de un JSON. */
    private static String esc(String texto) {
        if (texto == null) return "";
        StringBuilder s = new StringBuilder(texto.length() + 8);
        for (int i = 0; i < texto.length(); i++) {
            char c = texto.charAt(i);
            if (c == '"' || c == '\\') { s.append('\\').append(c); }
            else if (c == '\n') s.append("\\n");
            else if (c == '\r') s.append(' ');
            else if (c == '\t') s.append(' ');
            else if (c < 0x20) { /* fuera: los controles no viajan a la cara */ }
            else s.append(c);
        }
        return s.toString();
    }

    /** Constructor de la respuesta: `{"ok":true, …}` con comillas escapadas. */
    private static final class Json {
        private final StringBuilder s;

        private Json(boolean ok) {
            s = new StringBuilder("{\"ok\":").append(ok);
        }

        static Json ok() { return new Json(true); }

        Json p(String clave, String valor) {
            s.append(",\"").append(clave).append("\":\"").append(esc(valor)).append('"');
            return this;
        }

        Json p(String clave, int valor) {
            s.append(",\"").append(clave).append("\":").append(valor);
            return this;
        }

        Json p(String clave, boolean valor) {
            s.append(",\"").append(clave).append("\":").append(valor);
            return this;
        }

        /** Para lo que ya es JSON: listas y objetos armados arriba. */
        Json crudo(String clave, String valor) {
            s.append(",\"").append(clave).append("\":").append(valor);
            return this;
        }

        String fin() { return s.append('}').toString(); }
    }

    /**
     * Mini-parser privado de la petición. Acepta las tres formas que admite el
     * contrato: campos sueltos en la raíz (`{"que":"volumen","como":"sube"}`),
     * campos metidos en `args` como objeto, y `args` dicho a pelo
     * (`{"que":"linterna","args":"alterna"}`); y, para una cara vieja, el `que` y
     * su resto escritos sin JSON (`"linterna alterna"`).
     *
     * `org.json` en Android tiene `JSONException` como excepción **comprobada**,
     * así que sólo se construye el objeto con el constructor de texto, cuyo
     * `throws` está documentado, y siempre dentro de `try/catch`. No se crea ningún
     * `JSONObject` vacío: su firma sin argumentos no está en la lista verificada de
     * símbolos y un `unreported exception` cuesta un Run entero.
     */
    private static final class Petición {
        private final JSONObject raiz;     // null cuando la orden venía a pelo
        private final JSONObject args;     // null si no trajo `args` o no era objeto
        private final String que;          // el `que` de la forma vieja
        private final String suelto;       // `args` dicho como palabra suelta

        private Petición(JSONObject raiz, JSONObject args, String que, String suelto) {
            this.raiz = raiz;
            this.args = args;
            this.que = que == null ? "" : que;
            this.suelto = suelto == null ? "" : suelto;
        }

        static Petición de(String texto) {
            if (texto == null || texto.trim().isEmpty()) {
                return null;
            }
            String recio = texto.trim();
            if (!recio.startsWith("{")) {
                // Cara vieja o puente torcido: «linterna alterna».
                int corte = recio.indexOf(' ');
                if (corte < 0) {
                    return new Petición(null, null, recio, "");
                }
                return new Petición(null, null, recio.substring(0, corte),
                        recio.substring(corte + 1).trim());
            }
            try {
                JSONObject raiz = new JSONObject(recio);
                JSONObject args = null;
                String suelto = "";
                Object dentro = raiz.opt("args");
                if (dentro instanceof JSONObject) {
                    args = (JSONObject) dentro;
                } else if (dentro != null) {
                    suelto = dentro.toString().trim();
                    if (suelto.startsWith("{")) {
                        try {
                            args = new JSONObject(suelto);
                            suelto = "";
                        } catch (JSONException pareciaJson) {
                            // Se queda como palabra suelta: `texto(…)` la encontrará.
                        }
                    }
                }
                return new Petición(raiz, args, "", suelto);
            } catch (JSONException noEsJson) {
                return null;    // `accion` lo contesta con `ok:false`
            }
        }

        /** La primera clave que traiga algo; vacío si ninguna. */
        String texto(String... claves) {
            for (String clave : claves) {
                String valor = valor(clave);
                if (valor != null && !valor.trim().isEmpty()) {
                    return valor.trim();
                }
            }
            return "";
        }

        /** La raíz manda sobre `args`: si la cara duplicó un campo, gana el de fuera. */
        private String valor(String clave) {
            if (raiz != null) {
                String v = raiz.optString(clave, "");
                if (v != null && !v.trim().isEmpty()) return v;
            }
            if (args != null) {
                String v = args.optString(clave, "");
                if (v != null && !v.trim().isEmpty()) return v;
            }
            if (clave.equals("que")) return que;
            if (clave.equals("suelto")) return suelto;
            return "";
        }

        int enteroDef(int porDefecto, String... claves) {
            String valor = texto(claves);
            if (valor.isEmpty()) return porDefecto;
            try {
                return (int) Math.round(Double.parseDouble(valor.replace(',', '.')));
            } catch (NumberFormatException noEs) {
                return porDefecto;
            }
        }
    }
}
