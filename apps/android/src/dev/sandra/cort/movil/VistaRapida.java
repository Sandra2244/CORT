package dev.sandra.cort.movil;

import android.Manifest;
import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.text.InputType;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.WindowManager;
import android.view.inputmethod.EditorInfo;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import java.util.List;

/** La vista inferior que Android muestra sobre otra app cuando se invoca a CORT. */
public final class VistaRapida {
    private static VistaRapida actual;

    private final Context contexto;
    private final Handler principal = new Handler(Looper.getMainLooper());
    private final WindowManager ventanas;
    private final LinearLayout raiz;
    private final WindowManager.LayoutParams parametros;
    private final EditText entrada;
    private final TextView estado;
    private final LinearLayout accionesPanel;
    private final Button accionesBoton;
    private final Recuerdos recuerdos;
    private final Cerebro cerebro;
    private final Acciones acciones;
    private final Voz voz;
    private final Object ciclo = new Object();
    private volatile boolean cerrada;
    private volatile boolean procesando;
    private boolean trabajando;
    private boolean memoriaCerrada;

    private VistaRapida(Context contexto) {
        this.contexto = contexto.getApplicationContext();
        ventanas = (WindowManager) this.contexto.getSystemService(Context.WINDOW_SERVICE);
        recuerdos = new Recuerdos(this.contexto);
        cerebro = new Cerebro(this.contexto, recuerdos);
        acciones = new Acciones(this.contexto, recuerdos);
        voz = new Voz(this.contexto);

        raiz = new LinearLayout(this.contexto);
        raiz.setOrientation(LinearLayout.VERTICAL);
        int relleno = dp(12);
        raiz.setPadding(relleno, relleno, relleno, relleno);
        GradientDrawable fondo = new GradientDrawable();
        fondo.setColor(Color.argb(232, 3, 10, 20));
        fondo.setCornerRadius(dp(22));
        fondo.setStroke(dp(1), Color.argb(150, 92, 225, 255));
        raiz.setBackground(fondo);

        LinearLayout titulo = new LinearLayout(this.contexto);
        titulo.setGravity(Gravity.CENTER_VERTICAL);
        TextView nombre = new TextView(this.contexto);
        nombre.setText("CORT · vista rápida");
        nombre.setTextColor(Paleta.MENTA);
        nombre.setTextSize(17);
        nombre.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        LinearLayout.LayoutParams nombreP = new LinearLayout.LayoutParams(
                0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
        titulo.addView(nombre, nombreP);
        Button cerrarBoton = boton("×", v -> cerrar());
        cerrarBoton.setTextSize(22);
        cerrarBoton.setContentDescription("Cerrar la vista rápida");
        titulo.addView(cerrarBoton);
        raiz.addView(titulo);

        estado = new TextView(this.contexto);
        estado.setText("Dime o escribe qué necesitas.");
        estado.setTextColor(Paleta.SUAVE);
        estado.setTextSize(13);
        estado.setPadding(0, dp(4), 0, dp(8));
        raiz.addView(estado);

        entrada = new EditText(this.contexto);
        entrada.setHint("Hablar, alarma, abrir una app…");
        entrada.setTextColor(Paleta.CLARO);
        entrada.setHintTextColor(Color.argb(170, 174, 240, 255));
        entrada.setTextSize(15);
        entrada.setMinHeight(dp(48));
        entrada.setSingleLine(false);
        entrada.setMaxLines(3);
        entrada.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE
                | InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
        entrada.setImeOptions(EditorInfo.IME_ACTION_DONE);
        entrada.setOnEditorActionListener((v, accion, evento) -> {
            boolean enter = evento != null && evento.getKeyCode() == KeyEvent.KEYCODE_ENTER
                    && evento.getAction() == KeyEvent.ACTION_DOWN;
            if (accion == EditorInfo.IME_ACTION_DONE || enter) {
                procesar(entrada.getText().toString());
                return true;
            }
            return false;
        });
        raiz.addView(entrada);

        accionesPanel = new LinearLayout(this.contexto);
        accionesPanel.setOrientation(LinearLayout.VERTICAL);
        accionesPanel.setPadding(0, dp(8), 0, 0);
        accionesPanel.setVisibility(View.GONE);
        agregarAccion("Hablar", v -> escuchar());
        agregarAccion("Chat", v -> abrirChat(""));
        agregarAccion("Música", v -> abrirMusica());
        agregarAccion("Cerrar", v -> cerrar());
        raiz.addView(accionesPanel);

        accionesBoton = boton("Acciones", v -> alternarAcciones());
        accionesBoton.setTextColor(Paleta.FONDO);
        accionesBoton.setBackgroundColor(Paleta.MENTA);
        accionesBoton.setContentDescription("Mostrar las acciones de CORT");
        LinearLayout.LayoutParams accionesP = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        accionesP.topMargin = dp(10);
        raiz.addView(accionesBoton, accionesP);

        parametros = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.MATCH_PARENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
                        | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                android.graphics.PixelFormat.TRANSLUCENT);
        parametros.gravity = Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL;
        parametros.setTitle("CORT vista rápida");
        parametros.softInputMode = WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE;
    }

    public static void mostrar(Context contexto) {
        if (actual != null) {
            actual.cerrar();
        }
        if (!Settings.canDrawOverlays(contexto)) {
            abrirPermisoSuperposicion(contexto);
            return;
        }
        actual = new VistaRapida(contexto);
        actual.mostrarVentana();
    }

    private void mostrarVentana() {
        try {
            ventanas.addView(raiz, parametros);
        } catch (Exception noSePudo) {
            actual = null;
            cerrar();
            Toast.makeText(contexto, "No pude mostrar la vista rápida. Abre CORT desde su icono.",
                    Toast.LENGTH_LONG).show();
        }
    }

    private void agregarAccion(String texto, View.OnClickListener accion) {
        Button b = boton(texto, accion);
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        p.bottomMargin = dp(6);
        accionesPanel.addView(b, p);
    }

    private void alternarAcciones() {
        boolean abierto = accionesPanel.getVisibility() == View.VISIBLE;
        accionesPanel.setVisibility(abierto ? View.GONE : View.VISIBLE);
        accionesBoton.setText(abierto ? "Acciones" : "Cerrar acciones");
        accionesBoton.setContentDescription(abierto
                ? "Mostrar las acciones de CORT" : "Ocultar las acciones de CORT");
    }

    private void ocultarAcciones() {
        accionesPanel.setVisibility(View.GONE);
        accionesBoton.setText("Acciones");
        accionesBoton.setContentDescription("Mostrar las acciones de CORT");
    }

    private Button boton(String texto, View.OnClickListener accion) {
        Button b = new Button(contexto);
        b.setText(texto);
        b.setMinHeight(dp(48));
        b.setMinWidth(dp(48));
        b.setTextColor(Paleta.CLARO);
        b.setContentDescription(texto);
        GradientDrawable fondo = new GradientDrawable();
        fondo.setColor(Paleta.CAMPO);
        fondo.setStroke(dp(1), Paleta.CIAN);
        fondo.setCornerRadius(dp(8));
        b.setBackground(fondo);
        b.setOnClickListener(accion);
        return b;
    }

    private int dp(int valor) {
        return Math.round(valor * contexto.getResources().getDisplayMetrics().density);
    }

    private void escuchar() {
        ocultarAcciones();
        if (contexto.checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            estado.setText("Falta el permiso de micrófono. Te abro Ajustes.");
            abrirAjustesApp();
            return;
        }
        voz.dejarDeEscuchar();
        estado.setText("Escuchando… hasta " + Motor.segundosDictado(contexto) + " segundos.");
        voz.escuchar(contexto, new Voz.AlOir() {
            @Override
            public void dijo(String texto) {
                principal.post(() -> {
                    if (cerrada) return;
                    entrada.setText(texto);
                    procesar(texto);
                });
            }

            @Override
            public void fallo(String motivo) {
                principal.post(() -> {
                    if (!cerrada) estado.setText(motivo);
                });
            }

            @Override
            public void parcial(String texto) {
                principal.post(() -> {
                    if (!cerrada) {
                        entrada.setText(texto);
                        estado.setText("Escuchando: " + texto);
                    }
                });
            }
        });
    }

    private void procesar(String texto) {
        String limpio = texto == null ? "" : texto.trim();
        if (limpio.isEmpty() || cerrada || procesando) return;
        procesando = true;
        estado.setText("Procesando…");
        synchronized (ciclo) {
            trabajando = true;
        }
        new Thread(() -> {
            String resultado;
            try {
                List<Cerebro.Resultado> pasos = cerebro.cadena(limpio);
                StringBuilder respuesta = new StringBuilder();
                for (Cerebro.Resultado paso : pasos) {
                    String dicho = acciones.ejecutar(paso);
                    if (dicho != null && !dicho.trim().isEmpty()) {
                        if (respuesta.length() > 0) respuesta.append(" ");
                        respuesta.append(dicho);
                    }
                }
                resultado = respuesta.toString();
            } catch (Exception fallo) {
                resultado = "No pude completar la orden.";
            } finally {
                synchronized (ciclo) {
                    trabajando = false;
                }
                cerrarMemoriaSiTermino();
            }
            final String finalTexto = resultado;
            principal.post(() -> {
                if (cerrada) return;
                procesando = false;
                if (finalTexto.isEmpty()) {
                    abrirChat(limpio);
                    return;
                }
                estado.setText(finalTexto);
                if (contexto.getSharedPreferences("cort", Context.MODE_PRIVATE)
                        .getBoolean("habla", true)) {
                    voz.hablar(finalTexto);
                }
            });
        }, "cort-vista-rapida").start();
    }

    private void abrirChat(String frase) {
        ocultarAcciones();
        Intent abrir = new Intent(contexto, MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_REORDER_TO_FRONT)
                .putExtra(MainActivity.PIDE_CHAT, true)
                .putExtra(MainActivity.PIDE_FRASE, frase);
        cerrar();
        try {
            contexto.startActivity(abrir);
        } catch (ActivityNotFoundException noHayCara) {
            Toast.makeText(contexto, "No pude abrir el chat de CORT.", Toast.LENGTH_LONG).show();
        }
    }

    private void abrirMusica() {
        ocultarAcciones();
        Intent musica = new Intent(Intent.ACTION_MAIN)
                .addCategory(Intent.CATEGORY_APP_MUSIC)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            contexto.startActivity(musica);
        } catch (ActivityNotFoundException noHayMusica) {
            estado.setText("No encontré una app de música en este teléfono.");
        }
    }

    private void abrirAjustesApp() {
        Intent ajustes = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                Uri.parse("package:" + contexto.getPackageName()))
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            contexto.startActivity(ajustes);
        } catch (ActivityNotFoundException noHayAjustes) {
            Toast.makeText(contexto, "Abre Ajustes y concede el micrófono a CORT.",
                    Toast.LENGTH_LONG).show();
        }
    }

    private static void abrirPermisoSuperposicion(Context contexto) {
        Intent ajustes = new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                Uri.parse("package:" + contexto.getPackageName()))
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            contexto.startActivity(ajustes);
            Toast.makeText(contexto, "Permite que CORT se muestre sobre otras apps y vuelve a invocarlo.",
                    Toast.LENGTH_LONG).show();
        } catch (ActivityNotFoundException noHayAjustes) {
            Toast.makeText(contexto, "Este teléfono no abrió el permiso de superposición.",
                    Toast.LENGTH_LONG).show();
        }
    }

    private void cerrar() {
        synchronized (ciclo) {
            if (cerrada) return;
            cerrada = true;
            procesando = false;
        }
        voz.dejarDeEscuchar();
        voz.cerrar();
        try {
            ventanas.removeView(raiz);
        } catch (Exception yaNoEstaba) {
            // La vista ya pudo retirarla el sistema al morir el proceso.
        }
        cerrarMemoriaSiTermino();
        if (actual == this) actual = null;
    }

    private void cerrarMemoriaSiTermino() {
        synchronized (ciclo) {
            if (!cerrada || trabajando || memoriaCerrada) return;
            memoriaCerrada = true;
        }
        recuerdos.close();
    }
}
