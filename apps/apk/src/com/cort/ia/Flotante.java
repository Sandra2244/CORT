package com.cort.ia;

/*
 * El puntito de CORT flotando encima de lo que la dueña esté usando. Sección 6 de
 * `docs/CONTRATO-PUENTE-2.1.md`: `CortNative.burbuja(true)` monta un círculo de
 * 44 dp sobre la app de turno y `false` lo quita; tocarlo abre CORT y le pone el
 * micrófono a escuchar.
 *
 * Lo que NO puede hacer, dicho sin adornos:
 *
 * · **Aparecer sin el interruptor de la dueña.** Sin «Aparecer encima de otras
 *   apps» concedido, Android no deja montar la ventana y esto devuelve `ok:false`
 *   con el camino a mano. No se abre esa pantalla de Ajustes por detrás: la
 *   decide la cara, no CORT.
 * · **Existir en modo juego.** Con `juego` puesto en las preferencias `cort`, la
 *   respuesta es `{"ok":false,"dice":"estoy en modo juego"}` aunque se le pida
 *   por escrito: un punto moviéndose sobre una partida es exactamente lo que
 *   ella no quiere.
 * · **Pintar un layout XML.** No hay `R.java` para recursos nuevos (el APK se
 *   enlaza con `aapt2` sobre `res/`, y el pipeline no genera layouts): el círculo
 *   se dibuja a mano con `Paint` sobre `Canvas`, como `Orbe.java` en la línea
 *   hermana. Cero dependencias y cero recursos que mantener.
 * · **Atarse a una Activity.** La ventana se pide siempre al `Context` de
 *   aplicación y el `View` vive en un campo estático: si la cara se destruye y
 *   el punto se queda colgado de su `WindowManager`, Android contesta
 *   `BadTokenException` o deja un fantasma en pantalla. Todo el `addView` y el
 *   `removeView` va envuelto en `try/catch`.
 * · **Montarse desde el hilo equivocado.** Los `@JavascriptInterface` corren en
 *   el hilo del puente de WebView, y una vista montada desde un hilo que no es el
 *   de la interfaz revienta al primer toque. `burbuja` changea al hilo principal
 *   con un `Handler` y espera su resultado con un `CountDownLatch` acotado: el
 *   método sigue siendo síncrono como pide el contrato, pero no se queda colgado
 *   si la interfaz está ocupada.
 * · **Animar.** El punto está quieto a propósito: un bucle de pintado en segundo
 *   plano es batería y RAM en un teléfono de dos núcleos. El latido vivo es
 *   asunto de la cara cuando ella la abre.
 * · **Pulsar nada por la dueña.** El toque lanza `MainActivity` con el extra de
 *   escuchar; quien decide si CORT escucha es Android con el permiso del micro.
 */

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.PixelFormat;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.util.DisplayMetrics;
import android.util.Log;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

public class Flotante {

    private static final String LOG = "cort";

    /** El diámetro del contrato, en dp: 44 dp es lo mínimo tocable sin puntería. */
    private static final int DIAMETRO_DP = 44;
    /** Margen al borde de la pantalla, también en dp. */
    private static final int MARGEN_DP = 10;

    /**
     * El `View` montado y el `WindowManager` que lo sostiene, en **estático**
     * porque `burbuja` es estático y la ventana tiene que poder quitarse aunque la
     * cara que la pidió ya no exista. Sólo el hilo de la interfaz los escribe;
     * `volatile` porque los lee el hilo del puente para contestar `montada()` y el
     * `ya`.
     */
    private static volatile View punto;
    private static volatile WindowManager ventana;

    private Flotante() {
    }

    /* ────────────────────────────── la entrada ────────────────────────────── */

    /**
     * `burbuja(contexto, true)` monta el punto; `false` lo quita. Devuelve JSON y
     * nunca lanza: es lo que firma la sección 6 del contrato.
     */
    public static String burbuja(Context contexto, boolean on) {
        try {
            if (contexto == null) {
                return error("no tengo un teléfono donde aparecer.");
            }
            final Context app = app(contexto);

            // El modo juego manda primero: ni aunque la cara lo pida.
            if (juego(app)) {
                return "{\"ok\":false,\"dice\":\"estoy en modo juego\"}";
            }

            if (!on) {
                boolean habia = montada();
                if (!habia) {
                    return "{\"ok\":true,\"burbuja\":false,\"habia\":false}";
                }
                if (!enElHiloDeLaInterfaz()) {
                    awaitEnLaInterfaz(new Quitando(app));
                } else {
                    quitarYa();
                }
                return "{\"ok\":true,\"burbuja\":false,\"habia\":true}";
            }

            if (montada()) {
                return "{\"ok\":true,\"burbuja\":true,\"ya\":true,\"diametro\":" + DIAMETRO_DP + "}";
            }
            if (!puedeAparecer(app)) {
                return error("necesito que me dejes aparecer encima de otras apps: "
                        + "Ajustes ▸ Aplicaciones ▸ CORT ▸ «Aparecer encima de otras apps». "
                        + "Sin eso no hay burbuja.");
            }
            final boolean[] salida = new boolean[1];
            if (enElHiloDeLaInterfaz()) {
                salida[0] = montarYa(app);
            } else {
                awaitEnLaInterfaz(new Montando(app, salida));
            }
            if (salida[0]) {
                return Json.ok().p("burbuja", true).p("diametro", DIAMETRO_DP)
                        .p("dice", "Ahí estoy: tócame y escucho.").fin();
            }
            return error("Android no me dejó aparecer, aunque el permiso está puesto. "
                    + "Algunos fabricantes apagan los dibujos encima de otras apps "
                    + "para apps instaladas a mano.");
        } catch (Throwable todo) {
            Log.e(LOG, "burbuja", todo);
            return error("algo se rompió dentro de CORT al aparecer.");
        }
    }

    /** Si el punto está montado ahora mismo (para `estado()` y para la cara). */
    public static boolean montada() {
        return punto != null;
    }

    /** Lo que Android concedió: se puede preguntar sin montar nada. */
    public static boolean puedeAparecer(Context c) {
        try {
            // `Settings.canDrawOverlays` es de API 23 y el suelo del APK es 26:
            // por eso no lleva guarda de versión.
            return Settings.canDrawOverlays(app(c));
        } catch (Throwable sinForma) {
            return false;
        }
    }

    /* ───────────────────────── montar y quitar, a mano ────────────────────── */

    private static boolean montarYa(Context app) {
        if (punto != null) return true;
        WindowManager wm = ventana(app);
        if (wm == null) return false;
        int lado = Math.round(DIAMETRO_DP * densidad(app));
        int margen = Math.round(MARGEN_DP * densidad(app));

        Punto vista = new Punto(app);
        WindowManager.LayoutParams l = new WindowManager.LayoutParams(
                lado, lado,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                // Sin foco: la burbuja no le roba el teclado ni la espalda a la app
                // de turno. Sin `NOT_TOUCH_MODAL` tampoco: el resto de la pantalla
                // sigue tocándose normal.
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                PixelFormat.TRANSLUCENT);
        l.gravity = Gravity.CENTER_VERTICAL | Gravity.START;
        l.x = margen;
        l.y = 0;
        try {
            wm.addView(vista, l);
        } catch (WindowManager.BadTokenException tokenRoto) {
            // El `Context` había dejado de valer: se quita la referencia y se dice.
            Log.e(LOG, "burbuja: token inválido", tokenRoto);
            punto = null;
            ventana = null;
            return false;
        } catch (Throwable noDeja) {
            Log.e(LOG, "burbuja: addView", noDeja);
            punto = null;
            ventana = null;
            return false;
        }
        punto = vista;
        ventana = wm;
        return true;
    }

    private static void quitarYa() {
        WindowManager wm = ventana;
        View v = punto;
        // Se limpian los campos primero: si `removeView` revienta porque la vista
        // ya no está (el sistema la tiró al cambiar de usuario), CORT no debe
        // seguir creyendo que está montada.
        punto = null;
        ventana = null;
        if (v == null) return;
        try {
            if (wm != null) wm.removeView(v);
        } catch (Throwable yaNoEstaba) {
            Log.e(LOG, "burbuja: removeView", yaNoEstaba);
        }
    }

    /* ─────────────────────────────── el hilo ──────────────────────────────── */

    private static boolean enElHiloDeLaInterfaz() {
        return Looper.myLooper() == Looper.getMainLooper();
    }

    /**
     * Manda la tarea al hilo de la interfaz y espera dos segundos. Con el tiempo
     * cumplido se contesta `false` en vez de quedarse colgando: el puente no puede
     * congelar la cara, que es la regla que trajo este archivo.
     */
    private static void awaitEnLaInterfaz(Runnable tarea) {
        final CountDownLatch listo = new CountDownLatch(1);
        final Runnable envuelto = new Runnable() {
            @Override public void run() {
                try {
                    tarea.run();
                } finally {
                    listo.countDown();
                }
            }
        };
        try {
            new Handler(Looper.getMainLooper()).post(envuelto);
        } catch (Throwable sinManejador) {
            Log.e(LOG, "burbuja: sin hilo principal", sinManejador);
            return;
        }
        try {
            listo.await(2, TimeUnit.SECONDS);
        } catch (InterruptedException cortada) {
            Thread.currentThread().interrupt();
        }
    }

    private static final class Montando implements Runnable {
        private final Context app;
        private final boolean[] salida;

        Montando(Context app, boolean[] salida) {
            this.app = app;
            this.salida = salida;
        }

        @Override public void run() {
            salida[0] = montarYa(app);
        }
    }

    private static final class Quitando implements Runnable {
        private final Context app;

        Quitando(Context app) {
            this.app = app;
        }

        @Override public void run() {
            quitarYa();
        }
    }

    /* ─────────────────────────── la vista pintada ─────────────────────────── */

    /**
     * El círculo. Se pinta aquí, en código: un relleno con el color primario del
     * traje puesto, un aro con el secundario y un brillo dentro para que se vea
     * redondo y no una pegatina. Los colores vienen de `Paleta`, así que el punto
     * viste lo mismo que la cara.
     */
    private static final class Punto extends View {
        private final Paint relleno = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint aro = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint brillo = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final int primario;
        private final int secundario;

        Punto(Context c) {
            super(c);
            primario = colorDe(Paleta.primario(c), 0xFF59D9FF);
            secundario = colorDe(Paleta.secundario(c), 0xFF0A3D62);
            relleno.setStyle(Paint.Style.FILL);
            aro.setStyle(Paint.Style.STROKE);
            brillo.setStyle(Paint.Style.FILL);
            setClickable(true);
            setContentDescription("CORT");
            setOnClickListener(new View.OnClickListener() {
                @Override public void onClick(View v) {
                    abreCORT(v.getContext());
                }
            });
        }

        @Override protected void onDraw(Canvas canvas) {
            float x = getWidth() / 2f;
            float y = getHeight() / 2f;
            float radio = Math.min(x, y);
            if (radio <= 0f) return;

            aro.setColor(secundario);
            aro.setStrokeWidth(Math.max(2f, radio * 0.14f));
            relleno.setColor(primario);
            brillo.setColor(0x66FFFFFF);

            canvas.drawCircle(x, y, radio - aro.getStrokeWidth() / 2f, relleno);
            canvas.drawCircle(x, y, radio - aro.getStrokeWidth() / 2f, aro);
            // El brillo descentrado es lo que hace que parezca una bola de cristal.
            canvas.drawCircle(x - radio * 0.22f, y - radio * 0.26f, radio * 0.26f, brillo);
        }

        private static int colorDe(int color, int siNegro) {
            // Un traje con alfa cero o un `Color.parseColor` raro no pueden dejar
            // la burbuja invisible: se cae al cian de siempre.
            return (color >>> 24) == 0 ? siNegro : color;
        }
    }

    /**
     * El toque abre la cara y pide escuchar, que es lo que promete el contrato.
     * Se reutiliza la `MainActivity` que ya está abierta (`singleTop` en el
     * manifiesto) en vez de montar una segunda, y el extra es la constante pública
     * de `MainActivity`: escribirla a mano aquí sería la receta para que las dos
     * copias se quedaran distintas.
     */
    private static void abreCORT(Context c) {
        try {
            Intent cara = new Intent(app(c), MainActivity.class);
            cara.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
            cara.putExtra(MainActivity.PIDE_ESCUCHAR, true);
            app(c).startActivity(cara);
        } catch (Throwable noArranca) {
            Log.e(LOG, "burbuja: no pude abrir CORT", noArranca);
        }
    }

    /* ────────────────────────────── el suelo ──────────────────────────────── */

    private static Context app(Context c) {
        if (c == null) return null;
        try {
            Context base = c.getApplicationContext();
            return base != null ? base : c;
        } catch (Throwable sinAplicacion) {
            return c;
        }
    }

    private static WindowManager ventana(Context c) {
        try {
            Object servicio = c.getSystemService(Context.WINDOW_SERVICE);
            return servicio instanceof WindowManager ? (WindowManager) servicio : null;
        } catch (Throwable sinServicio) {
            Log.e(LOG, "burbuja: sin WindowManager", sinServicio);
            return null;
        }
    }

    private static float densidad(Context c) {
        try {
            DisplayMetrics m = c.getResources().getDisplayMetrics();
            return m == null || m.density <= 0f ? 1f : m.density;
        } catch (Throwable sinPantalla) {
            return 1f;
        }
    }

    private static boolean juego(Context c) {
        try {
            SharedPreferences p = c.getSharedPreferences("cort", Context.MODE_PRIVATE);
            return p.getBoolean("juego", false);
        } catch (Throwable sinPreferencias) {
            return false;
        }
    }

    /* ───────────────────────────── JSON a mano ────────────────────────────── */

    private static String error(String dice) {
        return "{\"ok\":false,\"dice\":\"" + esc(dice) + "\"}";
    }

    private static String esc(String texto) {
        if (texto == null) return "";
        StringBuilder s = new StringBuilder(texto.length() + 8);
        for (int i = 0; i < texto.length(); i++) {
            char c = texto.charAt(i);
            if (c == '"' || c == '\\') { s.append('\\').append(c); }
            else if (c == '\n') s.append("\\n");
            else if (c == '\r') s.append(' ');
            else if (c == '\t') s.append(' ');
            else if (c < 0x20) { /* fuera */ }
            else s.append(c);
        }
        return s.toString();
    }

    private static final class Json {
        private final StringBuilder s;

        private Json(boolean ok) {
            s = new StringBuilder("{\"ok\":").append(ok);
        }

        static Json ok() {
            return new Json(true);
        }

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

        String fin() {
            return s.append('}').toString();
        }
    }
}
