package dev.sandra.cort;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.pm.PackageManager;
import android.graphics.Typeface;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * La cara de CORT **cuando no hay portátil**. Hasta `v0.14.4` el teléfono sin
 * LAN no tenía cara: se abría y se quedaba en un formulario pidiendo un enlace,
 * que es justo lo que la dueña pidió quitar («no puede iniciar con su animación
 * como una IA normal»).
 *
 * Es `LinearLayout` + `TextView` + `Canvas`, no React: el WebView sigue siendo
 * la cara buena cuando el portátil está encendido, y aquí lo que importa es que
 * haya un sitio donde hablar y que conteste. La paleta y el anillo son los
 * mismos (`Paleta`, `Anillo`), para que las dos caras se reconozcan.
 *
 * El lazo es el de siempre —oír, proponer, ejecutar, medir, decir— y la parte
 * que no se resolvió sola se devuelve a la dueña: si CORT no conoce la frase,
 * **propone aprenderla** y sólo se guarda si ella aprueba la acción.
 */
public class Cara implements Voz.AlOir {
    /**
     * Acciones que una habilidad aprendida puede tener. La lista es corta **a
     * propósito**: una habilidad aprendida se guarda con la frase entera como
     * `resto`, así que sólo valen las cuatro que contestan sin necesitar ningún
     * dato. Aprender «modo cine» → `alarma` daría una alarma a las `null`, y
     * aprenderla → `guardar` anotaría la propia frase como un hecho.
     */
    private static final List<String> APRENDIBLES = Arrays.asList(
            "decir", "hora", "fecha", "listar");

    private final Activity actividad;
    private final Recuerdos recuerdos;
    private final Cerebro cerebro;
    private final Acciones acciones;
    private final Nube nube;
    private final Voz voz;

    private LinearLayout registro;
    private ScrollView hoja;
    private TextView estado;
    private EditText campo;
    private TextView micro;
    private boolean escuchando;

    public Cara(Activity actividad) {
        this.actividad = actividad;
        this.recuerdos = new Recuerdos(actividad.getApplicationContext());
        this.cerebro = new Cerebro(actividad.getApplicationContext(), recuerdos);
        this.acciones = new Acciones(actividad, recuerdos);
        this.nube = new Nube(actividad.getApplicationContext());
        this.voz = new Voz(actividad.getApplicationContext());
        sembrar();
    }

    /**
     * Los datos del aparato, la primera vez, sin que nadie los teclee. Es la
     * respuesta a «no estar todo el tiempo recordando quién soy o mi dispositivo»
     * dentro del propio teléfono.
     */
    private void sembrar() {
        recuerdos.sembrarDispositivo("teléfono",
                android.os.Build.MANUFACTURER + " " + android.os.Build.MODEL);
        recuerdos.sembrarDispositivo("android", "API " + android.os.Build.VERSION.SDK_INT);
    }

    /* ------------------------------------------------------------------ montaje */

    public View montar(LinearLayout raiz) {
        raiz.removeAllViews();
        hoja = new ScrollView(actividad);
        LinearLayout cuerpo = new LinearLayout(actividad);
        cuerpo.setOrientation(LinearLayout.VERTICAL);
        int pad = dp(18);
        cuerpo.setPadding(pad, dp(10), pad, pad);
        hoja.addView(cuerpo, par(-1, -2));
        raiz.addView(hoja, new LinearLayout.LayoutParams(-1, 0, 1f));

        Anillo anillo = new Anillo(actividad);
        LinearLayout.LayoutParams marca = new LinearLayout.LayoutParams(dp(74), dp(74));
        marca.gravity = Gravity.CENTER_HORIZONTAL;
        cuerpo.addView(anillo, marca);

        TextView titulo = texto("CORT", 26f, Paleta.CIAN);
        titulo.setTypeface(Typeface.create("sans-serif-light", Typeface.BOLD));
        titulo.setLetterSpacing(0.2f);
        titulo.setGravity(Gravity.CENTER_HORIZONTAL);
        cuerpo.addView(titulo, par(-1, -2));

        estado = texto("en tu teléfono · sin portátil", 11f, Paleta.SUAVE);
        estado.setLetterSpacing(0.22f);
        estado.setGravity(Gravity.CENTER_HORIZONTAL);
        cuerpo.addView(estado, par(-1, -2));

        registro = new LinearLayout(actividad);
        registro.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams caja = new LinearLayout.LayoutParams(-1, 0, 1f);
        caja.topMargin = dp(14);
        cuerpo.addView(registro, caja);

        LinearLayout fila = new LinearLayout(actividad);
        fila.setOrientation(LinearLayout.HORIZONTAL);
        fila.setGravity(Gravity.CENTER_VERTICAL);
        cuerpo.addView(fila, par(-1, -2));

        campo = new EditText(actividad);
        campo.setHint("dime algo");
        campo.setHintTextColor(Paleta.SUAVE);
        campo.setTextColor(Paleta.CLARO);
        campo.setBackgroundColor(Paleta.CAMPO);
        campo.setTextSize(16f);
        campo.setSingleLine(true);
        campo.setImeOptions(EditorInfo.IME_ACTION_SEND);
        campo.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
                | InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        campo.setPadding(dp(14), dp(14), dp(14), dp(14));
        fila.addView(campo, new LinearLayout.LayoutParams(0, dp(52), 1f));

        micro = new TextView(actividad);
        micro.setText("●");
        micro.setTextSize(26f);
        micro.setTextColor(Paleta.SUAVE);
        micro.setGravity(Gravity.CENTER);
        micro.setContentDescription("escuchar");
        micro.setOnClickListener(v -> escuchar());
        fila.addView(micro, new LinearLayout.LayoutParams(dp(52), dp(52)));

        Button enviar = new Button(actividad);
        enviar.setText("→");
        enviar.setTextSize(20f);
        enviar.setTextColor(Paleta.CIAN);
        enviar.setBackgroundColor(Paleta.CAMPO);
        enviar.setOnClickListener(v -> mandar());
        fila.addView(enviar, new LinearLayout.LayoutParams(dp(56), dp(52)));

        campo.setOnEditorActionListener((v, accion, ev) -> {
            mandar();
            return true;
        });

        linea("Estoy en el teléfono. No hace falta encender el portátil para esto.",
                Paleta.CLARO);
        if (!cerebro.avisoDeCarga().isEmpty()) {
            linea("Aviso: " + cerebro.avisoDeCarga(), Paleta.AVISO);
        }
        return hoja;
    }

    public void decirDondeEstaElPortatil(boolean encontrado) {
        if (estado == null) {
            return;
        }
        estado.setText(encontrado ? "tu portátil está conectado"
                : "en tu teléfono · sin portátil");
    }

    public void hablar(String texto) {
        voz.hablar(texto);
    }

    public void cerrar() {
        voz.cerrar();
    }

    /* ------------------------------------------------------------------ lazo */

    private void mandar() {
        String dicho = campo.getText().toString().trim();
        if (dicho.isEmpty()) {
            return;
        }
        campo.setText("");
        procesar(dicho);
    }

    /** El lazo completo: tabla → acción → medida → (nube) → aprender. */
    public void procesar(final String dicho) {
        linea("«" + dicho + "»", Paleta.SUAVE);
        Cerebro.Resultado r = cerebro.procesar(dicho);
        if (r != null) {
            String respuesta = acciones.ejecutar(r);
            if (respuesta != null) {
                contestar(respuesta);
                return;
            }
            // La acción estaba en la tabla pero faltaba un dato (una hora sin
            // números, por ejemplo): se pregunta en vez de ejecutar a ciegas.
            contestar("¿Cómo? Necesito el dato: pruébalo con «" + pideEjemplo(r) + "».");
            return;
        }
        porNube(dicho);
    }

    private String pideEjemplo(Cerebro.Resultado r) {
        if ("alarma".equals(r.accion)) {
            return "pon una alarma a las 7:30";
        }
        if ("cronometro".equals(r.accion)) {
            return "cronometro de 5 minutos";
        }
        return r.accion;
    }

    /**
     * Lo que la tabla no conoce va a la nube **en su propio hilo**: una llamada
     * HTTPS en el hilo de la interfaz congela la cara, y una cara congelada
     * vuelve a ser el formulario que este corte vino a quitar.
     */
    private void porNube(final String dicho) {
        if (!nube.configurada()) {
            proponer(dicho);
            return;
        }
        linea("pensando…", Paleta.SUAVE);
        final String memoria = recuerdos.lista(12);
        new Thread(() -> {
            final String respuesta = nube.preguntar(dicho, memoria);
            actividad.runOnUiThread(() -> {
                if (respuesta == null) {
                    quitarUltima();
                    proponer(dicho);
                } else {
                    quitarUltima();
                    contestar(respuesta);
                }
            });
        }).start();
    }

    private void contestar(String texto) {
        linea(texto, Paleta.CLARO);
        voz.hablar(texto);
    }

    /**
     * «no lo sé» con una salida: las acciones que CORT ya sabe hacer, para que
     * la dueña le asocie la frase nueva. Nunca se ofrece escribir código ni
     * comandos: la lista viene de `assets/habilidades.json` (regla 6).
     */
    private void proponer(final String dicho) {
        final String patron = Cerebro.normaliza(dicho);
        List<String> opciones = new ArrayList<>(cerebro.acciones());
        opciones.retainAll(APRENDIBLES);
        opciones.add("no, déjalo");
        new AlertDialog.Builder(actividad)
                .setTitle("No sé eso todavía")
                .setMessage("¿Qué quieres que haga cuando diga «" + dicho + "»?")
                .setItems(opciones.toArray(new String[0]), (d, i) -> {
                    String elegida = opciones.get(i);
                    if (elegida.startsWith("no,")) {
                        linea("Bueno. Sigo sin saber ésa.", Paleta.SUAVE);
                        return;
                    }
                    if ("decir".equals(elegida)) {
                        pedirRespuesta(patron);
                    } else {
                        recuerdos.aprender(patron, elegida, "", "");
                        linea("Aprendida: «" + dicho + "» → " + elegida + ".", Paleta.AVISO);
                    }
                })
                .show();
    }

    private void pedirRespuesta(final String patron) {
        final EditText escritura = new EditText(actividad);
        escritura.setHint("lo que CORT deberá responder");
        escritura.setTextColor(Paleta.CLARO);
        escritura.setHintTextColor(Paleta.SUAVE);
        new AlertDialog.Builder(actividad)
                .setTitle("¿Qué te contesto?")
                .setView(escritura)
                .setPositiveButton("Aprender", (d, w) -> {
                    String texto = escritura.getText().toString().trim();
                    if (texto.isEmpty()) {
                        return;
                    }
                    recuerdos.aprender(patron, "decir", "", texto);
                    linea("Aprendida: diré «" + texto + "\".", Paleta.AVISO);
                })
                .setNegativeButton("Dejarlo", null)
                .show();
    }

    /* ------------------------------------------------------------------ escucha */

    private void escuchar() {
        if (escuchando) {
            voz.dejarDeEscuchar();
            poniendoMicro(false);
            return;
        }
        if (actividad.checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            actividad.requestPermissions(
                    new String[] {android.Manifest.permission.RECORD_AUDIO}, 42);
            linea("Dame el permiso del micrófono y vuelve a pulsar ●.", Paleta.AVISO);
            return;
        }
        poniendoMicro(true);
        voz.escuchar(actividad, this);
    }

    private void poniendoMicro(boolean activo) {
        escuchando = activo;
        micro.setTextColor(activo ? Paleta.CIAN : Paleta.SUAVE);
    }

    @Override
    public void dijo(String texto) {
        actividad.runOnUiThread(() -> {
            poniendoMicro(false);
            procesar(texto);
        });
    }

    @Override
    public void fallo(String motivo) {
        actividad.runOnUiThread(() -> {
            poniendoMicro(false);
            linea("No oí: " + motivo + ".", Paleta.AVISO);
        });
    }

    /* ------------------------------------------------------------------ registro */

    private void linea(String texto, int color) {
        TextView linea = new TextView(actividad);
        linea.setText(texto);
        linea.setTextSize(16f);
        linea.setTextColor(color);
        linea.setLineSpacing(0f, 1.25f);
        LinearLayout.LayoutParams caja = par(-1, -2);
        caja.topMargin = dp(8);
        registro.addView(linea, caja);
        hoja.post(() -> hoja.fullScroll(View.FOCUS_DOWN));
    }

    private void quitarUltima() {
        int n = registro.getChildCount();
        if (n > 0) {
            registro.removeViewAt(n - 1);
        }
    }

    private TextView texto(String contenido, float sp, int color) {
        TextView t = new TextView(actividad);
        t.setText(contenido);
        t.setTextSize(sp);
        t.setTextColor(color);
        return t;
    }

    private LinearLayout.LayoutParams par(int ancho, int alto) {
        return new LinearLayout.LayoutParams(ancho, alto);
    }

    private int dp(float valor) {
        return Math.round(valor * actividad.getResources().getDisplayMetrics().density);
    }
}
