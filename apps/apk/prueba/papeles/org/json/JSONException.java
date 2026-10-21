package org.json;

/* Impls mínima de org.json para poder COMPILAR Y PROBAR en el portátil.
   No es el org.json de Android: es un sustituto con la misma firma pública que
   usan `Cerebro`, `Nube` y `Mente`, y un parser de verdad para poder cargar
   `apps/apk/assets/habilidades.json` aquí y ver qué decide el cerebro. */

public class JSONException extends Exception {
    public JSONException(String m) { super(m); }
    public JSONException(Throwable t) { super(t); }
}
