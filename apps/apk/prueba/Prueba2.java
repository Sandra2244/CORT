package com.cort.ia;

import android.content.Context;
import android.content.res.AssetManager;
import java.io.File;
import java.util.ArrayList;
import java.util.List;

/* La prueba de la RUTA: qué escalón de la mente responde cada frase.
   Se compila contra los papeles de `stub/` (Contexto, Log, org.json), no contra
   android.jar, así que prueba LOGICA, no el aparato. Lo que busca son tres cosas:
   1) `Cerebro` carga de verdad el `habilidades.json` del repo y también su tabla
      del código cuando el asset falta;
   2) la hora y la fecha las dice `Razon` con el reloj de carne, no la excusa
      antigua («mírala en la barra de estado»);
   3) una acción conocida sigue saliendo con `accion` para que la cara la mueva,
      y un `de:"local"` de `Razon` sale SIN `accion`. */
public class Prueba2 {

    static int pasadas = 0;
    static List<String> fallos = new ArrayList<>();

    static void check(String que, boolean vale, String detalle) {
        if (vale) { pasadas++; System.out.println("  ok  " + que); }
        else { fallos.add(que + " -> " + detalle); System.out.println("  MAL " + que + " :: " + detalle); }
    }

    /** Monta una mente completa con la tabla que haya en `carpetaAssets`. */
    static Mente monta(File carpetaAssets, boolean conNube, boolean conRed) {
        Context ctx = new Context();
        ctx.assets = new AssetManager(carpetaAssets);
        Nube nube = new Nube(ctx);
        if (conNube) nube.ajustar("groq", null, "llama-3.1-8b-instant", "clave-de-prueba");
        if (conRed) {
            ctx.sistema = new android.net.ConnectivityManager();
            ((android.net.ConnectivityManager) ctx.sistema).activa = new android.net.Network("wifi");
            ((android.net.ConnectivityManager) ctx.sistema).cap =
                new android.net.NetworkCapabilities().con(android.net.NetworkCapabilities.NET_CAPABILITY_INTERNET);
        }
        Cerebro cerebro = new Cerebro(ctx, nube);
        return new Mente(ctx, nube, cerebro);
    }

    /** Llama al contrato y devuelve el JSON del evento (va en el hilo del puente). */
    static String pregunta(Mente mente, String texto) {
        final List<String> recibidos = new ArrayList<>();
        mente.engancha(json -> { synchronized (recibidos) { recibidos.add(json); } });
        String dice = mente.mente("{\"que\":\"preguntar\",\"args\":{\"texto\":\""
            + texto.replace("\"", "'") + "\",\"eco\":\"prueba\"}}");
        check("menteporcontrato(" + texto + ") dice pendiente",
            dice.contains("\"pendiente\":true"), dice);
        // Las ramas locales entregan en el acto; la de nube lanza un hilo.
        for (int n = 0; n < 50 && recibidos.isEmpty(); n++) {
            try { Thread.sleep(20); } catch (InterruptedException e) { break; }
        }
        return recibidos.isEmpty() ? "{}" : recibidos.get(0);
    }

    static org.json.JSONObject json(String crudo) {
        try { return new org.json.JSONObject(crudo); } catch (Exception roto) { return null; }
    }

    /** Las reglas que trae un `Cerebro`, mirando su lista privada con reflexión. */
    static int reglasDe(Cerebro c) {
        try {
            java.lang.reflect.Field f = Cerebro.class.getDeclaredField("reglas");
            f.setAccessible(true);
            return ((List<?>) f.get(c)).size();
        } catch (Exception noDeja) {
            return -1;
        }
    }

    public static void main(String[] args) throws Exception {
        File conTabla = new File("/tmp/cort-mente/assets");          // el habilidades.json auténtico
        File sinTabla = new File("/tmp/cort-mente/assets-vacias");   // para forzar la tabla del código
        sinTabla.mkdirs();

        // ── 1 · las dos tablas cargan ────────────────────────────────
        Context ctx = new Context();
        ctx.assets = new AssetManager(conTabla);
        Nube n0 = new Nube(ctx);
        Cerebro desdeAsset = new Cerebro(ctx, n0);
        System.out.println("asset     : '" + desdeAsset.avisoDeCarga() + "' reglas=" + reglasDe(desdeAsset));
        ctx.assets = new AssetManager(sinTabla);
        Cerebro desdeCodigo = new Cerebro(ctx, n0);
        System.out.println("sin asset : '" + desdeCodigo.avisoDeCarga() + "' reglas=" + reglasDe(desdeCodigo));
        check("el asset se lee sin quejas", desdeAsset.avisoDeCarga().isEmpty(),
            desdeAsset.avisoDeCarga());
        check("el código responde cuando el asset falta",
            desdeCodigo.avisoDeCarga().contains("tabla del codigo")
                || desdeCodigo.avisoDeCarga().contains("tabla del código"),
            desdeCodigo.avisoDeCarga());
        int porAsset = reglasDe(desdeAsset), porCodigo = reglasDe(desdeCodigo);
        check("las dos tablas traen las mismas 33 reglas", porAsset == 33 && porCodigo == 33,
            "asset=" + porAsset + " codigo=" + porCodigo);
        check("el código responde sin asset",
            "volumen".equals(desdeCodigo.procesar("sube el volumen").accion),
            desdeCodigo.procesar("sube el volumen").toString());

        for (File carpeta : new File[] { conTabla, sinTabla }) {
            String donde = carpeta.equals(conTabla) ? "ASSET" : "CODIGO";
            System.out.println("\n── ruta con la tabla " + donde + " ──");
            Mente mente = monta(carpeta, false, false);

            // acción conocida: sale nombrada, con `accion` para que la cara la mueva
            org.json.JSONObject j = json(pregunta(mente, "sube el volumen"));
            check(donde + " volumen es accion local",
                j != null && "local".equals(j.optString("de")) && "volumen".equals(j.optString("accion")),
                String.valueOf(j));

            j = json(pregunta(mente, "abre spotify"));
            check(donde + " abrir spotify llega con param",
                j != null && "abrir".equals(j.optString("accion")) && "spotify".equals(j.optString("param")),
                String.valueOf(j));

            // la hora: ANTES era la excusa; ahora `Razon` con el reloj de carne
            j = json(pregunta(mente, "¿qué hora es?"));
            String hora = j == null ? "" : j.optString("responde");
            System.out.println("     hora  → " + hora);
            check(donde + " la hora la da Razon y no la excusa",
                j != null && "local".equals(j.optString("de")) && !j.has("accion")
                    && hora.matches(".*\\d{1,2}:\\d{2}.*")
                    && !hora.toLowerCase().contains("barra de estado"),
                hora);

            j = json(pregunta(mente, "qué día es hoy"));
            String fecha = j == null ? "" : j.optString("responde");
            System.out.println("     fecha → " + fecha);
            check(donde + " la fecha la da Razon",
                j != null && !j.has("accion") && fecha.matches(".*de \\d{4}.*")
                    && !fecha.toLowerCase().contains("arriba"),
                fecha);

            // cuentas, porcentaje, unidades: todo local, sin gastar red
            check(donde + " cuenta",
                "Es 51.".equals(json(pregunta(mente, "¿cuánto es 17 por 3?")).optString("responde")),
                pregunta(mente, "¿cuánto es 17 por 3?"));
            check(donde + " porcentaje",
                json(pregunta(mente, "el 15 por ciento de 240")).optString("responde").contains("36"),
                pregunta(mente, "el 15 por ciento de 240"));
            check(donde + " unidad",
                json(pregunta(mente, "3 km a millas")).optString("responde").contains("millas"),
                pregunta(mente, "3 km a millas"));

            // desconocida sin nube: la respuesta honesta, y NO la de Razon
            j = json(pregunta(mente, "explícame la fotosíntesis"));
            check(donde + " lo desconocido pide la nube",
                j != null && j.optString("responde").contains("nube"),
                String.valueOf(j));
        }

        // ── 2 · el JSON que sale es el que la cara sabe leer ─────────
        Mente mente = monta(conTabla, false, false);
        org.json.JSONObject j = json(pregunta(mente, "5 al cubo"));
        check("el evento trae eco", "prueba".equals(j.optString("eco")), j.optString("eco"));
        check("el evento dice 125", j.optString("responde").contains("125"), j.optString("responde"));

        System.out.println("\n" + pasadas + " casos; fallos=" + fallos.size());
        for (String f : fallos) System.out.println("  · " + f);
        System.exit(fallos.isEmpty() ? 0 : 1);
    }
}
