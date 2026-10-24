package com.cort.ia;

/*
 * El oído del despertador: lo que Android llama cuando llega la hora.
 *
 * Un `BroadcastReceiver` de tres líneas a propósito. Todo lo que se puede contar
 * —el aviso, la canción, la rutina, el cuadro de la cara— vive en `Alarma.java`,
 * que es donde se puede leer de arriba abajo sin saltar de fichero. Aquí sólo se
 * traduce la acción del `PendingIntent` a la orden que toca.
 *
 * No pide permiso ni se exporta: el único que puede mandarle algo es el
 * `PendingIntent` de esta misma app (`android:exported="false"`). Sin
 * `RECEIVE_BOOT_COMPLETED` no se rearma al reiniciar; es una decisión escrita en
 * `Alarma`, no un olvido.
 */

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public class AlarmaSuena extends BroadcastReceiver {

    @Override
    public void onReceive(Context c, Intent i) {
        if (c == null) return;
        String que = i == null || i.getAction() == null ? Alarma.ACCION : i.getAction();
        if (Alarma.ACCION_DETENER.equals(que)) {
            Alarma.detener(c);
            return;
        }
        if (Alarma.ACCION_POSPONER.equals(que)) {
            Alarma.posponer(c);
            return;
        }
        Alarma.sono(c);
    }
}
