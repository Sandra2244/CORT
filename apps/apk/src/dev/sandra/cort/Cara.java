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
    private final Sincroniza sincroniza;
    private final Voz voz;

    private LinearLayout registro;
    private ScrollView hoja;
    private TextView estado;
    private TextView nubeChip;
    private EditText campo;
    private TextView micro;
    private boolean escuchando;

    public Cara(Activity actividad) {
        this.actividad = actividad;
        this.recuerdos = new Recuerdos(actividad.getApplicationContext());
        this.cerebro = new Cerebro(actividad.getApplicationContext(), recuerdos);
        this.acciones = new Acciones(actividad, recuerdos);
        this.nube = new Nube(actividad.getApplicationContext());
        // El puente no decide solo: vive en la hoja de ajustes, y lee el enlace que
        // `MainActivity` ya guardó («cort» → `url`). Sin ese enlace, `hayPortatil()`
        // dice que no y la fila ni se intenta.
        this.sincroniza = new Sincroniza(actividad.getApplicationContext(), recuerdos);
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

        nubeChip = texto("", 12f, Paleta.SUAVE);
        nubeChip.setGravity(Gravity.CENTER_HORIZONTAL);
        nubeChip.setPadding(dp(14), dp(11), dp(14), dp(11));
        nubeChip.setBackgroundColor(Paleta.CAMPO);
        nubeChip.setOnClickListener(v -> abrirAjustes());
        LinearLayout.LayoutParams marcaChip = new LinearLayout.LayoutParams(-2, -2);
        marcaChip.gravity = Gravity.CENTER_HORIZONTAL;
        cuerpo.addView(nubeChip, marcaChip);
        actualizandoChip();

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
        List<Cerebro.Resultado> pasos = cerebro.cadena(dicho);        if (pasos.size() > 1) {
            encadenar(pasos);
            return;
        }
        Cerebro.Resultado r = pasos.isEmpty() ? null : pasos.get(0);
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

    /**
     * «Abre Lark player y pon After dark»: dos mandatos, dos intenciones, **una
     * sola respuesta hablada** al final. Si un paso pide un dato que no está en la
     * frase, la cadena se corta ahí y se pregunta por ese paso — seguir ejecutando
     * el resto sería hacer cosas que la dueña no confirmó.
     *
     * Lo que este lazo no puede prometer desde el portátil: el orden en que las
     * dos ventanas aparecen en la pantalla del teléfono depende de Android, y la
     * segunda tapa a la primera. Es la misma razón por la que «pon After dark»
     * abre una búsqueda en internet en vez de pulsar el play dentro de la app que
     * acabamos de abrir.
     */
    private void encadenar(List<Cerebro.Resultado> pasos) {
        StringBuilder texto = new StringBuilder();
        for (Cerebro.Resultado paso : pasos) {
            String respuesta = acciones.ejecutar(paso);
            if (respuesta == null) {
                contestar("¿Cómo? Necesito el dato: pruébalo con «" + pideEjemplo(paso) + "».");
                return;
            }
            if (texto.length() > 0) {
                texto.append(" ");
            }
            texto.append(respuesta);
        }
        contestar(texto.toString());
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

    /* ------------------------------------------------------------------ nube */

    /**
     * La pantalla que faltaba. La dueña eligió «nube si hay internet, local si
     * no», y hasta aquí la segunda mitad era letra muerta: `Nube` leía la clave
     * de un `SharedPreferences` que **nadie podía escribir desde el teléfono**.
     *
     * Tres decisiones que no son de estilo:
     *
     * 1. **La clave guardada no se vuelve a enseñar.** El campo se abre vacío y
     *    su pista dice cuántos caracteres hay guardados; escribir algo la
     *    reemplaza y dejarlo en blanco la conserva. En ningún punto se concatena
     *    `nube.clave()` con un texto de pantalla, y por eso la prueba
     *    `test_la_clave_guardada_nunca_vuelve_a_la_pantalla` existe.
     * 2. **Probar no congela la cara.** `Nube.preguntar` es HTTPS bloqueante: va
     *    en su propio `Thread` y el resultado vuelve con `runOnUiThread`, la
     *    misma regla que ya rige la búsqueda por UDP.
     * 3. **Se puede apagar.** «Borrar la clave de este teléfono» deja la cara
     *    exactamente como estaba antes de `v0.15.0`: tabla local y memoria local.
     *    La nube es un añadido, nunca un requisito.
     */
    public void abrirAjustes() {
        final String[] modo = {nube.proveedor()};
        ScrollView desplegable = new ScrollView(actividad);
        // El `AlertDialog` de Android es de tema **claro**, y aquí todo el texto se
        // pinta con la paleta oscura de CORT: sin este fondo, los avisos en
        // `Paleta.SUAVE` (blanco al 54 %) salen sobre blanco y no se leen. Se fija
        // con una prueba porque en esta máquina no hay pantalla donde verlo.
        desplegable.setBackgroundColor(Paleta.FONDO);
        LinearLayout caja = new LinearLayout(actividad);
        caja.setOrientation(LinearLayout.VERTICAL);
        int pad = dp(18);
        caja.setPadding(pad, pad, pad, pad);
        desplegable.addView(caja, par(-1, -2));

        caja.addView(texto("La nube, si quieres", 19f, Paleta.CIAN), par(-1, -2));
        TextView explic = texto("Sin clave CORT contesta con su tabla y su memoria, que es como funciona hoy. "
                + "Con clave, las frases que no conoce se las pregunta al modelo cuando hay internet. "
                + "La clave se queda escrita en este teléfono: no va al repositorio ni al APK.",
                12f, Paleta.SUAVE);
        explic.setLineSpacing(0f, 1.35f);
        caja.addView(explic, par(-1, -2));

        final TextView proveedor = texto("", 14f, Paleta.CLARO);
        proveedor.setText("modo: " + modo[0] + "  ·  toca para cambiar");
        proveedor.setPadding(0, dp(16), 0, dp(16));
        proveedor.setOnClickListener(v -> {
            modo[0] = "openai".equals(modo[0]) ? "anthropic" : "openai";
            proveedor.setText("modo: " + modo[0] + "  ·  toca para cambiar");
        });
        caja.addView(proveedor, par(-1, -2));

        final EditText base = campoDe("dirección del servicio", nube.base(), false);
        final EditText modelo = campoDe("modelo", nube.modelo(), false);
        final EditText clave = campoDe(hayClave()
                ? "clave guardada (" + nube.clave().length() + " caracteres) — en blanco: no la cambio"
                : "clave de la API, se teclea una vez", "", true);
        caja.addView(base, par(-1, -2));
        caja.addView(modelo, par(-1, -2));
        caja.addView(clave, par(-1, -2));

        final TextView salida = texto("", 12f, Paleta.AVISO);
        salida.setLineSpacing(0f, 1.35f);
        salida.setPadding(0, dp(12), 0, dp(4));
        caja.addView(salida, par(-1, -2));

        TextView probar = texto("▶  probar la conexión", 14f, Paleta.CIAN);
        probar.setPadding(0, dp(12), 0, dp(12));
        probar.setOnClickListener(v -> probandoNube(salida));
        caja.addView(probar, par(-1, -2));

        TextView borrar = texto("⌫  borrar la clave de este teléfono", 13f, Paleta.SUAVE);
        borrar.setPadding(0, dp(6), 0, dp(6));
        borrar.setOnClickListener(v -> {
            nube.ajustar(modo[0], lo(base), lo(modelo), "");
            clave.setText("");
            salida.setText("Clave borrada. CORT vuelve a su tabla local.");
            actualizandoChip();
        });
        caja.addView(borrar, par(-1, -2));

        // El puente de memoria (deuda 2 del acuerdo Java). Va en esta hoja y no en un
        // botón de la pantalla en reposo por dos motivos: la superficie de herramientas
        // es una sola, y sincronizar es algo que se hace de vez en cuando, no en cada
        // frase. La fila **no** desaparece si no hay portátil: explica por qué.
        TextView sincronizar = texto("↔  traer y llevar mis recuerdos al portátil",
                13f, Paleta.CIAN);
        sincronizar.setPadding(0, dp(12), 0, dp(6));
        sincronizar.setOnClickListener(v -> sincronizando(salida));
        caja.addView(sincronizar, par(-1, -2));

        new AlertDialog.Builder(actividad)
                .setView(desplegable)
                .setPositiveButton("Guardar", (d, w) -> guardandoAjustes(
                        modo[0], lo(base), lo(modelo), lo(clave)))
                .setNegativeButton("Cerrar", null)
                .show();
    }

    private void guardandoAjustes(String proveedor, String base, String modelo, String tecleada) {
        // Vacío significa «conserva la que ya está», no «bórrala»: si no, cada
        // arreglo de un modelo le haría volver a teclear el secreto entero.
        String guardada = tecleada.isEmpty() ? nube.clave() : tecleada;
        nube.ajustar(proveedor, base, modelo, guardada);
        actualizandoChip();
        if (nube.configurada()) {
            linea("Nube activada: " + modelo + " en " + base + ". Lo que no sepa la tabla se lo pregunta.",
                    Paleta.AVISO);
        } else {
            linea("Sin nube: CORT contesta solo con su tabla y su memoria.", Paleta.SUAVE);
        }
    }

    /** HTTPS en un hilo aparte, y el aviso vuelve a la cara por `runOnUiThread`. */
    private void probandoNube(final TextView salida) {
        if (!nube.configurada()) {
            salida.setText("Falta la clave, la dirección o el modelo.");
            return;
        }
        salida.setText("preguntando…");
        new Thread(() -> {
            final String respuesta = nube.preguntar(
                    "Responde únicamente con estas dos palabras: hola CORT", "");
            final String aviso = respuesta == null
                    ? "No contestó: " + nube.ultimoFallo()
                    : "Contestó: " + respuesta;
            actividad.runOnUiThread(() -> salida.setText(aviso));
        }).start();
    }

    /**
     * El puente, en su propio hilo, exactamente como la nube y que el UDP: dos
     * `HttpURLConnection` seguidos en el hilo de la interfaz congelan el anillo, y un
     * portátil apagado no puede quedarse con la cara colgada. El aviso vuelve por
     * `runOnUiThread`, y si hubo datos nuevos se escribe también en el registro, que es
     * donde la dueña los va a ver la próxima vez que abra la cara.
     */
    private void sincronizando(final TextView salida) {
        if (!sincroniza.hayPortatil()) {
            salida.setText("Todavía no sé dónde está tu portátil: busca la Wi-Fi o pega su "
                    + "enlace en la pantalla de estreno.");
            return;
        }
        salida.setText("cruzando el puente…");
        new Thread(() -> {
            final String recuento = sincroniza.sincronizar();
            final String aviso = recuento == null
                    ? "No sincronizó: " + sincroniza.ultimoFallo()
                    : recuento;
            actividad.runOnUiThread(() -> {
                salida.setText(aviso);
                if (recuento != null) {
                    linea("Memoria compartida con el portátil. " + recuento, Paleta.AVISO);
                }
            });
        }).start();
    }

    private boolean hayClave() {
        return !nube.clave().isEmpty();
    }

    private void actualizandoChip() {
        if (nubeChip == null) {
            return;
        }
        nubeChip.setText(nube.configurada()
                ? "⚙ nube: " + nube.proveedor() + " · " + nube.modelo()
                : "⚙ nube apagada · toca para escribirla");
    }

    private EditText campoDe(String pista, String valor, boolean secreta) {
        EditText campo = new EditText(actividad);
        campo.setHint(pista);
        campo.setHintTextColor(Paleta.SUAVE);
        campo.setTextColor(Paleta.CLARO);
        campo.setBackgroundColor(Paleta.CAMPO);
        campo.setTextSize(15f);
        campo.setSingleLine(true);
        campo.setInputType(secreta
                ? InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD
                : InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        campo.setPadding(dp(12), dp(14), dp(12), dp(14));
        campo.setText(valor);
        return campo;
    }

    private static String lo(EditText campo) {
        return campo.getText().toString().trim();
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
        // Bug de `v0.15.0` que nadie ha visto con un dedo porque nadie ha instalado
        // la cara nativa: el `AlertDialog` de Android viene con tema **claro**, y
        // este campo se pintaba en blanco sobre el blanco del diálogo. Ahora el
        // campo trae su propio vidrio oscuro, como los de la pantalla de la nube.
        escritura.setBackgroundColor(Paleta.CAMPO);
        escritura.setPadding(dp(14), dp(14), dp(14), dp(14));
        new AlertDialog.Builder(actividad)
                .setTitle("¿Qué te contesto?")
                .setView(escritura)
                .setPositiveButton("Aprender", (d, w) -> {
                    String texto = escritura.getText().toString().trim();
                    if (texto.isEmpty()) {
                        return;
                    }
                    recuerdos.aprender(patron, "decir", "", texto);
                    linea("Aprendida: diré «" + texto + "».", Paleta.AVISO);
                })
                .setNegativeButton("Dejarlo", null)
                .show();
    }

    /* ------------------------------------------------------------------ escucha */

    /**
     * Empezar a oír **sin que nadie pulse el ●**: es lo que hace `Sesion.java`
     * cuando la dueña eligió CORT como asistente del teléfono y aprieta la tecla
     * de asistente o el gesto de la pantalla de bloqueo. CORT usa aquí el
     * reconocedor que el aparato ya trae —el mismo del botón—, porque un modelo de
     * speech propio no cabe en un APK de 79 KB de Java ni en el portátil de la
     * dueña; está escrito en `docs/PLATFORM.md`.
     */
    public void escucharAhora() {
        if (!escuchando) {
            escuchar();
        }
    }

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
