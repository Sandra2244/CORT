package com.cort.ia;

/*
 * Las voces de CORT: lista, elección, preajustes tipo Siri/Alexa y descarga de
 * datos de TTS. Contrato: sección 2 de `docs/CONTRATO-PUENTE-2.1.md`
 * (`ajusteVoz`), con `que` = `lista | poner | predefinida | descargar | probar | estado`.
 *
 * Por qué esta clase crea SU PROPIO `TextToSpeech` y no usa el de `CortNative`:
 * el motor de `CortNative` es un campo privado de otra clase y compartirlo
 * obligaría a tocar `CortNative.java`, que está en manos de otra persona ahora
 * mismo. Dos enlaces al mismo motor conviven sin problema (Android permite
 * varias instancias de `TextToSpeech` en un proceso; el motor es del sistema,
 * no de la app), así que el precio es sólo un binder más, no una segunda voz.
 * El de `CortNative` sigue hablando; aquí se mira, se elige y se prueba. La
 * dueña ve el efecto completo porque `poner`/`predefinida` escriben en
 * `SharedPreferences` (`cort` / `voz-velocidad`, `voz-tono`, `voz-nombre`) y
 * `CortNative` puede leerlas al hablar sin que nadie le toque. `suelta()` hace
 * `shutdown()` y hay que llamarla desde `MainActivity` al destruir, igual que
 * el puente; olvidar es dejar un servicio atado a una app muerta.
 *
 * La lógica de qué voz es «mejor» está portada de `Voz.java` de la línea
 * hermana `/home/Sandra/Documentos/CORT-TELEFONO` (mejorVoz,
 * puestoEnPreferidas, paisAmericano): Natural 0, online 20, local 40; más el
 * puesto en la lista de preferidas (o 10 si no está) y un punto si el acento
 * no es CO/MX/US/419. Gana el número más bajo.
 *
 * Honestidades que hay que saber antes de tocar esto:
 *
 * · `getVoices()` es un binder a un motor que escriben fabricantes diversos:
 *   unos devuelven el set vacío, otros revientan. Todo va envuelto en
 *   try/catch y una lista vacía se dice como lista vacía, nunca como error
 *   falso ni como voz inventada.
 * · `descargar` no descarga nada solo: Android no deja instalar datos de voz
 *   desde una app normal, sólo abrir el instalador del sistema
 *   (`INSTALL_TTS_DATA`). Si nadie atiende ese intent, se escribe el camino
 *   manual en `dice` en vez de prometer un botón que no hace nada.
 * · `Voice` NO tiene `isDefault()` (eso lo trae `Voice.Style`, otra clase), así
 *   que la voz por defecto se pide al motor con `TextToSpeech.getDefaultVoice()`
 *   —público desde API 21, y con minSdk 26 cabe— y se compara por nombre. Medir
 *   «por defecto» con una clave inventada habría salido siempre `false`.
 */

import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.ResolveInfo;
import android.os.Bundle;
import android.speech.tts.TextToSpeech;
import android.speech.tts.Voice;
import java.text.Normalizer;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import org.json.JSONObject;

public class VozNueva {

    /* ── baremo portado de `Voz.java` de la línea hermana ─────────────────── */

    /** Las voces en español que suenan mejor, por orden de gusto. */
    private static final String[] PREFERIDAS = {
        "jorge", "gonzalo", "alvaro", "alonso", "tomas", "lorenzo", "raul", "pablo"};
    private static final int PUNTOS_NATURAL = 0, PUNTOS_EN_LINEA = 20, PUNTOS_LOCAL = 40;
    private static final String[] ACENTOS = {"co", "mx", "us", "419"};

    private static final class Ajuste {
        final String nombre;
        final String[] claves;   // palabras en el nombre de la voz (normalizadas)
        final String[] idiomas;  // etiquetas de locale preferidas
        final float velocidad, tono;
        Ajuste(String n, String[] c, String[] i, float v, float t) {
            nombre = n; claves = c; idiomas = i; velocidad = v; tono = t;
        }
    }

    /**
     * Los seis preajustes del contrato. No son voces mágicas que Android no
     * tenga: cada uno busca la voz instalada que más se parezca (por nombre o
     * por acento) y le pone la velocidad y el tono del estilo. Si ninguna se
     * parece, `predefinida` lo dice y sugiere las que sí hay.
     */
    private static final Ajuste[] PRESET = {
        new Ajuste("siri",
                   new String[] {"siri", "female", "mujer", "monica", "lucia", "valentina",
                                 "helena", "marisol", "paulina"},
                   new String[] {"es-us", "es-mx", "es-419", "es"},
                   0.92f, 1.06f),
        new Ajuste("alexa",
                   new String[] {"alexa", "penelope", "samantha", "zira", "female", "mujer"},
                   new String[] {"en-us", "es-us", "es-mx", "es"},
                   1.06f, 0.96f),
        new Ajuste("cortana",
                   new String[] {"cortana", "male", "hombre", "jorge", "diego", "pablo"},
                   new String[] {"es-es", "es-mx", "en-us"},
                   1.0f, 0.92f),
        new Ajuste("espanola",
                   new String[] {"espana", "es-es"},
                   new String[] {"es-es"},
                   1.0f, 1.0f),
        new Ajuste("mexicana",
                   new String[] {"mexico", "mexicana", "es-mx"},
                   new String[] {"es-mx", "es-419"},
                   0.95f, 1.0f),
        new Ajuste("neutra",
                   new String[] {},
                   new String[] {"es"},
                   1.0f, 1.0f),
    };

    private final Context ctx;
    private final SharedPreferences prefs;
    private volatile TextToSpeech boca;
    private volatile boolean bocaLista = false;
    private volatile String avisoInit = "";

    public VozNueva(android.content.Context c) {
        this.ctx = c.getApplicationContext();
        this.prefs = ctx.getSharedPreferences("cort", Context.MODE_PRIVATE);
        try {
            boca = new TextToSpeech(ctx, estado -> {
                if (estado == TextToSpeech.SUCCESS) {
                    eligeIdioma();
                    bocaLista = true;
                } else {
                    avisoInit = "el motor de voz de este teléfono no arrancó";
                }
            });
        } catch (Exception noHayMotorDeVoz) {
            // Un ROM sin servicio de texto-a-voz (algún tablet sin GApps) llega
            // hasta aquí: la clase existe, el motor no, y se dice en cada `que`.
            boca = null;
            avisoInit = "este teléfono no trae motor de voz";
        }
    }

    /** Apaga el enlace propio. `MainActivity` debe llamarla al destruir. */
    public void suelta() {
        bocaLista = false;
        try {
            if (boca != null) boca.shutdown();
        } catch (Exception elMotorYaSeFue) { /* shutdown de un binder muerto */ }
        boca = null;
    }

    /** Para que nadie pregunte por el interior: ¿despertó la boca? */
    public boolean estaLista() { return bocaLista; }

    /* ─────────────────────────── entrada única ─────────────────────────── */

    /**
     * El `ajusteVoz` del contrato: recibe `{"que":"…", …}` (los campos también
     * pueden venir dentro de `args`, como en `accion`) y devuelve el cuadro
     * JSON. Nunca lanza: lo que no se pueda hacer sale como `ok:false` con
     * `dice` explicado.
     */
    public String ajusteVoz(String peticion) {
        try {
            JSONObject j = junto(peticion);
            String que = j.optString("que", "");
            switch (que) {
                case "lista":       return lista();
                case "poner":       return poner(j);
                case "predefinida": return predefinida(j);
                case "descargar":   return descargar();
                case "probar":      return probar(j.optString("texto", ""));
                case "estado":      return estado();
                default:
                    return "{\"ok\":false,\"dice\":\"no conozco ese que de la voz: "
                         + comilla(que) + "\"}";
            }
        } catch (Exception cualquierCosa) {
            // Aquí cae el JSON mal formado de la cara y cualquier sorpresa del
            // binder del TTS. La cara merece un cuadro honesto, no un crash.
            return "{\"ok\":false,\"dice\":\"la voz no respondió: "
                 + comilla(motivo(cualquierCosa)) + "\"}";
        }
    }

    /** Une `args` (objeto o string dentro de string) con los campos sueltos. */
    private static JSONObject junto(String peticion) throws Exception {
        JSONObject j = new JSONObject(peticion == null || peticion.trim().isEmpty() ? "{}" : peticion);
        Object args = j.opt("args");
        if (args != null) {
            JSONObject a = null;
            if (args instanceof JSONObject) a = (JSONObject) args;
            else if (args instanceof String && !((String) args).trim().isEmpty()) {
                try { a = new JSONObject((String) args); } catch (Exception argsSueltos) { a = null; }
            }
            if (a != null) {
                java.util.Iterator<String> ks = a.keys();
                while (ks.hasNext()) {
                    String k = ks.next();
                    if (!j.has(k) || k.equals("args")) {
                        if (!k.equals("args")) j.put(k, a.get(k));
                    }
                }
            }
        }
        return j;
    }

    /* ─────────────────────────────── lista ─────────────────────────────── */

    /**
     * `{"voces":[{nombre,idioma,porDefecto}],"vozActual","velocidad","tono",
     * "faltanVoces"}`. Orden: los `es_*` primero y, dentro del idioma, por el
     * baremo portado (natural gana a online, y online a local); el empate se
     * rompe por latencia, que es lo único objetivo que `Voice` ofrece.
     */
    @SuppressWarnings("deprecation")
    private String lista() {
        List<Voice> vacias = new ArrayList<>();
        Set<Voice> disponibles = null;
        try {
            disponibles = boca == null ? null : boca.getVoices();
        } catch (Exception elMotorRevienta) {
            disponibles = null; // muchos motores devuelven vacío o revientan: mismo trato
        }
        if (disponibles != null) vacias.addAll(disponibles);
        Collections.sort(vacias, new Comparator<Voice>() {
            @Override public int compare(Voice a, Voice b) {
                float pa = pesoEspanol(a), pb = pesoEspanol(b);
                int r = pa < pb ? -1 : (pa > pb ? 1 : 0); // Math.signum da double: nada de asignarlo entero
                if (r != 0) return r;
                r = Integer.compare(puntos(a), puntos(b));
                if (r != 0) return r;
                return Integer.compare(latencia(a), latencia(b));
            }
        });
        StringBuilder v = new StringBuilder("[");
        Voice actual = null;
        try { actual = boca == null ? null : boca.getVoice(); }
        catch (Exception elMotorNoDice) { actual = null; }
        // `Voice` no tiene `isDefault()` (eso lo trae `Voice.Style`): la voz por
        // defecto se pide al motor con `TextToSpeech.getDefaultVoice()`, y se
        // compara por nombre porque son objetos distintos en cada consulta.
        String nombrePorDefecto = null;
        try {
            Voice predilecta = boca == null ? null : boca.getDefaultVoice();
            nombrePorDefecto = predilecta == null ? null : predilecta.getName();
        } catch (Exception elMotorNoDice2) { nombrePorDefecto = null; }
        boolean primero = true;
        for (Voice voz : vacias) {
            if (!primero) v.append(',');
            primero = false;
            Locale l = voz.getLocale();
            boolean porDefecto;
            try {
                porDefecto = (nombrePorDefecto != null && nombrePorDefecto.equals(voz.getName()))
                    || (actual != null && actual.getName().equals(voz.getName()));
            } catch (Exception sinCriterio) {
                porDefecto = false;
            }
            v.append("{\"nombre\":").append(comilla(voz.getName()))
             .append(",\"idioma\":").append(comilla(l == null ? "" : l.toLanguageTag()))
             .append(",\"porDefecto\":").append(porDefecto)
             .append('}');
        }
        return "{\"ok\":true,\"voces\":" + v.append(']').toString()
             + ",\"vozActual\":" + comilla(actual == null ? "" : actual.getName())
             + ",\"velocidad\":" + guardada("voz-velocidad", 1.0f)
             + ",\"tono\":" + guardada("voz-tono", 1.0f)
             + ",\"faltanVoces\":" + faltanVoces() + "}";
    }

    private double guardada(String clave, float porDefecto) {
        try { return redondeado(prefs.getFloat(clave, porDefecto)); }
        catch (Exception prefsRaras) { return porDefecto; }
    }

    /**
     * Un `float` guardado y leído como `double` sale con ruido de binario
     * (0.92 → 0.9200000167). La cara pinta estos números: se redondean a dos
     * decimales antes de escribirlos en el cuadro.
     */
    private static double redondeado(double x) {
        return Math.round(x * 100.0) / 100.0;
    }

    /**
     * `faltanVoces`: si el español sale con `LANG_MISSING_DATA` es que al motor
     * le faltan los datos (el caso típico de un ROM pelado). Se pregunta, no se
     * cambia el idioma: cambiarlo desde aquí pisaría lo que `CortNative` está
     * hablando en este momento.
     */
    private boolean faltanVoces() {
        try {
            if (boca == null) return true;
            int r = boca.isLanguageAvailable(new Locale("es", "MX"));
            if (r == TextToSpeech.LANG_MISSING_DATA) return true;
            return esVacio();
        } catch (Exception elMotorNoContesta) {
            return esVacio();
        }
    }

    private boolean esVacio() {
        try {
            Set<Voice> d = boca == null ? null : boca.getVoices();
            if (d == null || d.isEmpty()) return true;
            for (Voice v : d) {
                Locale l = v.getLocale();
                if (l != null && "es".equalsIgnoreCase(l.getLanguage())) return false;
            }
            return true;
        } catch (Exception sinLista) {
            return true;
        }
    }

    /* ─────────────────────────────── poner ──────────────────────────────── */

    /**
     * Nombre + velocidad (0,5–2,0) + tono (0,5–2,0). Fuera de rango se
     * rechaza con `dice` dicho (el contrato fija el rango, y un 3,0 de
     * velocidad haría a CORT ininteligible). Se aplica a esta boca y se
     * guarda en `cort` / `voz-nombre`, `voz-velocidad`, `voz-tono` para que
     * `CortNative` la lea al hablar.
     */
    private String poner(JSONObject j) {
        if (!bocaLista) return sinBoca();
        double vel = j.optDouble("velocidad", Double.NaN);
        double tono = j.optDouble("tono", Double.NaN);
        if (!Double.isNaN(vel) && (vel < 0.5 || vel > 2.0)) {
            return "{\"ok\":false,\"dice\":\"la velocidad ha de estar entre 0,5 y 2,0"
                 + " (llegó " + vel + ")\"}";
        }
        if (!Double.isNaN(tono) && (tono < 0.5 || tono > 2.0)) {
            return "{\"ok\":false,\"dice\":\"el tono ha de estar entre 0,5 y 2,0"
                 + " (llegó " + tono + ")\"}";
        }
        String nombre = j.optString("nombre", "");
        Voice elegida = null;
        if (!nombre.isEmpty()) {
            try {
                Set<Voice> d = boca.getVoices();
                if (d != null) {
                    for (Voice v : d) {
                        if (nombre.equals(v.getName())) { elegida = v; break; }
                    }
                }
            } catch (Exception elMotorNoLista) { elegida = null; }
            if (elegida == null) {
                return "{\"ok\":false,\"dice\":\"no hay ninguna voz instalada que se llame "
                     + comilla(nombre) + "\",\"sugerencia\":" + nombres() + "}";
            }
        }
        try {
            if (elegida != null) boca.setVoice(elegida);
            double velF = Double.isNaN(vel) ? prefs.getFloat("voz-velocidad", 1.0f) : vel;
            double tonoF = Double.isNaN(tono) ? prefs.getFloat("voz-tono", 1.0f) : tono;
            boca.setSpeechRate((float) velF);
            boca.setPitch((float) tonoF);
            SharedPreferences.Editor e = prefs.edit();
            e.putFloat("voz-velocidad", (float) velF);
            e.putFloat("voz-tono", (float) tonoF);
            if (!nombre.isEmpty()) e.putString("voz-nombre", nombre);
            e.apply();
            return "{\"ok\":true,\"nombre\":" + comilla(nombre.isEmpty()
                       ? prefs.getString("voz-nombre", "") : nombre)
                 + ",\"velocidad\":" + redondeado(velF) + ",\"tono\":" + redondeado(tonoF) + "}";
        } catch (Exception elMotorNoAplica) {
            return "{\"ok\":false,\"dice\":\"el motor de voz no aplicó el cambio: "
                 + comilla(motivo(elMotorNoAplica)) + "\"}";
        }
    }

    /* ──────────────────────────── predefinida ───────────────────────────── */

    /**
     * Siri / Alexa / Cortana / española / mexicana / neutra, pero no como
     * promesa de una voz que Android no tiene: se busca la instalada que más
     * se parezca (nombre o acento) y se le pone la velocidad y el tono del
     * estilo. La puntuación es la portada de `Voz.java`. Si nada se parece →
     * `ok:false` con `dice` honesto y `sugerencia` con las voces que sí hay.
     */
    private String predefinida(JSONObject j) {
        if (!bocaLista) return sinBoca();
        String estilo = sinAcentos(j.optString("nombre", "")).toLowerCase(Locale.US);
        if (estilo.equals("espanola") || estilo.equals("española")) estilo = "espanola";
        Ajuste preset = null;
        for (Ajuste a : PRESET) if (a.nombre.equals(estilo)) { preset = a; break; }
        if (preset == null) {
            return "{\"ok\":false,\"dice\":" + comilla("no conozco el estilo \"" + estilo
                 + "\"; valen siri, alexa, cortana, española, mexicana y neutra") + "}";
        }
        List<Voice> candidatas = new ArrayList<>();
        try {
            Set<Voice> d = boca.getVoices();
            if (d != null) {
                for (Voice v : d) {
                    if (encaja(v, preset)) candidatas.add(v);
                }
            }
        } catch (Exception elMotorNoLista) { candidatas.clear(); }
        if (candidatas.isEmpty()) {
            return "{\"ok\":false,\"dice\":\"no tengo ninguna voz instalada que se"
                 + " parezca a " + comilla(preset.nombre) + "\""
                 + ",\"sugerencia\":" + nombres() + "}";
        }
        Voice mejor = null;
        int mejorPuntos = Integer.MAX_VALUE;
        int mejorDist = Integer.MAX_VALUE;
        for (Voice v : candidatas) {
            int p = puntos(v) + distancia(v, preset);
            int d = idiomaPuntado(v, preset) == 0 ? 0 : 2;
            if (p < mejorPuntos || (p == mejorPuntos && d < mejorDist)) {
                mejorPuntos = p; mejorDist = d; mejor = v;
            }
        }
        if (mejor == null) {
            return "{\"ok\":false,\"dice\":\"no tengo ninguna voz instalada que se"
                 + " parezca a " + comilla(preset.nombre) + "\""
                 + ",\"sugerencia\":" + nombres() + "}";
        }
        try {
            boca.setVoice(mejor);
            boca.setSpeechRate(mejorVelocidad(mejor, preset));
            boca.setPitch(preset.tono);
            float vel = (float) mejorVelocidad(mejor, preset);
            prefs.edit().putString("voz-nombre", mejor.getName())
                      .putFloat("voz-velocidad", vel)
                      .putFloat("voz-tono", preset.tono).apply();
            Locale l = mejor.getLocale();
            return "{\"ok\":true,\"usada\":" + comilla(mejor.getName())
                 + ",\"idioma\":" + comilla(l == null ? "" : l.toLanguageTag())
                 + ",\"velocidad\":" + redondeado(vel) + ",\"tono\":" + redondeado(preset.tono)
                 + ",\"porQue\":" + comilla(razon(mejor, preset)) + "}";
        } catch (Exception elMotorNoAplica) {
            return "{\"ok\":false,\"dice\":\"el motor no aplicó la voz del estilo: "
                 + comilla(motivo(elMotorNoAplica)) + "\"}";
        }
    }

    /** Candidata si el nombre suena al estilo o si el acento es de los preferidos. */
    private static boolean encaja(Voice v, Ajuste a) {
        String nombre = sinAcentos(v.getName() == null ? "" : v.getName()).toLowerCase(Locale.US);
        for (String c : a.claves) if (nombre.contains(c)) return true;
        if (a.claves.length == 0 && "neutra".equals(a.nombre)
                && v.getLocale() != null && "es".equalsIgnoreCase(v.getLocale().getLanguage())) {
            return true; // neutra: vale cualquier español
        }
        return idiomaPuntado(v, a) >= 0;
    }

    /** 0 si el idioma coincide exacto, 1 si es del mismo idioma, -1 si no pega. */
    private static int idiomaPuntado(Voice v, Ajuste a) {
        Locale l = v.getLocale();
        if (l == null) return -1;
        String tag = l.toLanguageTag().toLowerCase(Locale.US);
        int mejor = -1;
        for (int n = 0; n < a.idiomas.length; n++) {
            String id = a.idiomas[n];
            if (tag.equals(id)) return 0;
            if (id.equals("es") && tag.startsWith("es-")) {
                if (mejor < 0 || n < mejor) mejor = 1;
            }
        }
        return mejor;
    }

    private static int distancia(Voice v, Ajuste a) {
        int p = idiomaPuntado(v, a);
        return p == 0 ? 0 : (p == 1 ? 2 : 4);
    }

    /** La velocidad del estilo, rebajada un pelo si la candidata no es del acento exacto. */
    private static float mejorVelocidad(Voice v, Ajuste a) {
        // La voz base del estilo manda; si la candidata es la del sistema en
        // español neutro no hay nada que corregir, y si es una voz online con
        // acento distinto se rebaja un pelo la velocidad para que no atropelle.
        return idiomaPuntado(v, a) == 0 ? a.velocidad : a.velocidad - 0.03f;
    }

    private static String razon(Voice v, Ajuste a) {
        Locale l = v.getLocale();
        String tag = l == null ? "su idioma" : l.toLanguageTag();
        String nombre = sinAcentos(v.getName() == null ? "" : v.getName()).toLowerCase(Locale.US);
        String base = "«" + v.getName() + "\" suena a " + a.nombre + " (idioma " + tag;
        if (nombre.contains("natural")) return base + ", es natural)";
        if (!v.isNetworkConnectionRequired()) return base + ", es local y no necesita red)";
        return base + ", está en el motor del sistema)";
    }

    /* ───────────────────────────── descargar ─────────────────────────────── */

    /**
     * Abre el instalador de datos de TTS de Android. CORT no puede descargar
     * las voces por su cuenta (Android no lo permite a una app normal); lo que
     * sí puede es llevar a la dueña al sitio, y si el fabricante ni siquiera
     * atiende el intent, escribir el camino manual en `dice`.
     */
    private String descargar() {
        Intent i = new Intent("com.android.intent.action.INSTALL_TTS_DATA");
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            ResolveInfo quien = ctx.getPackageManager().resolveActivity(i, 0);
            if (quien == null) return sinInstalador();
            ctx.startActivity(i);
            return "{\"ok\":true,\"abre\":\"ajustes\",\"dice\":"
                 + comilla("Ahí puedes descargar las voces y los idiomas del motor de TTS") + "}";
        } catch (ActivityNotFoundException nadie) {
            return sinInstalador();
        } catch (Exception cualquierCosa) {
            return sinInstalador();
        }
    }

    private static String sinInstalador() {
        return "{\"ok\":false,\"dice\":\"este teléfono no atiende el instalador de voces"
             + " de TTS; el camino manual es Ajustes > Sistema > Idiomas > Voz de salida\","
             + "\"abre\":\"ninguno\"}";
    }

    /* ──────────────────────────────── probar ─────────────────────────────── */

    /** La muestra, en voz alta, con la voz y el ajuste que estén puestos ahora. */
    private String probar(String j) {
        if (!bocaLista) return sinBoca();
        String texto = j == null ? "" : j;
        if (texto.trim().isEmpty()) {
            texto = "Hola, soy CORT. Así sueno con esta voz, a esta velocidad y con este tono.";
        }
        try {
            boca.stop();
            boca.speak(texto, TextToSpeech.QUEUE_FLUSH, new Bundle(), "cort-prueba-voz");
            return "{\"ok\":true,\"dice\":\"te lo digo en voz alta\"}";
        } catch (Exception elMotorNoHabla) {
            return "{\"ok\":false,\"dice\":\"el motor no quiso hablar: "
                 + comilla(motivo(elMotorNoHabla)) + "\"}";
        }
    }

    /* ──────────────────────────────── estado ─────────────────────────────── */

    /**
     * `{"listo","motor","idioma"}`. `getDefaultEngine()` existe desde API 1 y
     * `getVoices()` desde 21, así que con minSdk 26 se usan directos; aun así
     * todo va envuelto porque el binder puede no contestar.
     */
    @SuppressWarnings("deprecation")
    private String estado() {
        String motor = "";
        String idioma = "";
        try {
            if (boca != null) motor = boca.getDefaultEngine();
        } catch (Exception elMotorNoDice) { motor = ""; }
        try {
            if (bocaLista && boca != null && boca.getLanguage() != null) {
                idioma = boca.getLanguage().toLanguageTag();
            }
        } catch (Exception elMotorNoIdioma) { idioma = ""; }
        return "{\"ok\":true,\"listo\":" + bocaLista
             + ",\"motor\":" + comilla(motor)
             + ",\"idioma\":" + comilla(idioma)
             + (bocaLista ? "" : ",\"dice\":" + comilla(avisoInit.isEmpty()
                    ? "la boca todavía no despertó; reintenta en un momento" : avisoInit))
             + "}";
    }

    private String sinBoca() {
        return "{\"ok\":false,\"dice\":" + comilla(avisoInit.isEmpty()
               ? "la boca todavía no despertó; reintenta en un momento" : avisoInit) + "}";
    }

    /* ─────────────────────── el baremo portado de Voz.java ────────────────── */

    private static float pesoEspanol(Voice v) {
        Locale l = v.getLocale();
        return (l != null && "es".equalsIgnoreCase(l.getLanguage())) ? 0f : 1f;
    }

    private static int latencia(Voice v) {
        try { return v.getLatency(); }      // API 21: milisegundos; menor = más rápido
        catch (Exception sinMedida) { return Integer.MAX_VALUE; }
    }

    /** El mismo baremo que `Voz.java`: gana el número más bajo. */
    private static int puntos(Voice voz) {
        String nombre = sinAcentos(voz.getName() == null ? "" : voz.getName())
                            .toLowerCase(Locale.US);
        int puntos = voz.isNetworkConnectionRequired() ? PUNTOS_EN_LINEA : PUNTOS_LOCAL;
        if (nombre.contains("natural")) puntos = PUNTOS_NATURAL;
        int puesto = puestoEnPreferidas(nombre);
        puntos += puesto >= 0 ? puesto : 10;
        Locale sitio = voz.getLocale();
        if (sitio != null && !paisAmericano(sitio)) puntos += 1;
        return puntos;
    }

    static int puestoEnPreferidas(String nombreEnMinusculas) {
        for (int i = 0; i < PREFERIDAS.length; i++) {
            if (nombreEnMinusculas.contains(PREFERIDAS[i])) return i;
        }
        return -1;
    }

    static boolean paisAmericano(Locale sitio) {
        String pais = sitio.getCountry() == null ? "" : sitio.getCountry().toLowerCase(Locale.US);
        if (pais.isEmpty() && sitio.getVariant() != null) {
            pais = sitio.getVariant().toLowerCase(Locale.US);
        }
        for (String candidato : ACENTOS) {
            if (pais.equals(candidato)) return true;
        }
        return "419".equals(sitio.getVariant());
    }

    /** Quita tildes para comparar nombres sin depender del teclado del fabricante. */
    private static String sinAcentos(String s) {
        try {
            return Normalizer.normalize(s, Normalizer.Form.NFD).replaceAll("\\p{M}+", "");
        } catch (Exception normalizadorRaro) {
            return s;
        }
    }

    private static String motivo(Exception e) {
        String m = e.getMessage();
        return (m == null || m.trim().isEmpty()) ? e.getClass().getSimpleName() : m;
    }

    /** Las voces instaladas por nombre, para la `sugerencia` del contrato. */
    private String nombres() {
        StringBuilder s = new StringBuilder("[");
        try {
            Set<Voice> d = boca == null ? null : boca.getVoices();
            if (d != null) {
                boolean primero = true;
                for (Voice v : d) {
                    if (!primero) s.append(',');
                    primero = false;
                    s.append(comilla(v.getName()));
                }
            }
        } catch (Exception sinLista) { /* array vacío: es lo que hay */ }
        return s.append(']').toString();
    }

    /* ──────────────────────────── idioma inicial ──────────────────────────── */

    /** Como en `Voz.java`: se prueban variantes hasta que una esté instalada. */
    private void eligeIdioma() {
        if (boca == null) return;
        for (String variante : new String[] {"es-MX", "es-US", "es-419", "es-ES", "es"}) {
            int r = boca.setLanguage(Locale.forLanguageTag(variante));
            if (r != TextToSpeech.LANG_MISSING_DATA && r != TextToSpeech.LANG_NOT_SUPPORTED) {
                return;
            }
        }
        avisoInit = "este teléfono no tiene español instalado en su motor de voz";
    }

    /* ──────────────────────────── JSON a mano ───────────────────────────── */

    /** El mismo patrón que `CortNative.comilla`: cuerdas escapadas a mano. */
    private static String comilla(String s) {
        if (s == null) return "null";
        StringBuilder out = new StringBuilder("\"");
        for (int n = 0; n < s.length(); n++) {
            char c = s.charAt(n);
            switch (c) {
                case '"':  out.append("\\\""); break;
                case '\\': out.append("\\\\"); break;
                case '\n': out.append("\\n");  break;
                case '\r': out.append("\\r");  break;
                case '\t': out.append("\\t");  break;
                default:
                    if (c < 0x20) out.append(String.format("\\u%04x", (int) c));
                    else out.append(c);
            }
        }
        return out.append('"').toString();
    }
}
