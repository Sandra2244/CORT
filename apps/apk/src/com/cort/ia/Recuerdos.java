package com.cort.ia;

/*
 * La memoria de CORT **dentro del teléfono**: SQLite propio
 * (`cort-recuerdos.db`), el motor que Android ya trae, sin dependencias que el
 * pipeline (`aapt2 + javac + d8`) tenga que descargar.
 *
 * Tres tablas, la misma forma que la línea hermana de
 * `/home/Sandra/Documentos/CORT-TELEFONO` (`Recuerdos.java`), que es la fuente
 * de esta lógica:
 *
 * · `hechos(clave, valor, cuando)` — lo que la dueña dice con «recuerda que
 *   mi correo es …», partido en par clave/valor (la cópula y el `limpia`
 *   están portados tal cual, con su corrección de la longitud: « es » mide 4
 *   y « son » 5, y con número fijo «mis gestos son uno y dos» se guardaba
 *   deformado).
 * · `recuerdos(contenido, cuando)` — la frase entera, para la lista y para
 *   bajar el muro del portátil.
 * · `habilidades(patron, accion, param, respuesta)` — atajos aprendidos; son
 *   datos, nunca código: regla 6 del core, CORT no escribe instrucciones.
 *
 * El contrato es la sección 3 de `docs/CONTRATO-PUENTE-2.1.md`:
 * `memoria(que, args)` con `que` = guardar | buscar | lista | quien | olvidar
 * | sincronizar | estado. `guarda/valor/frase/busca` quedan públicos para que
 * `CortNative` los use por su cuenta sin duplicar la base.
 *
 * Lo que **no** hace, escrito está:
 *
 * · `olvidar` borra filas de CORT y nada más. Nunca toca archivos: no hay
 *   `File.delete`, no hay `MediaStore`, no hay ruta en la que Android note
 *   que CORT existió. La cara recibe `borrados` (un número de filas) y `dice`
 *   lo recuerda por si la dueña confunde «olvida» con «borra mis fotos».
 * · `sincronizar` no toca la red desde el hilo del puente de WebView:
 *   `HttpURLConnection` congelaría la cara con el portátil apagado. Se
 *   contesta `{"ok":true,"pendiente":true}` enseguida y el viaje va en un
 *   hilo llamado `cort-memoria-sync`; el resultado vuelve por el callback
 *   `AlTermina` (que `CortNative` engancha a su `cuadro`).
 * · Ningún método público que llama la cara lanza: hasta los `Cursor` se
 *   cierran en `finally` y el SQL lleva el texto del usuario como
 *   `selectionArgs`, jamás concatenado.
 * · `estado` dice cuántos hechos hay y si hay dirección de portátil, y ni
 *   una clave API se imprime nunca aquí ni en ningún otro cuadro.
 */

import android.content.ContentValues;
import android.content.Context;
import android.content.SharedPreferences;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.TimeZone;
import org.json.JSONObject;

public class Recuerdos extends SQLiteOpenHelper {

    private static final String NOMBRE = "cort-recuerdos.db";
    private static final int VERSION = 1;

    /** El resultado largo del hilo de sincronía, para engancharlo a `cuadro`. */
    public interface AlTermina {
        void con(String json);
    }

    private final Context ctx;
    private volatile AlTermina bocaSync;
    private volatile boolean syncEnCurso = false;

    public Recuerdos(android.content.Context contexto) {
        super(contexto.getApplicationContext(), NOMBRE, null, VERSION);
        this.ctx = contexto.getApplicationContext();
    }

    @Override
    public void onCreate(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE IF NOT EXISTS hechos ("
                 + "clave TEXT PRIMARY KEY,"
                 + "valor TEXT NOT NULL,"
                 + "cuando INTEGER NOT NULL)");
        db.execSQL("CREATE TABLE IF NOT EXISTS recuerdos ("
                 + "contenido TEXT,"
                 + "cuando INTEGER NOT NULL)");
        db.execSQL("CREATE TABLE IF NOT EXISTS habilidades ("
                 + "patron TEXT PRIMARY KEY,"
                 + "accion TEXT NOT NULL,"
                 + "param TEXT,"
                 + "respuesta TEXT)");
    }

    @Override
    public void onUpgrade(SQLiteDatabase db, int desde, int hasta) {
        // Una sola versión por ahora. Si algún día la hay, aquí se migra y no
        // se borra: estas tablas son la memoria de la dueña, no una caché.
        try { onCreate(db); } catch (Exception yaExisten) { /* nada que crear */ }
    }

    /* ─────────────────────────── entrada del contrato ─────────────────────── */

    /**
     * El `memoria(que, args)` de la sección 3. Recibe `{"que":"…","texto":…}`
     * (los campos también pueden venir dentro de `args`, como en `accion`) y
     * devuelve el cuadro. Nunca lanza.
     */
    public String memoria(String peticion) {
        try {
            JSONObject j = junto(peticion);
            String que = j.optString("que", "");
            String texto = j.optString("texto", "");
            switch (que) {
                case "guardar":   return guardarCuadro(texto);
                case "buscar":    return buscarCuadro(texto);
                case "lista":     return listaCuadro();
                case "quien":     return "{\"ok\":true,\"dice\":" + comilla(quienSoy()) + "}";
                case "olvidar":   return olvidarCuadro(texto);
                case "sincronizar": return sincronizarCuadro();
                case "estado":    return estadoCuadro();
                default:
                    return "{\"ok\":false,\"dice\":\"no conozco ese que de la memoria: "
                         + comilla(que) + "\"}";
            }
        } catch (Exception cualquierCosa) {
            return "{\"ok\":false,\"dice\":\"la memoria no respondió: "
                 + comilla(motivo(cualquierCosa)) + "\"}";
        }
    }

    /** Une `args` (objeto o string dentro de string) con los campos sueltos. */
    private static JSONObject junto(String peticion) throws Exception {
        JSONObject j = new JSONObject(peticion == null || peticion.trim().isEmpty() ? "{}" : peticion);
        Object args = j.opt("args");
        if (args != null) {
            JSONObject a = null;
            if (args instanceof JSONObject) a = (JSONObject) args;
            else if (args instanceof String && !((String) args).trim().isEmpty()) {
                try { a = new JSONObject((String) args); } catch (Exception argsSueltos) { a = null; }
            }
            if (a != null) {
                java.util.Iterator<String> ks = a.keys();
                while (ks.hasNext()) {
                    String k = ks.next();
                    if (k.equals("args")) continue;
                    if (!j.has(k)) j.put(k, a.get(k));
                }
            }
        }
        return j;
    }

    /* ────────────────────────────── los `que` ─────────────────────────────── */

    /** `guardar` → «la clave del wifi es …» → `{"ok":true,"clave":"wifi",…}`. */
    private String guardarCuadro(String texto) {
        String[] par = parte(texto);
        if (par == null) {
            return "{\"ok\":false,\"dice\":"
                 + comilla("No supe qué anotar de eso. Prueba con «recuerda que mi clave es valor».") + "}";
        }
        guarda(par[0], par[1]);
        nota(texto);
        return "{\"ok\":true,\"clave\":" + comilla(par[0])
             + ",\"dice\":" + comilla("Anotado: " + limpia(par[0]) + " es " + par[1]
                + ". Se queda en este teléfono.") + "}";
    }

    /** `buscar` → `{"encuentra":"…"}`; si no hay nada, `ok:false` dicho. */
    private String buscarCuadro(String texto) {
        String hallado = busca(texto);
        if (hallado == null) {
            return "{\"ok\":false,\"dice\":"
                 + comilla("No tengo nada guardado sobre " + texto.trim() + ".") + "}";
        }
        return "{\"ok\":true,\"encuentra\":" + comilla(hallado) + "}";
    }

    /** `lista` → hasta 40 recuerdos, el más nuevo primero, con fecha ISO. */
    private String listaCuadro() {
        StringBuilder s = new StringBuilder("[");
        Cursor c = null;
        try {
            c = getReadableDatabase().query("recuerdos",
                    new String[] {"contenido", "cuando"},
                    null, null, null, null, "cuando DESC", "40");
            boolean primero = true;
            if (c != null) {
                while (c.moveToNext()) {
                    if (!primero) s.append(',');
                    primero = false;
                    s.append("{\"contenido\":").append(comilla(c.getString(0)))
                     .append(",\"cuando\":").append(comilla(iso(c.getLong(1))))
                     .append('}');
                }
            }
        } catch (Exception laBaseNoDeja) { /* array vacío: es lo que hay */ }
        finally {
            if (c != null) try { c.close(); } catch (Exception ignorado) { }
        }
        return "{\"ok\":true,\"recuerdos\":" + s.append(']').toString() + "}";
    }

    /**
     * `olvidar`. Con texto borra las filas que coinciden; sin texto, toda la
     * memoria de CORT. **Sólo filas de CORT**: no se toca ningún archivo del
     * teléfono, y `dice` lo dice porque la dueña no debe confundir «olvida»
     * con «borra mis fotos».
     */
    private String olvidarCuadro(String texto) {
        try {
            int borrados = olvidar(texto);
            return "{\"ok\":true,\"borrados\":" + borrados
                 + ",\"dice\":\"sólo he borrado cosas que yo guardé;"
                 + " no he tocado ningún archivo del teléfono\"}";
        } catch (Exception laBaseNoDeja) {
            return "{\"ok\":false,\"dice\":\"no pude borrar: "
                 + comilla(motivo(laBaseNoDeja)) + "\"}";
        }
    }

    /** `sincronizar`: enseguida `pendiente`; el viaje largo va en su hilo. */
    private String sincronizarCuadro() {
        Sincroniza s = new Sincroniza(ctx, this);
        if (!s.hayPortatil()) {
            return "{\"ok\":false,\"dice\":"
                 + comilla("no sé dónde está tu portátil: dime su dirección primero") + "}";
        }
        arrancaSync(bocaSync);
        return "{\"ok\":true,\"pendiente\":true}";
    }

    /**
     * `estado`: recuentos y si hay dirección de portátil guardada
     * (`cort` / `pc`). Ninguna clave se imprime aquí: la llave de red nunca
     * sale del teléfono hacia la cara.
     */
    private String estadoCuadro() {
        SharedPreferences p = prefs();
        String pc = "";
        try { pc = p.getString("pc", ""); } catch (Exception prefsRaras) { pc = ""; }
        boolean conPC = pc != null && !pc.trim().isEmpty();
        return "{\"ok\":true,\"hechos\":" + cuantos("hechos")
             + ",\"recuerdos\":" + cuantos("recuerdos")
             + ",\"habilidades\":" + cuantos("habilidades")
             + ",\"conPortatil\":" + conPC
             + (conPC ? ",\"direccion\":" + comilla(pc.trim()) : "")
             + ",\"sincronizando\":" + syncEnCurso + "}";
    }

    /* ─────────────────── lo que usa CortNative por su cuenta ──────────────── */

    /** Guarda un par clave/valor. No lanza nunca: la cara no se entera de SQL. */
    public void guarda(String k, String v) {
        try {
            ContentValues fila = new ContentValues();
            fila.put("clave", k);
            fila.put("valor", v);
            fila.put("cuando", System.currentTimeMillis());
            getWritableDatabase().insertWithOnConflict("hechos", null, fila,
                    SQLiteDatabase.CONFLICT_REPLACE);
        } catch (Exception laBaseNoDeja) { /* la escritura se pierde, la app no */ }
    }

    /** El valor de una clave, o `null`. Con `selectionArgs`, nunca concatenado. */
    public String valor(String k) {
        if (k == null) return null;
        Cursor c = null;
        try {
            c = getReadableDatabase().query("hechos", new String[] {"valor"},
                    "clave=?", new String[] {k}, null, null, null, "1");
            if (c != null && c.moveToFirst()) return c.getString(0);
            return null;
        } catch (Exception laBaseNoDeja) {
            return null;
        } finally {
            if (c != null) try { c.close(); } catch (Exception ignorado) { }
        }
    }

    /**
     * «recuerda que mi correo es Y» dicho por la dueña: parte, guarda el par
     * y la frase entera, y devuelve la confirmación con la que CORT lo lee.
     */
    public String frase(String texto) {
        String[] par = parte(texto);
        if (par == null) {
            return "No supe qué anotar de eso. Prueba con «recuerda que mi clave es valor».";
        }
        guarda(par[0], par[1]);
        nota(texto);
        return "Anotado: " + limpia(par[0]) + " es " + par[1] + ". Se queda en este teléfono.";
    }

    /** Clave exacta, luego la clave que contenga la pregunta, luego el valor. */
    public String busca(String pregunta) {
        if (pregunta == null) return null;
        String limpio = pregunta.trim();
        if (limpio.isEmpty()) return null;
        String directa = valor(limpio);
        if (directa != null) return limpia(limpio) + ": " + directa;
        List<String> hallados = new ArrayList<>();
        Cursor c = null;
        try {
            c = getReadableDatabase().query("hechos", new String[] {"clave", "valor"},
                    "clave LIKE ? OR valor LIKE ?",
                    new String[] {"%" + limpio + "%", "%" + limpio + "%"},
                    null, null, "cuando DESC", "3");
            if (c != null) {
                while (c.moveToNext()) hallados.add(c.getString(0) + ": " + c.getString(1));
            }
        } catch (Exception laBaseNoDeja) { /* se prueba igual con el muro */ }
        finally {
            if (c != null) try { c.close(); } catch (Exception ignorado) { }
        }
        if (hallados.isEmpty()) {
            // Las frases sueltas del muro también valen («qué sabes de mi
            // hermano» encuentra la nota que lo menciona).
            c = null;
            try {
                c = getReadableDatabase().query("recuerdos", new String[] {"contenido"},
                        "contenido LIKE ?", new String[] {"%" + limpio + "%"},
                        null, null, "cuando DESC", "3");
                if (c != null) {
                    while (c.moveToNext()) hallados.add(c.getString(0));
                }
            } catch (Exception laBaseNoDejaOtra) { /* nada más que intentarlo */ }
            finally {
                if (c != null) try { c.close(); } catch (Exception ignorado) { }
            }
        }
        return hallados.isEmpty() ? null : unire(hallados);
    }

    /** «quién soy» responde por el nombre, y si no lo hay lo dice sin inventar. */
    public String quienSoy() {
        for (String clave : new String[] {"nombre", "me llamo", "soy"}) {
            String v = valor(clave);
            if (v != null) {
                return "Eres " + v + ". Guardo " + cuantos("hechos")
                     + " cosas de ti en este teléfono.";
            }
        }
        return "No me has dicho tu nombre. Dime «recuerda que te llamas …» y lo guardo aquí.";
    }

    /* ──────────────────────────── el partedor ─────────────────────────────── */

    /**
     * «la clave del wifi es 1234», «soy Sandra», «me llamo Sandra» → par
     * {clave, valor}, o `null` si la frase no tiene forma. Portado de la línea
     * hermana con las tres formas que fija el diseño:
     *
     * · «me llamo X» / «mi nombre es X» → clave `nombre` (de ella dependen
     *   `quienSoy` y el saludo).
     * · «soy X» → clave `soy`.
     * · cópula « es » / « son » → clave antes, valor después, con el artículo
     *   «mi/el/la…» fuera de la clave («mi correo es Y» → `correo`).
     *
     * La longitud de la cópula se devuelve y no se fija en 3: « es » mide 4 y
     * « son » 5; con número fijo «mis gestos son uno y dos» se guardaba
     * deformado. Medido leyendo el código de la hermana, no inventado.
     */
    public static String[] parte(String resto) {
        String limpio = resto == null ? "" : resto.trim();
        if (limpio.isEmpty()) return null;
        // «recuerda que …» puede llegar con el «que» dentro: fuera.
        String baja = limpio.toLowerCase(Locale.US);
        if (baja.startsWith("que ")) {
            limpio = limpio.substring(4).trim();
            baja = limpio.toLowerCase(Locale.US);
        }
        if (limpio.isEmpty()) return null;
        if (baja.startsWith("me llamo ")) {
            String v = limpio.substring("me llamo ".length()).trim();
            return v.isEmpty() ? null : new String[] {"nombre", v};
        }
        if (baja.equals("soy") || baja.startsWith("soy ")) {
            String v = limpio.substring("soy".length()).trim();
            if (v.isEmpty()) return null;
            // «soy el fontanero» es una frase entera, no un nombre: la cópula
            // manda si hay un verbo por el medio; si no, «soy X» es nombre.
            if (copula(v) == null) return new String[] {"soy", v};
        }
        int[] copula = copula(limpio);
        if (copula == null) {
            // Sin cópula, la clave son las dos primeras palabras… en la
            // hermana la primera y el resto; se porta igual para no cambiar
            // la forma en que «mis gestos» ya vivía guardada.
            String[] palabras = limpio.split("\\s+");
            if (palabras.length < 2) return new String[] {limpio, limpio};
            int i = limpio.indexOf(palabras[0]);
            return new String[] {palabras[0],
                    limpio.substring(i + palabras[0].length()).trim()};
        }
        String clave = limpio.substring(0, copula[0]).trim();
        String valor = limpio.substring(copula[0] + copula[1]).trim();
        for (String articulo : new String[] {"mi ", "el ", "la ", "los ", "las "}) {
            if (clave.toLowerCase(Locale.US).startsWith(articulo)) {
                clave = clave.substring(articulo.length());
                break;
            }
        }
        // «mi nombre es X» sin artículo que quite… el artículo ya salió; si la
        // clave quedó «nombre» o «nombre mío» se deja tal cual: quienSoy mira `nombre`.
        if (clave.isEmpty() || valor.isEmpty()) return null;
        return new String[] {clave, valor};
    }

    /** {índice, longitud} de la cópula, o `null` si no la hay. Portada tal cual. */
    private static int[] copula(String texto) {
        int es = texto.indexOf(" es ");
        int son = texto.indexOf(" son ");
        if (es >= 0 && (son < 0 || es <= son)) return new int[] {es, 4};
        return son >= 0 ? new int[] {son, 5} : null;
    }

    static String limpia(String texto) {
        return texto == null ? "" : texto.replace('_', ' ').trim();
    }

    /* ──────────────────────────── el muro y las llaves ─────────────────────── */

    /** La frase entera, en la tabla `recuerdos`, sin duplicar la misma vez. */
    public void nota(String contenido) {
        if (contenido == null) return;
        String limpio = contenido.trim();
        if (limpio.isEmpty()) return;
        Cursor c = null;
        try {
            c = getReadableDatabase().query("recuerdos", new String[] {"contenido"},
                    "contenido=?", new String[] {limpio}, null, null, null, "1");
            if (c != null && c.moveToFirst()) return; // ya estaba: sincronizar dos veces no duplica
            ContentValues fila = new ContentValues();
            fila.put("contenido", limpio);
            fila.put("cuando", System.currentTimeMillis());
            getWritableDatabase().insert("recuerdos", null, fila);
        } catch (Exception laBaseNoDeja) { /* se pierde la nota, no la app */ }
        finally {
            if (c != null) try { c.close(); } catch (Exception ignorado) { }
        }
    }

    /**
     * Guardar en **esta** cabeza un recuerdo que llega del portátil, con las
     * tres reglas portadas de la hermana (nombre → `nombre`, «clave: valor» →
     * par, cualquier otra frase → nota con clave derivada del contenido, para
     * que ida y vuelta no deforme ni duplique). Devuelve si almacenó algo
     * nuevo: `Sincroniza` cuenta los bajados con eso.
     */
    public boolean recuerda(String contenido) {
        if (contenido == null) return false;
        String limpio = contenido.trim();
        if (limpio.isEmpty()) return false;
        int llama = limpio.indexOf("se llama");
        if (llama >= 0) {
            String nombre = limpio.substring(llama + "se llama".length()).trim();
            if (!nombre.isEmpty()) {
                boolean nuevo = valor("nombre") == null;
                guarda("nombre", nombre);
                nota(limpio);
                return nuevo;
            }
        }
        int dosPuntos = limpio.indexOf(": ");
        if (dosPuntos > 0 && dosPuntos <= 40) {
            String clave = limpio.substring(0, dosPuntos).trim();
            String valor = limpio.substring(dosPuntos + 2).trim();
            if (!clave.isEmpty() && !valor.isEmpty()) {
                boolean nuevo = valor(clave) == null;
                guarda(clave, valor);
                nota(limpio);
                return nuevo;
            }
        }
        String clave = "nota " + Integer.toHexString(normaliza(limpio).hashCode());
        boolean nuevo = valor(clave) == null;
        if (!nuevo) return false; // la misma frase ya vivía aquí: nada nuevo que contar
        guarda(clave, limpio);
        nota(limpio);
        return true;
    }

    /** Las filas para subir: {clave, valor}, lo más nuevo primero. */
    public List<String[]> hechos(int maximo) {
        List<String[]> salida = new ArrayList<>();
        Cursor c = null;
        try {
            c = getReadableDatabase().query("hechos", new String[] {"clave", "valor"},
                    null, null, null, null, "cuando DESC", String.valueOf(maximo));
            if (c != null) {
                while (c.moveToNext()) salida.add(new String[] {c.getString(0), c.getString(1)});
            }
        } catch (Exception laBaseNoDeja) { /* subir nada es mejor que inventar */ }
        finally {
            if (c != null) try { c.close(); } catch (Exception ignorado) { }
        }
        return salida;
    }

    /**
     * Las frases sueltas que CORT apuntó en el teléfono («acuédate de que la clave
     * del wifi es…»), la más nueva primero. Son la carga de `POST /api/memories`:
     * sin esta lista la sincronía se quedaba en bajar y nunca subir, que es justo
     * lo que se perdió al cambiar de móvil.
     */
    public List<String> recuerdos(int maximo) {
        List<String> salida = new ArrayList<>();
        Cursor c = null;
        try {
            c = getReadableDatabase().query("recuerdos", new String[] {"contenido"},
                    null, null, null, null, "cuando DESC", String.valueOf(maximo));
            if (c != null) {
                while (c.moveToNext()) {
                    String dicho = c.getString(0);
                    if (dicho != null && !dicho.trim().isEmpty()) salida.add(dicho);
                }
            }
        } catch (Exception laBaseNoDeja) { /* subir nada es mejor que inventar */ }
        finally {
            if (c != null) try { c.close(); } catch (Exception ignorado) { }
        }
        return salida;
    }

    /** Cuántos hechos hay, para el `estado` y el recuento tras sincronizar. */
    public int cuantosHechos() { return cuantos("hechos"); }

    /** Un `SELECT COUNT(*)` fijo, con tabla de una whitelist interna. */
    private int cuantos(String tabla) {
        String sql;
        if (tabla.equals("hechos")) sql = "SELECT COUNT(*) FROM hechos";
        else if (tabla.equals("recuerdos")) sql = "SELECT COUNT(*) FROM recuerdos";
        else if (tabla.equals("habilidades")) sql = "SELECT COUNT(*) FROM habilidades";
        else return 0; // nombre fuera de la lista: ni preguntar
        Cursor c = null;
        try {
            c = getReadableDatabase().rawQuery(sql, null);
            return (c != null && c.moveToFirst()) ? c.getInt(0) : 0;
        } catch (Exception laBaseNoDeja) {
            return 0;
        } finally {
            if (c != null) try { c.close(); } catch (Exception ignorado) { }
        }
    }

    /** Borrar filas que CORT guardó. Nunca archivos: aquí no hay ningún File. */
    private int olvidar(String texto) {
        SQLiteDatabase db = getWritableDatabase();
        int borrados = 0;
        if (texto == null || texto.trim().isEmpty()) {
            borrados += db.delete("hechos", null, null);
            borrados += db.delete("recuerdos", null, null);
            return borrados;
        }
        String como = "%" + texto.trim() + "%";
        borrados += db.delete("hechos", "clave LIKE ? OR valor LIKE ?", new String[] {como, como});
        borrados += db.delete("recuerdos", "contenido LIKE ?", new String[] {como});
        return borrados;
    }

    /* ──────────────────────────── habilidades ──────────────────────────────── */

    /**
     * Una habilidad aprendida es un patrón que apunta a una acción de la lista
     * cerrada de acciones; no es código. CORT no escribe instrucciones, escribe
     * atajos (regla 6 del core, portada).
     */
    public void aprender(String patron, String accion, String param, String respuesta) {
        try {
            ContentValues fila = new ContentValues();
            fila.put("patron", patron);
            fila.put("accion", accion);
            fila.put("param", param == null ? "" : param);
            fila.put("respuesta", respuesta == null ? "" : respuesta);
            getWritableDatabase().insertWithOnConflict("habilidades", null, fila,
                    SQLiteDatabase.CONFLICT_REPLACE);
        } catch (Exception laBaseNoDeja) { /* el atajo se pierde, la app no */ }
    }

    /** {accion, param, respuesta} del patrón, o `null`. Con selectionArgs. */
    public String[] habilidad(String patron) {
        if (patron == null) return null;
        Cursor c = null;
        try {
            c = getReadableDatabase().query("habilidades",
                    new String[] {"accion", "param", "respuesta"},
                    "patron=?", new String[] {patron}, null, null, null, "1");
            if (c != null && c.moveToFirst()) {
                return new String[] {c.getString(0), c.getString(1), c.getString(2)};
            }
            return null;
        } catch (Exception laBaseNoDeja) {
            return null;
        } finally {
            if (c != null) try { c.close(); } catch (Exception ignorado) { }
        }
    }

    /* ───────────────────────────── sincronía ───────────────────────────────── */

    /**
     * Registra la boca del evento y lanza el viaje. `CortNative` la engancha a
     * su `cuadro` para que llegue `{type:"memoria", ok, subidos, bajados}`.
     * Si ya hay un viaje en curso no se monta otro: dos hilos escribiendo la
     * misma base contra el mismo portátil es una segunda verdad del tiempo.
     */
    public void sincroniza(AlTermina sigue) {
        if (sigue != null) bocaSync = sigue;
        arrancaSync(sigue != null ? sigue : bocaSync);
    }

    /**
     * Registra SÓLO la boca del evento, sin lanzar el viaje. Es lo que llama
     * `CortNative` al montar la memoria: el viaje lo arranca la dueña con
     * «sincroniza con el portátil», y arrancarlo también al enganchar la boca
     * sería sincronizar por accidente con sólo abrir la pantalla Equipo.
     */
    public void engancha(AlTermina sigue) {
        if (sigue != null) bocaSync = sigue;
    }

    private void arrancaSync(final AlTermina sigue) {
        if (syncEnCurso) return;
        syncEnCurso = true;
        new Thread(new Runnable() {
            @Override public void run() {
                String res;
                try {
                    res = new Sincroniza(ctx, Recuerdos.this).sincronizar();
                } catch (Exception elPuenteRevento) {
                    res = "{\"ok\":false,\"dice\":\"el puente no cerró\"}";
                } finally {
                    syncEnCurso = false;
                }
                if (sigue != null) {
                    try { sigue.con(conTipoMemoria(res)); }
                    catch (Exception laCaraSeCerro) { /* nada que hacer: el evento se pierde */ }
                }
            }
        }, "cort-memoria-sync").start();
    }

    /** El cuadro del viaje, ya con el `type` que la cara espera. */
    private static String conTipoMemoria(String res) {
        try {
            JSONObject e = new JSONObject(res);
            e.put("type", "memoria");
            return e.toString();
        } catch (Exception noEsCuadro) {
            return "{\"type\":\"memoria\",\"ok\":false,\"dice\":\"el puente contestó cualquiercosa\"}";
        }
    }

    /* ────────────────────────────── utilidades ─────────────────────────────── */

    private SharedPreferences prefs() {
        return ctx.getSharedPreferences("cort", Context.MODE_PRIVATE);
    }

    /** `millis` en ISO-8601 UTC, como lo escribe la otra cabeza: nada de segundos locales. */
    private static String iso(long millis) {
        SimpleDateFormat formato = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US);
        formato.setTimeZone(TimeZone.getTimeZone("UTC"));
        return formato.format(new Date(millis));
    }

    /** Normalización para deduplicar: minúsculas, sin espacios raros. */
    private static String normaliza(String s) {
        return s.toLowerCase(Locale.US).replaceAll("\\s+", " ").trim();
    }

    private static String unire(List<String> trozos) {
        StringBuilder out = new StringBuilder();
        for (int n = 0; n < trozos.size(); n++) {
            if (n > 0) out.append(", ");
            out.append(trozos.get(n));
        }
        return out.toString();
    }

    private static String motivo(Exception e) {
        String m = e.getMessage();
        return (m == null || m.trim().isEmpty()) ? e.getClass().getSimpleName() : m;
    }

    /** El mismo patrón de `CortNative.comilla`: cuerdas escapadas a mano. */
    private static String comilla(String s) {
        if (s == null) return "null";
        StringBuilder out = new StringBuilder("\"");
        for (int n = 0; n < s.length(); n++) {
            char c = s.charAt(n);
            switch (c) {
                case '"':  out.append("\\\""); break;
                case '\\': out.append("\\\\"); break;
                case '\n': out.append("\\n");  break;
                case '\r': out.append("\\r");  break;
                case '\t': out.append("\\t");  break;
                default:
                    if (c < 0x20) out.append(String.format("\\u%04x", (int) c));
                    else out.append(c);
            }
        }
        return out.append('"').toString();
    }
}
