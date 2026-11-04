package dev.sandra.cort.movil;

import android.app.Activity;
import android.content.Context;
import android.content.pm.PackageManager;
import android.graphics.ImageFormat;
import android.graphics.Matrix;
import android.graphics.SurfaceTexture;
import android.hardware.camera2.CameraCaptureSession;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraDevice;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.params.StreamConfigurationMap;
import android.media.Image;
import android.media.ImageReader;
import android.os.Bundle;
import android.os.Handler;
import android.os.HandlerThread;
import android.util.Size;
import android.view.Gravity;
import android.view.TextureView;
import android.widget.FrameLayout;
import android.widget.TextView;

import com.google.zxing.BinaryBitmap;
import com.google.zxing.DecodeHintType;
import com.google.zxing.LuminanceSource;
import com.google.zxing.MultiFormatReader;
import com.google.zxing.NotFoundException;
import com.google.zxing.Result;
import com.google.zxing.common.HybridBinarizer;

import java.util.concurrent.atomic.AtomicBoolean;

/**
 * La cámara leyendo el QR que pinta CORT en la pantalla de la PC (F14b).
 *
 * Por qué dentro del APK y no con la app de terceros de siempre: en un Galaxy A16 sin
 * Google Play Services no hay `IntentIntegrator` que lanzar, y mandarse el enlace por una
 * cámara ajena sería entregarle a otra aplicación la llave de la red de la casa. El decodificador
 * es `com.google.zxing:core` (Apache-2.0, Java puro, sin librerías nativas) fijado por SHA-256
 * en `deps.txt`; lo que se baja se lee antes de compilarlo.
 *
 * Dos cosas de este archivo no son ornamentales y se rompen si se tocan sin medir:
 *
 * * La luminancia se toma del plano `Y` de `YUV_420_888` con su `rowStride`. Convertir el
 *   frame a ARGB costaría un millón de operaciones por imagen en un teléfono de gama de
 *   entrada; leer el plano es copiar bytes.
 * * Sólo hay un decodificador trabajando a la vez (`ocupado`): si cada frame entrante
 *   encolara un `MultiFormatReader`, la cola crecería más rápido que la cámara y el
 *   escáner se comería la RAM del aparato.
 */
public class Escaner extends Activity {

    /** Lo que devuelve la actividad: el texto del cuadro, tal cual lo imprimió la PC. */
    public static final String TEXTO = "dev.sandra.cort.movil.Escaner.texto";

    // 640×480 decodifica un QR de pantalla a un metro con margen de sobra y es lo bastante
    // pequeño para no atragantar al aparato. Más grande no lee mejor: baja el fps.
    private static final int ANCHO_MINIMO = 640;
    private static final int ALTO_MINIMO = 480;

    private TextureView lienzo;
    private CameraDevice camara;
    private CameraCaptureSession sesion;
    private ImageReader lector;
    private HandlerThread hilo;
    private Handler fondo;
    private final AtomicBoolean ocupado = new AtomicBoolean(false);
    private Size cuadro;
    private boolean cerrado;

    @Override
    protected void onCreate(Bundle guardado) {
        super.onCreate(guardado);
        lienzo = new TextureView(this);
        lienzo.setBackgroundColor(0xFF05121A);
        FrameLayout marco = new FrameLayout(this);
        marco.addView(lienzo, new FrameLayout.LayoutParams(-1, -1));

        TextView guia = new TextView(this);
        guia.setText("Apunta el cuadro que pinta CORT en la PC\n"
                + "«python3 cort-bridge/cort_enlace.py --qr»\n\n"
                + "(no se guarda ninguna imagen: se lee y se va)");
        guia.setTextColor(Paleta.CLARO);
        guia.setTextSize(14f);
        guia.setPadding(48, 48, 48, 48);
        guia.setGravity(Gravity.CENTER_HORIZONTAL | Gravity.BOTTOM);
        marco.addView(guia, new FrameLayout.LayoutParams(-1, -2, Gravity.BOTTOM));

        TextView titulo = new TextView(this);
        titulo.setText("ENLACE · ESCANEAR");
        titulo.setTextColor(Paleta.CIAN);
        titulo.setTextSize(13f);
        titulo.setLetterSpacing(0.12f);
        titulo.setPadding(48, 48, 48, 8);
        marco.addView(titulo, new FrameLayout.LayoutParams(-1, -2, Gravity.TOP));
        setContentView(marco);

        lienzo.setSurfaceTextureListener(enlaceSuperficie);
        hilo = new HandlerThread("cort-camara");
        hilo.start();
        fondo = new Handler(hilo.getLooper());
    }

    /** El marco de la cámara, cuando la superficie ya está disponível. */
    private final TextureView.SurfaceTextureListener enlaceSuperficie =
            new TextureView.SurfaceTextureListener() {
                @Override public void onSurfaceTextureAvailable(SurfaceTexture textura, int w, int h) {
                    abrirCamara();
                }
                @Override public void onSurfaceTextureSizeChanged(SurfaceTexture t, int w, int h) {
                    centrar(w, h);
                }
                @Override public boolean onSurfaceTextureDestroyed(SurfaceTexture t) {
                    apagar();
                    return true;
                }
                @Override public void onSurfaceTextureUpdated(SurfaceTexture t) { }
            };

    private void abrirCamara() {
        if (hilo == null) {
            // Tras un `onPause` el hilo se soltó y la superficie se rehace al volver: si no
            // se rehace él, `openCamera(..., null)` caería en el hilo de la interfaz y el
            // decodificador congelaría la pantalla.
            hilo = new HandlerThread("cort-camara");
            hilo.start();
            fondo = new Handler(hilo.getLooper());
        }
        CameraManager servicios = (CameraManager) getSystemService(Context.CAMERA_SERVICE);
        try {
            String id = null;
            for (String candidato : servicios.getCameraIdList()) {
                CameraCharacteristics rasgos = servicios.getCameraCharacteristics(candidato);
                Integer sentido = rasgos.get(CameraCharacteristics.LENS_FACING);
                if (sentido != null && sentido == CameraCharacteristics.LENS_FACING_BACK) {
                    id = candidato;
                    cuadro = elegir(rasgos.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP));
                    break;
                }
            }
            if (id == null) {
                avisar("este teléfono no tiene cámara trasera: pega la dirección a mano");
                return;
            }
            if (checkSelfPermission(android.Manifest.permission.CAMERA)
                    != PackageManager.PERMISSION_GRANTED) {
                pedirPermisoYReintentar();
                return;
            }
            lector = ImageReader.newInstance(cuadro.getWidth(), cuadro.getHeight(),
                    ImageFormat.YUV_420_888, 2);
            lector.setOnImageAvailableListener(this::leerFrame, fondo);
            servicios.openCamera(id, estadoDeCamara, fondo);
        } catch (SecurityException noAutorizado) {
            avisar("sin permiso de cámara no hay escáner: pega la dirección a mano");
        } catch (Exception cualquierCosa) {
            avisar("la cámara no arrancó: " + cualquierCosa.getMessage());
        }
    }

    /**
     * El permiso se pide aquí y no antes: así la pantalla de enlace puede lanzar el escáner
     * sin una coreografía de callbacks, y si la dueña dice que no, el plan B (teclear) sigue vivo.
     */
    private void pedirPermisoYReintentar() {
        requestPermissions(new String[]{android.Manifest.permission.CAMERA}, 41);
    }

    @Override
    public void onRequestPermissionsResult(int peticion, String[] permisos, int[] resultados) {
        super.onRequestPermissionsResult(peticion, permisos, resultados);
        if (resultados.length > 0 && resultados[0] == PackageManager.PERMISSION_GRANTED) {
            abrirCamara();
        } else {
            avisar("sin permiso de cámara no hay escáner: pega la dirección a mano");
        }
    }

    /** El tamaño YUV que más se ajuste a 640×480 sin pasarse: no se elige a ojo. */
    private Size elegir(StreamConfigurationMap mapas) {
        Size[] tamanos = mapas == null ? new Size[0]
                : mapas.getOutputSizes(ImageFormat.YUV_420_888);
        Size mejor = null;
        for (Size s : tamanos) {
            if (s.getWidth() < ANCHO_MINIMO || s.getHeight() < ALTO_MINIMO) {
                continue;
            }
            if (mejor == null
                    || (long) s.getWidth() * s.getHeight() < (long) mejor.getWidth() * mejor.getHeight()) {
                mejor = s;
            }
        }
        if (mejor != null) {
            return mejor;
        }
        // Ninguna salida llega al mínimo: se toma la mayor y se le pide al QR que sea grande
        // (el de la PC se imprime a 6 módulos por celda, así que normalmente sobra).
        Size mayor = null;
        for (Size s : tamanos) {
            if (mayor == null || (long) s.getWidth() * s.getHeight() > (long) mayor.getWidth() * mayor.getHeight()) {
                mayor = s;
            }
        }
        return mayor == null ? new Size(ANCHO_MINIMO, ALTO_MINIMO) : mayor;
    }

    private final CameraDevice.StateCallback estadoDeCamara = new CameraDevice.StateCallback() {
        @Override public void onOpened(CameraDevice dispositivo) {
            camara = dispositivo;
            pedirSesion();
        }
        @Override public void onDisconnected(CameraDevice dispositivo) {
            dispositivo.close();
            camara = null;
        }
        @Override public void onError(CameraDevice dispositivo, int error) {
            dispositivo.close();
            camara = null;
            runOnUiThread(() -> avisar("la cámara falló (" + error + "): pega la dirección a mano"));
        }
    };

    private void pedirSesion() {
        try {
            final SurfaceTexture textura = lienzo.getSurfaceTexture();
            if (textura == null || camara == null) {
                return;
            }
            textura.setDefaultBufferSize(cuadro.getWidth(), cuadro.getHeight());
            centrar(lienzo.getWidth(), lienzo.getHeight());
            android.view.Surface vistaPrevia = new android.view.Surface(textura);
            CaptureRequest.Builder peticion =
                    camara.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW);
            peticion.addTarget(vistaPrevia);
            peticion.set(CaptureRequest.CONTROL_AF_MODE,
                    CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE);
            CameraCaptureSession.StateCallback estados = new CameraCaptureSession.StateCallback() {
                @Override public void onConfigured(CameraCaptureSession nueva) {
                    sesion = nueva;
                    try {
                        peticion.set(CaptureRequest.CONTROL_MODE,
                                CaptureRequest.CONTROL_MODE_AUTO);
                        nueva.setRepeatingRequest(peticion.build(), null, fondo);
                    } catch (Exception cualquierCosa) {
                        runOnUiThread(() -> avisar("la vista previa no arrancó: pega la dirección"));
                    }
                }
                @Override public void onConfigureFailed(CameraCaptureSession fallida) {
                    runOnUiThread(() -> avisar("la cámara no se configuró: pega la dirección a mano"));
                }
            };
            camara.createCaptureSession(java.util.Arrays.asList(
                    vistaPrevia, lector.getSurface()), estados, fondo);
        } catch (Exception cualquierCosa) {
            avisar("no se pudo montar la sesión: " + cualquierCosa.getMessage());
        }
    }

    /** Que la vista previa no se estire: se escala y centra la matriz del TextureView. */
    private void centrar(int anchoVista, int altoVista) {
        if (cuadro == null || anchoVista == 0 || altoVista == 0) {
            return;
        }
        float escalar = Math.max((float) anchoVista / cuadro.getWidth(),
                (float) altoVista / cuadro.getHeight());
        float desplazadoX = (anchoVista - cuadro.getWidth() * escalar) / 2f;
        float desplazadoY = (altoVista - cuadro.getHeight() * escalar) / 2f;
        Matrix matriz = new Matrix();
        matriz.setScale(escalar, escalar);
        matriz.postTranslate(desplazadoX, desplazadoY);
        lienzo.setTransform(matriz);
    }

    /**
     * Un frame, una intención de decodificar. Si el lector anterior sigue ocupado, este se
     * tira: es mejor perder imágenes que acumularlas.
     */
    private void leerFrame(ImageReader fuente) {
        Image imagen = null;
        try {
            imagen = fuente.acquireLatestImage();
            if (imagen == null || !ocupado.compareAndSet(false, true)) {
                return;
            }
            final byte[] plano = copiarLuminancia(imagen);
            final int ancho = imagen.getWidth();
            final int alto = imagen.getHeight();
            fondo.post(() -> {
                try {
                    Result leido = decodificar(ancho, alto, plano);
                    if (leido != null) {
                        final String texto = leido.getText();
                        runOnUiThread(() -> entregar(texto));
                    }
                } finally {
                    ocupado.set(false);
                }
            });
        } catch (Exception cualquierCosa) {
            ocupado.set(false);
        } finally {
            if (imagen != null) {
                imagen.close();
            }
        }
    }

    /** El plano `Y` apretado, sin los rellenos de `rowStride` (zxing espera filas pegadas). */
    private static byte[] copiarLuminancia(Image imagen) {
        Image.Plano y = imagen.getPlanes()[0];
        java.nio.ByteBuffer buffer = y.getBuffer();
        int ancho = imagen.getWidth();
        int alto = imagen.getHeight();
        int salto = y.getRowStride();
        byte[] apretado = new byte[ancho * alto];
        if (salto == ancho) {
            buffer.get(apretado, 0, Math.min(buffer.remaining(), apretado.length));
            return apretado;
        }
        byte[] linea = new byte[salto];
        for (int fila = 0; fila < alto; fila++) {
            int disponible = buffer.remaining();
            if (disponible <= 0) {
                break;
            }
            buffer.get(linea, 0, Math.min(disponible, salto));
            System.arraycopy(linea, 0, apretado, fila * ancho, Math.min(ancho, salto));
        }
        return apretado;
    }

    /** QR y nada más: con todos los formatos activados zxing pierde ciclos buscando barras. */
    private static Result decodificar(int ancho, int alto, byte[] luminancia) {
        MultiFormatReader lector = new MultiFormatReader();
        java.util.Map<DecodeHintType, Object> pistas = new java.util.HashMap<>();
        pistas.put(DecodeHintType.POSSIBLE_FORMATS,
                java.util.Collections.singletonList(com.google.zxing.BarcodeFormat.QR_CODE));
        pistas.put(DecodeHintType.TRY_HARDER, Boolean.TRUE);
        try {
            return lector.decodeWithState(new BinaryBitmap(new HybridBinarizer(
                    new FuenteY(ancho, alto, luminancia))));
        } catch (NotFoundException noHayCuadro) {
            return null;
        } catch (Exception cualquierCosa) {
            return null;
        } finally {
            lector.reset();
        }
    }

    /** La luminancia de la cámara como fuente de zxing: sin ARGB, sin copias de más. */
    private static final class FuenteY extends LuminanceSource {
        private final byte[] datos;

        FuenteY(int ancho, int alto, byte[] datos) {
            super(ancho, alto);
            this.datos = datos;
        }

        @Override public byte[] getMatrix() {
            return datos;
        }

        @Override public int[] getRow(int y, int[] fila) {
            int ancho = getWidth();
            if (fila == null || fila.length < ancho) {
                fila = new int[ancho];
            }
            int base = y * ancho;
            for (int x = 0; x < ancho; x++) {
                fila[x] = datos[base + x] & 0xFF;
            }
            return fila;
        }
    }

    private void entregar(String texto) {
        if (cerrado) {
            return;
        }
        cerrado = true;
        android.content.Intent respuesta = new android.content.Intent();
        respuesta.putExtra(TEXTO, texto);
        setResult(RESULT_OK, respuesta);
        finish();
    }

    private void avisar(String motivo) {
        if (cerrado) {
            return;
        }
        cerrado = true;
        setResult(RESULT_CANCELED, new android.content.Intent().putExtra(TEXTO, motivo));
        finish();
    }

    @Override
    protected void onPause() {
        super.onPause();
        apagar();
    }

    /** La cámara es un recurso prestado: se suelta siempre, también si la dueña sale a media lectura. */
    private void apagar() {
        try {
            if (sesion != null) {
                sesion.close();
            }
        } catch (Exception ignorado) {
            // Cerrar una sesión ya cerrada es un `IllegalStateException` que no dice nada nuevo.
        }
        sesion = null;
        if (camara != null) {
            camara.close();
        }
        camara = null;
        if (lector != null) {
            lector.close();
        }
        lector = null;
        if (hilo != null) {
            hilo.quitSafely();
        }
        hilo = null;
    }
}
