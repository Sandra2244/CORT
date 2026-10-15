package dev.sandra.cort;

import android.animation.ValueAnimator;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.view.View;
import android.view.animation.LinearInterpolator;

/**
 * El anillo de la marca, dibujado con `Canvas`: la misma geometría de
 * `scripts/marca.py` (banda cian de radio 0,68 del semitamaño, halo violeta por
 * dentro y núcleo caliente en el centro) girando despacio.
 *
 * Gira porque una pantalla de arranque quieta es un formulario, y CORT se
 * presenta. Desde `v0.15.0` vive en su archivo: lo gira igual en la pantalla de
 * estreno y en la cara nativa del teléfono, y un `View` que se duplica en dos
 * clases es un `View` que se desincroniza.
 */
public class Anillo extends View {
    private final Paint pincel = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final RectF aro = new RectF();
    private float angulo;
    private ValueAnimator giro;

    public Anillo(Context contexto) {
        super(contexto);
        setBackgroundColor(Paleta.FONDO);
        giro = ValueAnimator.ofFloat(0f, 360f);
        giro.setDuration(4200L);
        giro.setRepeatCount(ValueAnimator.INFINITE);
        giro.setInterpolator(new LinearInterpolator());
        giro.addUpdateListener(animacion -> {
            angulo = (float) animacion.getAnimatedValue();
            invalidate();
        });
        giro.start();
    }

    /** El giro se para si la vista se va de la ventana: sin esto el hilo de animación sigue vivo. */
    public void quieto(boolean detenido) {
        if (giro == null) {
            return;
        }
        if (detenido) {
            giro.cancel();
        } else if (!giro.isRunning()) {
            giro.start();
        }
    }

    @Override
    protected void onDetachedFromWindow() {
        super.onDetachedFromWindow();
        if (giro != null) {
            giro.cancel();
        }
    }

    @Override
    protected void onDraw(Canvas lienzo) {
        float cx = getWidth() / 2f;
        float cy = getHeight() / 2f;
        float mitad = Math.min(cx, cy);
        float radio = mitad * 0.68f;
        aro.set(cx - radio, cy - radio, cx + radio, cy + radio);
        pincel.setStyle(Paint.Style.STROKE);
        // Halo violeta: más grueso, más suave y por dentro de la banda, como en
        // el PNG. Alpha fijo porque aquí no hay que sumar exposición, hay que dar
        // profundidad con dos trazos.
        pincel.setColor(Paleta.VIOLETA);
        pincel.setAlpha(90);
        pincel.setStrokeWidth(mitad * 0.11f);
        lienzo.drawArc(aro, angulo + 150f, 210f, false, pincel);
        // Banda cian: el trazo fino, con un tercio del aro abierto para que el
        // giro se vea.
        pincel.setAlpha(255);
        pincel.setStrokeWidth(mitad * 0.035f);
        lienzo.drawArc(aro, angulo, 240f, false, pincel);
        // Núcleo caliente.
        pincel.setColor(Paleta.CLARO);
        pincel.setStyle(Paint.Style.FILL);
        lienzo.drawCircle(cx, cy, mitad * 0.07f, pincel);
    }
}
