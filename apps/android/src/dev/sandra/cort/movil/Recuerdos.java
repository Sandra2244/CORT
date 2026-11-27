package dev.sandra.cort.movil;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.TimeZone;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/**
 * La memoria de CORT **dentro del teléfono**: una tabla en SQLite, el motor que
 * Android ya trae, sin dependencias que el pipeline tenga que descargar.
 *
 * Hasta `v0.14.4` los datos de la dueña vivían en `memory.db` del portátil, así
 * que un móvil sin portátil no tenía memoria. Desde este corte la memoria es
 * local al aparato y el portátil, si aparece, es un añadido: la misma frase
 * «recuerda que …» se guarda en los dos sitios y ninguno de los dos es
 * obligatorio.
 *
 * La escritura sólo pasa por aquí, y `guardar()` **no** evalúa nada: recibe una
 * clave y un valor de texto. Regla 6 de `AGENTS.md` — nada de comandos
 * arbitrarios — se respeta igual que en el core de Python.
 */
public class Recuerdos extends SQLiteOpenHelper implements Puente.Cabeza {
    private static final String NOMBRE = "cort.db";
    private static final int VERSION = 3;
    static final int ESPERA_NUEVA = -2;
    static final int ESPERA_AUSENTE = -3;

    /**
     * Cuántos turnos se guardan. La conversación continua (F20d) no puede crecer sin
     * techo: cada turno es una fila y el modelo sólo lee los últimos `Consticion.turnos`.
     * Doscientos son unas cuantas semanas de uso y caben de sobra en el carbajo.
     */
    private static final int MAX_TURNOS = 200;

    public Recuerdos(Context contexto) {
        super(contexto.getApplicationContext(), NOMBRE, null, VERSION);
    }

    @Override
    public void onCreate(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE IF NOT EXISTS hechos ("
                + "clave TEXT PRIMARY KEY,"
                + "valor TEXT NOT NULL,"
                + "cuando INTEGER NOT NULL,"
                + "origen TEXT NOT NULL DEFAULT 'legacy',"
                + "confirmado INTEGER NOT NULL DEFAULT 0,"
                + "creado_en INTEGER NOT NULL DEFAULT 0,"
                + "actualizado_en INTEGER NOT NULL DEFAULT 0,"
                + "eliminado_en INTEGER,"
                + "version INTEGER NOT NULL DEFAULT 1)");
        db.execSQL("CREATE TABLE IF NOT EXISTS hechos_historial ("
                + "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                + "hecho_id TEXT NOT NULL,"
                + "valor_anterior TEXT,"
                + "valor_nuevo TEXT,"
                + "origen TEXT NOT NULL,"
                + "aprobacion_id TEXT NOT NULL DEFAULT '',"
                + "cuando INTEGER NOT NULL)");
        db.execSQL("CREATE INDEX IF NOT EXISTS hechos_historial_id "
                + "ON hechos_historial(hecho_id, id DESC)");
        db.execSQL("CREATE TABLE IF NOT EXISTS habilidades ("
                + "patron TEXT PRIMARY KEY,"
                + "accion TEXT NOT NULL,"
                + "param TEXT,"
                + "respuesta TEXT,"
                + "veces INTEGER NOT NULL DEFAULT 1)");
        db.execSQL("CREATE TABLE IF NOT EXISTS turnos ("
                + "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                + "rol TEXT NOT NULL,"
                + "texto TEXT NOT NULL,"
                + "cuando INTEGER NOT NULL)");
        db.execSQL("CREATE TABLE IF NOT EXISTS alarmas_entregadas ("
                + "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                + "texto TEXT NOT NULL, tipo TEXT NOT NULL, hora INTEGER NOT NULL,"
                + "minuto INTEGER NOT NULL, dias INTEGER NOT NULL, segundos INTEGER NOT NULL,"
                + "etiqueta TEXT NOT NULL, estado TEXT NOT NULL, origen TEXT NOT NULL,"
                + "aprobacion_id TEXT NOT NULL DEFAULT '', creado_en INTEGER NOT NULL)");
        db.execSQL("CREATE TABLE IF NOT EXISTS rutinas ("
                + "id TEXT PRIMARY KEY, nombre TEXT NOT NULL, pasos TEXT NOT NULL,"
                + "version INTEGER NOT NULL, creado_en INTEGER NOT NULL, actualizado_en INTEGER NOT NULL)");
        db.execSQL("CREATE TABLE IF NOT EXISTS rutinas_ejecuciones ("
                + "id TEXT PRIMARY KEY, rutina_id TEXT NOT NULL, version INTEGER NOT NULL,"
                + "inicio INTEGER NOT NULL, fin INTEGER, estado TEXT NOT NULL, detalle TEXT NOT NULL)");
        db.execSQL("CREATE TABLE IF NOT EXISTS rutinas_resultados ("
                + "id INTEGER PRIMARY KEY AUTOINCREMENT, ejecucion_id TEXT NOT NULL,"
                + "orden INTEGER NOT NULL, accion TEXT NOT NULL, estado TEXT NOT NULL,"
                + "detalle TEXT NOT NULL, cuando INTEGER NOT NULL)");
        db.execSQL("CREATE INDEX IF NOT EXISTS rutinas_resultados_ejecucion "
                + "ON rutinas_resultados(ejecucion_id, orden)");
    }

    @Override
    public void onUpgrade(SQLiteDatabase db, int desde, int hasta) {
        // `IF NOT EXISTS` en las tres: la versión 1 ya tenía `hechos` y `habilidades`
        // con la memoria de la dueña dentro, y un `CREATE TABLE` a secas reventaba
        // con «table hechos already exists» en cuanto se subía el número. Aquí se
        // añade lo que falta y no se borra nada: esta base es su memoria, no una caché.
        onCreate(db);
        if (desde < 3) {
            agregarColumna(db, "origen", "TEXT NOT NULL DEFAULT 'legacy'");
            agregarColumna(db, "confirmado", "INTEGER NOT NULL DEFAULT 0");
            agregarColumna(db, "creado_en", "INTEGER NOT NULL DEFAULT 0");
            agregarColumna(db, "actualizado_en", "INTEGER NOT NULL DEFAULT 0");
            agregarColumna(db, "eliminado_en", "INTEGER");
            agregarColumna(db, "version", "INTEGER NOT NULL DEFAULT 1");
            db.execSQL("UPDATE hechos SET origen='legacy', confirmado=0, "
                    + "creado_en=CASE WHEN creado_en=0 THEN cuando ELSE creado_en END, "
                    + "actualizado_en=CASE WHEN actualizado_en=0 THEN cuando ELSE actualizado_en END "
                    + "WHERE origen='legacy' AND version=1");
        }
    }

    private static void agregarColumna(SQLiteDatabase db, String nombre, String definicion) {
        Cursor columnas = db.rawQuery("PRAGMA table_info(hechos)", null);
        boolean existe = false;
        try {
            while (columnas.moveToNext()) {
                if (nombre.equals(columnas.getString(1))) {
                    existe = true;
                    break;
                }
            }
        } finally {
            columnas.close();
        }
        if (!existe) db.execSQL("ALTER TABLE hechos ADD COLUMN " + nombre + " " + definicion);
    }

    /* ---------------------------------------------------------- la conversación */

    /**
     * Un turno dicho, de ella (`user`) o de CORT (`assistant`). Se guarda **después**
     * de contestar, no antes: si la vuelta falla no queda un «user» huérfano que el
     * modelo leería como una pregunta sin responder.
     */
    public void apuntaTurno(String rol, String texto) {
        if (texto == null || texto.trim().isEmpty()) {
            return;
        }
        ContentValues fila = new ContentValues();
        fila.put("rol", "assistant".equals(rol) ? "assistant" : "user");
        fila.put("texto", texto.trim());
        fila.put("cuando", System.currentTimeMillis());
        getWritableDatabase().insert("turnos", null, fila);
        // La poda va en la misma escritura: sin ella, un año de uso deja miles de
        // filas que nadie lee y que hacen lento cada `SELECT`.
        getWritableDatabase().execSQL("DELETE FROM turnos WHERE id NOT IN "
                + "(SELECT id FROM turnos ORDER BY id DESC LIMIT " + MAX_TURNOS + ")");
    }

    /** Los últimos turnos, de viejos a nuevos: la forma que espera `CerebroLocal.preguntar`. */
    public List<String[]> turnos(int maximo) {
        List<String[]> salida = new ArrayList<>();
        Cursor c = getReadableDatabase().query("turnos", new String[] {"rol", "texto"},
                null, null, null, null, "id DESC", String.valueOf(Math.max(1, maximo)));
        try {
            while (c.moveToNext()) {
                salida.add(0, new String[] {c.getString(0), c.getString(1)});
            }
        } finally {
            c.close();
        }
        return salida;
    }

    public int cuentasDeTurnos() {
        Cursor c = getReadableDatabase().rawQuery("SELECT COUNT(*) FROM turnos", null);
        try {
            return c.moveToFirst() ? c.getInt(0) : 0;
        } finally {
            c.close();
        }
    }

    /** «olvida la conversación»: borra los turnos y deja los hechos y las habilidades. */
    public void olvidaTurnos() {
        getWritableDatabase().delete("turnos", null, null);
    }

    /* ---------------------------------------------------------------- hechos */

    public void guarda(String clave, String valor) {
        guardarConfirmado(clave, valor, "usuario", "", true);
    }

    public boolean guardarConfirmado(String clave, String valor, String origen,
                                     String aprobacionId, boolean confirmado) {
        return guardarConfirmado(clave, valor, origen, aprobacionId, confirmado, -1, true);
    }

    public boolean guardarConfirmado(String clave, String valor, String origen,
                                     String aprobacionId, boolean confirmado,
                                     int versionEsperada) {
        return guardarConfirmado(clave, valor, origen, aprobacionId, confirmado,
                versionEsperada, true);
    }

    private boolean guardarConfirmado(String clave, String valor, String origen,
                                      String aprobacionId, boolean confirmado,
                                      int versionEsperada, boolean permitirCrear) {
        String motivo = validarDato(clave, valor);
        if (motivo != null) return false;
        SQLiteDatabase db = getWritableDatabase();
        long ahora = System.currentTimeMillis();
        db.beginTransaction();
        try {
            Cursor anterior = db.query("hechos", new String[] {"valor", "version", "creado_en",
                            "eliminado_en"},
                    "clave=?", new String[] {clave}, null, null, null, "1");
            String valorAnterior = null;
            long creadoEn = 0L;
            int version = 1;
            boolean existe = false;
            boolean activo = false;
            try {
                if (anterior.moveToFirst()) {
                    existe = true;
                    activo = anterior.isNull(3);
                    valorAnterior = anterior.getString(0);
                    version = anterior.getInt(1) + 1;
                    creadoEn = anterior.getLong(2);
                }
            } finally {
                anterior.close();
            }
            if (!permitirCrear && !activo) return false;
            if (versionEsperada == ESPERA_NUEVA && activo) return false;
            if (versionEsperada == ESPERA_AUSENTE && existe) return false;
            if (versionEsperada >= 0 && (!activo || version - 1 != versionEsperada)) return false;
            ContentValues fila = new ContentValues();
            fila.put("clave", clave.trim());
            fila.put("valor", valor.trim());
            fila.put("cuando", ahora);
            fila.put("origen", origenLimpio(origen));
            fila.put("confirmado", confirmado ? 1 : 0);
            fila.put("creado_en", valorAnterior == null ? ahora : creadoEn);
            fila.put("actualizado_en", ahora);
            fila.put("eliminado_en", (String) null);
            fila.put("version", version);
            if (db.insertWithOnConflict("hechos", null, fila,
                    SQLiteDatabase.CONFLICT_REPLACE) < 0) return false;
            if (!existe) {
                ContentValues creado = new ContentValues();
                creado.put("hecho_id", clave.trim());
                creado.put("valor_anterior", (String) null);
                creado.put("valor_nuevo", valor.trim());
                creado.put("origen", origenLimpio(origen));
                creado.put("aprobacion_id", aprobacionId == null ? "" : aprobacionId);
                creado.put("cuando", ahora);
                if (db.insert("hechos_historial", null, creado) < 0) return false;
            } else if (!valorAnterior.equals(valor.trim())) {
                if (!anotarHistorial(db, clave, valorAnterior, valor.trim(), origen,
                        aprobacionId, ahora)) return false;
            }
            db.setTransactionSuccessful();
            return true;
        } finally {
            db.endTransaction();
        }
    }

    private boolean guardarImportado(String clave, String valor) {
        return guardarConfirmado(clave, valor, "pc_importado", "", false, ESPERA_AUSENTE);
    }

    public String valor(String clave) {
        Cursor c = getReadableDatabase().query("hechos", new String[] {"valor"},
                "clave=? AND eliminado_en IS NULL", new String[] {clave}, null, null, null, "1");
        try {
            if (c.moveToFirst()) {
                return c.getString(0);
            }
            return null;
        } finally {
            c.close();
        }
    }

    /** Las primeras claves que caben en una frase dicha en voz alta. */
    public String lista(int maximo) {
        List<String> leidos = new ArrayList<>();
        Cursor c = getReadableDatabase().query("hechos", new String[] {"clave", "valor"},
                "eliminado_en IS NULL", null, null, null, "cuando DESC",
                String.valueOf(Math.max(1, maximo)));
        try {
            while (c.moveToNext()) {
                leidos.add(c.getString(0) + ": " + c.getString(1));
            }
        } finally {
            c.close();
        }
        return leidos.isEmpty() ? "nada todavía" : String.join(", ", leidos);
    }

    /**
     * «recuerda que mi nombre es Sandra» → clave `nombre`, valor `Sandra`.
     *
     * La regla que aprendió el core de Python y se porta aquí tal cual: sólo se
     * guarda lo que tiene la forma `X es Y`, y «uso el cronómetro» no la tiene —
     * si se guardara, la memoria se llenaría de frases sueltas que luego CORT
     * suelta sin sentido.
     */
    public static String[] parte(String resto) {
        String limpio = resto.trim();
        if (limpio.isEmpty()) {
            return null;
        }
        int[] copula = copula(limpio);
        if (copula == null) {
            // «me llamo Sandra» / «tengo 30 años»: la clave es las dos primeras
            // palabras y el valor el resto, que es lo que luego se pregunta.
            String[] palabras = limpio.split("\\s+");
            if (palabras.length < 2) {
                return new String[] {limpio, limpio};
            }
            return new String[] {palabras[0],
                    limpio.substring(limpio.indexOf(palabras[0]) + palabras[0].length()).trim()};
        }
        String clave = limpio.substring(0, copula[0]).trim();
        String valor = limpio.substring(copula[0] + copula[1]).trim();
        for (String articulo : new String[] {"mi ", "el ", "la ", "los ", "las "}) {
            if (clave.startsWith(articulo)) {
                clave = clave.substring(articulo.length());
                break;
            }
        }
        if (clave.isEmpty() || valor.isEmpty()) {
            return null;
        }
        return new String[] {clave, valor};
    }

    /**
     * {índice, longitud} de la cópula, o `null` si no la hay. La longitud se
     * devuelve y no se fija en 3: « es » mide 4 caracteres y « son » 5, y con el
     * número fijo «mis gestos son uno y dos» se guardaba como
     * clave `mis gestos`, valor `n uno y dos`. Medido leyendo el código, no en el
     * teléfono — por eso la prueba de este archivo está en `parte` y no en SQLite—.
     */
    private static int[] copula(String texto) {
        int es = texto.indexOf(" es ");
        int son = texto.indexOf(" son ");
        if (es >= 0 && (son < 0 || es <= son)) {
            return new int[] {es, 4};
        }
        return son >= 0 ? new int[] {son, 5} : null;
    }

    /** Guarda lo que la dueña dijo y devuelve la frase con la que CORT lo confirma. */
    public String guardarFrase(String resto) {
        String[] par = parte(resto);
        if (par == null) {
            return "No supe qué anotar de eso. Prueba con «recuerda que mi clave es valor».";
        }
        if (!guardarConfirmado(par[0], par[1], "voz_o_chat", "", true)) {
            return "No guardé ese dato: usa una clave normal y no guardes contraseñas ni credenciales.";
        }
        return "Anotado: " + par[0] + " es " + par[1] + ". Se queda en este teléfono.";
    }

    /** Búsqueda por clave exacta y, si no, por la clave que contenga la pregunta. */
    public String buscar(String pregunta) {
        String limpio = pregunta.trim();
        String directa = valor(limpio);
        if (directa != null) {
            return limpia(limpio) + ": " + directa;
        }
        Cursor c = getReadableDatabase().query("hechos", new String[] {"clave", "valor"},
                "clave LIKE ? AND eliminado_en IS NULL", new String[] {"%" + limpio + "%"},
                null, null, null, "3");
        try {
            List<String> found = new ArrayList<>();
            while (c.moveToNext()) {
                found.add(c.getString(0) + ": " + c.getString(1));
            }
            if (!found.isEmpty()) {
                return String.join(", ", found);
            }
        } finally {
            c.close();
        }
        return null;
    }

    /** «quién soy» responde por el nombre, y si no lo hay lo dice sin inventar. */
    public String quienSoy() {
        for (String clave : new String[] {"nombre", "me llamo", "soy"}) {
            String v = valor(clave);
            if (v != null) {
                return "Eres " + v + ".";
            }
        }
        return "No me has dicho tu nombre. Dime «recuerda que te llamas …» y lo guardo aquí.";
    }

    /** Los datos del aparato, la primera vez, sin que nadie los teclee. */
    public void sembrarDispositivo(String clave, String valorPropuesto) {
        if (valor(clave) == null) {
            guardarConfirmado(clave, valorPropuesto, "sistema", "", false);
        }
    }

    /* ------------------------------------------------------------- el puente */

    /**
     * Las filas que `Puente.exportar` sube al portátil, en la forma del teléfono:
     * `clave: valor`. El `cuando` sale en ISO-8601 UTC porque es lo que viaja en el
     * cuadro del portátil (`memory.db` guarda el `created_at` así) y un número de
     * milisegundos en el JSON de la otra cabeza sería una segunda verdad del tiempo.
     *
     * El orden es el de `lista()`: lo más nuevo primero. Si un viaje corta por
     * `MAX_FILAS`, lo que se queda fuera es lo más viejo, no un recorte al azar.
     */
    @Override
    public List<String[]> filas(int maximo) {
        List<String[]> salida = new ArrayList<>();
        Cursor c = getReadableDatabase().query("hechos",
                new String[] {"clave", "valor", "cuando"},
                "eliminado_en IS NULL", null, null, null, "cuando DESC",
                String.valueOf(Math.max(1, maximo)));
        try {
            while (c.moveToNext()) {
                salida.add(new String[] {Puente.contenidoDe(c.getString(0), c.getString(1)),
                        iso(c.getLong(2))});
            }
        } finally {
            c.close();
        }
        return salida;
    }

    /**
     * Guardando, en **esta** cabeza, un recuerdo que llega del portátil. Es la mitad
     * inversa del puente y la que decide si un dato sirve o no.
     *
     * El portátil guarda frases canónicas; el teléfono, `clave, valor` — y de la clave
     * dependen `quienSoy()` y el saludo, que miran `nombre`, `me llamo` y `soy`. Si
     * «El usuario se llama Sandra» se guardara como texto suelto, la dueña sincronizaría
     * con su portátil y CORT seguiría sin saber cómo se llama **en el teléfono**, que es
     * el aparato donde más lo necesita. De ahí las tres reglas, en orden:
     *
     * 1. Si la frase dice cómo se llama (`se llama`), la clave es `nombre` y el valor
     *    la última palabra. Es la única forma canónica que el teléfono sabe leer, y es
     *    la que paga el corte.
     * 2. Si ya tiene forma `clave: valor` —porque el portátil está devolviendo una fila
     *    que subió él—, se guarda con esa clave tal cual. Ida y vuelta sin deformar.
     * 3. Cualquier otra frase se guarda como nota, con una clave **derivada del
     *    contenido**: la misma frase produce la misma clave, así que sincronizar dos
     *    veces no crea dos filas ni borra la primera (`CONFLICT REPLACE`).
     *
     * No hay `DELETE` en este método ni en `Puente.fusionar`: regla 3 del puente, un
     * lado que se poda no es un lado que olvidó.
     */
    @Override
    public void recuerda(String contenido) {
        if (contenido == null) {
            return;
        }
        String limpio = contenido.trim();
        if (limpio.isEmpty()) {
            return;
        }
        int llama = limpio.indexOf("se llama");
        if (llama >= 0) {
            String nombre = limpio.substring(llama + "se llama".length()).trim();
            if (!nombre.isEmpty()) {
                guardarImportado("nombre", nombre);
                return;
            }
        }
        int dosPuntos = limpio.indexOf(": ");
        if (dosPuntos > 0 && dosPuntos <= 40) {
            String clave = limpio.substring(0, dosPuntos).trim();
            String valor = limpio.substring(dosPuntos + 2).trim();
            if (!clave.isEmpty() && !valor.isEmpty()) {
                guardarImportado(clave, valor);
                return;
            }
        }
        // La clave se **deriva del contenido** con el mismo criterio con el que el
        // puente deduplica (`Puente.normaliza`), no con una copia del algoritmo: la
        // misma frase produce la misma clave, así que sincronizar dos veces no crea dos
        // filas ni borra la primera (`CONFLICT REPLACE` de `guarda`).
        guardarImportado("nota " + Integer.toHexString(Puente.normaliza(limpio).hashCode()), limpio);
    }

    /** Cuántos hechos hay, para el recuento que la cara enseña tras sincronizar. */
    public int cuentasDeHechos() {
        Cursor c = getReadableDatabase().rawQuery(
                "SELECT COUNT(*) FROM hechos WHERE eliminado_en IS NULL", null);
        try {
            return c.moveToFirst() ? c.getInt(0) : 0;
        } finally {
            c.close();
        }
    }

    public int cuentasDeCorrecciones() {
        Cursor c = getReadableDatabase().rawQuery("SELECT COUNT(*) FROM hechos_historial "
                + "WHERE valor_anterior IS NOT NULL AND valor_nuevo IS NOT NULL", null);
        try {
            return c.moveToFirst() ? c.getInt(0) : 0;
        } finally {
            c.close();
        }
    }

    /** `millis` en ISO-8601 UTC, como lo escribe SQLite en la otra cabeza. */
    private static String iso(long millis) {
        SimpleDateFormat formato = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US);
        formato.setTimeZone(TimeZone.getTimeZone("UTC"));
        return formato.format(new Date(millis));
    }

    private static String limpia(String texto) {
        return texto.replace('_', ' ').trim();
    }

    public JSONObject listarHechos(int maximo) throws JSONException {
        JSONArray lista = new JSONArray();
        Cursor c = getReadableDatabase().query("hechos",
                new String[] {"clave", "valor", "origen", "confirmado", "creado_en",
                        "actualizado_en", "version"},
                "eliminado_en IS NULL", null, null, null, "actualizado_en DESC",
                String.valueOf(Math.min(200, Math.max(1, maximo))));
        try {
            while (c.moveToNext()) {
                lista.put(new JSONObject().put("id", c.getString(0)).put("clave", c.getString(0))
                        .put("valor", c.getString(1)).put("origen", c.getString(2))
                        .put("confirmado", c.getInt(3) != 0).put("creado_en", c.getLong(4))
                        .put("actualizado_en", c.getLong(5)).put("version", c.getInt(6)));
            }
        } finally {
            c.close();
        }
        return new JSONObject().put("type", "memoria_lista").put("origen", "real")
                .put("hechos", lista).put("total", cuentasDeHechos());
    }

    public int versionHecho(String clave) {
        Cursor c = getReadableDatabase().query("hechos", new String[] {"version"},
                "clave=? AND eliminado_en IS NULL", new String[] {clave}, null, null, null, "1");
        try {
            return c.moveToFirst() ? c.getInt(0) : -1;
        } finally {
            c.close();
        }
    }

    public String editarHecho(String clave, String nuevoValor, String origen, String aprobacionId) {
        return editarHecho(clave, nuevoValor, origen, aprobacionId, -1);
    }

    public String editarHecho(String clave, String nuevoValor, String origen, String aprobacionId,
                              int versionEsperada) {
        if (versionEsperada < 0) {
            if (valor(clave) == null) return "ese recuerdo ya no existe";
            return guardarConfirmado(clave, nuevoValor, origen, aprobacionId, true)
                    ? null : "el recuerdo propuesto no es válido";
        }
        if (validarDato(clave, nuevoValor) != null) return "el recuerdo propuesto no es válido";
        return guardarConfirmado(clave, nuevoValor, origen, aprobacionId, true,
                versionEsperada, false)
                ? null : "el recuerdo cambió o ya no existe; vuelve a preparar la edición";
    }

    public String borrarHecho(String clave, String origen, String aprobacionId) {
        return borrarHecho(clave, origen, aprobacionId, -1);
    }

    public String borrarHecho(String clave, String origen, String aprobacionId, int versionEsperada) {
        SQLiteDatabase db = getWritableDatabase();
        long ahora = System.currentTimeMillis();
        db.beginTransaction();
        try {
            Cursor c = db.query("hechos", new String[] {"valor", "version"},
                    "clave=? AND eliminado_en IS NULL", new String[] {clave}, null, null, null, "1");
            if (!c.moveToFirst()) {
                c.close();
                return "ese recuerdo ya no existe";
            }
            String anterior = c.getString(0);
            int versionAnterior = c.getInt(1);
            c.close();
            if (versionEsperada >= 0 && versionAnterior != versionEsperada) {
                return "el recuerdo cambió; vuelve a preparar el borrado";
            }
            ContentValues fila = new ContentValues();
            fila.put("eliminado_en", ahora);
            fila.put("actualizado_en", ahora);
            fila.put("version", versionAnterior + 1);
            if (db.update("hechos", fila, "clave=? AND eliminado_en IS NULL AND version=?",
                    new String[] {clave, String.valueOf(versionAnterior)}) != 1) {
                return "el recuerdo cambió; vuelve a preparar el borrado";
            }
            if (!anotarHistorial(db, clave, anterior, null, origen, aprobacionId, ahora)) {
                return "no pude registrar el historial; el recuerdo no se borró";
            }
            db.setTransactionSuccessful();
            return null;
        } finally {
            db.endTransaction();
        }
    }

    public JSONObject historialHecho(String clave) throws JSONException {
        JSONArray lista = new JSONArray();
        Cursor c = getReadableDatabase().query("hechos_historial",
                new String[] {"valor_anterior", "valor_nuevo", "origen", "aprobacion_id", "cuando"},
                "hecho_id=?", new String[] {clave}, null, null, "id DESC", "50");
        try {
            while (c.moveToNext()) {
                lista.put(new JSONObject().put("valor_anterior", c.isNull(0) ? JSONObject.NULL : c.getString(0))
                        .put("valor_nuevo", c.isNull(1) ? JSONObject.NULL : c.getString(1))
                        .put("origen", c.getString(2)).put("aprobacion_id", c.getString(3))
                        .put("cuando", c.getLong(4)));
            }
        } finally {
            c.close();
        }
        return new JSONObject().put("type", "memoria_historial").put("origen", "real")
                .put("id", clave).put("cambios", lista);
    }

    public JSONObject exportacionLocal() throws JSONException {
        return new JSONObject().put("type", "memoria_exportacion").put("origen", "real")
                .put("version", VERSION).put("exportado_en", System.currentTimeMillis())
                .put("hechos", listarHechos(200).getJSONArray("hechos"));
    }

    public long registrarAlarma(EspecificacionAlarma especificacion, String origen,
                                String aprobacionId) {
        if (!especificacion.valida) return -1L;
        ContentValues fila = new ContentValues();
        fila.put("texto", especificacion.texto);
        fila.put("tipo", especificacion.tipo);
        fila.put("hora", especificacion.hora);
        fila.put("minuto", especificacion.minuto);
        fila.put("dias", especificacion.dias);
        fila.put("segundos", especificacion.segundos);
        fila.put("etiqueta", especificacion.etiqueta);
        fila.put("estado", "SOLICITADO");
        fila.put("origen", origenLimpio(origen));
        fila.put("aprobacion_id", aprobacionId == null ? "" : aprobacionId);
        fila.put("creado_en", System.currentTimeMillis());
        return getWritableDatabase().insert("alarmas_entregadas", null, fila);
    }

    public boolean marcarAlarma(long id, String estado) {
        if (id < 1 || !("ENTREGADO_RELOJ".equals(estado) || "FALLO".equals(estado))) return false;
        ContentValues fila = new ContentValues();
        fila.put("estado", estado);
        return getWritableDatabase().update("alarmas_entregadas", fila, "id=?",
                new String[] {String.valueOf(id)}) == 1;
    }

    public JSONObject alarmasEntregadas(int maximo) throws JSONException {
        JSONArray lista = new JSONArray();
        Cursor c = getReadableDatabase().query("alarmas_entregadas",
                new String[] {"id", "texto", "tipo", "hora", "minuto", "dias", "segundos",
                        "etiqueta", "estado", "origen", "aprobacion_id", "creado_en"},
                null, null, null, null, "id DESC", String.valueOf(Math.min(100, Math.max(1, maximo))));
        try {
            while (c.moveToNext()) {
                lista.put(new JSONObject().put("id", c.getLong(0)).put("texto", c.getString(1))
                        .put("tipo", c.getString(2)).put("hora", c.getInt(3))
                        .put("minuto", c.getInt(4)).put("dias", c.getInt(5))
                        .put("segundos", c.getInt(6)).put("etiqueta", c.getString(7))
                        .put("estado", c.getString(8)).put("origen", c.getString(9))
                        .put("aprobacion_id", c.getString(10)).put("creado_en", c.getLong(11)));
            }
        } finally {
            c.close();
        }
        return new JSONObject().put("type", "alarmas_estado").put("origen", "real")
                .put("alarmas", lista).put("limite", "El catálogo local registra entregas al reloj; "
                        + "Android no permite enumerar ni cancelar universalmente alarmas de otras apps.");
    }

    public String cancelarAlarmaLocal(long id) {
        Cursor c = getReadableDatabase().query("alarmas_entregadas", new String[] {"estado"},
                "id=?", new String[] {String.valueOf(id)}, null, null, null, "1");
        String estado;
        if (c.moveToFirst()) estado = c.getString(0);
        else estado = "";
        c.close();
        if (estado.isEmpty()) return "esa entrega ya no existe";
        if ("ENTREGADO_RELOJ".equals(estado)) {
            return "el reloj recibió la alarma: ábrelo para cancelarla allí";
        }
        ContentValues fila = new ContentValues();
        fila.put("estado", "CANCELADO_LOCAL");
        if (getWritableDatabase().update("alarmas_entregadas", fila, "id=? AND estado=?",
                new String[] {String.valueOf(id), estado}) != 1) {
            return "no pude cancelar la entrega local";
        }
        return null;
    }

    private static boolean anotarHistorial(SQLiteDatabase db, String clave, String anterior,
                                           String nuevo, String origen, String aprobacionId, long cuando) {
        ContentValues fila = new ContentValues();
        fila.put("hecho_id", clave);
        fila.put("valor_anterior", anterior);
        fila.put("valor_nuevo", nuevo);
        fila.put("origen", origenLimpio(origen));
        fila.put("aprobacion_id", aprobacionId == null ? "" : aprobacionId);
        fila.put("cuando", cuando);
        return db.insert("hechos_historial", null, fila) >= 0;
    }

    private static String validarDato(String clave, String valor) {
        if (clave == null || valor == null) return "falta la clave o el valor";
        String key = clave.trim();
        String value = valor.trim();
        if (key.isEmpty() || key.length() > 80) return "la clave debe tener entre 1 y 80 caracteres";
        if (value.isEmpty() || value.length() > 2000) return "el valor debe tener entre 1 y 2000 caracteres";
        if (key.matches(".*[\\u0000-\\u001f\\u007f].*")
                || value.matches(".*[\\u0000-\\u001f\\u007f].*")) return "hay caracteres de control";
        String normal = Cerebro.normaliza(key);
        for (String prohibida : new String[] {"password", "contrasena", "credencial", "secreto",
                "token", "api key", "llave privada"}) {
            if (normal.contains(prohibida)) return "no se guardan credenciales";
        }
        return null;
    }

    private static String origenLimpio(String origen) {
        String valor = origen == null ? "desconocido" : origen.trim();
        return valor.substring(0, Math.min(40, valor.length()));
    }

    /* ------------------------------------------------------------ habilidades */

    /**
     * Una habilidad aprendida es un patrón normalizado que apunta a una acción de
     * la **lista cerrada** de `assets/habilidades.json`. No es código: CORT no
     * escribe instrucciones, escribe atajos. Así el «closed learning loop» de
     * Hermes cabe dentro de la regla 6.
     */
    public void aprender(String patron, String accion, String param, String respuesta) {
        ContentValues fila = new ContentValues();
        fila.put("patron", patron);
        fila.put("accion", accion);
        fila.put("param", param == null ? "" : param);
        fila.put("respuesta", respuesta == null ? "" : respuesta);
        fila.put("veces", 1);
        getWritableDatabase().insertWithOnConflict("habilidades", null, fila,
                SQLiteDatabase.CONFLICT_REPLACE);
    }

    public String[] habilidad(String patron) {
        Cursor c = getReadableDatabase().query("habilidades",
                new String[] {"accion", "param", "respuesta"},
                "patron=?", new String[] {patron}, null, null, null, "1");
        try {
            if (c.moveToFirst()) {
                return new String[] {c.getString(0), c.getString(1), c.getString(2)};
            }
            return null;
        } finally {
            c.close();
        }
    }

    public int cuentasDeHabilidades() {
        Cursor c = getReadableDatabase().rawQuery("SELECT COUNT(*) FROM habilidades", null);
        try {
            return c.moveToFirst() ? c.getInt(0) : 0;
        } finally {
            c.close();
        }
    }
}
