package dev.sandra.cort.movil;

import android.accessibilityservice.AccessibilityService;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.provider.Settings;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

/**
 * La pantalla entera leída y escrita (F19e, F20b, F20c). La dueña pidió que CORT
 * pudiera «leer lo que estoy viendo», «escribir por mí» y «analizar esto». En Android
 * las dos primeras sólo se pueden hacer con un servicio de accesibilidad: no hay
 * permiso en tiempo de ejecución que dé el texto de otra aplicación, y el menú
 * «Leer con CORT» (`Lectura.java`, `ACTION_PROCESS_TEXT`) sólo ve lo que ella
 * selecciona a mano, no la ventana completa.
 *
 * Cuatro decisiones escritas antes del código, porque éste es el archivo con más
 * poder de todo el APK:
 *
 * 1. **Lo que se lee NO se guarda.** El texto de la pantalla vive en memoria, con
 *    fecha y caducidad de 90 segundos, y se pierde al apagar el servicio. No va a
 *    SQLite, no va a un archivo y no viaja a la nube salvo que ella pida explícitamente
 *    «analiza esto» — y aun entonces se le dice qué se está mandando. Es la misma
 *    regla que ya rige el audio y los fotogramas de la cámara: no se quedan.
 * 2. **Los campos de contraseña se saltan.** `isPassword()` se consulta antes de
 *    leer el texto de un nodo. Un lector de pantalla que copie claves es un teclado
 *    registrado, y eso no es lo que ella pidió.
 * 3. **No se filtran teclas.** `canRequestFilterKeyEvents` va en false en
 *    `res/xml/accesibilidad.xml`: CORT lee ventanas, no pulsaciones.
 * 4. **Se enciende ella, en los Ajustes de Android.** No hay forma de autoconceder
 *    esto —por diseño— y `abreAjustes` la lleva a la pantalla exacta. Mientras no
 *    esté concedido, todo lo que depende de esto contesta el motivo en vez de callar.
 *
 * Lo que NO hace: no toca otras ventanas (sin `dispatchGesture`), no pulsa botones
 * por su cuenta y no escribe en un campo que no tenga el foco. «Escribe por mí»
 * reemplaza el contenido del campo enfocado, y si no hay campo enfocado lo dice.
 */
public class Pantalla extends AccessibilityService {

    /** Cuánto vale una captura. Pasado este tiempo hay que volver a leer la ventana. */
    private static final long FRESCURA_MS = 90_000L;

    /** Tope de nodos y de caracteres: una lista infinita no puede congelar el teléfono. */
    private static final int MAX_NODOS = 4000;
    private static final int MAX_CHARS = 24_000;

    /** Como mínimo este tiempo entre capturas: `TYPE_WINDOW_CONTENT_CHANGED` es un torrente. */
    private static final long PASO_CAPTURA_MS = 1200L;

    private static volatile Pantalla viva;

    private volatile String texto = "";
    private volatile String paquete = "";
    private volatile long cuando;
    private long ultimaCaptura;

    /* ------------------------------------------------------------------ estática */

    /** Si la dueña lo encendió en los Ajustes y el sistema lo conectó de verdad. */
    public static boolean concedida() {
        return viva != null;
    }

    /** La lleva a la lista de accesibilidad, que es el único sitio donde esto se enciende. */
    public static void abreAjustes(Context contexto) {
        Intent ajustes = new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS);
        ajustes.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        contexto.startActivity(ajustes);
    }

    /** Por qué no se puede leer ahora mismo, en una frase que se puede decir en voz alta. */
    public static String motivo() {
        Pantalla yo = viva;
        if (yo == null) {
            return "no tengo permiso para leer la pantalla: enciende CORT en Ajustes → "
                    + "Accesibilidad → Servicios instalados";
        }
        if (yo.texto.isEmpty()) {
            return "todavía no leí ninguna ventana: abre la app que quieras y vuelve a pedírmelo";
        }
        if (System.currentTimeMillis() - yo.cuando > FRESCURA_MS) {
            return "lo que leí ya tiene más de 90 segundos: vuelve a pedírmelo con la pantalla puesta";
        }
        return "";
    }

    /** El texto de la ventana, o `null` si no hay nada fresco que leer. */
    public static String pantalla() {
        return motivo().isEmpty() ? viva.texto : null;
    }

    /** De qué app es lo último leído, para decirlo antes de analizarlo. */
    public static String paqueteActual() {
        Pantalla yo = viva;
        return yo == null ? "" : yo.paquete;
    }

    /**
     * Escribe en el campo que tenga el foco (F20b). **Reemplaza** lo que hubiera: es
     * lo que hace `ACTION_SET_TEXT`, y append a mano perdería el cursor de la dueña.
     * Devuelve false si no hay servicio, no hay ventana o no hay campo editable.
     */
    public static boolean escribe(String dicho) {
        Pantalla yo = viva;
        if (yo == null || dicho == null || dicho.isEmpty()) {
            return false;
        }
        AccessibilityNodeInfo raiz = yo.getRootInActiveWindow();
        if (raiz == null) {
            return false;
        }
        AccessibilityNodeInfo campo = raiz.findFocus(AccessibilityNodeInfo.FOCUS_INPUT);
        if (campo == null) {
            return false;
        }
        Bundle argumentos = new Bundle();
        argumentos.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,
                dicho);
        return campo.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, argumentos);
    }

    /**
     * El plan B de «escribe por mí»: dejarlo en el portapapeles para que ella lo pegue.
     * Desde Android 10 una app en segundo plano no puede leer el portapapeles, pero
     * un servicio de accesibilidad sí puede escribir en él; si el sistema se niega,
     * devuelve false y la cara lo dice en vez de fingir que lo dejó.
     */
    public static boolean alPortapapeles(Context contexto, String dicho) {
        if (dicho == null || dicho.isEmpty()) {
            return false;
        }
        ClipboardManager mesa = (ClipboardManager)
                contexto.getSystemService(Context.CLIPBOARD_SERVICE);
        if (mesa == null) {
            return false;
        }
        mesa.setPrimaryClip(ClipData.newPlainText("CORT", dicho));
        return true;
    }

    /* ------------------------------------------------------------------ servicio */

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        viva = this;
        captura();
    }

    /**
     * Sólo se vuelve a leer cuando cambia la ventana o su contenido, y con el paso
     * de 1,2 s: cada fotograma de una lista que se desplaza dispara este evento y
     * recorrer el árbol entero en cada uno sería el teléfono congelado.
     */
    @Override
    public void onAccessibilityEvent(AccessibilityEvent evento) {
        if (evento == null) {
            return;
        }
        int tipo = evento.getEventType();
        if (tipo != AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED
                && tipo != AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED
                && tipo != AccessibilityEvent.TYPE_VIEW_TEXT_SELECTION_CHANGED) {
            return;
        }
        long ahora = System.currentTimeMillis();
        if (tipo == AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED
                && ahora - ultimaCaptura < PASO_CAPTURA_MS) {
            return;
        }
        ultimaCaptura = ahora;
        captura();
    }

    @Override
    public void onInterrupt() {
        // el sistema pide callar: aquí no hay voz que interrumpir, sólo lectura
    }

    @Override
    public void onDestroy() {
        // Lo leído se va con el servicio: no queda en disco ni en preferencias.
        texto = "";
        paquete = "";
        cuando = 0L;
        if (viva == this) {
            viva = null;
        }
        super.onDestroy();
    }

    /** Recorre la ventana activa y se queda con el texto, saltándose las contraseñas. */
    private void captura() {
        AccessibilityNodeInfo raiz = getRootInActiveWindow();
        if (raiz == null) {
            return;
        }
        StringBuilder junto = new StringBuilder();
        int[] cuenta = {0};
        recorre(raiz, junto, cuenta);
        CharSequence nombre = raiz.getPackageName();
        paquete = nombre == null ? "" : nombre.toString();
        texto = junto.toString().trim();
        cuando = System.currentTimeMillis();
    }

    /**
     * El recorrido. `cuenta[0]` es el techo de nodos y `MAX_CHARS` el de texto: los
     * dos existen porque una ventana con una lista larga puede tener decenas de
     * miles de nodos y esto corre en el proceso de CORT, no en un servidor.
     */
    private static void recorre(AccessibilityNodeInfo nodo, StringBuilder junto, int[] cuenta) {
        if (nodo == null || cuenta[0] >= MAX_NODOS || junto.length() >= MAX_CHARS) {
            return;
        }
        cuenta[0]++;
        if (!nodo.isPassword()) {
            CharSequence leido = nodo.getText();
            if (leido == null || leido.length() == 0) {
                leido = nodo.getContentDescription();
            }
            if (leido != null && leido.length() > 0) {
                String limpio = leido.toString().trim();
                if (!limpio.isEmpty()) {
                    if (junto.length() > 0) {
                        junto.append('\n');
                    }
                    junto.append(limpio);
                }
            }
        }
        for (int i = 0; i < nodo.getChildCount(); i++) {
            recorre(nodo.getChild(i), junto, cuenta);
        }
    }
}
