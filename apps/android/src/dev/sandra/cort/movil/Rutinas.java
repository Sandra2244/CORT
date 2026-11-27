package dev.sandra.cort.movil;

import android.content.ContentValues;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

final class Rutinas {
    interface Ejecutor {
        String ejecutar(Cerebro.Resultado paso);

        default Acciones.Resultado ejecutarConEstado(Cerebro.Resultado paso) {
            String salida = ejecutar(paso);
            return salida == null ? Acciones.Resultado.fallo("la acción no devolvió resultado")
                    : Acciones.Resultado.exito(salida);
        }

        default void iniciada(String ejecucionId, String rutinaId) {
        }
    }

    static final class Paso {
        final String accion;
        final String param;
        final String resto;
        final String plantilla;
        final String riesgo;
        final String permiso;
        final boolean requiereConfirmacion;
        final String autor;
        final String fuente;
        final String licencia;

        Paso(String accion, String param, String resto, String plantilla, String riesgo,
             String permiso, boolean requiereConfirmacion, String autor, String fuente,
             String licencia) {
            this.accion = accion;
            this.param = param;
            this.resto = resto;
            this.plantilla = plantilla;
            this.riesgo = riesgo;
            this.permiso = permiso;
            this.requiereConfirmacion = requiereConfirmacion;
            this.autor = autor;
            this.fuente = fuente;
            this.licencia = licencia;
        }

        static boolean informativa(String accion) {
            return "hora".equals(accion) || "fecha".equals(accion)
                    || "listar".equals(accion) || "decir".equals(accion);
        }

        static String riesgoCalculado(String accion) {
            return informativa(accion) ? "bajo" : ("linterna".equals(accion) ? "medio" : "reversible");
        }

        static String permisoCalculado(String accion) {
            return "linterna".equals(accion) ? "CAMERA"
                    : ("volumen".equals(accion) ? "MODIFY_AUDIO_SETTINGS" : "ninguno");
        }

        static Paso desde(JSONObject json) throws JSONException {
            String accion = json.optString("accion", "").trim();
            String param = json.optString("param", "").trim();
            String resto = json.optString("resto", json.optString("texto", "")).trim();
            String plantilla = json.optString("plantilla", "").trim();
            String autor = json.optString("autor", "").trim();
            String fuente = json.optString("fuente", "").trim();
            String licencia = json.optString("licencia", "").trim();
            boolean informativa = informativa(accion);
            String riesgo = riesgoCalculado(accion);
            String permiso = permisoCalculado(accion);
            if (autor.isEmpty()) autor = "decir".equals(accion) ? "autor no indicado" : "CORT";
            if (fuente.isEmpty()) fuente = "decir".equals(accion) ? "texto de la persona" : "proyecto CORT";
            if (licencia.isEmpty()) licencia = "decir".equals(accion) ? "derechos por revisar" : "licencia del proyecto";
            return new Paso(accion, param, resto, plantilla, riesgo, permiso,
                    !informativa, autor, fuente, licencia);
        }

        String error() {
            if (accion.length() > 40 || param.length() > 80 || resto.length() > 500
                    || plantilla.length() > 500) return "un paso supera el límite de texto";
            switch (accion) {
                case "hora":
                case "fecha":
                case "listar":
                    return param.isEmpty() && resto.isEmpty() ? null : "este paso no admite parámetros";
                case "decir":
                    if (resto.isEmpty()) return "falta la frase";
                    return null;
                case "abrir":
                    if (!destinoValido(param) || !resto.isEmpty()) return "destino de apertura no permitido";
                    return null;
                case "volumen":
                    if (!direccionValida(param) || !resto.isEmpty()) return "acción de volumen no permitida";
                    return null;
                case "linterna":
                    if (!("encender".equals(param) || "apagar".equals(param)) || !resto.isEmpty()) {
                        return "la linterna sólo admite encender o apagar";
                    }
                    return null;
                case "alarma":
                    EspecificacionAlarma alarma = EspecificacionAlarma.parsear(resto);
                    return alarma.valida && EspecificacionAlarma.ALARMA.equals(alarma.tipo)
                            ? null : "la alarma no es válida";
                case "cronometro":
                    EspecificacionAlarma timer = EspecificacionAlarma.parsear("temporizador " + resto);
                    return timer.valida && EspecificacionAlarma.TEMPORIZADOR.equals(timer.tipo)
                            ? null : "el temporizador no es válido";
                default:
                    return "acción no allowlisted: " + accion;
            }
        }

        JSONObject json() throws JSONException {
            return new JSONObject().put("accion", accion).put("param", param).put("resto", resto)
                    .put("plantilla", plantilla).put("riesgo", riesgo).put("permiso", permiso)
                    .put("requiere_confirmacion", requiereConfirmacion).put("autor", autor)
                    .put("fuente", fuente).put("licencia", licencia);
        }

        Cerebro.Resultado resultado() {
            String plantilla = this.plantilla;
            if ("hora".equals(accion)) plantilla = "Son las {hora}.";
            else if ("fecha".equals(accion)) plantilla = "Hoy es {fecha}.";
            else if ("listar".equals(accion)) plantilla = "Sé esto: {lista}.";
            else if ("decir".equals(accion)) plantilla = resto;
            return new Cerebro.Resultado("rutina", accion, param, plantilla, resto);
        }

        private static boolean destinoValido(String valor) {
            for (String permitido : new String[] {"ajustes", "teclado", "wifi", "bluetooth",
                    "navegador", "reloj", "musica", "mensajeria"}) {
                if (permitido.equals(valor)) return true;
            }
            return false;
        }

        private static boolean direccionValida(String valor) {
            return "subir".equals(valor) || "bajar".equals(valor) || "silencio".equals(valor)
                    || "maximo".equals(valor);
        }
    }

    static final class Reto {
        final String rutinaId;
        final int version;
        final String token;
        final long expira;

        Reto(String rutinaId, int version, String token, long expira) {
            this.rutinaId = rutinaId;
            this.version = version;
            this.token = token;
            this.expira = expira;
        }
    }

    private final Recuerdos recuerdos;
    private final Map<String, Reto> retos = new HashMap<>();
    private final Set<String> cancelaciones = ConcurrentHashMap.newKeySet();

    Rutinas(Recuerdos recuerdos) {
        this.recuerdos = recuerdos;
    }

    JSONObject crear(String nombre, JSONArray datos) throws JSONException {
        if (nombre == null || nombre.trim().isEmpty() || nombre.trim().length() > 60) {
            return error("rutina_creada", "el nombre debe tener entre 1 y 60 caracteres");
        }
        if (datos == null || datos.length() == 0 || datos.length() > 12) {
            return error("rutina_creada", "una rutina debe tener entre 1 y 12 pasos");
        }
        List<Paso> pasos = new ArrayList<>();
        for (int i = 0; i < datos.length(); i++) {
            try {
                Paso paso = Paso.desde(datos.getJSONObject(i));
                String problema = paso.error();
                if (problema != null) return error("rutina_creada", "paso " + (i + 1) + ": " + problema);
                pasos.add(paso);
            } catch (JSONException roto) {
                return error("rutina_creada", "paso " + (i + 1) + ": JSON inválido");
            }
        }
        String id = UUID.randomUUID().toString();
        long ahora = System.currentTimeMillis();
        ContentValues fila = new ContentValues();
        fila.put("id", id);
        fila.put("nombre", nombre.trim());
        fila.put("pasos", pasosJson(pasos).toString());
        fila.put("version", 1);
        fila.put("creado_en", ahora);
        fila.put("actualizado_en", ahora);
        long insertada = recuerdos.getWritableDatabase().insert("rutinas", null, fila);
        if (insertada < 1) return error("rutina_creada", "no pude guardar la rutina");
        return new JSONObject().put("type", "rutina_creada").put("origen", "real")
                .put("ok", true).put("id", id).put("nombre", nombre.trim());
    }

    JSONObject listar() throws JSONException {
        JSONArray lista = new JSONArray();
        Set<String> activas = new HashSet<>();
        Cursor ejecutando = recuerdos.getReadableDatabase().rawQuery(
                "SELECT DISTINCT rutina_id FROM rutinas_ejecuciones WHERE estado='EJECUTANDO'", null);
        try {
            while (ejecutando.moveToNext()) activas.add(ejecutando.getString(0));
        } finally {
            ejecutando.close();
        }
        Cursor c = recuerdos.getReadableDatabase().query("rutinas",
                new String[] {"id", "nombre", "pasos", "version", "creado_en", "actualizado_en"},
                null, null, null, null, "actualizado_en DESC", "100");
        try {
            while (c.moveToNext()) {
                lista.put(new JSONObject().put("id", c.getString(0)).put("nombre", c.getString(1))
                        .put("pasos", new JSONArray(c.getString(2))).put("version", c.getInt(3))
                        .put("creado_en", c.getLong(4)).put("actualizado_en", c.getLong(5))
                        .put("en_ejecucion", activas.contains(c.getString(0))));
            }
        } finally {
            c.close();
        }
        return new JSONObject().put("type", "rutinas_estado").put("origen", "real")
                .put("rutinas", lista);
    }

    synchronized JSONObject plan(String id) throws JSONException {
        Cursor c = recuerdos.getReadableDatabase().query("rutinas",
                new String[] {"nombre", "pasos", "version"}, "id=?", new String[] {id},
                null, null, null, "1");
        String nombre;
        String datos;
        int version;
        if (c.moveToFirst()) {
            nombre = c.getString(0);
            datos = c.getString(1);
            version = c.getInt(2);
        } else {
            c.close();
            return error("rutina_plan", "la rutina no existe");
        }
        c.close();
        JSONArray original = new JSONArray(datos);
        JSONArray pasos = new JSONArray();
        boolean sensible = false;
        for (int i = 0; i < original.length(); i++) {
            JSONObject paso = original.getJSONObject(i);
            sensible |= paso.optBoolean("requiere_confirmacion", false);
            pasos.put(paso);
        }
        String token = UUID.randomUUID().toString();
        retos.put(id, new Reto(id, version, token, System.currentTimeMillis() + 120_000L));
        return new JSONObject().put("type", "rutina_plan").put("origen", "real")
                .put("ok", true).put("id", id).put("nombre", nombre).put("version", version)
                .put("pasos", pasos).put("requiere_confirmacion", sensible)
                .put("token", token).put("expira_en", 120);
    }

    static boolean retoCoincide(Reto reto, String id, String token) {
        return reto != null && reto.rutinaId.equals(id) && reto.token.equals(token);
    }

    synchronized boolean cancelarPlan(String id, String token) {
        Reto reto = retos.get(id);
        if (!retoCoincide(reto, id, token)) return false;
        retos.remove(id);
        return true;
    }

    synchronized JSONObject ejecutar(String id, String token, Ejecutor ejecutor) throws JSONException {
        Cursor c = recuerdos.getReadableDatabase().query("rutinas",
                new String[] {"nombre", "pasos", "version"}, "id=?", new String[] {id},
                null, null, null, "1");
        if (!c.moveToFirst()) {
            c.close();
            return error("rutina_resultado", "la rutina no existe");
        }
        String nombre = c.getString(0);
        JSONArray datos = new JSONArray(c.getString(1));
        int version = c.getInt(2);
        c.close();
        List<Paso> pasos = new ArrayList<>();
        for (int i = 0; i < datos.length(); i++) {
            Paso paso = Paso.desde(datos.getJSONObject(i));
            String problema = paso.error();
            if (problema != null) return error("rutina_resultado", "paso " + (i + 1) + ": " + problema);
            pasos.add(paso);
        }
        Reto reto = retos.remove(id);
        if (!retoCoincide(reto, id, token) || reto.version != version
                || reto.expira < System.currentTimeMillis()) {
            return error("rutina_resultado", "la confirmación caducó; vuelve a planificar la rutina");
        }
        String ejecucionId = UUID.randomUUID().toString();
        long inicio = System.currentTimeMillis();
        ContentValues fila = new ContentValues();
        fila.put("id", ejecucionId);
        fila.put("rutina_id", id);
        fila.put("version", version);
        fila.put("inicio", inicio);
        fila.put("fin", (Long) null);
        fila.put("estado", "EJECUTANDO");
        fila.put("detalle", nombre);
        if (recuerdos.getWritableDatabase().insert("rutinas_ejecuciones", null, fila) < 1) {
            return error("rutina_resultado", "no pude registrar el inicio de la ejecución");
        }
        cancelaciones.remove(ejecucionId);
        try {
            ejecutor.iniciada(ejecucionId, id);
        } catch (RuntimeException avisoCaido) {
            // La ejecución ya está registrada; un aviso perdido no debe dejarla a medias.
        }
        JSONArray resultados = new JSONArray();
        int completados = 0;
        boolean auditoriaOk = true;
        String estado = "COMPLETADA";
        String detalle = "todos los pasos terminaron";
        for (int i = 0; i < pasos.size(); i++) {
            if (cancelaciones.contains(ejecucionId)) {
                estado = "CANCELADA";
                detalle = "cancelada por la persona";
                break;
            }
            Paso paso = pasos.get(i);
            String salida = null;
            String resultadoEstado = "FALLO";
            try {
                Acciones.Resultado resultado = ejecutor.ejecutarConEstado(paso.resultado());
                if (resultado != null) salida = resultado.texto;
                if (resultado != null && resultado.ok && salida != null) {
                    resultadoEstado = "COMPLETADO";
                    completados++;
                }
            } catch (RuntimeException fallo) {
                salida = "fallo local: " + fallo.getClass().getSimpleName();
            }
            if (salida == null) salida = "la acción no devolvió resultado";
            resultados.put(new JSONObject().put("orden", i + 1).put("accion", paso.accion)
                    .put("estado", resultadoEstado).put("detalle", salida));
            if (!registrarResultado(ejecucionId, i + 1, paso.accion, resultadoEstado, salida)) {
                auditoriaOk = false;
                estado = completados > 0 ? "PARCIAL" : "FALLO";
                detalle = "se detuvo al auditar el paso " + (i + 1);
                break;
            }
            if (!"COMPLETADO".equals(resultadoEstado)) {
                estado = completados > 0 ? "PARCIAL" : "FALLO";
                detalle = "se detuvo en el paso " + (i + 1);
                break;
            }
        }
        if (cancelaciones.contains(ejecucionId) && "COMPLETADA".equals(estado)) {
            estado = "CANCELADA";
            detalle = "cancelada por la persona";
        }
        long fin = System.currentTimeMillis();
        ContentValues cierre = new ContentValues();
        cierre.put("fin", fin);
        cierre.put("estado", estado);
        cierre.put("detalle", detalle);
        try {
            if (recuerdos.getWritableDatabase().update("rutinas_ejecuciones", cierre, "id=?",
                    new String[] {ejecucionId}) != 1) auditoriaOk = false;
        } catch (RuntimeException fallo) {
            auditoriaOk = false;
        }
        if (!auditoriaOk && "todos los pasos terminaron".equals(detalle)) {
            detalle = "los pasos terminaron, pero no pude cerrar su registro de auditoría";
        }
        cancelaciones.remove(ejecucionId);
        return new JSONObject().put("type", "rutina_resultado").put("origen", "real")
                .put("ok", !"FALLO".equals(estado) && auditoriaOk).put("id", id).put("nombre", nombre)
                .put("ejecucion_id", ejecucionId).put("estado", estado).put("detalle", detalle)
                .put("auditoria_ok", auditoriaOk).put("resultados", resultados);
    }

    boolean cancelar(String ejecucionId) {
        if (ejecucionId == null || ejecucionId.isEmpty()) return false;
        Cursor c = recuerdos.getReadableDatabase().query("rutinas_ejecuciones",
                new String[] {"estado"}, "id=?", new String[] {ejecucionId}, null, null, null, "1");
        String estado = c.moveToFirst() ? c.getString(0) : "";
        c.close();
        if (!"EJECUTANDO".equals(estado)) return false;
        cancelaciones.add(ejecucionId);
        return true;
    }

    void cancelarTodas() {
        Cursor c = recuerdos.getReadableDatabase().query("rutinas_ejecuciones",
                new String[] {"id"}, "estado=?", new String[] {"EJECUTANDO"},
                null, null, null, "100");
        try {
            while (c.moveToNext()) cancelaciones.add(c.getString(0));
        } finally {
            c.close();
        }
    }

    JSONObject historial() throws JSONException {
        JSONArray lista = new JSONArray();
        Cursor c = recuerdos.getReadableDatabase().query("rutinas_ejecuciones",
                new String[] {"id", "rutina_id", "version", "inicio", "fin", "estado", "detalle"},
                null, null, null, null, "inicio DESC", "50");
        try {
            while (c.moveToNext()) {
                lista.put(new JSONObject().put("id", c.getString(0)).put("rutina_id", c.getString(1))
                        .put("version", c.getInt(2)).put("inicio", c.getLong(3))
                        .put("fin", c.isNull(4) ? JSONObject.NULL : c.getLong(4))
                        .put("estado", c.getString(5)).put("detalle", c.getString(6)));
            }
        } finally {
            c.close();
        }
        return new JSONObject().put("type", "rutinas_historial").put("origen", "real")
                .put("ejecuciones", lista);
    }

    private boolean registrarResultado(String ejecucionId, int orden, String accion,
                                       String estado, String detalle) {
        ContentValues fila = new ContentValues();
        fila.put("ejecucion_id", ejecucionId);
        fila.put("orden", orden);
        fila.put("accion", accion);
        fila.put("estado", estado);
        fila.put("detalle", detalle.substring(0, Math.min(1000, detalle.length())));
        fila.put("cuando", System.currentTimeMillis());
        try {
            return recuerdos.getWritableDatabase().insert("rutinas_resultados", null, fila) >= 0;
        } catch (RuntimeException fallo) {
            return false;
        }
    }

    private static JSONArray pasosJson(List<Paso> pasos) {
        JSONArray salida = new JSONArray();
        for (Paso paso : pasos) {
            try {
                salida.put(paso.json());
            } catch (JSONException imposible) {
                throw new IllegalStateException(imposible);
            }
        }
        return salida;
    }

    private static JSONObject error(String tipo, String motivo) throws JSONException {
        return new JSONObject().put("type", tipo).put("origen", "real")
                .put("ok", false).put("motivo", motivo);
    }
}
