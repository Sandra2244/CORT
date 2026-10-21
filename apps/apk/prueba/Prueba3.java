package com.cort.ia;

import android.content.Context;
import android.content.res.AssetManager;
import java.io.File;
import java.util.List;
import java.util.Map;
import java.util.ArrayList;

/* PRUEBA DE TABLA: cada frase escrita en la tabla tiene que caer en la regla que
   la escribió. Es el único modo de ver los robos por orden («pon silencio» se lo
   llevaba «pon {resto}») sin encender el teléfono. Corre sobre las DOS tablas:
   la del asset y la del código, porque si alguna vez se separan, aquí salta. */
public class Prueba3 {

    /** La palabra que hace de {resto}: no aparece en ninguna otra frase. */
    static final String RELLENO = "salsa de tomate";

    public static void main(String[] a) throws Exception {
        int fallos = 0, comprobadas = 0;
        for (File carpeta : new File[] { new File("/tmp/cort-mente/assets"),
                                         new File("/tmp/cort-mente/assets-vacias") }) {
            String donde = carpeta.getName().equals("assets") ? "ASSET" : "CODIGO";
            Context ctx = new Context();
            ctx.assets = new AssetManager(carpeta);
            Cerebro cerebro = new Cerebro(ctx, new Nube(ctx));

            // La lista de frases se lee del propio JSON cuando hay JSON; con la
            // tabla del código se pasa la misma lista leída del asset (tienen que
            // dar idéntico resultado, que es lo que se está probando aquí).
            List<String[]> frases = frasesDesdeJson();
            for (String[] fila : frases) {                 // [accion, param, frase]
                Cerebro.Resultado r = cerebro.procesar(fila[2]);
                comprobadas++;
                if (!fila[0].equals(r.accion)) {
                    System.out.println("  MAL " + donde + " «" + fila[2] + "» → " + r
                        + " (se esperaba " + fila[0] + ")");
                    fallos++;
                    continue;
                }
                // Las de {resto} transforman el trozo (apps, horas, segundos): sólo
                // se mira que la acción sea la debida, no el param ya mastigado.
                if (!fila[1].contains("{resto}") && !fila[1].isEmpty()
                    && !("abrir".equals(r.accion)) && !("alarma".equals(r.accion))
                    && !("temporizador".equals(r.accion))) {
                    if (fila[1] == null || !fila[1].equals(r.param)) {
                        System.out.println("  MAL " + donde + " «" + fila[2] + "» param="
                            + r.param + " (se esperaba " + fila[1] + ")");
                        fallos++;
                    }
                }
            }
            System.out.println(donde + ": " + comprobadas + " frases comprobadas, fallos " + fallos);
            comprobadas = 0;
        }

        // Y las frases nuevas que SÍ se transforman: se comprueba el destino concreto.
        Context ctx = new Context();
        ctx.assets = new AssetManager(new File("/tmp/cort-mente/assets"));
        Cerebro cerebro = new Cerebro(ctx, new Nube(ctx));
        String[][] destinos = {
            {"abre whatsapp", "abrir", "whatsapp"},
            {"abre la camara", "abrir", "camara"},
            {"abre el navegador", "abrir", "navegador"},
            {"abre mis archivos", "abrir", "archivos"},
            {"abre el gestor de carpetas", "abrir", "archivos"},
            {"abre mis fotos", "abrir", "fotos"},
            {"abre los ajustes", "abrir", "ajustes"},
            {"abre el reloj", "abrir", "reloj"},
            {"abre la wifi", "abrir", "wifi"},
            {"abre telegram", "abrir", "telegram"},
            {"abre el calendario", "abrir", "calendario"},
            {"ve a instagram", "abrir", "instagram"},
            {"lanza tiktok", "abrir", "tiktok"},
            {"prende google maps", "abrir", "maps"},
            {"pon una alarma a las 7:30", "alarma", "07:30"},
            {"despiertame a las 8", "alarma", "8"},
            {"temporizador de 10 minutos", "temporizador", "600"},
            {"avisame en 90 segundos", "temporizador", "90"},
            {"me avisas en 2 horas", "temporizador", "7200"},
        };
        for (String[] f : destinos) {
            Cerebro.Resultado r = cerebro.procesar(f[0]);
            boolean vale = f[1].equals(r.accion) && f[2].equals(r.param);
            System.out.println((vale ? "  ok  " : "  MAL ") + f[0] + " → " + r.accion + "|" + r.param
                + (vale ? "" : "  (se esperaba " + f[1] + "|" + f[2] + ")"));
            if (!vale) fallos++;
        }

        System.out.println(fallos == 0 ? "TABLA OK" : "TABLA CON " + fallos + " FALLOS");
        System.exit(fallos == 0 ? 0 : 1);
    }

    /** Lee el `habilidades.json` del repo y saca (accion, param, frase) de cada patrón. */
    static List<String[]> frasesDesdeJson() throws Exception {
        List<String[]> fuera = new ArrayList<>();
        java.io.File f = new java.io.File("/tmp/cort-mente/assets/habilidades.json");
        byte[] crudo = java.nio.file.Files.readAllBytes(f.toPath());
        org.json.JSONObject tabla = new org.json.JSONObject(new String(crudo, "UTF-8"));
        org.json.JSONArray lista = tabla.getJSONArray("patrones");
        for (int i = 0; i < lista.length(); i++) {
            org.json.JSONObject r = lista.getJSONObject(i);
            String accion = r.getString("accion"), param = r.getString("param");
            org.json.JSONArray ps = r.getJSONArray("patrones");
            for (int j = 0; j < ps.length(); j++) {
                String p = ps.getString(j);
                fuera.add(new String[] { accion, param, p.replace("{resto}", RELLENO) });
            }
        }
        return fuera;
    }
}
