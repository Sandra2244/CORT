package dev.sandra.cort.movil;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * El almacén de cerebros (U1): la parte que la dueña pidió con «que aparte de su
 * cerebro gguf pueda descargar mas cerebros y modelos estilo el de pc».
 *
 * El catálogo lo lee `CerebroLocal.catalogo()` de `assets/cerebros.json`, donde están
 * el peso y la SHA-256 **medidos** el 2026-11-05 contra el árbol público de Hugging
 * Face. Esta pantalla los lista, los baja, los verifica y deja usar uno. El método es
 * el de la PC, no uno nuevo: descargar, comprobar la suma entera y sólo entonces
 * fiarse del archivo.
 *
 * Cuatro decisiones, todas elegidas por ella y ninguna callada:
 *
 * * **Hilo de CORT, sin `DownloadManager` ni WorkManager.** Un enlace de descarga
 *   puede llevar token y una notificación del sistema se lee desde la pantalla
 *   bloqueada; además el `Range` con el que se reanada lo manda este código, no un
 *   servicio que decide cuándo reintenta.
 * * **El carbajo de la app** (`getExternalFilesDir("modelos")`): nadie más abre esos
 *   bytes, no se pide permiso de almacenamiento y se van con la app. Por eso el
 *   aviso escrito abajo, para que no sea sorpresa el día que se desinstale.
 * * **La suma se calcula al final, sobre el archivo entero.** Un GGUF truncado no
 *   falla al abrir: abre y contesta basura. Verificar y tirar es la única forma de
 *   que un corte de Wi-Fi no deje un cerebro mentiroso en el teléfono.
 * * **La puerta de RAM** — la holgada pide el archivo entero más la reserva de
 *   contexto; como el motor mapea con mmap, por debajo se puede intentar. Se escribe
 *   junto a cada modelo con los megas libres de ESTE teléfono encendido ahora, no
 *   con los que se anuncien desde un PC.
 */
public class Cerebros extends Activity {

    /** El dato del catálogo más los cachivaches de su fila en pantalla. */
    private static final class Fila {
        final CerebroLocal.Ficha datos;
        TextView estado;
        Button bajar, usar, borrar;

        Fila(CerebroLocal.Ficha datos) {
            this.datos = datos;
        }
    }

    private final List<Fila> filas = new ArrayList<>();
    private final Handler hiloUI = new Handler(Looper.getMainLooper());
    private volatile boolean cerrando;

    private CerebroLocal cerebro;
    private Recuerdos recuerdos;
    private TextView resumen;
    private TextView estadoOido;
    private Button bajarOido;
    private LinearLayout filaModos;
    private EditText pregunta;
    private TextView respuesta;
    private TextView estadoDespertador;
    private TextView estadoAuto;
    private TextView estadoCaracter;
    private Button botonDespertador;
    private Button botonAuto;

    @Override
    protected void onCreate(Bundle guardado) {
        super.onCreate(guardado);
        getWindow().getDecorView().setBackgroundColor(Paleta.FONDO);
        cerebro = new CerebroLocal(this);
        recuerdos = new Recuerdos(this);

        ScrollView desplazable = new ScrollView(this);
        LinearLayout pantalla = new LinearLayout(this);
        pantalla.setOrientation(LinearLayout.VERTICAL);
        int pad = dp(22);
        pantalla.setPadding(pad, pad, pad, pad);
        desplazable.addView(pantalla, new LinearLayout.LayoutParams(-1, -2));
        setContentView(desplazable);

        TextView titulo = texto("ALMACÉN DE CEREBROS", 13f, Paleta.CIAN);
        titulo.setLetterSpacing(0.12f);
        pantalla.addView(titulo);

        resumen = texto("", 13f, Paleta.SUAVE);
        resumen.setLineSpacing(0f, 1.3f);
        pantalla.addView(resumen, conMargen());

        pantalla.addView(texto("CÓMO PIENSA CORT", 12f, Paleta.AVISO), conMargen());
        filaModos = new LinearLayout(this);
        filaModos.setOrientation(LinearLayout.HORIZONTAL);
        String[][] modos = {{"auto", "Automático"}, {"local", "Teléfono"},
                            {"nube", "PC o nube"}};
        for (String[] modo : modos) {
            Button b = new Button(this);
            b.setText(modo[1]);
            b.setTextSize(12f);
            b.setLetterSpacing(0f);
            b.setOnClickListener(v -> {
                cerebro.ponerModo(modo[0]);
                pintaResumen();
            });
            filaModos.addView(b, enFila(52));
        }
        pantalla.addView(filaModos, conMargen());

        if (!CerebroLocal.hayLibreria()) {
            pantalla.addView(texto("Sin la librería del motor en este APK ("
                    + CerebroLocal.motivoSinLibreria() + ") los cerebros se bajan y se "
                    + "verifican igual, pero no se abren. La compila el trabajo "
                    + "`motor-local` del repo y la mete en el APK `compilar.sh`.",
                    12f, Paleta.AVISO), conMargen());
        }

        pantalla.addView(texto("CEREBROS OFRECIDOS", 12f, Paleta.AVISO), conMargen());
        List<CerebroLocal.Ficha> catalogo = CerebroLocal.catalogo(this);
        if (catalogo.isEmpty()) {
            pantalla.addView(texto("El catálogo del APK está roto o vacío ("
                    + CerebroLocal.avisoDeCatalogo() + ").", 13f, Paleta.AVISO),
                    conMargen());
        }
        for (CerebroLocal.Ficha d : catalogo) {
            Fila f = new Fila(d);
            filas.add(f);
            pantalla.addView(fila(f), conMargen());
        }

        pantalla.addView(texto("OÍDO EN ESPAÑOL (VOSK)", 12f, Paleta.AVISO), conMargen());
        final Motor oido = Motor.compartido(this);
        estadoOido = texto("", 13f, Paleta.SUAVE);
        estadoOido.setLineSpacing(0f, 1.3f);
        pantalla.addView(estadoOido, conMargen());
        LinearLayout filaOido = new LinearLayout(this);
        filaOido.setOrientation(LinearLayout.HORIZONTAL);
        bajarOido = boton("Bajar el oído");
        bajarOido.setOnClickListener(v -> {
            oido.bajaYMonta();
            hiloUI.postDelayed(repintaOido, 400L);
        });
        filaOido.addView(bajarOido, enFila(52));
        pantalla.addView(filaOido, conMargen());
        pantalla.addView(texto("Este es el dictado que NO sale del teléfono. Sin él, "
                + "CORT escucha con el motor de voz de Android y el audio viaja por "
                + "internet. Son " + Motor.mb(oido.pesoDelModelo()) + " MB una sola vez: "
                + "se reanuda si se corta la Wi-Fi y la suma se comprueba entera antes "
                + "de fiarse.", 12f, Paleta.SUAVE), conMargen());

        pantalla.addView(texto("PALABRA DE ACTIVACIÓN", 12f, Paleta.AVISO), conMargen());
        estadoDespertador = texto("", 13f, Paleta.SUAVE);
        estadoDespertador.setLineSpacing(0f, 1.3f);
        pantalla.addView(estadoDespertador, conMargen());
        LinearLayout filaDespertador = new LinearLayout(this);
        filaDespertador.setOrientation(LinearLayout.HORIZONTAL);
        botonDespertador = boton("Encender «hola CORT»");
        botonDespertador.setOnClickListener(v -> cambiaDespertador());
        filaDespertador.addView(botonDespertador, enFila(52));
        pantalla.addView(filaDespertador, conMargen());
        pantalla.addView(texto("Con Vosk y gramática cerrada: sólo «hola cort» u «oye cort», "
                + "no la casa entera. Se apaga sola a los cinco minutos sin que nadie la "
                + "llame y al apagar la pantalla. El aviso de la bandeja no escribe lo que "
                + "se oyó. El gasto de batería real se mide en este aparato, no se promete.",
                12f, Paleta.SUAVE), conMargen());

        pantalla.addView(texto("CEREBRO QUE SE BAJA SOLO", 12f, Paleta.AVISO), conMargen());
        estadoAuto = texto("", 13f, Paleta.SUAVE);
        estadoAuto.setLineSpacing(0f, 1.3f);
        pantalla.addView(estadoAuto, conMargen());
        LinearLayout filaAuto = new LinearLayout(this);
        filaAuto.setOrientation(LinearLayout.HORIZONTAL);
        botonAuto = boton("Encender");
        botonAuto.setOnClickListener(v -> cambiaAuto());
        filaAuto.addView(botonAuto, enFila(52));
        Button comprobar = boton("Comprobar ahora");
        comprobar.setOnClickListener(v -> {
            AutoCerebro.revisa(this);
            pintaAuto();
        });
        filaAuto.addView(comprobar, enFila(52));
        Button detener = boton("Detener");
        detener.setOnClickListener(v -> {
            ServicioBajada.detener(this);
            pintaAuto();
        });
        filaAuto.addView(detener, enFila(52));
        pantalla.addView(filaAuto, conMargen());
        pantalla.addView(texto("Sólo con Wi-Fi (red sin medir), sólo si no hay ya un GGUF "
                + "bajado, y sólo el primero del catálogo que quepa en la RAM libre y en el "
                + "disco. A los 40 KB/s medidos en esta casa, los 491 MB del 0,5B son unas "
                + "3 h 20 min: por eso viene apagado y el costo está escrito aquí. La bajada "
                + "sigue aunque cierres esta pantalla, con su aviso y su botón de Detener.",
                12f, Paleta.SUAVE), conMargen());

        pantalla.addView(texto("CARÁCTER Y CONVERSACIÓN", 12f, Paleta.AVISO), conMargen());
        estadoCaracter = texto("", 13f, Paleta.SUAVE);
        estadoCaracter.setLineSpacing(0f, 1.3f);
        pantalla.addView(estadoCaracter, conMargen());
        LinearLayout filaCaracter = new LinearLayout(this);
        filaCaracter.setOrientation(LinearLayout.HORIZONTAL);
        Button saludar = boton("Saludo de la primera vez");
        saludar.setOnClickListener(v -> {
            respuesta.setText(Consticion.primerSaludo(this));
            respuesta.setTextColor(Paleta.CLARO);
        });
        filaCaracter.addView(saludar, enFila(52));
        Button olvidar = boton("Olvida la conversación");
        olvidar.setOnClickListener(v -> {
            recuerdos.olvidaTurnos();
            pintaCaracter();
        });
        filaCaracter.addView(olvidar, enFila(52));
        pantalla.addView(filaCaracter, conMargen());
        pantalla.addView(texto("El carácter vive en `assets/consticion.json`, no escrito en "
                + "Java: se puede cambiar el tono sin recompilar. Los turnos se guardan en "
                + "la memoria del teléfono y viajan con cada pregunta; «olvida la "
                + "conversación» borra los turnos y deja los hechos y las habilidades.",
                12f, Paleta.SUAVE), conMargen());

        pantalla.addView(texto("PROBAR EL QUE ESTÉ ABIERTO", 12f, Paleta.AVISO),
                conMargen());
        pregunta = new EditText(this);
        pregunta.setHint("pregunta algo corto");
        pregunta.setText("dime en dos frases qué es un puerto serie");
        pregunta.setTextColor(Paleta.CLARO);
        pregunta.setHintTextColor(Paleta.SUAVE);
        pregunta.setBackgroundColor(Paleta.CAMPO);
        pregunta.setTextSize(14f);
        pantalla.addView(pregunta, conMargen());

        LinearLayout filaPrueba = new LinearLayout(this);
        filaPrueba.setOrientation(LinearLayout.HORIZONTAL);
        Button probar = boton("Probar (mide tokens/s)");
        probar.setOnClickListener(v -> probar());
        filaPrueba.addView(probar, enFila(52));
        Button parar = boton("Interrumpir");
        parar.setOnClickListener(v -> {
            cerebro.interrumpir();
            respuesta.append("…");
        });
        filaPrueba.addView(parar, enFila(52));
        pantalla.addView(filaPrueba, conMargen());

        respuesta = texto("", 14f, Paleta.CLARO);
        respuesta.setTextIsSelectable(true);
        respuesta.setLineSpacing(0f, 1.35f);
        pantalla.addView(respuesta, conMargen());

        pantalla.addView(texto("Los archivos caen en la carpeta de datos de CORT "
                + "(`Android/data/dev.sandra.cort.movil/files/modelos`, y el oído en "
                + "`files/motor`): no los ve otra "
                + "app y se van si se desinstala CORT. Con la red de la casa son minutos; "
                + "con datos del teléfono, cuenta los megas.\n\n"
                + "Ningún GGUF viaja dentro del APK, y desde `cort-v0.16.2` tampoco el "
                + "modelo de español: lo que se instala pesa decenas de MB y no 792 MB más.",
                12f, Paleta.SUAVE), conMargen());

        Button volver = boton("Volver");
        volver.setOnClickListener(v -> finish());
        pantalla.addView(volver, conMargen());

        pintaResumen();
    }

    // ------------------------------------------------------------------ la fila

    private LinearLayout fila(Fila f) {
        CerebroLocal.Ficha d = f.datos;
        LinearLayout caja = new LinearLayout(this);
        caja.setOrientation(LinearLayout.VERTICAL);
        caja.setBackgroundColor(Paleta.CAMPO);
        int pad = dp(14);
        caja.setPadding(pad, pad, pad, pad);

        caja.addView(texto(d.nombre, 15f, Paleta.CLARO));
        caja.addView(texto(mb(d.bytes) + " MB · contexto " + d.contexto + " tokens · "
                + d.hilos + " hilos · " + d.nota, 12f, Paleta.SUAVE), conMargen());

        f.estado = texto("", 12f, Paleta.SUAVE);
        f.estado.setLineSpacing(0f, 1.3f);
        caja.addView(f.estado, conMargen());

        LinearLayout botones = new LinearLayout(this);
        botones.setOrientation(LinearLayout.HORIZONTAL);
        f.bajar = boton("Bajar");
        f.bajar.setOnClickListener(v -> bajar(f));
        botones.addView(f.bajar, enFila(48));
        f.usar = boton("Usar");
        f.usar.setOnClickListener(v -> usar(f));
        botones.addView(f.usar, enFila(48));
        f.borrar = boton("Borrar");
        f.borrar.setOnClickListener(v -> borrar(f));
        botones.addView(f.borrar, enFila(48));
        caja.addView(botones, conMargen());
        return caja;
    }

    private File finalDe(Fila f) {
        return CerebroLocal.archivoDe(this, f.datos.archivo);
    }

    private File parcialDe(Fila f) {
        return new File(finalDe(f).getPath() + ".part");
    }

    /** Lo que hay en disco ahora mismo, dicho con números de este teléfono. */
    private void pintaEstado(Fila f) {
        CerebroLocal.Ficha d = f.datos;
        File gguf = finalDe(f);
        File parcial = parcialDe(f);
        String puerta = cerebro.cabe(d.bytes)
                ? "cabe holgado en la RAM libre"
                : "va justo: la puerta holgada pide " + cerebro.falta(d.bytes)
                        + " y hay " + cerebro.memoriaLibre() / 1024 / 1024 + " MB"
                        + (cerebro.sePuedeIntentar(d.bytes)
                                ? " · se puede intentar con mmap" : " · ni para intentarlo");
        boolean abierto = cerebro.modeloActivo() != null
                && cerebro.modeloActivo().getName().equals(d.archivo);

        if (gguf.isFile() && gguf.length() == d.bytes) {
            f.estado.setText("bajado y verificado con su SHA-256 · " + puerta
                    + (abierto ? " · ESTÁ ABIERTO" : ""));
            f.estado.setTextColor(Paleta.CIAN);
            f.bajar.setEnabled(false);
            f.usar.setEnabled(true);
            return;
        }
        if (gguf.isFile()) {
            f.estado.setText("el archivo pesa " + gguf.length() + " bytes y el catálogo "
                    + "anuncia " + d.bytes + ": no es el mismo. Bórralo.");
            f.estado.setTextColor(Paleta.AVISO);
            f.bajar.setEnabled(false);
            f.usar.setEnabled(false);
            return;
        }
        if (parcial.isFile()) {
            long hecho = parcial.length();
            f.estado.setText("a medias: " + mb(hecho) + " de " + mb(d.bytes) + " MB ("
                    + tantoPorCiento(hecho, d.bytes) + " %) · " + puerta);
            f.estado.setTextColor(Paleta.AVISO);
            f.bajar.setText("Seguir");
            f.bajar.setEnabled(true);
            f.usar.setEnabled(false);
            return;
        }
        f.estado.setText("sin bajar · " + puerta);
        f.estado.setTextColor(Paleta.SUAVE);
        f.bajar.setText("Bajar");
        f.bajar.setEnabled(true);
        f.usar.setEnabled(false);
    }

    /**
     * El estado del oído, con su progreso. No lo pinta `Motor` (vive en otro
     * hilo y no toca pantallas): este enhebrador lo rele cada segundo mientras
     * haya una descarga en curso, que es cuando cambia sola.
     */
    private final Runnable repintaOido = new Runnable() {
        @Override
        public void run() {
            pintaOido();
            if (!cerrando && Motor.compartido(Cerebros.this).estaDescargando()) {
                hiloUI.postDelayed(this, 1000L);
            }
        }
    };

    private void pintaOido() {
        if (estadoOido == null) {
            return;
        }
        Motor oido = Motor.compartido(this);
        if (oido.listo()) {
            estadoOido.setText("montado y listo · el dictado no sale del teléfono");
            estadoOido.setTextColor(Paleta.CIAN);
            bajarOido.setText("Ya está");
            bajarOido.setEnabled(false);
            return;
        }
        if (!oido.sePuedeBajar()) {
            estadoOido.setText("sin ficha de descarga (falta `assets/oido.json` en el APK): "
                    + "el dictado va por el motor de Android, que usa internet.");
            estadoOido.setTextColor(Paleta.AVISO);
            bajarOido.setEnabled(false);
            return;
        }
        if (oido.estaDescargando()) {
            estadoOido.setText(oido.descargaTexto());
            estadoOido.setTextColor(Paleta.CIAN);
            bajarOido.setText("Bajando…");
            bajarOido.setEnabled(false);
            // `removeCallbacks` antes del `postDelayed`: si no, cada repintado
            // (cambio de modo, regreso de otra pantalla) monta un enhebrador más.
            hiloUI.removeCallbacks(repintaOido);
            hiloUI.postDelayed(repintaOido, 1000L);
            return;
        }
        File parcial = new File(oido.zipDelModelo().getPath() + ".part");
        if (parcial.isFile() && parcial.length() > 0) {
            estadoOido.setText("cortado a " + Motor.mb(parcial.length()) + " de "
                    + Motor.mb(oido.pesoDelModelo()) + " MB · toca Seguir y arranca donde se paró");
            estadoOido.setTextColor(Paleta.AVISO);
            bajarOido.setText("Seguir");
            bajarOido.setEnabled(true);
            return;
        }
        estadoOido.setText(oido.descargaTexto() + " · " + Motor.mb(oido.pesoDelModelo())
                + " MB por bajar");
        estadoOido.setTextColor(Paleta.SUAVE);
        bajarOido.setText("Bajar");
        bajarOido.setEnabled(true);
    }

    private void pintaResumen() {
        String modo = cerebro.modo();
        String rotulo = "auto".equals(modo) ? "Automático (teléfono si cabe, si no PC/nube)"
                : "local".equals(modo) ? "Sólo el teléfono"
                : "PC o nube (el GGUF no interviene)";
        resumen.setText("este teléfono: " + cerebro.memoriaLibre() / 1024 / 1024
                + " MB libres ahora · " + CerebroLocal.infoSistema() + "\n"
                + "modo: " + rotulo + "\n" + cerebro.estado());
        pintaModos();
        for (Fila f : filas) {
            pintaEstado(f);
        }
        pintaOido();
        pintaDespertador();
        pintaAuto();
        pintaCaracter();
    }

    /* ------------------------------------------- voz, bajada sola y carácter */

    /**
     * El interruptor de la palabra de activación. Se escribe la preferencia **antes**
     * de llamar al servicio y se revierte si Android no lo deja: así la pantalla no
     * dice «encendido» mientras el sistema lo rechazó. El `try/catch` está aquí, en
     * la frontera con la interfaz, y no dentro de `ServicioEscucha.cambia`.
     */
    private void cambiaDespertador() {
        boolean puesto = !ServicioEscucha.encendida(this);
        prefsDespertador().edit().putBoolean(ServicioEscucha.CLAVE, puesto).apply();
        try {
            ServicioEscucha.cambia(this, puesto);
        } catch (RuntimeException noDeja) {
            prefsDespertador().edit().putBoolean(ServicioEscucha.CLAVE, false).apply();
            estadoDespertador.setText("el teléfono no la dejó encender: "
                    + noDeja.getMessage() + ". Ábrela desde el menú de CORT con la app "
                    + "en primer plano.");
            estadoDespertador.setTextColor(Paleta.AVISO);
            return;
        }
        hiloUI.postDelayed(this::pintaDespertador, 700L);
    }

    private android.content.SharedPreferences prefsDespertador() {
        return getSharedPreferences("cort", MODE_PRIVATE);
    }

    private void pintaDespertador() {
        boolean puesta = ServicioEscucha.encendida(this);
        boolean montada = ServicioEscucha.montada();
        boolean oido = Motor.compartido(this).listo();
        botonDespertador.setText(puesta ? "Apagar «hola CORT»" : "Encender «hola CORT»");
        String linea;
        if (!puesta) {
            linea = "apagada · el ● de la cara sigue dictando igual";
        } else if (!oido) {
            linea = "encendida en los ajustes, pero sin el modelo de español no hay palabra "
                    + "que reconocer: bájalo arriba";
        } else if (montada) {
            linea = "encendida y escuchando ahora mismo · se apaga a los 5 min sin que nadie "
                    + "la llame y al apagar la pantalla";
        } else {
            linea = "encendida en los ajustes · Android no la deja arrancar sola desde atrás: "
                    + "se monta al abrir CORT";
        }
        estadoDespertador.setText(linea);
        estadoDespertador.setTextColor(puesta && oido ? Paleta.CIAN : Paleta.SUAVE);
    }

    private void cambiaAuto() {
        boolean puesto = !AutoCerebro.quiere(this);
        AutoCerebro.pon(this, puesto);
        if (puesto) {
            AutoCerebro.revisa(this);
        }
        pintaAuto();
    }

    /**
     * La bajada sola, con su motivo escrito. El progreso se lee de las preferencias
     * que escribe `ServicioBajada`: no hay IPC, así que esta pantalla puede montarse
     * después de que la bajada empezara y aun así verla.
     */
    private void pintaAuto() {
        boolean quiere = AutoCerebro.quiere(this);
        botonAuto.setText(quiere ? "Apagar" : "Encender");
        String junto = (quiere ? "encendido" : "apagado")
                + " · " + (AutoCerebro.redSinLimite(this) ? "Wi-Fi sin medir" : "red medida o sin red")
                + " · disco libre " + AutoCerebro.huecoLibre(this) / 1024 / 1024 + " MB"
                + " · RAM libre " + cerebro.memoriaLibre() / 1024 / 1024 + " MB";
        if (ServicioBajada.enCurso(this)) {
            junto += "\n" + ServicioBajada.texto(this) + " (" + ServicioBajada.pct(this) + " %)";
            estadoAuto.setTextColor(Paleta.CIAN);
            hiloUI.removeCallbacks(repintaAuto);
            hiloUI.postDelayed(repintaAuto, 1500L);
        } else {
            junto += "\n" + AutoCerebro.motivo(this);
            estadoAuto.setTextColor(quiere ? Paleta.SUAVE : Paleta.AVISO);
        }
        estadoAuto.setText(junto);
    }

    private final Runnable repintaAuto = new Runnable() {
        @Override
        public void run() {
            if (cerrando) {
                return;
            }
            pintaAuto();
        }
    };

    private void pintaCaracter() {
        estadoCaracter.setText(Consticion.resumen(this) + "\n"
                + recuerdos.cuentasDeTurnos() + " turnos guardados · "
                + recuerdos.cuentasDeHechos() + " hechos · "
                + recuerdos.cuentasDeHabilidades() + " habilidades aprendidas");
        estadoCaracter.setTextColor(Consticion.avisoDeCarga(this).isEmpty()
                ? Paleta.SUAVE : Paleta.AVISO);
    }

    private void pintaModos() {
        String activo = cerebro.modo();
        String[] claves = {"auto", "local", "nube"};
        for (int i = 0; i < filaModos.getChildCount() && i < claves.length; i++) {
            Button b = (Button) filaModos.getChildAt(i);
            boolean elegido = activo.equals(claves[i]);
            b.setTextColor(elegido ? Paleta.FONDO : Paleta.CIAN);
            b.setBackgroundColor(elegido ? Paleta.CIAN : 0xFF132F3F);
        }
    }
    // --------------------------------------------------------------- descarga

    private void bajar(Fila f) {
        f.bajar.setEnabled(false);
        Thread trabajo = new Thread(() -> {
            try {
                descargar(f);
            } catch (Exception algo) {
                final String culpa = algo.getClass().getSimpleName() + ": "
                        + algo.getMessage();
                hiloUI.post(() -> {
                    f.estado.setText("falló: " + culpa + ". Lo bajado queda: se reanada.");
                    f.estado.setTextColor(Paleta.AVISO);
                    f.bajar.setText("Reintentar");
                    f.bajar.setEnabled(true);
                });
            }
        }, "cort-bajar-" + f.datos.id);
        trabajo.setDaemon(true);
        trabajo.start();
    }

    /**
     * Baja, y si ya había un `.part` lo retoma donde se cortó. Al reanadar la suma se
     * rehace desde el principio — es volver a leer el archivo una vez — y es el precio
     * de no fiarse de lo que hubo antes.
     */
    private void descargar(Fila f) throws Exception {
        CerebroLocal.Ficha d = f.datos;
        File parcial = parcialDe(f);
        File directorio = parcial.getParentFile();
        if (directorio != null && !directorio.isDirectory() && !directorio.mkdirs()) {
            throw new IOException("no se pudo crear " + directorio);
        }
        long reanudado = parcial.isFile() ? parcial.length() : 0L;

        HttpURLConnection conexion = (HttpURLConnection) new URL(d.url).openConnection();
        try {
            conexion.setInstanceFollowRedirects(true);
            conexion.setConnectTimeout(20_000);
            conexion.setReadTimeout(60_000);
            if (reanudado > 0) {
                conexion.setRequestProperty("Range", "bytes=" + reanudado + "-");
            }
            int codigo = conexion.getResponseCode();
            boolean continua = codigo == 206 && reanudado > 0;
            if (codigo != 200 && !continua) {
                throw new IOException("HTTP " + codigo + " al pedir " + d.url);
            }
            // Un 200 cuando se pidió `Range` quiere decir que el servidor hizo caso
            // omiso: lo que hay en el `.part` no es el principio de este archivo.
            long base = continua ? reanudado : 0L;
            if (!continua && reanudado > 0) {
                parcial.delete();
            }

            long ofrece = conexion.getContentLengthLong();
            if (ofrece > 0 && base + ofrece != d.bytes) {
                throw new IOException("el servidor ofrece " + (base + ofrece)
                        + " bytes y el catálogo fija " + d.bytes);
            }

            MessageDigest digiero = MessageDigest.getInstance("SHA-256");
            if (base > 0) {
                sumarDesde(digiero, parcial, base);
            }

            long escrito = base;
            long antes = System.currentTimeMillis();
            long ultimoPintado = 0L;
            try (InputStream entrada = conexion.getInputStream();
                 OutputStream salida = new FileOutputStream(parcial, base > 0)) {
                byte[] trozo = new byte[64 * 1024];
                int n;
                while (!cerrando && (n = entrada.read(trozo)) > 0) {
                    salida.write(trozo, 0, n);
                    digiero.update(trozo, 0, n);
                    escrito += n;
                    long ahora = System.currentTimeMillis();
                    if (ahora - ultimoPintado > 500L) {
                        ultimoPintado = ahora;
                        final long cb = escrito;
                        final long kbps = (escrito - base) * 1000
                                / Math.max(1L, ahora - antes) / 1024L;
                        hiloUI.post(() -> {
                            f.estado.setText("bajando: " + mb(cb) + " de " + mb(d.bytes)
                                    + " MB (" + tantoPorCiento(cb, d.bytes) + " %) · "
                                    + kbps + " KB/s");
                            f.estado.setTextColor(Paleta.CIAN);
                        });
                    }
                }
            }
            if (cerrando) {
                return;                       // lo bajado queda para la próxima vez
            }
            if (escrito != d.bytes) {
                throw new IOException("la conexión cortó en " + escrito + " bytes, se "
                        + "esperaban " + d.bytes);
            }
            String suma = hex(digiero.digest());
            if (!suma.equalsIgnoreCase(d.sha256)) {
                parcial.delete();
                throw new IOException("la SHA-256 no cuadra (" + suma.substring(0, 12)
                        + "… contra " + d.sha256.substring(0, 12) + "…): se borró");
            }
            if (!parcial.renameTo(finalDe(f))) {
                throw new IOException("verificado, pero no se pudo renombrar el archivo");
            }
            hiloUI.post(this::pintaResumen);
        } finally {
            conexion.disconnect();
        }
    }

    private void borrar(Fila f) {
        finalDe(f).delete();
        parcialDe(f).delete();
        if (cerebro.modeloActivo() != null
                && cerebro.modeloActivo().getName().equals(f.datos.archivo)) {
            cerebro.cerrar();
        }
        pintaResumen();
    }

    // ------------------------------------------------------------------ abrir

    /** Abrir 752 MB de disco también va en su hilo; la cara no se congela. */
    private void usar(Fila f) {
        f.usar.setEnabled(false);
        f.estado.setText("abriendo " + f.datos.archivo + " en memoria, un momento…");
        f.estado.setTextColor(Paleta.AVISO);
        Thread trabajo = new Thread(() -> {
            final int codigo = cerebro.cargar(finalDe(f), f.datos.contexto, f.datos.hilos);
            hiloUI.post(() -> {
                f.usar.setEnabled(true);
                f.estado.setText(motivo(codigo, f));
                f.estado.setTextColor(codigo == 0 ? Paleta.CIAN : Paleta.AVISO);
                pintaResumen();
            });
        }, "cort-abrir-" + f.datos.id);
        trabajo.setDaemon(true);
        trabajo.start();
    }

    private String motivo(int codigo, Fila f) {
        switch (codigo) {
            case 0:  return "abierto: " + f.datos.archivo + " · " + cerebro.backends()
                            + " · ya se puede probar abajo";
            case 1:  return "el archivo no existe o está cortado";
            case 2:  return "sin memoria para un contexto de " + f.datos.contexto
                            + " tokens: hay " + cerebro.memoriaLibre() / 1024 / 1024
                            + " MB libres";
            case 3:  return "no es un GGUF que este motor entienda";
            default: return "sin librería nativa en este APK ("
                            + CerebroLocal.motivoSinLibreria() + ")";
        }
    }

    // ------------------------------------------------------------------ probar

    private void probar() {
        if (!cerebro.abierto()) {
            respuesta.setText("Ningún cerebro abierto: baja uno, espera su «verificado» "
                    + "y pulsa «Usar».");
            respuesta.setTextColor(Paleta.AVISO);
            return;
        }
        respuesta.setText("");
        respuesta.setTextColor(Paleta.CLARO);
        final String dicho = pregunta.getText().toString().trim();
        if (dicho.isEmpty()) {
            respuesta.setText("Escribe la pregunta primero.");
            return;
        }
        final List<String[]> historial = new ArrayList<>();
        historial.add(new String[] {"user", dicho});
        Thread trabajo = new Thread(() -> {
            final String sa = cerebro.preguntar(CerebroLocal.sistemaCort(""), historial,
                    pieza -> hiloUI.post(() -> {
                        if (pieza != null) {
                            respuesta.append(pieza);
                        }
                    }), 160, 0.7f);
            final String medida = cerebro.ultimaMedida();
            hiloUI.post(() -> {
                if (sa == null) {
                    respuesta.setText("no respondió (" + medida + ")");
                    respuesta.setTextColor(Paleta.AVISO);
                    return;
                }
                respuesta.append("\n\n— " + medida);
                respuesta.setTextColor(Paleta.CLARO);
            });
        }, "cort-probar-cerebro");
        trabajo.setDaemon(true);
        trabajo.start();
    }

    // ---------------------------------------------------------------- utilería

    private static void sumarDesde(MessageDigest digiero, File archivo, long hasta)
            throws IOException {
        byte[] trozo = new byte[128 * 1024];
        try (InputStream in = new FileInputStream(archivo)) {
            long leido = 0L;
            int n;
            while (leido < hasta
                   && (n = in.read(trozo, 0, (int) Math.min(trozo.length, hasta - leido)))
                      > 0) {
                digiero.update(trozo, 0, n);
                leido += n;
            }
            if (leido != hasta) {
                throw new IOException("lo ya bajado se acortó mientras se verificaba");
            }
        }
    }

    private static String hex(byte[] bytes) {
        StringBuilder cuadro = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) {
            cuadro.append(Character.forDigit((b >> 4) & 0xF, 16));
            cuadro.append(Character.forDigit(b & 0xF, 16));
        }
        return cuadro.toString();
    }

    private static String mb(long bytes) {
        return String.format(Locale.US, "%.2f", bytes / 1024.0 / 1024.0);
    }

    private static long tantoPorCiento(long hecho, long total) {
        return total > 0 ? hecho * 100 / total : 0L;
    }

    private TextView texto(String contenido, float tam, int color) {
        TextView campo = new TextView(this);
        campo.setText(contenido);
        campo.setTextSize(tam);
        campo.setTextColor(color);
        return campo;
    }

    private Button boton(String rotulo) {
        Button b = new Button(this);
        b.setText(rotulo);
        b.setTextColor(Paleta.CIAN);
        b.setBackgroundColor(0xFF132F3F);
        b.setTextSize(13f);
        return b;
    }

    /** Un botón dentro de una fila horizontal: ancho 0 y peso, para que quepan tres. */
    private LinearLayout.LayoutParams enFila(int altoDp) {
        LinearLayout.LayoutParams medida = new LinearLayout.LayoutParams(0, dp(altoDp), 1f);
        medida.topMargin = dp(10);
        return medida;
    }

    private LinearLayout.LayoutParams conMargen() {
        LinearLayout.LayoutParams medida = new LinearLayout.LayoutParams(-1, -2);
        medida.topMargin = dp(14);
        return medida;
    }

    private int dp(float valor) {
        return Math.round(valor * getResources().getDisplayMetrics().density);
    }

    @Override
    protected void onDestroy() {
        cerrando = true;
        hiloUI.removeCallbacks(repintaAuto);
        hiloUI.removeCallbacks(repintaOido);
        cerebro.interrumpir();
        super.onDestroy();
    }
}
