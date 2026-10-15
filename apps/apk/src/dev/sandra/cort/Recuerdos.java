package dev.sandra.cort;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import java.util.ArrayList;
import java.util.List;

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
public class Recuerdos extends SQLiteOpenHelper {
    private static final String NOMBRE = "cort.db";
    private static final int VERSION = 1;

    public Recuerdos(Context contexto) {
        super(contexto.getApplicationContext(), NOMBRE, null, VERSION);
    }

    @Override
    public void onCreate(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE hechos ("
                + "clave TEXT PRIMARY KEY,"
                + "valor TEXT NOT NULL,"
                + "cuando INTEGER NOT NULL)");
        db.execSQL("CREATE TABLE habilidades ("
                + "patron TEXT PRIMARY KEY,"
                + "accion TEXT NOT NULL,"
                + "param TEXT,"
                + "respuesta TEXT,"
                + "veces INTEGER NOT NULL DEFAULT 1)");
    }

    @Override
    public void onUpgrade(SQLiteDatabase db, int desde, int hasta) {
        // Una sola versión por ahora. Si algún día la hay, aquí se migra y no se
        // borra: esta tabla es la memoria de la dueña, no una caché.
        onCreate(db);
    }

    /* ---------------------------------------------------------------- hechos */

    public void guarda(String clave, String valor) {
        ContentValues fila = new ContentValues();
        fila.put("clave", clave);
        fila.put("valor", valor);
        fila.put("cuando", System.currentTimeMillis());
        getWritableDatabase().insertWithOnConflict("hechos", null, fila,
                SQLiteDatabase.CONFLICT_REPLACE);
    }

    public String valor(String clave) {
        Cursor c = getReadableDatabase().query("hechos", new String[] {"valor"},
                "clave=?", new String[] {clave}, null, null, null, "1");
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
                null, null, null, null, "cuando DESC", String.valueOf(maximo));
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
        guarda(par[0], par[1]);
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
                "clave LIKE ?", new String[] {"%" + limpio + "%"}, null, null, null, "3");
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
            guarda(clave, valorPropuesto);
        }
    }

    private static String limpia(String texto) {
        return texto.replace('_', ' ').trim();
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
