package dev.sandra.cort.movil;

import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.media.AudioManager;
import android.os.Bundle;
import android.view.Gravity;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.util.ArrayList;
import java.util.List;

/**
 * Leer con CORT (U2). Lo que la dueña describió del iPhone —pulsar un mensaje y que
 * entre las opciones salga «leer»— es en Android la intención `ACTION_PROCESS_TEXT`:
 * cualquier actividad que la declara aparece en el menú de selección de texto de
 * **cualquier aplicación**, sin permisos y sin servicios de accesibilidad. Añade el
 * `ACTION_SEND` y la misma pantalla sirve para lo que se comparte desde el navegador.
 *
 * La lectura va por la boca de Android (`Voz`), trozada en frases: un motor de TTS
 * corta una línea muy larga sin avisar, y un párrafo partido por la mitad suena a
 * avería. El sensor de audífonos manda: si la dueña se quita los auriculares mientras
 * CORT está hablando, se calla en vez de quedarse leyendo por el altavoz de la casa.
 */
public class Lectura extends android.app.Activity implements Audifonos.AlCambiar {

    /** Un trozo de 380 caracteres son ~24 s dictados; por encima, el motor empieza a recortar. */
    private static final int TROZO_MAX = 380;

    private static final float[] PASOS = {1.0f, 1.4f, 1.9f};

    private Voz boca;
    private AudioManager gestor;
    private TextView origen;
    private TextView cuerpo;
    private TextView estado;
    private Button botonPaso;
    private final List<String> trozos = new ArrayList<>();
    private String texto = "";
    private int paso = 0;
    private Audifonos.Receptor receptor;
    private Audifonos.Cambios cambios;
    private boolean vivo;

    @Override
    protected void onCreate(Bundle guardado) {
        super.onCreate(guardado);
        gestor = (AudioManager) getSystemService(Context.AUDIO_SERVICE);
        boca = new Voz(this);
        getWindow().getDecorView().setBackgroundColor(Paleta.FONDO);

        ScrollView desplazable = new ScrollView(this);
        LinearLayout pantalla = new LinearLayout(this);
        pantalla.setOrientation(LinearLayout.VERTICAL);
        int pad = dp(22);
        pantalla.setPadding(pad, pad, pad, pad);
        desplazable.addView(pantalla, new LinearLayout.LayoutParams(-1, -2));
        setContentView(desplazable);

        TextView titulo = texto("LEER CON CORT", 13f, Paleta.CIAN);
        titulo.setLetterSpacing(0.12f);
        pantalla.addView(titulo);

        origen = texto("", 14f, Paleta.AVISO);
        pantalla.addView(origen, conMargen());

        texto = sacaDelIntent(getIntent());
        if (texto.isEmpty()) {
            cuerpo = texto("No llegó ningún texto subrayado o compartido: CORT no tiene "
                    + "nada que leer.", 15f, Paleta.CLARO);
            estado = texto("", 14f, Paleta.SUAVE);
            pantalla.addView(cuerpo, conMargen());
            pantalla.addView(estado, conMargen());
        } else {
            trocear(texto);
            cuerpo = texto(texto.length() > 4000 ? texto.substring(0, 4000) + "…" : texto,
                    16f, Paleta.CLARO);
            cuerpo.setTextIsSelectable(true);
            cuerpo.setLineSpacing(0f, 1.25f);
            pantalla.addView(cuerpo, conMargen());

            Button leer = boton("Leer en voz alta");
            leer.setOnClickListener(v -> di());
            pantalla.addView(leer, caja(64));

            Button parar = boton("Parar");
            parar.setOnClickListener(v -> {
                boca.callar();
                estado.setText("Parada. «Leer en voz alta» la retoma desde el principio.");
            });
            pantalla.addView(parar, caja(54));

            botonPaso = boton(pasoActual());
            botonPaso.setOnClickListener(v -> {
                paso = (paso + 1) % PASOS.length;
                boca.ritmo(PASOS[paso]);
                botonPaso.setText(pasoActual());
                estado.setText("Al paso " + pasoActual() + ". Se cambia aunque ya esté leyendo.");
            });
            pantalla.addView(botonPaso, caja(54));

            Button copiar = boton("Copiar el texto");
            copiar.setOnClickListener(v -> {
                ClipboardManager mesas = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
                mesas.setPrimaryClip(ClipData.newPlainText("CORT", texto));
                estado.setText("Copiado: " + texto.length() + " caracteres en el portapapeles.");
            });
            pantalla.addView(copiar, caja(54));

            estado = texto("Sale por " + Audifonos.salida(gestor) + ". " + trozos.size()
                    + " trozos · ~" + estimacion() + " s.", 14f, Paleta.SUAVE);
            estado.setLineSpacing(0f, 1.3f);
            pantalla.addView(estado, conMargen());
        }

        Button volver = boton("Volver");
        volver.setOnClickListener(v -> finish());
        pantalla.addView(volver, caja(54));
    }

    /** Lo que trae la orden: el texto subrayado (`PROCESS_TEXT`) o lo compartido (`SEND`). */
    private String sacaDelIntent(Intent orden) {
        if (orden == null) {
            return "";
        }
        CharSequence subrayado = orden.getCharSequenceExtra(Intent.EXTRA_PROCESS_TEXT);
        if (subrayado != null && subrayado.length() > 0) {
            return subrayado.toString().trim();
        }
        CharSequence compartido = orden.getCharSequenceExtra(Intent.EXTRA_TEXT);
        if (compartido != null && compartido.length() > 0) {
            String titulo = orden.getStringExtra(Intent.EXTRA_SUBJECT);
            String cuerpo = compartido.toString().trim();
            return (titulo == null || titulo.trim().isEmpty() ? "" : titulo.trim() + ". ") + cuerpo;
        }
        return "";
    }

    /** Corta por frase, no por número de letras: una palabra partida suena a avería. */
    private void trocear(String del) {
        trozos.clear();
        int desde = 0;
        while (desde < del.length()) {
            int fin = Math.min(del.length(), desde + TROZO_MAX);
            if (fin < del.length()) {
                int corte = -1;
                for (int i = fin; i > desde + TROZO_MAX / 2; i--) {
                    char c = del.charAt(i - 1);
                    if (c == '.' || c == '!' || c == '?' || c == '\n') {
                        corte = i;
                        break;
                    }
                }
                fin = corte > 0 ? corte : del.lastIndexOf(' ', fin);
                if (fin <= desde) {
                    fin = desde + TROZO_MAX;      // un bloque sin hueco donde partir: se parte
                }
            }
            trozos.add(del.substring(desde, fin).trim());
            desde = fin;
        }
    }

    private void di() {
        boca.ritmo(PASOS[paso]);
        for (String trozo : trozos) {
            boca.seguir(trozo);
        }
        estado.setText("Leyendo " + trozos.size() + " trozos por " + Audifonos.salida(gestor)
                + " · " + estimacion() + " s estimados (se mide en este aparato, no en el PC).");
    }

    /** ~16 caracteres por segundo al paso normal; la estimación se imprime como estimación. */
    private String estimacion() {
        return String.valueOf(Math.max(1, (int) (texto.length() / (16.0 * PASOS[paso]))));
    }

    private String pasoActual() {
        return paso == 0 ? "Paso normal" : (paso == 1 ? "Paso rápido" : "Paso muy rápido");
    }

    /* ------------------------------------------------------------- audífonos */

    @Override
    protected void onResume() {
        super.onResume();
        vivo = true;
        if (receptor == null) {
            receptor = new Audifonos.Receptor(this);
        }
        registerReceiver(receptor, Audifonos.Receptor.filtro());
        if (gestor != null) {
            // una sola instancia: el registro y el retiro tienen que ser el MISMO objeto,
            // registrar uno y retirar otro deja el aviso clavado en el sistema
            if (cambios == null) {
                cambios = new Audifonos.Cambios(this);
            }
            gestor.registerAudioDeviceCallback(cambios, null);
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        vivo = false;
        if (receptor != null) {
            try {
                unregisterReceiver(receptor);
            } catch (Exception yaFuera) {
                // nunca llegó a estar registrado
            }
        }
        if (gestor != null && cambios != null) {
            try {
                gestor.unregisterAudioDeviceCallback(cambios);
            } catch (Exception yaFuera) {
                // sin registro no hay retiro que hacer
            }
        }
        boca.callar();
    }

    @Override
    public void cambioDeSalida() {
        if (!vivo || estado == null) {
            return;
        }
        runOnUiThread(() -> {
            if (!Audifonos.hay(gestor) && boca.hablando()) {
                boca.callar();
                estado.setText("Te quitaste los audífonos: CORT se calló en vez de leer por "
                        + "el altavoz. «Leer en voz alta» la retoma.");
            } else {
                estado.setText("Sale por " + Audifonos.salida(gestor) + ".");
            }
        });
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
        medida.topMargin = dp(10);
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
}
