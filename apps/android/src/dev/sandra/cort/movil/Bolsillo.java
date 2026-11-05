package dev.sandra.cort.movil;

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * El bolsillo (F17, mitad teléfono): abrir el móvil y ver qué le debe la PC.
 *
 * No son los recuerdos —ésos viajan por el enlace de F14— sino lo pendiente de verdad:
 * recordatorios con los minutos que faltan, la lista, las notas y cómo está la máquina,
 * leído en /proc por el puente. Si la PC está apagada esto no funciona y la pantalla lo
 * dice con la palabra que toca: **no disponible**. Levantar la PC apagada no está: en
 * esta laptop el `eth0` (r8169) no declara Wake-on y el Wi-Fi (rtl8723be) no anuncia
 * WoWLAN, medido el 2026-11-04.
 */
public class Bolsillo extends Activity {

    private SharedPreferences prefs;
    private TextView estado;
    private LinearLayout filas;
    private volatile boolean cerrado;

    @Override
    protected void onCreate(Bundle guardado) {
        super.onCreate(guardado);
        prefs = getSharedPreferences("cort", MODE_PRIVATE);
        getWindow().getDecorView().setBackgroundColor(Paleta.FONDO);

        ScrollView desplazable = new ScrollView(this);
        LinearLayout pantalla = new LinearLayout(this);
        pantalla.setOrientation(LinearLayout.VERTICAL);
        int pad = dp(22);
        pantalla.setPadding(pad, pad, pad, pad);
        desplazable.addView(pantalla, new LinearLayout.LayoutParams(-1, -2));
        setContentView(desplazable);

        TextView titulo = texto("EL BOLSILLO · LO QUE DEBE LA PC", 13f, Paleta.CIAN);
        titulo.setLetterSpacing(0.12f);
        pantalla.addView(titulo);

        estado = texto("", 15f, Paleta.AVISO);
        estado.setLineSpacing(0f, 1.3f);
        pantalla.addView(estado, conMargen());

        filas = new LinearLayout(this);
        filas.setOrientation(LinearLayout.VERTICAL);
        pantalla.addView(filas, conMargen());

        Button refrescar = boton("Volver a preguntar");
        refrescar.setOnClickListener(v -> baja());
        pantalla.addView(refrescar, caja(56));

        Button volver = boton("Volver");
        volver.setOnClickListener(v -> finish());
        pantalla.addView(volver, caja(56));

        baja();
    }

    private void baja() {
        final String enlace = prefs.getString("url", "");
        final String url = Puente.urlDelBolsillo(enlace);
        if (url == null || !url.contains("?token=")) {
            estado.setText("No hay enlace con la PC: sin la dirección y la llave que da el "
                    + "portátil no se puede preguntar nada.");
            return;
        }
        estado.setText("Preguntando a la PC…");
        Thread hilo = new Thread(() -> {
            try {
                HttpURLConnection conexion = (HttpURLConnection) new URL(url).openConnection();
                conexion.setConnectTimeout(8000);
                conexion.setReadTimeout(15000);
                conexion.setRequestMethod("GET");
                int codigo = conexion.getResponseCode();
                if (codigo == 401) {
                    estadoDesdeHilo("La PC rechazó la llave: el enlace que guardaste ya no "
                            + "sirve. Pide uno nuevo en el portátil.");
                    return;
                }
                if (codigo != 200) {
                    estadoDesdeHilo("La PC respondió " + codigo + ": no disponible.");
                    return;
                }
                final JSONObject cuadro = new JSONObject(lee(conexion.getInputStream()));
                pinta(cuadro);
            } catch (Exception algo) {
                estadoDesdeHilo("La PC no contestó (" + loQueDice(algo)
                        + "). Está apagada o fuera de la red.");
            }
        }, "cort-bolsillo");
        hilo.setDaemon(true);
        hilo.start();
    }

    private void pinta(final JSONObject cuadro) {
        final JSONArray pendientes = cuadro.optJSONArray("pendientes");
        final JSONArray compras = cuadro.optJSONArray("compras");
        final JSONArray notas = cuadro.optJSONArray("notas");
        final JSONObject maquina = cuadro.optJSONObject("maquina");
        runOnUiThread(() -> {
            if (cerrado) {
                return;
            }
            filas.removeAllViews();
            int cuantos = pendientes == null ? 0 : pendientes.length();
            estado.setText(cuantos == 0
                    ? "La PC no tiene nada pendiente. " + horaDelCuadro(cuadro)
                    : cuantos + " pendiente(s) en la PC" + (cuadro.optInt("vencidos") > 0
                        ? " y " + cuadro.optInt("vencidos") + " ya vencido(s)" : "") + ". "
                        + horaDelCuadro(cuadro));
            if (pendientes != null) {
                for (int i = 0; i < pendientes.length(); i++) {
                    JSONObject r = pendientes.optJSONObject(i);
                    anade(texto("· " + r.optString("texto") + "  —  en "
                            + r.optInt("minutos") + " min (" + r.optString("cuando") + ")",
                            16f, Paleta.CLARO));
                }
            }
            if (compras != null && compras.length() > 0) {
                anade(texto("Lista de compras: " + unira(compras, 8), 15f, Paleta.SUAVE));
            }
            if (notas != null && notas.length() > 0) {
                anade(texto("Notas: " + unira(notas, 6), 15f, Paleta.SUAVE));
            }
            if (maquina != null) {
                anade(texto("La PC: RAM libre " + maquina.optInt("ram_disponible_mb")
                        + " de " + maquina.optInt("ram_total_mb") + " MB · CPU "
                        + maquina.optString("cpu") + " % · " + maquina.optInt("nucleos")
                        + " núcleos · encendida " + minutosDe(maquina.optLong("despierto_s"))
                        + " min · " + maquina.optString("origen"), 14f, Paleta.AVISO));
            }
        });
    }

    private void anade(View vista) {
        LinearLayout.LayoutParams caja = new LinearLayout.LayoutParams(-1, -2);
        caja.topMargin = dp(8);
        filas.addView(vista, caja);
    }

    private static String unira(JSONArray lista, int maximo) {
        StringBuilder cuadro = new StringBuilder();
        for (int i = 0; i < Math.min(lista.length(), maximo); i++) {
            cuadro.append(cuadro.length() > 0 ? " · " : "").append(lista.optString(i));
        }
        if (lista.length() > maximo) {
            cuadro.append(" …");
        }
        return cuadro.toString();
    }

    private static String horaDelCuadro(JSONObject cuadro) {
        String hora = cuadro.optString("hora", "");
        return hora.isEmpty() ? "" : "A las " + hora + " de la PC.";
    }

    private static String minutosDe(long segundos) {
        return segundos <= 0 ? "?" : String.valueOf(segundos / 60);
    }

    private void estadoDesdeHilo(String dicho) {
        runOnUiThread(() -> estado.setText(dicho));
    }

    private String lee(InputStream entrada) throws Exception {
        ByteArrayOutputStream acumulado = new ByteArrayOutputStream();
        byte[] trozo = new byte[4096];
        int n;
        while ((n = entrada.read(trozo)) > 0) {
            acumulado.write(trozo, 0, n);
        }
        entrada.close();
        return new String(acumulado.toByteArray(), StandardCharsets.UTF_8);
    }

    private static String loQueDice(Exception e) {
        String mensaje = e.getMessage();
        return mensaje == null || mensaje.trim().isEmpty() ? e.getClass().getSimpleName() : mensaje;
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
        nuevo.setLetterSpacing(0.04f);
        return nuevo;
    }

    private LinearLayout.LayoutParams caja(int alto) {
        LinearLayout.LayoutParams medida = new LinearLayout.LayoutParams(-1, dp(alto));
        medida.topMargin = dp(12);
        return medida;
    }

    private LinearLayout.LayoutParams conMargen() {
        LinearLayout.LayoutParams caja = new LinearLayout.LayoutParams(-1, -2);
        caja.topMargin = dp(18);
        return caja;
    }

    private int dp(float valor) {
        return Math.round(valor * getResources().getDisplayMetrics().density);
    }

    @Override
    protected void onDestroy() {
        cerrado = true;
        super.onDestroy();
    }
}
