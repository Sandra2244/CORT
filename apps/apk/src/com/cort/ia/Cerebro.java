package com.cort.ia;

/*
 * El oído de CORT dentro del teléfono: sin red, sin coste. Lee una tabla de
 * frases, normaliza lo que dijo la dueña y devuelve la intención que casó. **No
 * ejecuta nada** y no sabe hablar: sólo empareja. `Mente` decide después si el
 * mandato se nombra para la cara o se manda a la nube.
 *
 * Porte de `dev.sandra.cort.Cerebro`, adaptado al contrato 2.1: la `accion` que
 * sale de aquí usa el vocabulario EXACTO del puente de la cara — `volumen`,
 * `linterna`, `alarma`, `temporizador`, `abrir`, `poner`, `llamar`, `buscar`,
 * `musica`, `avisos`, `juego`, `memoria`, `saludo` y `desconocido`. Una frase que
 * no casa devuelve `desconocido` con `respuesta=null`, y entonces es `Mente` (no
 * esta clase) quien pregunta a la nube.
 *
 * De dónde sale la tabla: primero se intenta `assets/habilidades.json` (viaja
 * dentro del APK, hermano de `ui/` y NO lo borra `compilar.sh`, que sólo limpia
 * `assets/ui`); si el asset no está o viene roto, se usa la **tabla escrita en
 * el código**. Las dos son LA MISMA tabla, vertida de una única lista
 * (`scripts/habilidades.py`) y vigilada por `scripts/prueba-costura.py`: si el
 * asset falta no puede haber un fallo silencioso que deje a CORT mudo, y si las
 * dos se separaran, la dueña oiría frases distintas según cómo cargó el APK.
 *
 * Lo que a propósito NO está en ninguna de las dos: la hora, el día, las cuentas,
 * los porcentajes y los cambios de unidad. Esos los resuelve `Razon` (puro Java,
 * sin red), y una regla suya aquí delante le robaría la frase devolviendo una
 * respuesta de adorno — así estaban «qué hora es» hasta la ronda 2.2.
 *
 * El `Nube` del constructor se guarda pero no se usa para hacer red aquí: el
 * parser es offline por diseño. Se consulta sólo para saber si la nube está
 * lista (`nubeLista`), que es lo que `Mente` mira antes de disparar el hilo.
 */

import android.content.Context;
import android.util.Log;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.text.Normalizer;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Pattern;
import org.json.JSONArray;
import org.json.JSONObject;

public class Cerebro {

    /** El vocabulario cerrado de acciones que entiende la cara. Nada fuera entra. */
    private static final Set<String> ACCIONES = new HashSet<>(Arrays.asList(
        "volumen", "linterna", "alarma", "temporizador", "abrir", "poner", "llamar",
        "buscar", "musica", "avisos", "juego", "memoria", "saludo", "desconocido"));

    /** Una regla casada: qué acción es, con qué parámetro y con qué decir. */
    public static class Resultado {
        public String accion;
        public String param;
        public String respuesta;

        public Resultado(String accion, String param, String respuesta) {
            this.accion = accion;
            this.param = param;
            this.respuesta = respuesta;
        }

        @Override public String toString() {
            return accion + "|" + (param == null ? "" : param);
        }
    }

    private static final class Regla {
        final String accion;
        final String param;         // para reglas sin {resto}
        final String respuesta;
        final List<String> patrones;
        Regla(String accion, String param, String respuesta, List<String> patrones) {
            this.accion = accion; this.param = param;
            this.respuesta = respuesta; this.patrones = patrones;
        }
    }

    private final List<Regla> reglas = new ArrayList<>();
    private final Nube nube;
    private String avisoDeCarga = "";

    public Cerebro(Context contexto, Nube nube) {
        this.nube = nube;
        cargar(contexto);
    }

    /** La nube está lista para que `Mente` la use (esta clase nunca la llama). */
    public boolean nubeLista() {
        return nube != null && nube.configurada();
    }

    /** Lo que salió leyendo la tabla, para que la cara lo diga en vez de callarse. */
    public String avisoDeCarga() {
        return avisoDeCarga;
    }

    /* ───────────────────────────── carga ────────────────────────── */

    private void cargar(Context contexto) {
        boolean leida = false;
        try (InputStream entrada = contexto.getAssets().open("habilidades.json")) {
            String crudo = new String(todo(entrada), StandardCharsets.UTF_8);
            leida = desdeJson(crudo);
            if (!leida) avisoDeCarga = "la tabla del asset no trae patrones válidos";
        } catch (IOException noHayAsset) {
            avisoDeCarga = "no había asset de frases: uso la tabla del código";
        } catch (Exception cualquierCosa) {
            avisoDeCarga = "no pude leer la tabla (" + cualquierCosa.getMessage() + ")";
        }
        if (!leida || reglas.isEmpty()) {
            reglas.clear();
            tablaDelCodigo();          // nunca nos quedamos sin oído
        }
    }

    private boolean desdeJson(String crudo) {
        try {
            JSONObject tabla = new JSONObject(crudo);
            JSONArray lista = tabla.optJSONArray("patrones");
            if (lista == null || lista.length() == 0) return false;
            for (int i = 0; i < lista.length(); i++) {
                JSONObject regla = lista.getJSONObject(i);
                String accion = normaliza(regla.optString("accion", ""));
                if (!ACCIONES.contains(accion)) continue;   // fuera de vocabulario, se ignora
                List<String> patrones = new ArrayList<>();
                JSONArray ps = regla.optJSONArray("patrones");
                for (int j = 0; ps != null && j < ps.length(); j++) {
                    patrones.add(normaliza(ps.getString(j)));
                }
                if (patrones.isEmpty()) continue;
                reglas.add(new Regla(accion, normaliza(regla.optString("param", "")),
                        regla.optString("respuesta", ""), patrones));
            }
            return !reglas.isEmpty();
        } catch (Exception roto) {
            Log.w("cort", "cerebro-tabla", roto);
            return false;
        }
    }

    private static byte[] todo(InputStream in) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] trozo = new byte[8192];
        int n;
        while ((n = in.read(trozo)) > 0) out.write(trozo, 0, n);
        return out.toByteArray();
    }

    /* ─────────────────────── la tabla, en el código ─────────────── */

    private static Regla r(String accion, String param, String resp, String... patrones) {
        List<String> normales = new ArrayList<>();
        for (String p : patrones) normales.add(normaliza(p));
        return new Regla(accion, param, resp, normales);
    }

    /**
     * Orden = prioridad. Las exactas van antes de las de prefijo `{resto}`; y las
     * de prefijo cortas (`pon la linterna`) antes de las generales (`pon {resto}`),
     * para que una no le robe la frase a la otra.
     *
     * ESTO NO SE ESCRIBE A MANO: sale de `scripts/habilidades.py`, la misma lista
     * que genera `assets/habilidades.json`. Cambiar una frase en un sitio y no en
     * el otro es el tipo de fallo que sólo se ve en la boca del teléfono.
     */
    private void tablaDelCodigo() {
        reglas.add(r("volumen", "sube", "Subo el volumen.",
             "sube el volumen", "subir el volumen", "sube volumen", "subele el volumen",
             "sube un poco el volumen", "mas volumen", "mas fuerte", "mas alto",
             "sube el sonido", "sube la musica", "volumen mas alto", "pon el volumen mas alto"));
        reglas.add(r("volumen", "baja", "Lo bajo.",
             "baja el volumen", "bajar el volumen", "baja volumen", "bajale el volumen",
             "baja un poco el volumen", "menos volumen", "mas bajo", "mas suave",
             "baja el sonido", "baja la musica", "volumen mas bajo", "dejalo mas bajo"));
        reglas.add(r("volumen", "max", "Volumen al máximo.",
             "volumen al maximo", "sube todo el volumen", "ponlo al maximo", "sube al maximo",
             "volumen al tope", "al maximo el volumen", "sube el volumen al maximo",
             "pon el volumen al maximo", "pon el volumen al tope"));
        reglas.add(r("volumen", "min", "Volumen al mínimo.",
             "volumen al minimo", "baja todo el volumen", "baja al minimo",
             "al minimo el volumen", "pon el volumen al minimo", "pon el volumen bajito"));
        reglas.add(r("volumen", "callar", "Silencio. Sigo escuchando.",
             "silencio", "pon silencio", "callate", "calla", "sin sonido", "mudo",
             "quita el sonido", "apaga el sonido", "sin ruido", "calla la musica", "mute",
             "ponlo en mudo", "en mudo"));
        reglas.add(r("linterna", "on", "Alumbro.",
             "enciende la linterna", "prende la linterna", "pon la linterna", "dame luz",
             "enciende linterna", "necesito luz", "linterna encendida", "alumbrame",
             "prendele la linterna", "ponme luz"));
        reglas.add(r("linterna", "off", "Apago la luz.",
             "apaga la linterna", "apagar la linterna", "quita la linterna", "apaga luz",
             "linterna off", "apaga la luz", "linterna apagada", "ya no alumbres",
             "apaga el foco"));
        reglas.add(r("linterna", "alterna", "Cambio la linterna.",
             "linterna", "la linterna", "linterna por favor"));
        reglas.add(r("juego", "on", "Modo juego: me hago pequeña para no estorbarte.",
             "modo juego", "activa el modo juego", "activa modo juego", "pon el modo juego",
             "voy a jugar", "me pongo a jugar", "estoy jugando", "activar modo juego",
             "modo gamer", "no me interrumpas mientras juego"));
        reglas.add(r("juego", "off", "Vuelvo a por el oído.",
             "sal del modo juego", "desactiva el modo juego", "desactiva modo juego",
             "quita el modo juego", "modo juego off", "ya termine de jugar", "vuelve cort",
             "desactivar modo juego", "sal de modo juego"));
        reglas.add(r("avisos", "avisos", "Te los cuento.",
             "lee mis avisos", "leer mis avisos", "leeme los avisos", "que me llego",
             "ultimos avisos", "mis notificaciones", "lee mis notificaciones",
             "hay avisos nuevos", "avisos", "mirame los avisos", "que me escribieron",
             "hay mensajes nuevos", "leeme whatsapp", "revisa mis mensajes", "que hay de nuevo"));
        reglas.add(r("musica", "pausa", "La dejo en pausa.",
             "pausa", "pon en pausa", "para la musica", "pausa la musica", "deten la musica",
             "stop", "para todo", "quieto", "apaga la musica"));
        reglas.add(r("musica", "reanuda", "Sigo.",
             "continua", "reanuda", "sigue la musica", "vuelve la musica", "vuelve", "dale play",
             "reanuda la musica", "sigue sonando", "pon la musica otra vez"));
        reglas.add(r("musica", "siguiente", "Voy con la siguiente.",
             "siguiente", "pasa", "cambia de cancion", "la siguiente", "siguiente cancion",
             "pista siguiente", "pon la siguiente", "otra cancion", "dale a la siguiente"));
        reglas.add(r("musica", "anterior", "Vuelvo a la anterior.",
             "anterior", "la anterior", "cancion anterior", "retrocede", "la de antes",
             "pista anterior", "pon la anterior", "vuelve a la anterior"));
        reglas.add(r("musica", "mueve", "Me muevo un poco en la cancion.",
             "muevete", "adelanta", "retrocede un poco", "adelanta un poco",
             "adelanta la cancion", "atrasa la cancion"));
        reglas.add(r("memoria", "listar", "Te leo lo que tengo guardado.",
             "que sabes de mi", "que recuerdas", "que tengo guardado", "dime lo que sabes",
             "que guardaste", "tus recuerdos", "mi informacion"));
        reglas.add(r("saludo", "", "Hola, te escucho.",
             "hola", "buenos dias", "buenas tardes", "buenas noches", "oye cort", "cort",
             "hola cort", "ey cort", "buenas", "ey"));
        reglas.add(r("saludo", "", "Soy CORT, tu asistente en este teléfono.",
             "quien eres", "como te llamas", "que eres", "quien eres tu", "tu nombre",
             "eres humana", "quien te hizo"));
        reglas.add(r("saludo", "", "Para eso estoy.",
             "gracias", "muchas gracias", "muy amable", "de nada", "gracias cort"));
        reglas.add(r("saludo", "", "Bien, aquí en el teléfono, sin tu portátil.",
             "estas ahi", "me oyes", "funcionas", "como estas", "estas alli", "aqui estas",
             "estas despierta", "cort estas", "me escuchas"));
        reglas.add(r("saludo", "", "Qué bueno que estés.",
             "adios", "hasta luego", "chao", "nos vemos", "hasta luego cort"));
        reglas.add(r("saludo", "tiempo", "Sin la nube no te sé el tiempo; actívala en el perfil y te lo digo.",
             "que tiempo hace", "que tiempo", "como esta el tiempo", "va a llover", "hace frio",
             "hace calor", "lleva paraguas"));
        reglas.add(r("saludo", "", "Mando sobre el aparato: volumen, linterna, alarmas, temporizadores, abrir apps, poner música, llamar, buscar, leer tus avisos y acordarme de lo que me cuentes. Y sin internet sé hacer cuentas, porcentajes, cambios de unidad, y darte la hora y el día. Lo que no sepa, se lo pregunto a la nube.",
             "que puedes hacer", "para que sirves", "ayuda", "comandos", "que sabes hacer",
             "dime que puedes", "para que sirves tu", "ayudame", "que puedes hacer por mi"));
        reglas.add(r("memoria", "guardar:{resto}", "Me quedo con eso.",
             "acuerdate de {resto}", "acuedate {resto}", "recuerda que {resto}",
             "guarda que {resto}", "aprende que {resto}", "anota {resto}", "apunta {resto}",
             "acuerdate que {resto}", "recuerdame {resto}", "ten presente {resto}",
             "no se olvide {resto}", "memoriza {resto}"));
        reglas.add(r("memoria", "buscar:{resto}", "Miro en mis recuerdos.",
             "que sabes de {resto}", "que recuerdas de {resto}", "recuerdas {resto}",
             "que te conte de {resto}", "sabes de {resto}", "en que quedo lo de {resto}"));
        reglas.add(r("alarma", "{resto}", "Pongo la alarma.",
             "pon una alarma a las {resto}", "pon alarma a las {resto}",
             "despiertame a las {resto}", "despierta a las {resto}", "alarma a las {resto}",
             "alerta a las {resto}", "alarma {resto}", "programa una alarma a las {resto}",
             "necesito una alarma a las {resto}", "despiertame en {resto}",
             "ponme una alarma {resto}"));
        reglas.add(r("temporizador", "{resto}", "Cuento hacia atrás y te aviso.",
             "pon un temporizador de {resto}", "temporizador de {resto}", "temporizador {resto}",
             "cuenta atras de {resto}", "cuenta atras {resto}", "timer {resto}",
             "cronometro de {resto}", "avisame en {resto}", "avisa en {resto}",
             "me avisas en {resto}"));
        reglas.add(r("llamar", "{resto}", "Abro el marcador.",
             "llama al numero {resto}", "llama a {resto}", "llamar a {resto}", "marca a {resto}",
             "llama {resto}", "llamada a {resto}", "marcame {resto}"));
        reglas.add(r("buscar", "{resto}", "Busco en el navegador.",
             "busca en la red {resto}", "busca en internet {resto}", "buscar {resto}",
             "busca {resto}", "googlea {resto}", "investiga {resto}",
             "quiero saber sobre {resto}"));
        reglas.add(r("poner", "{resto}", "Pongo eso.",
             "pon la cancion {resto}", "pon el video {resto}", "ponme musica de {resto}",
             "reproduce {resto}", "poner {resto}", "pon {resto}", "suena {resto}",
             "dale a {resto}", "escucha {resto}"));
        reglas.add(r("abrir", "ajustes", "Abro los ajustes.",
             "configuracion"));
        reglas.add(r("abrir", "{resto}", "Abro.",
             "abre el navegador de {resto}", "abre la aplicacion {resto}", "entra en {resto}",
             "abreme {resto}", "abre {resto}", "abrir {resto}", "arranca {resto}",
             "lanza {resto}", "ve a {resto}", "navega {resto}", "prende {resto}",
             "quiero abrir {resto}"));
    }

    /* ───────────────────────────── procesar ─────────────────────── */

    /**
     * Empareja la frase. Nunca devuelve `null`: si nada casa sale una
     * `desconocido` con `respuesta=null`, y `Mente` decide si pregunta a la nube.
     */
    public Resultado procesar(String entrada) {
        String dicho = normaliza(entrada);
        if (dicho.isEmpty()) return new Resultado("desconocido", "", null);
        for (Regla regla : reglas) {
            for (String patron : regla.patrones) {
                String resto = encaja(patron, dicho);
                if (resto != null) {
                    return resuelve(regla, resto);
                }
            }
        }
        return new Resultado("desconocido", "", null);
    }

    /** Construye el `Resultado` a partir de la regla y el trozo capturado. */
    private Resultado resuelve(Regla regla, String resto) {
        boolean dinamica = resto != null && !resto.isEmpty();
        String param = regla.param;
        if (param.contains("{resto}")) {
            param = dinamica ? param.replace("{resto}", resto) : "";
        } else if (param.isEmpty() && dinamica) {
            param = resto;
        }
        // Ajustes por acción: nombre de app resuelto y tiempo a segundos.
        if ("abrir".equals(regla.accion)) param = resuelveApp(param);
        if ("alarma".equals(regla.accion)) param = hora(param);
        if ("temporizador".equals(regla.accion)) param = aSegundos(param);
        String respuesta = regla.respuesta;
        if (respuesta != null && respuesta.contains("{resto}")) {
            respuesta = respuesta.replace("{resto}", resto == null ? "" : resto);
        }
        return new Resultado(regla.accion, param, respuesta);
    }

    /**
     * Un patrón sin `{resto}` casa sólo si es exacto. Con `{resto}` casa por
     * prefijo y devuelve lo que sobra (o `""` si el patrón es exacto). `null` si no casa.
     */
    private static String encaja(String patron, String dicho) {
        int hueco = patron.indexOf("{resto}");
        if (hueco < 0) return patron.equals(dicho) ? "" : null;
        String prefijo = patron.substring(0, hueco).trim();
        if (prefijo.isEmpty() || !dicho.startsWith(prefijo)) return null;
        String resto = dicho.substring(prefijo.length()).trim();
        return resto.isEmpty() ? null : resto;
    }

    /* ───────────────────────── resolutores sueltos ──────────────── */

    /**
     * Pasa el nombre dicho por la clave que espera el puente (§1 `abrir.a`).
     *
     * Los posesivos y los artículos se quitan ANTES de nada: «abre mis archivos»
     * tiene que llegar al puente como `archivos`, porque `Acciones` compara su clave
     * sin espacios («misarchivos» no está en ninguna lista y la dueña oiría «no
     * conozco esa app» teniendo el gestor delante). Lo que no se reconoce se deja
     * tal cual: `Acciones.app()` lo busca por el rótulo instalado, y ahí «fotos» o
     * «telegram» sí tienen arreglo.
     */
    private static String resuelveApp(String dicho) {
        String d = dicho.toLowerCase(java.util.Locale.ROOT)
            .replaceAll("^(el|la|los|las|un|una|unos|unas|mi|mis|tu|tus|su|sus|nuestro|"
                + "nuestra|nuestros|nuestras|la app de|el app de|app de|aplicacion de|"
                + "la aplicacion de|aplicacion|el programa de|programa de)\\s+", "").trim();
        if (d.contains("whatsapp")) return "whatsapp";
        if (d.contains("spotify")) return "spotify";
        if (d.contains("youtube") || d.contains("video")) return "youtube";
        if (d.contains("map") || d.contains("google maps") || d.contains("ruta")) return "maps";
        if (d.contains("gmail") || d.contains("correo") || d.contains("email") || d.contains("mail")) return "gmail";
        if (d.contains("calendario") || d.contains("agenda")) return "calendario";
        if (d.contains("instagram")) return "instagram";
        if (d.contains("facebook")) return "facebook";
        if (d.contains("tiktok")) return "tiktok";
        if (d.contains("navegador") || d.contains("chrome") || d.contains("browser")) return "navegador";
        if (d.contains("ajuste") || d.contains("configuraci")) return "ajustes";
        if (d.contains("musica")) return "musica";
        if (d.contains("telefono") || d.contains("marcador") || d.contains("llamar")) return "telefono";
        // Categorías que el puente ya tiene resueltas: se pasan con su clave exacta.
        if (d.contains("archiv") || d.contains("carpet") || d.contains("gestor")) return "archivos";
        if (d.contains("mensaje") || d.contains("sms")) return "mensajes";
        if (d.contains("reloj") || d.contains("cronometro")) return "reloj";
        if (d.contains("wifi") || d.contains("wi-fi")) return "wifi";
        if (d.contains("bluetooth")) return "bluetooth";
        if (d.contains("teclado")) return "teclado";
        if (d.contains("notificaci") || d.contains("avisos")) return "avisos";
        return d.isEmpty() ? dicho : d;   // app cualquiera: la cara tira de `app`
    }

    /** Deja la hora como `HH:MM` cuando se puede; si no, la deja como vino. */
    private static String hora(String dicho) {
        java.util.regex.Matcher m =
            Pattern.compile("(\\d{1,2})[:. ]?(\\d{2})").matcher(dicho);
        if (m.find()) {
            int h = entero(m.group(1), -1);
            int mi = entero(m.group(2), -1);
            if (h >= 0 && h <= 23 && mi >= 0 && mi <= 59) {
                return String.format(java.util.Locale.ROOT, "%02d:%02d", h, mi);
            }
        }
        return dicho.trim();
    }

    /** «10 minutos» → 600, «90 segundos» → 90, «2 horas» → 7200. Sin unidad: minutos. */
    private static String aSegundos(String dicho) {
        java.util.regex.Matcher m = Pattern.compile("(\\d+)").matcher(dicho);
        if (!m.find()) return "";
        int n = entero(m.group(1), 0);
        String d = dicho.toLowerCase(java.util.Locale.ROOT);
        if (d.contains("hora")) return String.valueOf(n * 3600);
        if (d.contains("segund")) return String.valueOf(n);
        return String.valueOf(n * 60);            // sin unidad se asume minutos
    }

    private static int entero(String s, int porDefecto) {
        try { return Integer.parseInt(s.trim()); }
        catch (Exception e) { return porDefecto; }
    }

    /* ───────────────────────────── encadenar ────────────────────── */

    private static final Pattern UNION = Pattern.compile(
        " (?:y luego|luego|y despues|despues de|despues|y) ");

    /** Parte la frase por las junturas, tirando los trozos vacíos. Pura: sin Android. */
    public static List<String> partir(String entrada) {
        List<String> piezas = new ArrayList<>();
        for (String trozo : UNION.split(normaliza(entrada))) {
            String limpio = trozo.trim();
            if (!limpio.isEmpty()) piezas.add(limpio);
        }
        return piezas;
    }

    /**
     * Los pasos de una frase, casi siempre uno. Se parte primero y sólo se acepta
     * la cadena si TODOS los trozos casan: así «abre spotify y sube el volumen»
     * salen en dos, y «pon una alarma a las ocho y media» no se parte en dos.
     */
    public List<Resultado> cadena(String entrada) {
        List<String> piezas = partir(entrada);
        if (piezas.size() > 1) {
            List<Resultado> pasos = new ArrayList<>();
            for (String pieza : piezas) {
                Resultado r = procesar(pieza);
                if ("desconocido".equals(r.accion)) { pasos = null; break; }
                pasos.add(r);
            }
            if (pasos != null && pasos.size() > 1) return pasos;
        }
        Resultado entera = procesar(entrada);
        if ("desconocido".equals(entera.accion)) return Collections.emptyList();
        return Collections.singletonList(entera);
    }

    /**
     * Minúsculas, sin tildes, sin signos, un solo espacio: la forma en que se
     * compara el habla. La tabla (`assets/habilidades.json` y `tablaDelCodigo`)
     * está escrita así; un patrón con tilde sería un patrón que nunca casa.
     */
    public static String normaliza(String texto) {
        if (texto == null) return "";
        String bajo = Normalizer.normalize(texto, Normalizer.Form.NFD)
            .replaceAll("\\p{Mn}+", "").toLowerCase(java.util.Locale.ROOT);
        bajo = bajo.replaceAll("[¿?¡!.,;:\"“”'()]", " ");
        return bajo.replaceAll("\\s+", " ").trim();
    }
}
