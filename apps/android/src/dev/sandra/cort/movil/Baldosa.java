package dev.sandra.cort.movil;

import android.app.PendingIntent;
import android.content.Intent;
import android.os.Build;
import android.service.quicksettings.Tile;
import android.service.quicksettings.TileService;

/**
 * La baldosa del panel rápido (U2): un toque arriba del todo y CORT está escuchando,
 * sin buscar el icono entre las páginas del lanzador. Es lo más cerca que se puede
 * estar de «llamarla» sin usar la voz, y no cuesta permiso ninguno.
 *
 * Con Android 14 (`SDK_INT >= 34`) `startActivityAndCollapse` pide un `PendingIntent`
 * en vez de un `Intent` suelto: la firma vieja sigue compilando pero el sistema ignora
 * la llamada y la baldosa se queda muerta. Es la diferencia que hay entre una baldosa
 * que abre la escucha y una que no hace nada en el teléfono nuevo de la dueña.
 */
public class Baldosa extends TileService {

    @Override
    public void onStartListening() {
        super.onStartListening();
        Tile baldosa = getTile();
        if (baldosa != null) {
            baldosa.setState(Tile.STATE_INACTIVE);
            baldosa.setLabel("CORT te escucha");
            baldosa.updateTile();
        }
    }

    @Override
    public void onClick() {
        super.onClick();
        Intent abrir = new Intent(this, MainActivity.class);
        abrir.putExtra(MainActivity.PIDE_ESCUCHAR, true);
        abrir.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startActivityAndCollapse(PendingIntent.getActivity(this, 1, abrir,
                    PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT));
            return;
        }
        startActivityAndCollapse(abrir);
    }
}
