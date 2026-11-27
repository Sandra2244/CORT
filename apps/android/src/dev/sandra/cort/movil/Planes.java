package dev.sandra.cort.movil;

import android.app.Activity;
import android.app.AlertDialog;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/** Ejecuta sólo planes ya validados y consume una aprobación exacta antes de los efectos. */
final class Planes {
    static final class Resultado {
        final String texto;
        final boolean ok;
        final String motivo;

        private Resultado(String texto, boolean ok, String motivo) {
            this.texto = texto;
            this.ok = ok;
            this.motivo = motivo;
        }
    }

    private final Activity actividad;
    private final Acciones acciones;
    private final Aprobaciones aprobaciones;

    Planes(Activity actividad, Acciones acciones, Aprobaciones aprobaciones) {
        this.actividad = actividad;
        this.acciones = acciones;
        this.aprobaciones = aprobaciones;
    }

    synchronized Resultado ejecutar(PlanNeural.Plan plan) {
        if (plan == null || plan.pasos.isEmpty()) {
            return new Resultado("No había un plan válido que ejecutar.", false, "plan vacío");
        }
        if (plan.sensible) {
            String firma = plan.firma();
            String token = aprobaciones.preparar("plan_neuronal", "ejecutar", "1", firma, firma);
            if (token == null) return new Resultado("No pude preparar la confirmación.", false, "sin token");
            if (!confirmar(plan)) {
                aprobaciones.revocar(token);
                return new Resultado("No ejecuté el plan: no recibí una confirmación a tiempo.",
                        false, "confirmación ausente o caducada");
            }
            if (!aprobaciones.consumir("plan_neuronal", "ejecutar", "1", firma, firma, token)) {
                return new Resultado("No ejecuté el plan: la confirmación ya no era válida.",
                        false, "confirmación consumida o caducada");
            }
        }
        StringBuilder texto = new StringBuilder();
        for (Cerebro.Resultado paso : plan.pasos) {
            Acciones.Resultado salida = enLaInterfaz(paso);
            if (salida == null || !salida.ok || salida.texto == null) {
                if (texto.length() > 0) texto.append(' ');
                texto.append("No pude completar «").append(paso.accion).append("»");
                if (salida != null && salida.texto != null && !salida.texto.isEmpty()) {
                    texto.append(": ").append(salida.texto);
                }
                texto.append("; los pasos anteriores ya no se revierten.");
                return new Resultado(texto.toString(), false, "falló " + paso.accion);
            }
            if (texto.length() > 0) texto.append(' ');
            texto.append(salida.texto);
        }
        return new Resultado(texto.toString(), true, "");
    }

    private boolean confirmar(PlanNeural.Plan plan) {
        CountDownLatch decision = new CountDownLatch(1);
        boolean[] aceptado = {false};
        AlertDialog[] dialogo = new AlertDialog[1];
        actividad.runOnUiThread(() -> {
            if (actividad.isFinishing() || actividad.isDestroyed()) {
                decision.countDown();
                return;
            }
            try {
                dialogo[0] = new AlertDialog.Builder(actividad)
                        .setTitle("¿Ejecutar este plan?")
                        .setMessage(plan.resumen() + "\n\nSólo se ejecutarán estas acciones. "
                                + "La confirmación caduca en 120 segundos y sirve una vez.")
                        .setPositiveButton("Ejecutar", (d, cual) -> {
                            aceptado[0] = true;
                            decision.countDown();
                        })
                        .setNegativeButton("Cancelar", (d, cual) -> decision.countDown())
                        .setOnCancelListener(d -> decision.countDown())
                        .show();
            } catch (RuntimeException noSePuedeMostrar) {
                decision.countDown();
            }
        });
        try {
            boolean aTiempo = decision.await(120, TimeUnit.SECONDS);
            actividad.runOnUiThread(() -> {
                if (dialogo[0] != null && dialogo[0].isShowing()) dialogo[0].dismiss();
            });
            return aTiempo && aceptado[0];
        } catch (InterruptedException pausa) {
            Thread.currentThread().interrupt();
            return false;
        }
    }

    String ejecutarPaso(Cerebro.Resultado paso) {
        Acciones.Resultado salida = enLaInterfaz(paso);
        return salida == null ? null : salida.texto;
    }

    Acciones.Resultado ejecutarPasoTipado(Cerebro.Resultado paso) {
        return enLaInterfaz(paso);
    }

    private Acciones.Resultado enLaInterfaz(Cerebro.Resultado paso) {
        Acciones.Resultado[] salida = {null};
        CountDownLatch listo = new CountDownLatch(1);
        AtomicBoolean valido = new AtomicBoolean(true);
        actividad.runOnUiThread(() -> {
            if (!valido.get() || actividad.isFinishing() || actividad.isDestroyed()) {
                listo.countDown();
                return;
            }
            try {
                salida[0] = acciones.ejecutarTipado(paso);
            } catch (RuntimeException fallo) {
                salida[0] = null;
            } finally {
                listo.countDown();
            }
        });
        try {
            if (!listo.await(15, TimeUnit.SECONDS)) valido.set(false);
            return valido.get() ? salida[0] : null;
        } catch (InterruptedException pausa) {
            valido.set(false);
            Thread.currentThread().interrupt();
            return null;
        }
    }
}
