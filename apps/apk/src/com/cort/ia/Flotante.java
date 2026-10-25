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
 *   por escrito: un punto encima de una partida es exactamente lo que ella no
 *   quiere, aunque se pueda arrastrar a una esquina.
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
 * · **Animar en bucle.** El punto no tiene bucle de pintado: se pinta al montarse
 *   y cuando el dedo lo mueve. El único cambio de opacidad es un fundido de una
 *   vez al reposar, que la deja translúcida para dejar ver lo de debajo —lo que
 *   a ella le gustó de la 1.1.4—. Un latido por fotograma en segundo plano sería
 *   batería y RAM en un teléfono de dos núcleos; el latido vivo es de la cara.
 * · **Quedarse quieta.** Se arrastra con el dedo: `ACTION_MOVE` mueve la ventana
 *   (`updateViewLayout`), pero al soltar **no salta al borde**: se queda donde la
 *   dejó. Ese salto automático era la «movilidad» que no le gustó; ahora el único
 *   movimiento es el de su propio dedo. Un toque sin arrastre sigue siendo «abre
 *   CORT y escucha». La posición no se guarda: al volver a montarla nace centrada a
 *   la izquierda, que es donde el contrato la puso siempre.
 * · **Ser una pegatina opaca.** Es azul translúcida —el cian de CORT, no el color
 *   del traje— y sube a opaca mientras el dedo está encima. En reposo queda al 28 %
 *   para dejar ver lo de debajo, que es la transparencia que pidió. Sin
 *   `backdrop-filter` ni desenfoque: en una vista de 44 dp no se nota y cuesta lo
 *   mismo que el resto de la cara en modo juego.
 * · **Ser un círculo vacío.** Lleva dentro el icono redondo de la app (el de la
 *   1.1.4 que sí le gustaba), leído de `mipmap` por nombre porque el pipeline no
 *   genera `R.java`. Si el recurso no estuviera, queda el cristal cian y nunca un
 *   hueco negro.
 * · **Pulsar nada por la dueña.** El toque lanza `MainActivity` con el extra de
 *   escuchar; quien decide si CORT escucha es Android con el permiso del micro.
 */

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.PixelFormat;
import android.graphics.RadialGradient;
import android.graphics.RectF;
import android.graphics.Shader;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.util.DisplayMetrics;
import android.util.Log;
import android.view.Gravity;
import android.view.MotionEvent;
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
    /** Lo translúcida que queda en reposo: la transparencia que pidió. */
    private static final float ALFA_REPOSO = .28f;
    /** Cuánto tarda en volver a translúcida tras el último toque, en ms. */
    private static final int ESPERA_OPACIDAD = 1800;
    /** El cian de CORT, fijo: la burbuja no cambia con el traje (la roja no le gustó). */
    private static final int CIAN = 0xFF59D9FF;
    private static final int AZUL = 0xFF0A3D62;

    /**
     * El `View` montado y el `WindowManager` que lo sostiene, en **estático**
     * porque `burbuja` es estático y la ventana tiene que poder quitarse aunque la
     * cara que la pidió ya no exista. Sólo el hilo de la interfaz los escribe;
     * `volatile` porque los lee el hilo del puente para contestar `montada()` y el
     * `ya`.
     */
    private static volatile Punto punto;
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
        // `TOP|START` en vez de `CENTER_VERTICAL|START`: con coordenadas desde la
        // esquina, el arrastre se acota contra la pantalla sin cuentas de centro.
        l.gravity = Gravity.TOP | Gravity.START;
        l.x = margen;
        l.y = Math.max(0, (alto(app) - lado) / 2);
        vista.engancha(wm, l);
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
     * El círculo de la 1.1.4: azul translúcido, con gradiente del traje puesto,
     * un aro del secundario y un brillo dentro. Se pinta a mano con `Paint` (no
     * hay recursos que enlazar) y se arrastra con el dedo. La opacidad baja sola
     * un rato después del último toque; mientras el dedo está encima va opaca.
     */
    private static final class Punto extends View {
        private final Paint relleno = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint aro = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint brillo = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint tintaIcono = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
        private final RectF cajaIcono = new RectF();
        private final Path recorte = new Path();
        private final Bitmap icono;
        private final int primario = CIAN;
        private final int secundario = AZUL;
        private final int lado;
        private final int tope;
        private final int dp;

        private final Runnable seApaga = new Runnable() {
            @Override public void run() {
                setAlpha(ALFA_REPOSO);
            }
        };

        private WindowManager ventana;
        private WindowManager.LayoutParams puesto;
        private RadialGradient gradiente;
        private float x0, y0, toqueX, toqueY;
        private boolean arrastro;

        Punto(Context c) {
            super(c);
            dp = Math.round(densidad(c));
            lado = Math.round(DIAMETRO_DP * densidad(c));
            tope = Math.max(6, Math.round(6 * densidad(c)));   // `ViewConfiguration` fuera: una línea
            icono = cargaIcono(c);
            relleno.setStyle(Paint.Style.FILL);
            aro.setStyle(Paint.Style.STROKE);
            brillo.setStyle(Paint.Style.FILL);
            setAlpha(ALFA_REPOSO);
            setClickable(true);
            setContentDescription("CORT");
            setOnClickListener(new View.OnClickListener() {
                @Override public void onClick(View v) {
                    abreCORT(v.getContext());
                }
            });
            setOnTouchListener(new View.OnTouchListener() {
                @Override public boolean onTouch(View v, MotionEvent e) {
                    return toca(e);
                }
            });
        }

        /** La ventana y sus parámetros: sin ellos no hay arrastre posible. */
        void engancha(WindowManager wm, WindowManager.LayoutParams lp) {
            ventana = wm;
            puesto = lp;
        }

        /* ── el dedo: toque = abrir CORT; arrastre = mover; soltar = borde ── */
        private boolean toca(MotionEvent e) {
            if (puesto == null || ventana == null) return false;
            switch (e.getActionMasked()) {
                case MotionEvent.ACTION_DOWN:
                    x0 = puesto.x;
                    y0 = puesto.y;
                    toqueX = e.getRawX();
                    toqueY = e.getRawY();
                    arrastro = false;
                    setAlpha(1f);
                    removeCallbacks(seApaga);
                    return true;
                case MotionEvent.ACTION_MOVE: {
                    float dx = e.getRawX() - toqueX;
                    float dy = e.getRawY() - toqueY;
                    if (!arrastro && Math.hypot(dx, dy) > tope) arrastro = true;
                    if (arrastro) {
                        puesto.x = acota(Math.round(x0 + dx), 0, Math.max(0, ancho() - ladoVivo()));
                        puesto.y = acota(Math.round(y0 + dy), 0, Math.max(0, alto() - ladoVivo()));
                        mueve();
                    }
                    return true;
                }
                case MotionEvent.ACTION_UP:
                    setAlpha(1f);
                    if (!arrastro) performClick();       // el toque de siempre: abre y escucha
                    // Sin `pegaAlBorde`: se queda donde la soltó. El salto automático
                    // era el movimiento que no le gustaba de la burbuja roja.
                    postDelayed(seApaga, ESPERA_OPACIDAD);
                    return true;
                case MotionEvent.ACTION_CANCEL:
                    postDelayed(seApaga, ESPERA_OPACIDAD);
                    return true;
                default:
                    return false;
            }
        }

        private void mueve() {
            try {
                ventana.updateViewLayout(this, puesto);
            } catch (Throwable noMueve) {
                Log.e(LOG, "burbuja: updateViewLayout", noMueve);
            }
        }

        private int ancho() {
            try { return getResources().getDisplayMetrics().widthPixels; }
            catch (Throwable sinPantalla) { return lado * 8; }
        }

        private int alto() {
            try { return getResources().getDisplayMetrics().heightPixels; }
            catch (Throwable sinPantalla) { return lado * 16; }
        }

        private int ladoVivo() {
            return getWidth() > 0 ? getWidth() : lado;
        }

        @Override protected void onSizeChanged(int w, int h, int viejoW, int viejoH) {
            super.onSizeChanged(w, h, viejoW, viejoH);
            gradiente = null;                 // el gradiente depende del radio
        }

        @Override protected void onDetachedFromWindow() {
            removeCallbacks(seApaga);
            super.onDetachedFromWindow();
        }

        @Override protected void onDraw(Canvas canvas) {
            float x = getWidth() / 2f;
            float y = getHeight() / 2f;
            float radio = Math.min(x, y);
            if (radio <= 1f) return;

            if (gradiente == null) {
                // Azul de cristal: centro claro, cuerpo del primario y borde que se
                // hunde en el secundario. Las alfas son lo que deja ver lo de abajo.
                gradiente = new RadialGradient(x - radio * .18f, y - radio * .24f, radio * 1.12f,
                        new int[]{conAlfa(aclara(primario, .45f), 0xE6),
                                  conAlfa(primario, 0xC8),
                                  conAlfa(secundario, 0xF0)},
                        new float[]{0f, .58f, 1f}, Shader.TileMode.CLAMP);
                relleno.setShader(gradiente);
            }
            aro.setStrokeWidth(Math.max(2f, radio * .12f));
            aro.setColor(conAlfa(aclara(secundario, .30f), 0xCC));
            brillo.setColor(0x55FFFFFF);

            canvas.drawCircle(x, y, radio - aro.getStrokeWidth() / 2f, relleno);
            // La imagen de la 1.1.4, dentro del cristal: icono redondo de la app,
            // recortado al círculo de la burbuja. Si faltara, queda el cristal cian.
            if (icono != null && !icono.isRecycled()) {
                float d = radio * 1.34f;
                cajaIcono.set(x - d / 2f, y - d / 2f, x + d / 2f, y + d / 2f);
                recorte.reset();
                recorte.addCircle(x, y, d / 2f, Path.Direction.CW);
                canvas.save();
                canvas.clipPath(recorte);
                canvas.drawBitmap(icono, null, cajaIcono, tintaIcono);
                canvas.restore();
            }
            canvas.drawCircle(x, y, radio - aro.getStrokeWidth() / 2f, aro);
            // El brillo descentrado es lo que hace que parezca una bola de cristal.
            canvas.drawCircle(x - radio * .24f, y - radio * .28f, radio * .22f, brillo);
        }

        /** El icono redondo de la app, por nombre: el pipeline no genera `R.java`. */
        private static Bitmap cargaIcono(Context c) {
            try {
                int id = c.getResources().getIdentifier(
                        "ic_launcher_round", "mipmap", c.getPackageName());
                if (id == 0) id = c.getResources().getIdentifier(
                        "ic_launcher", "mipmap", c.getPackageName());
                return id == 0 ? null : BitmapFactory.decodeResource(c.getResources(), id);
            } catch (Throwable sinIcono) {
                Log.w(LOG, "burbuja: sin icono, queda el cristal");
                return null;
            }
        }

        private static int conAlfa(int color, int alfa) {
            return (color & 0x00FFFFFF) | ((alfa & 0xFF) << 24);
        }

        private static int aclara(int color, float t) {
            int r = Math.round(Color.red(color) + (255 - Color.red(color)) * t);
            int g = Math.round(Color.green(color) + (255 - Color.green(color)) * t);
            int b = Math.round(Color.blue(color) + (255 - Color.blue(color)) * t);
            return Color.rgb(r, g, b);
        }

        private static int acota(int v, int min, int max) {
            return v < min ? min : (v > max ? max : v);
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

    private static int alto(Context c) {
        try {
            DisplayMetrics m = c.getResources().getDisplayMetrics();
            return m == null || m.heightPixels <= 0 ? 1920 : m.heightPixels;
        } catch (Throwable sinPantalla) {
            return 1920;
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
