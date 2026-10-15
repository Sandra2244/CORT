package dev.sandra.cort;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.view.View;
import java.util.Random;

/**
 * El reactor de CORT **en el teléfono**, dibujado con `Canvas`.
 *
 * Por qué existe y no se quedó en el `Anillo`: el anillo es la marca, y la marca
 * gira; lo que la dueña pide desde el primer día es que la cara del teléfono se
 * vea como la del PC —«que se active en modo orbe con su animación y todo»—. La
 * cara de PC es WebGL (`apps/web/src/scene/`), y en el APK no hay tres.js ni GPU
 * shaders: `compilar.sh` es `aapt2` + `javac` + `d8`, sin Gradle ni dependencias.
 * Este archivo es el mismo orbe dibujado con lo que Android sí trae.
 *
 * Los números **no se inventan aquí**: son los literales de la cara de PC, y hay
 * una prueba (`test_apk_orbe.py`) que los compara con los del TypeScript para que
 * un cambio estético en un aparato viaje al otro. Lo único recortado es la
 * cantidad de polvo —4 000 puntos en GPU contra 220 en `Canvas` 2D— porque el
 * teléfono también es un aparato de dos núcleos para el usuario, y un orbe que
 * baja los cuadros por segundo se ve peor que un orbe con menos partículas.
 */
public class Orbe extends View {

    /** Los cuatro estados de la cara de PC (`Drive`), en el mismo orden de mérito. */
    public static final int REPOSO = 0;
    public static final int ESCUCHA = 1;
    public static final int PENSAR = 2;
    public static final int HABLA = 3;

    // -- los literales que se copian del TypeScript ------------------------------
    static final float SUAVIZADO = 8f;         // Core.tsx: `dt * 8`
    static final float CAIDA = 4.5f;           // Scene.tsx: `nivel *= exp(-dt * 4.5)`
    static final float RESPIRACION = 0.05f;    // Scene.tsx: `const idle = 0.05 + …`
    static final float RESPIRO_PENSAR = 0.22f; // Scene.tsx: `… + (target.spin > 1 ? 0.22 : 0)`
    static final float PULSO_RESP = 0.9f;      // Scene.tsx: `sin(t * 0.9)`
    static final float HABLA_BASE = 0.28f;     // Scene.tsx: `0.28 + 0.22 * |sin(t*7.1)|`
    static final float HABLA_ONDA = 0.22f;
    static final float HABLA_RAPIDA = 7.1f;
    static final float HABLA_LENTA = 2.3f;
    static final float ESCUCHA_BASE = 0.35f;   // Scene.tsx: `0.35 + 0.3 * …`
    static final float ESCUCHA_ONDA = 0.3f;
    static final float ESCUCHA_LENTA = 0.7f;
    static final float ESCUCHA_RAPIDA = 5.0f;
    static final float EMPUJE = 0.35f;         // Particles.tsx: `1.0 + uLevel * 0.35`
    static final float TEMBLOR = 0.02f;        // Particles.tsx: `… * 0.02`
    static final float GIRO_REPOSO = 0.55f;    // palette.ts: `SPIN = { idle: 0.55, … }`
    static final float GIRO_PENSAR = 2.8f;     // palette.ts: `…, thinking: 2.8 }`
    static final float RADIO = 0.74f;          // Core.tsx: `float R = 0.74 + wob + grain + uLevel * 0.03`
    static final float GROSOR = 0.030f;        // Core.tsx: `band(r, R, 0.030)`
    static final float OSCILACION = 0.055f;    // Core.tsx: `wob = fbm(ring * 2.6 + …) * 0.055`
    static final float GRANILLA = 0.020f;      // Core.tsx: `grain = fbm(ring * 9.0 - …) * 0.020`
    static final float CRECIMIENTO = 0.03f;    // Core.tsx: `+ uLevel * 0.03`
    static final float CASCARON_INICIO = 1.9f; // Particles.tsx: `1.9 + pow(rand, 2) * 2.6`
    static final float CASCARON_ANCHO = 2.6f;
    static final int POLVO = 220;              // recorte honesto de los 4 000 de la GPU

    private final Paint pincel = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Path contorno = new Path();
    private final RectF marco = new RectF();
    private final float[] semilla = new float[POLVO];
    private final float[] angulo = new float[POLVO];
    private final float[] altura = new float[POLVO];
    private final float[] cascara = new float[POLVO];

    private int modo = REPOSO;
    private float nivel;
    private float empujado;           // el nivel que manda el micrófono, si hay
    private float fase;
    private float tiempo;
    private long ultimoNanosegundos;
    private boolean animando = true;

    public Orbe(Context contexto) {
        super(contexto);
        // El mismo `Random` con semilla fija: dos openings del APK se ven igual, y
        // así el polvo es reproducible en las capturas.
        Random dado = new Random(20261015L);
        for (int i = 0; i < POLVO; i++) {
            semilla[i] = dado.nextFloat();
            angulo[i] = dado.nextFloat() * 6.2831853f;
            altura[i] = dado.nextFloat() * 2f - 1f;
            // `1.9 + pow(rand, 2) * 2.6` normalizado a 0..1: el cascarón se aprieta
            // contra el reactor, que es como se ve en la cara de PC.
            cascara[i] = (float) (Math.pow(dado.nextDouble(), 2) * CASCARON_ANCHO);
        }
        setBackgroundColor(Paleta.FONDO);
    }

    /** El estado de la conversación: reposo, escuchando, pensando o hablando. */
    public void modo(int nuevo) {
        modo = nuevo;
        invalidar();
    }

    /**
     * El nivel de audio **de verdad** (0..1), que la cara de PC no tiene: el
     * navegador no entrega el volumen del micrófono durante el reconocimiento y
     * tiene que simularlo. Android sí lo da (`onRmsChanged`), así que aquí el orbe
     * se mueve con la voz de la dueña y no con una curva.
     */
    public void nivel(float nuevo) {
        empujado = Math.max(0f, Math.min(1f, nuevo));
        invalidar();
    }

    public void quieto(boolean detenido) {
        animando = !detenido;
        if (animando) {
            invalidar();
        }
    }

    /** El giro se acumula y no se deriva del reloj: la turbulencia ya ocurrida no se reescribe. */
    private void avanzar(float dt) {
        tiempo += dt;
        float meta = meta();
        empujado *= Math.exp(-dt * CAIDA);
        nivel += (Math.max(meta, empujado) - nivel) * Math.min(1f, dt * SUAVIZADO);
        float giro = modo == PENSAR ? GIRO_PENSAR : GIRO_REPOSO;
        fase += dt * (0.5f + nivel * 0.7f) * giro;
    }

    /** Las mismas cuatro fuentes que en `Scene.tsx`, con la misma fórmula. */
    private float meta() {
        // `const idle = 0.05 + (target.spin > 1 ? 0.22 : 0)`: cuando el giro es de
        // pensar (2,8) el reactor respira más fuerte. En el teléfono el equivalente
        // de `target.spin` es el modo, así que la condición se lee igual.
        float giro = modo == PENSAR ? GIRO_PENSAR : GIRO_REPOSO;
        float idle = RESPIRACION + (giro > 1f ? RESPIRO_PENSAR : 0f);
        float respiracion = (float) (Math.sin(tiempo * PULSO_RESP) * 0.5 + 0.5) * idle;
        float habla = modo == HABLA
                ? (float) (HABLA_BASE + HABLA_ONDA * Math.abs(Math.sin(tiempo * HABLA_RAPIDA))
                        * (0.6 + 0.4 * Math.sin(tiempo * HABLA_LENTA)))
                : 0f;
        float escucha = modo == ESCUCHA
                ? (float) (ESCUCHA_BASE + ESCUCHA_ONDA * Math.max(0f, (float) Math.sin(tiempo * ESCUCHA_LENTA))
                        * Math.abs(Math.sin(tiempo * ESCUCHA_RAPIDA)))
                : 0f;
        return Math.max(respiracion, Math.max(habla, escucha));
    }

    private void invalidar() {
        ultimoNanosegundos = 0L;
        postInvalidateOnAnimation();
    }

    @Override
    protected void onDraw(Canvas lienzo) {
        int ancho = getWidth(), alto = getHeight();
        if (ancho <= 0 || alto <= 0) {
            return;
        }
        long ahora = System.nanoTime();
        if (ultimoNanosegundos == 0L) {
            ultimoNanosegundos = ahora;
        }
        float dt = Math.min(0.05f, (ahora - ultimoNanosegundos) / 1_000_000_000f);
        ultimoNanosegundos = ahora;
        avanzar(dt);

        float cx = ancho / 2f, cy = alto / 2f;
        float mitad = Math.min(cx, cy);
        float escala = mitad * 0.62f;
        float push = (float) (1f + nivel * EMPUJE
                + Math.sin(tiempo * 2.0 + semilla[0] * 12.0) * TEMBLOR);

        // -- el corazón: cinco discos de radio creciente y alpha menguante -------
        // En la GPU es un `RadialGradient` de shader; en `Canvas` son discos, y el
        // color se mezcla a mano entre el cian del acento y el violeta de `night`.
        int caliente = mezclar(Paleta.CLARO, Paleta.CIAN, 0.35f + nivel * 0.4f);
        int cuerpo = mezclar(Paleta.VIOLETA, Paleta.CIAN, 0.45f + nivel * 0.45f);
        if (modo == PENSAR) {
            // El orbe tira a magenta mientras CORT piensa (THINKING_HOT).
            cuerpo = mezclar(cuerpo, Paleta.PENSAMIENTO, 0.55f);
            caliente = mezclar(caliente, Paleta.PENSAMIENTO, 0.30f);
        }
        pincel.setStyle(Paint.Style.FILL);
        for (int capa = 5; capa >= 1; capa--) {
            float fraccion = capa / 5f;
            pincel.setColor(mezclar(cuerpo, caliente, 1f - fraccion));
            pincel.setAlpha((int) (26 + fraccion * fraccion * 150 * (0.55 + nivel)));
            lienzo.drawCircle(cx, cy, escala * (0.22f + fraccion * 0.55f) * push, pincel);
        }

        // -- el anillo que respira: el `R` de Core.tsx con su oscilación y su grana
        contorno.rewind();
        int segmentos = 96;
        for (int i = 0; i <= segmentos; i++) {
            double a = i * 6.2831853 / segmentos;
            double oscilacion = Math.sin(a * 2.6 + fase * 0.22) * OSCILACION
                    + Math.sin(a * 9.0 - fase * 0.40) * GRANILLA;
            double r = (RADIO + (float) oscilacion + nivel * CRECIMIENTO) * escala * push;
            float x = (float) (cx + Math.cos(a) * r);
            float y = (float) (cy + Math.sin(a) * r);
            if (i == 0) {
                contorno.moveTo(x, y);
            } else {
                contorno.lineTo(x, y);
            }
        }
        contorno.close();
        pincel.setStyle(Paint.Style.STROKE);
        pincel.setStrokeWidth(Math.max(1.4f, escala * GROSOR * 2.2f));
        pincel.setColor(cuerpo);
        pincel.setAlpha((int) (120 + 135 * Math.min(1f, nivel * 2.2f)));
        lienzo.drawPath(contorno, pincel);
        // La pared interior, que es lo que hace que el aro se lea tubo y no línea.
        pincel.setStrokeWidth(Math.max(1f, escala * GROSOR));
        pincel.setColor(caliente);
        pincel.setAlpha(90);
        lienzo.drawPath(contorno, pincel);

        // -- el polvo del cascarón ------------------------------------------------
        pincel.setStyle(Paint.Style.FILL);
        for (int i = 0; i < POLVO; i++) {
            double anguloDelPunto = angulo[i] + fase * (0.35 + semilla[i] * 0.5);
            double radioDelPunto = (CASCARON_INICIO + cascara[i]) / (CASCARON_INICIO + CASCARON_ANCHO);
            float plano = (float) (1 - altura[i] * altura[i]);
            double r = radioDelPunto * escala * 1.65 * push;
            float x = (float) (cx + Math.cos(anguloDelPunto) * r * Math.sqrt(Math.max(0.05, plano)));
            float y = (float) (cy + Math.sin(anguloDelPunto) * r * 0.62 + altura[i] * escala * 0.34);
            pincel.setColor(Paleta.POLVO);
            pincel.setAlpha((int) (30 + 190 * semilla[i] * (0.35 + nivel * 0.9)));
            lienzo.drawCircle(x, y, Math.max(1f, escala * 0.012f * (0.6 + semilla[i])), pincel);
        }

        // Un aro fino de vidrio alrededor, como el de la marca: ancla el orbe a la
        // identidad del proyecto cuando el nivel cae a cero.
        marco.set(cx - escala * 1.06f, cy - escala * 1.06f, cx + escala * 1.06f, cy + escala * 1.06f);
        pincel.setStyle(Paint.Style.STROKE);
        pincel.setStrokeWidth(Math.max(1f, mitad * 0.012f));
        pincel.setColor(Paleta.BORDE);
        pincel.setAlpha(200);
        lienzo.drawArc(marco, fase * 57f % 360f, 250f, false, pincel);

        if (animando) {
            ultimoNanosegundos = System.nanoTime();
            postInvalidateOnAnimation();
        }
    }

    /** Mezcla dos ARGB sin depender de `ArgbEvaluator` (es de `android.animation`, y esto corre en `onDraw`). */
    static int mezclar(int desde, int hasta, float fraccion) {
        float f = Math.max(0f, Math.min(1f, fraccion));
        int a = (int) (((desde >>> 24 & 0xFF) * (1 - f) + (hasta >>> 24 & 0xFF) * f));
        int r = (int) (((desde >> 16 & 0xFF) * (1 - f) + (hasta >> 16 & 0xFF) * f));
        int g = (int) (((desde >> 8 & 0xFF) * (1 - f) + (hasta >> 8 & 0xFF) * f));
        int b = (int) (((desde & 0xFF) * (1 - f) + (hasta & 0xFF) * f));
        return (a << 24) | (r << 16) | (g << 8) | b;
    }
}
