package com.cort.ia;

/*
 * El aparato a la vista: batería, memoria, almacenamiento, red, brillo, CPU y quién
 * es el teléfono. Lo que lee la ventana «02 · Entorno» cuando CORT corre en el
 * móvil, que hasta la ronda 2.2 no leía nada suyo: las barras de CPU/RAM/DISCO sólo
 * se llenaban preguntándole al portátil (`/api/status`), así que sin PC el panel
 * salía en blanco y eso es lo que ella notó como «sensores que no funcionan».
 *
 * Mismo criterio que en `Sentidos`: **se mide o se dice que no se sabe**. Cada clave
 * sale con su número real o con `-1`, y la cara pinta `—` cuando ve `-1`. Aquí no
 * hay ningún valor de adorno.
 *
 * Lo que usa, todo público en el SDK 34:
 * · batería → el `Intent` pegajoso de `ACTION_BATTERY_CHANGED` (no necesita permiso).
 * · memoria → `ActivityManager.MemoryInfo` (deprecado en 34 pero sigue siendo la
 *   única lectura pública; se marca `@SuppressWarnings` y se tolera el aviso).
 * · disco   → `StatFs` sobre la raíz de datos y sobre el almacenamiento público.
 * · red     → `ConnectivityManager` + `NetworkCapabilities`, igual que `Nube.hayRed`.
 *   Requiere `ACCESS_NETWORK_STATE` en el manifiesto: sin esa línea el sistema
 *   devuelve `null` y CORT diría «sin red» estando con Wi‑Fi, que es exactamente el
 *   fallo silencioso que `Acciones.estado()` evitaba callando la red.
 * · CPU     → delta de `/proc/stat` entre dos lecturas. La primera lectura no puede
 *   saber el delta, así que devuelve `-1` y la cara lo enseña como `—` hasta la
 *   siguiente.
 * · brillo  → `Settings.System.SCREEN_BRIGHTNESS` (0-255), que no es un secreto.
 */

import android.app.ActivityManager;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.os.BatteryManager;
import android.os.Build;
import android.os.Environment;
import android.os.StatFs;
import android.provider.Settings;

import java.io.BufferedReader;
import java.io.FileReader;

public class Aparato {

    private static Aparato unico;

    private long[] anteriorStat;        // {trabajando, total} del último /proc/stat

    private Aparato() { }

    static synchronized Aparato de(Context c) {
        if (unico == null) unico = new Aparato();
        return unico;
    }

    /** El JSON entero que pinta la cara. Las claves son el contrato con `hud.js`. */
    String estado(Context ctx) {
        int[] batt = bateria(ctx);
        long[] ram = ram(ctx);
        long[] disco = disco();
        int cpu = cpu();
        String red = red(ctx);
        int brillo = brillo(ctx);

        Json j = new Json();
        j.p("ok", true);
        j.n("bateria", batt[0]);
        j.n("cargando", batt[1]);
        j.n("battTemp", batt[2]);              // décimas de °C, tal cual las da Android
        j.s("salud", batt[3] == -1 ? "" : salud(batt[3]));
        j.s("tecnologia", batt[4] == -1 ? "" : tecnologia(ctx));
        j.n("ramLibreMB", ram[0]);
        j.n("ramTotalMB", ram[1]);
        j.n("ramPct", ram[2]);
        j.n("discoLibreMB", disco[0]);
        j.n("discoTotalMB", disco[1]);
        j.n("discoPct", disco[2]);
        j.n("cpu", cpu);
        j.s("red", red);
        j.n("brillo", brillo);
        j.s("modelo", Build.MANUFACTURER + " " + Build.BRAND + " " + Build.MODEL);
        j.s("android", Build.VERSION.RELEASE);
        j.n("sdk", Build.VERSION.SDK_INT);
        j.s("fabricante", Build.MANUFACTURER);
        j.p("memoriaBaja", ramPobre(ctx));
        j.s("dice", dice(batt[0], red, cpu));
        return j.texto();
    }

    private String dice(int batt, String red, int cpu) {
        StringBuilder b = new StringBuilder();
        b.append(batt >= 0 ? "Batería al " + batt + "%" : "Batería sin leer");
        if (batt >= 0) b.append(red.isEmpty() ? " y sin conexión" : ", conectada por " + red);
        b.append(cpu >= 0 ? " · CPU al " + cpu + "%" : " · CPU sin medir todavía");
        if (batt >= 0 && batt <= 15) b.append(" · vas justa: CORT se guarda el micrófono en cuanto Android lo pida");
        return b.toString();
    }

    /* ────────────────────────────── batería ────────────────────────────── */

    /** {nivel, cargando (0/1), temperatura en décimas, estado, plugged} — `-1` = no leído. */
    private int[] bateria(Context c) {
        int[] salida = { -1, 0, -1, -1, -1 };
        try {
            Intent i = c.getApplicationContext()
                .registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
            if (i == null) return salida;
            int nivel = i.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
            int escala = i.getIntExtra(BatteryManager.EXTRA_SCALE, -1);
            if (nivel >= 0 && escala > 0) salida[0] = Math.round(100f * nivel / escala);
            int plug = i.getIntExtra(BatteryManager.EXTRA_PLUGGED, 0);
            salida[1] = plug > 0 ? 1 : 0;
            salida[2] = i.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, -1);
            salida[3] = i.getIntExtra(BatteryManager.EXTRA_STATUS, -1);
            salida[4] = i.getIntExtra(BatteryManager.EXTRA_PLUGGED, -1);
        } catch (Exception elSistemaNoContesta) {
            return new int[] { -1, 0, -1, -1, -1 };
        }
        return salida;
    }

    private static String salud(int estado) {
        if (estado == BatteryManager.BATTERY_STATUS_CHARGING) return "cargando";
        if (estado == BatteryManager.BATTERY_STATUS_FULL) return "llena";
        if (estado == BatteryManager.BATTERY_STATUS_NOT_CHARGING) return "sin cargar";
        if (estado == BatteryManager.BATTERY_STATUS_DISCHARGING) return "descargando";
        return "";
    }

    private static String tecnologia(Context c) {
        try {
            Intent i = c.getApplicationContext()
                .registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
            return i == null ? "" : i.getStringExtra(BatteryManager.EXTRA_TECHNOLOGY);
        } catch (Exception noLoDice) {
            return "";
        }
    }

    /* ────────────────────────────── memoria ────────────────────────────── */

    @SuppressWarnings("deprecation")
    private long[] ram(Context c) {
        try {
            ActivityManager am = (ActivityManager) c.getApplicationContext()
                .getSystemService(Context.ACTIVITY_SERVICE);
            ActivityManager.MemoryInfo m = new ActivityManager.MemoryInfo();
            if (am == null) return new long[] { -1, -1, -1 };
            am.getMemoryInfo(m);
            long total = m.totalMem / (1024 * 1024);
            long libre = m.availMem / (1024 * 1024);
            int pct = total > 0 ? (int) Math.round(100.0 * (total - libre) / total) : -1;
            return new long[] { libre, total, pct };
        } catch (Exception noSePuedeLeer) {
            return new long[] { -1, -1, -1 };
        }
    }

    /**
     * Si el sistema está apretado de RAM. OJO: `ActivityManager` **no** tiene un
     * método `isLowMemory()` (lo dijo `javac` en el run 39685806249 de v0.2.17-demo:
     * `cannot find symbol`). Lo que existe es el campo `lowMemory` de `MemoryInfo`,
     * y lo rellena `getMemoryInfo`.
     */
    @SuppressWarnings("deprecation")
    private boolean ramPobre(Context c) {
        try {
            ActivityManager am = (ActivityManager) c.getApplicationContext()
                .getSystemService(Context.ACTIVITY_SERVICE);
            if (am == null) return false;
            ActivityManager.MemoryInfo m = new ActivityManager.MemoryInfo();
            am.getMemoryInfo(m);
            return m.lowMemory;
        } catch (Exception tampoco) {
            return false;
        }
    }

    /* ──────────────────────────── almacenamiento ────────────────────────── */

    /** {libreMB, totalMB, usadoPct} del almacenamiento interno del teléfono. */
    private long[] disco() {
        try {
            StatFs fs = new StatFs(Environment.getDataDirectory().getPath());
            long total = fs.getTotalBytes() / (1024 * 1024);
            long libre = fs.getAvailableBytes() / (1024 * 1024);
            int pct = total > 0 ? (int) Math.round(100.0 * (total - libre) / total) : -1;
            return new long[] { libre, total, pct };
        } catch (Exception elStatFsFall) {
            return new long[] { -1, -1, -1 };
        }
    }

    /* ──────────────────────────────── red ──────────────────────────────── */

    /** `wifi`, `celular`, `ethernet`, `otro` o `""` (sin red o sin permiso). */
    String red(Context c) {
        try {
            ConnectivityManager cm = (ConnectivityManager) c.getApplicationContext()
                .getSystemService(Context.CONNECTIVITY_SERVICE);
            if (cm == null) return "";
            Network n = cm.getActiveNetwork();
            if (n == null) return "";
            NetworkCapabilities cap = cm.getNetworkCapabilities(n);
            if (cap == null) return "otro";
            if (cap.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) return "wifi";
            if (cap.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR)) return "celular";
            if (cap.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET)) return "ethernet";
            return "otro";
        } catch (Exception elSistemaNoLoCuenta) {
            // Sin `ACCESS_NETWORK_STATE` declarada, `getActiveNetwork` devuelve `null`
            // y esto sale `""`. Por eso la línea está en el manifiesto.
            return "";
        }
    }

    /* ──────────────────────────────── CPU ──────────────────────────────── */

    /**
     * % de ocupación entre la lectura anterior y ésta, sacado de `/proc/stat`.
     * `-1` la primera vez (no hay delta que calcular) y si el archivo no se deja.
     */
    private int cpu() {
        try {
            BufferedReader r = new BufferedReader(new FileReader("/proc/stat"), 256);
            String linea;
            try {
                linea = r.readLine();
            } finally {
                r.close();
            }
            if (linea == null || !linea.startsWith("cpu")) return -1;
            String[] partes = linea.trim().split("\\s+");
            if (partes.length < 5) return -1;
            long trabajando = 0, inactivo = 0, total = 0;
            for (int i = 1; i < partes.length; i++) {
                long v;
                try { v = Long.parseLong(partes[i]); } catch (Exception esaNoEsNumero) { continue; }
                total += v;
                // Campos 4 (idle) y 5 (iowait) son el tiempo en que la CPU no trabaja.
                if (i == 4 || i == 5) inactivo += v;
            }
            trabajando = total - inactivo;
            long[] antes = anteriorStat;
            anteriorStat = new long[] { trabajando, total };
            if (antes == null) return -1;
            long dTotal = total - antes[1];
            long dTrabajo = trabajando - antes[0];
            if (dTotal <= 0) return -1;
            int pct = (int) Math.round(100.0 * dTrabajo / dTotal);
            return Math.max(0, Math.min(100, pct));
        } catch (Exception elProcNoSeLee) {
            return -1;
        }
    }

    /* ─────────────────────────────── brillo ─────────────────────────────── */

    /** 0-100 del brillo de la pantalla, o `-1` si el fabricante no lo deja leer. */
    private int brillo(Context c) {
        try {
            int v = Settings.System.getInt(c.getApplicationContext().getContentResolver(),
                                           Settings.System.SCREEN_BRIGHTNESS, -1);
            return v < 0 ? -1 : Math.round(100f * v / 255f);
        } catch (Exception noLoDeja) {
            return -1;
        }
    }

    /* ───────────────────────────── el JSON ─────────────────────────────── */

    /**
     * El mismo cuaderno a mano que en `Acciones` (`j.p`/`j.n`/`j.s`), reducido a lo
     * que usa esta clase. `n` escribe número tal cual (los `-1` se ven como `-1`,
     * que es lo que la cara traduce a `—`) y `s` escapa texto.
     */
    private static final class Json {
        private final StringBuilder b = new StringBuilder("{");
        private boolean lleno;

        private void coma() { if (lleno) b.append(','); lleno = true; }

        void p(String k, boolean v) { coma(); b.append('"').append(k).append("\":").append(v); }
        void n(String k, long v) { coma(); b.append('"').append(k).append("\":").append(v); }
        void s(String k, String v) { coma(); b.append('"').append(k).append("\":").append(texto(v)); }

        String texto() { return b.append('}').toString(); }

        private static String texto(String s) {
            if (s == null) return "\"\"";
            StringBuilder q = new StringBuilder("\"");
            for (int i = 0; i < s.length(); i++) {
                char c = s.charAt(i);
                if (c == '"') q.append("\\\"");
                else if (c == '\\') q.append("\\\\");
                else if (c == '\n') q.append("\\n");
                else if (c == '\r') q.append("\\r");
                else if (c == '\t') q.append("\\t");
                else if (c < 0x20) q.append(String.format(java.util.Locale.US, "\\u%04x", (int) c));
                else q.append(c);
            }
            return q.append('"').toString();
        }
    }
}
