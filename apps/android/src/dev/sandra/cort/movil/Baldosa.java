package dev.sandra.cort.movil;

import android.app.PendingIntent;
import android.content.Intent;
import android.os.Build;
import android.service.quicksettings.Tile;
import android.service.quicksettings.TileService;

/** La baldosa refleja la vigilia real; si está activa, un toque la detiene. */
public class Baldosa extends TileService {
    private final EscuchaEstadoGlobal.Oyente oyente = (estado, motivo) -> pintar();
    private boolean observando;

    @Override
    public void onStartListening() {
        super.onStartListening();
        if (!observando) {
            EscuchaEstadoGlobal.observar(oyente);
            observando = true;
        }
        pintar();
    }

    @Override
    public void onStopListening() {
        quitaObservador();
        super.onStopListening();
    }

    @Override
    public void onDestroy() {
        quitaObservador();
        super.onDestroy();
    }

    private void quitaObservador() {
        if (observando) {
            EscuchaEstadoGlobal.desobservar(oyente);
            observando = false;
        }
    }

    private void pintar() {
        Tile baldosa = getQsTile();
        if (baldosa == null) {
            return;
        }
        boolean activa = ServicioEscucha.montada() && EscuchaEstadoGlobal.estado().activa();
        baldosa.setState(activa ? Tile.STATE_ACTIVE : Tile.STATE_INACTIVE);
        baldosa.setLabel(activa ? "CORT te escucha" : "Abrir CORT");
        baldosa.updateTile();
    }

    @Override
    public void onClick() {
        super.onClick();
        if (ServicioEscucha.montada() && EscuchaEstadoGlobal.estado().activa()) {
            ServicioEscucha.cambia(this, false);
            pintar();
            return;
        }
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
