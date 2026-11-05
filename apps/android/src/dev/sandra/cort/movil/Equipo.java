package dev.sandra.cort.movil;

import android.app.Activity;
import android.content.Context;
import android.content.pm.ApplicationInfo;
import android.os.BatteryManager;
import android.os.Build;
import android.os.Bundle;
import android.os.StatFs;
import android.text.TextUtils;
import android.view.Gravity;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.app.ActivityManager;
import java.io.File;
import java.util.Arrays;

/**
 * El aparato dicho con números (U1, y lo que desbloquea el cerebro local). El modelo
 * que la dueña dio pesa 752 880 160 bytes; meterlo en el teléfono o no depende de
 * cuánta RAM libre tenga ESTE Galaxy A16 encendido, con sus apps abiertas, y eso no se
 * sabe desde un PC. Esta pantalla lee lo mismo que va a mirar la puerta del motor y lo
 * imprime entero para copiarlo en un informe.
 *
 * Nada de esto se manda a ningún sitio: se queda en la pantalla.
 */
public class Equipo extends Activity {

    /** El modelo q2_k que tiene que caber, en bytes. */
    private static final long MODELO_BYTES = 752_880_160L;

    @Override
    protected void onCreate(Bundle guardado) {
        super.onCreate(guardado);
        getWindow().getDecorView().setBackgroundColor(Paleta.FONDO);

        ScrollView desplazable = new ScrollView(this);
        LinearLayout pantalla = new LinearLayout(this);
        pantalla.setOrientation(LinearLayout.VERTICAL);
        int pad = dp(22);
        pantalla.setPadding(pad, pad, pad, pad);
        desplazable.addView(pantalla, new LinearLayout.LayoutParams(-1, -2));
        setContentView(desplazable);

        TextView titulo = texto("EL APARATO, MEDIDO", 13f, Paleta.CIAN);
        titulo.setLetterSpacing(0.12f);
        pantalla.addView(titulo);

        TextView cifras = texto(mide(), 15f, Paleta.CLARO);
        cifras.setTextIsSelectable(true);           // la dueña copia esto para el informe
        cifras.setLineSpacing(0f, 1.35f);
        pantalla.addView(cifras, conMargen());

        Button volver = boton("Volver");
        volver.setOnClickListener(v -> finish());
        pantalla.addView(volver, conMargen());
    }

    private String mide() {
        StringBuilder cuadro = new StringBuilder();

        ActivityManager memoria = (ActivityManager) getSystemService(Context.ACTIVITY_SERVICE);
        ActivityManager.MemoryInfo libre = new ActivityManager.MemoryInfo();
        memoria.getMemoryInfo(libre);
        long totalRam = totalRamKb() * 1024L;
        cuadro.append("aparato: ").append(Build.MANUFACTURER).append(' ').append(Build.MODEL)
                .append(" · Android ").append(Build.VERSION.RELEASE)
                .append(" (API ").append(Build.VERSION.SDK_INT).append(")\n");
        cuadro.append("RAM total: ").append(mb(totalRam)).append(" MB · libre ahora: ")
                .append(mb(libre.availMem)).append(" MB · umbral bajo: ")
                .append(mb(libre.threshold)).append(" MB\n");
        cuadro.append("núcleos: ").append(Runtime.getRuntime().availableProcessors())
                .append(" · instrucciones: ").append(TextUtils.join(", ", Build.SUPPORTED_ABIS))
                .append('\n');
        cuadro.append("NEON (armeabi-v7a): ").append(neon()).append('\n');

        File datos = getDataDir();
        StatFs disco = new StatFs(datos.getPath());
        long libreDisco = disco.getLongAvailableBytes();
        cuadro.append("almacenamiento de la app: ").append(mb(libreDisco))
                .append(" MB libres\n");

        cuadro.append("\n--- el cerebro local ---\n");
        cuadro.append("modelo q2_k de 1,5 B: ").append(mb(MODELO_BYTES)).append(" MB\n");
        cuadro.append("cabe en el disco: ").append(siNo(libreDisco > MODELO_BYTES + 100_000_000L))
                .append(" (sobran ").append(mb(libreDisco - MODELO_BYTES)).append(" MB)\n");
        // Regla de la puerta: el modelo se mapea en RAM y la caché clave-valor crece con
        // la conversación; se pide el doble del archivo por encima de lo que ya usa el
        // sistema. Con menos, CORT dice que no y usa el cerebro de la PC.
        long haceFalta = MODELO_BYTES * 2;
        cuadro.append("RAM libre para sostenerlo: ").append(haceFalta / 1024 / 1024).append(" MB\n");
        cuadro.append("hoy se puede intentar: ").append(siNo(libre.availMem > haceFalta)).append('\n');

        BatteryManager pila = (BatteryManager) getSystemService(Context.BATTERY_SERVICE);
        int nivel = pila.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY);
        cuadro.append("\n--- la pila ---\n").append("carga: ").append(nivel).append(" %\n");

        cuadro.append("--- la boca y el oído ---\n");
        cuadro.append("motor de voz de Android: ").append(vozDelSistema()).append('\n');
        cuadro.append("modelo de español dentro del APK: ").append(siNo(motorLocal())).append('\n');

        ApplicationInfo info = getApplicationInfo();
        cuadro.append("\n--- la casa ---\n").append("targetSdk: ").append(info.targetSdkVersion)
                .append(" · densidad: ").append(getResources().getDisplayMetrics().density)
                .append("x · pantalla: ").append(getResources().getDisplayMetrics().widthPixels)
                .append('x').append(getResources().getDisplayMetrics().heightPixels).append(" px\n");
        return cuadro.toString();
    }

    /** MemTotal de /proc/meminfo: `totalMem` del ActivityManager está redondeado por arriba. */
    private long totalRamKb() {
        try {
            for (String linea : new String(java.nio.file.Files.readAllBytes(
                    new File("/proc/meminfo").toPath())).split("\n")) {
                if (linea.startsWith("MemTotal:")) {
                    return Long.parseLong(linea.replaceAll("\\D", ""));
                }
            }
        } catch (Exception sinProc) {
            // sin /proc se queda en cero y la pantalla lo dice como número, no como excusa
        }
        return 0L;
    }

    /** El bit de NEON no lo publica Android: se deduce del ABI y se comprueba cargando la property. */
    private String neon() {
        boolean hayV7a = Arrays.asList(Build.SUPPORTED_ABIS).contains("armeabi-v7a");
        try {
            Class<?> sistema = Class.forName("android.os.SystemProperties");
            Object cpu = sistema.getMethod("get", String.class)
                    .invoke(null, "ro.hardware.cpuvariant");
            if (cpu != null && !String.valueOf(cpu).isEmpty()) {
                return "ABI v7a: " + (hayV7a ? "sí" : "no") + " · cpuvariant " + cpu;
            }
        } catch (Exception sinProperty) {
            // la property no existe en todos los fabricantes: abajo se dice sólo el ABI
        }
        return "por el ABI: " + (hayV7a ? "v7a presente" : "sin v7a")
                + " · " + (Build.SUPPORTED_ABIS[0].contains("arm64") ? "arm64 trae NEON" : "sin arm64");
    }

    /** El motor de voz que el sistema tiene asignado; es lo que va a sonar en el A16. */
    private String vozDelSistema() {
        try {
            String asignado = android.provider.Settings.Secure.getString(
                    getContentResolver(), "tts_default_synth");
            return asignado == null || asignado.isEmpty() ? "sin motor asignado" : asignado;
        } catch (Exception sinAjuste) {
            return "no se pudo leer el motor asignado";
        }
    }

    /** La misma ruta que usa `Motor`: el español descomprimido en el almacenamiento de la app. */
    private boolean motorLocal() {
        return new File(getFilesDir(), "motor/vosk-model-small-es-0.42").isDirectory();
    }

    private static String siNo(boolean cumple) {
        return cumple ? "sí" : "no";
    }

    private static long mb(long bytes) {
        return bytes / 1024 / 1024;
    }

    private TextView texto(String contenido, float tamanio, int color) {
        TextView etiqueta = new TextView(this);
        etiqueta.setText(contenido);
        etiqueta.setTextSize(tamanio);
        etiqueta.setTextColor(color);
        etiqueta.setGravity(Gravity.START);
        return etiqueta;
    }

    private Button boton(String rotulo) {
        Button nuevo = new Button(this);
        nuevo.setText(rotulo);
        nuevo.setTextColor(Paleta.CIAN);
        nuevo.setBackgroundColor(0xFF0F2B3A);
        nuevo.setTextSize(17f);
        return nuevo;
    }

    private LinearLayout.LayoutParams conMargen() {
        LinearLayout.LayoutParams caja = new LinearLayout.LayoutParams(-1, -2);
        caja.topMargin = dp(18);
        return caja;
    }

    private int dp(float valor) {
        return Math.round(valor * getResources().getDisplayMetrics().density);
    }
}
