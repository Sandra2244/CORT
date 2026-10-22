package com.cort.ia;

/*
 * El **baldosín de la cortina rápida** — «CORT escucha» (ronda 2.4.1).
 *
 * Por qué existe: hasta ahora las dos puertas que tenía la dueña eran el icono
 * del cajón y el gesto del asistente, y el gesto del asistente sólo funciona si
 * el fabricante deja que CORT sea la app de asistencia predeterminada. Un
 * `TileService` no pide ese favor a nadie: se arrastra desde «Editar los ajustes
 * rápidos», se pulsa, y CORT se abre ya escuchando. Cero permisos nuevos — lo que
 * lista el baldosín es `android.permission.BIND_QUICK_SETTINGS_TILE` en el
 * `<service>` del manifiesto, que es una *obligación* del servicio, no algo que
 * se le pida a ella.
 *
 * Todo lo de abajo está escrito con la misma regla que el resto del APK: sin
 * AndroidX. `TileService` es público desde Android 7.0 (API 24) y este App
 * mínimo es 26, así que no hace falta ninguna biblioteca.
 *
 * Dos cosas que no se pueden comprobar en el portátil y se dejan dichas:
 * el icono del baldosín debe ser **monocromo** (Android lo tiñe), por eso se usa
 * el `ic_btn_speak_now` del sistema y no el anillo del launcher — el anillo con
 * alpha sale como una mancha negra en casi todos los lanzadores. Y con la pantalla
 * bloqueada Android no deja arrancar una actividad desde un baldosín: se pide el
 * `unlockAndRun` (API 30) para que el gesto se complete después de desbloquear,
 * en vez de tragar el toque en silencio.
 */

import android.app.PendingIntent;
import android.content.Intent;
import android.graphics.drawable.Icon;
import android.os.Build;
import android.service.quicksettings.Tile;
import android.service.quicksettings.TileService;

public class Panel extends TileService {

    /** Un toque abajo: la cara aparece y el micro se abre. */
    @Override
    public void onClick() {
        super.onClick();
        abreYCortaBaldosin();
    }

    /**
     * El viaje, con el método que exista en el teléfono.
     *
     * `startActivityAndCollapse(Intent)` es el **nuevo** (Android 14): con
     * `targetSdk` 34 es el que recomienda Google. `startActivityAndCollapse(PendingIntent)`
     * es el antiguo y sigue funcionando —está obsoleto, no borrado.
     */
    private void via(Intent abrir) {
        if (Build.VERSION.SDK_INT >= 34) startActivityAndCollapse(abrir);
        else startActivityAndCollapse(pendienteDe(abrir));
    }

    /**
     * Se llama así, con el plan B dentro de un `try/catch`, por lo que midió el
     * pipeline de `v0.2.26-demo`: `unlockAndRun` **no** recibe un `PendingIntent`,
     * recibe un `Runnable`, y `javac` lo paró con «PendingIntent cannot be converted
     * to Runnable». Escrito con la firma de verdad, el encargo es un trozo de código
     * que Android ejecuta justo después de que la dueña desbloquee.
     *
     * `startActivity`: el último recurso, que en algunas capas de fabricante es lo
     * único que no lanza `SecurityException` cuando el baldosín se pulsa con la
     * pantalla recién encendida. Si ni eso puede, el toque se pierde pero CORT no se
     * cierra en la cara: un baldosín mudo es mejor que un asistente que revienta.
     */
    private void abreYCortaBaldosin() {
        Intent abrir = new Intent(this, MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_REORDER_TO_FRONT)
                .putExtra(MainActivity.PIDE_ESCUCHAR, true);
        try {
            if (Build.VERSION.SDK_INT >= 30 && isLocked()) {
                // Con el teléfono bloqueado Android no deja lanzar actividades desde
                // un baldosín: se deja encargado el viaje para después del desbloqueo.
                unlockAndRun(() -> via(abrir));
                return;
            }
            via(abrir);
        } catch (Exception noPuede) {
            try {
                startActivity(abrir);
            } catch (Exception tampoco) {
                // Nada que avisar: la dueña acaba de pulsar y verá si se abrió.
            }
        }
    }

    /** `FLAG_IMMUTABLE` es obligatorio desde Android 12 para un pendiente de actividad. */
    private PendingIntent pendienteDe(Intent abrir) {
        return PendingIntent.getActivity(this, 0, abrir,
            PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
    }

    /**
     * Android llama aquí cada vez que la cortina se abre (y también al crear el
     * baldosín). Aprovechamos para poner el rótulo y el icono desde código: así el
     * manifiesto no depende de un drawable propio que `compilar.sh` regenera en
     * cada pipeline, y el baldosín se tiñe del color del sistema.
     *
     * El estado se deja `INACTIVE` a propósito. Sería mentir ponerlo `ACTIVE`
     * mientras CORT escucha: el micrófono se cierra solo al terminar la frase, el
     * baldosín no se entera de eso desde su proceso, y un azul encendido que nunca
     * se apaga es peor que un gris honesto.
     */
    @Override
    public void onStartListening() {
        Tile baldosin = getQsTile();
        if (baldosin == null) return;
        baldosin.setLabel("CORT escucha");
        try {
            baldosin.setIcon(Icon.createWithResource(this, android.R.drawable.ic_btn_speak_now));
        } catch (Exception sinIcono) {
            // Sin icono el sistema usa el de la app: se ve, sólo es más feo.
        }
        baldosin.setState(Tile.STATE_INACTIVE);
        baldosin.updateTile();
    }
}
