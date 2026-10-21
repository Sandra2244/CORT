package com.cort.ia;

/*
 * Marcar y buscar a quién. Lo que CORT puede hacer con el teléfono de la dueña
 * sin volverla loca de susto, dicho sin adornos:
 *
 * · **Marcar sí**: «llama a Samuel» busca el número en sus contactos y abre la
 *   llamada. Con el permiso `CALL_PHONE` va directo; sin él se abre el marcador
 *   del sistema con el número escrito, que es peor un segundo y no rompe nada.
 * · **Contestar por ella NO en esta entrega**: para eso Android exige ser el
 *   «teléfono predeterminado» (`RoleManager.ROLE_CALLING` + `InCallService`), y
 *   si CORT toma ese rol, el marcador que ve la dueña pasa a ser el de CORT.
 *   Con un `InCallService` a medias se queda sin contestar llamadas normales,
 *   y eso no es un detalle: es el teléfono. Entra cuando tenga su pantalla de
 *   llamadas hecha, y mientras tanto se dice aquí en vez de fingir.
 * · **Leer SMS no**: no hay API para un asistente que no sea el mensajería
 *   predeterminada. Lo que sí se lee es lo que ya está en la barra de
 *   notificaciones (`Avisos.java`), y desde ahí se puede *responder* a un chat
 *   que tenga su botón de respuesta.
 */

import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.provider.ContactsContract;

import java.util.ArrayList;
import java.util.List;

public class Telefono {

    static class Contacto {
        String nombre, numero, letraPrimera;
    }

    static boolean puedeMarcarDirecto(Context c) {
        try {
            return c.checkSelfPermission(android.Manifest.permission.CALL_PHONE)
                    == PackageManager.PERMISSION_GRANTED;
        } catch (Exception e) {
            return false;
        }
    }

    /** Busca por nombre de pila (o entero) y devuelve hasta `n` coincidencias. */
    static List<Contacto> buscar(Context c, String quien, int n) {
        List<Contacto> salida = new ArrayList<>();
        if (quien == null || quien.trim().isEmpty()) return salida;
        try {
            if (c.checkSelfPermission(android.Manifest.permission.READ_CONTACTS)
                    != PackageManager.PERMISSION_GRANTED) return salida;
        } catch (Exception e) { return salida; }

        Uri tabla = ContactsContract.CommonDataKinds.Phone.CONTENT_URI;
        String[] columnas = {
            ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
            ContactsContract.CommonDataKinds.Phone.NUMBER,
            ContactsContract.CommonDataKinds.Phone.TYPE,
        };
        // LIKE con el nombre: «Samuel» encuentra a «Samuel Ríos». Si no viene
        // nadie, se prueba con la primera palabra, que es lo que hace una búsqueda.
        Cursor cur = null;
        try {
            String limpio = quien.trim();
            String nombre = ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME;
            cur = c.getContentResolver().query(tabla, columnas,
                    "(" + nombre + " LIKE ? OR " + nombre + " LIKE ?)",
                    new String[] { "%" + limpio + "%", "%" + primeraPalabra(limpio) + "%" },
                    nombre + " ASC");
            if (cur == null) return salida;
            int iNom = cur.getColumnIndexOrThrow(
                    ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME);
            int iNum = cur.getColumnIndexOrThrow(
                    ContactsContract.CommonDataKinds.Phone.NUMBER);
            int iTip = cur.getColumnIndexOrThrow(
                    ContactsContract.CommonDataKinds.Phone.TYPE);
            while (cur.moveToNext() && salida.size() < n) {
                Contacto k = new Contacto();
                k.nombre = cur.getString(iNom);
                k.numero = cur.getString(iNum);
                k.letraPrimera = tipo(cur.getInt(iTip));
                if (k.numero == null || k.numero.trim().isEmpty()) continue;
                salida.add(k);
            }
        } catch (Exception noHayContactosODiscoRaro) {
            /* Sin índice de contactos (un tablet, o el permiso denegado): lista vacía. */
        } finally {
            if (cur != null) try { cur.close(); } catch (Exception ignorado) { }
        }
        return salida;
    }

    private static String primeraPalabra(String s) {
        int espacio = s.indexOf(' ');
        return espacio > 0 ? s.substring(0, espacio) : s;
    }

    private static String tipo(int t) {
        switch (t) {
            case ContactsContract.CommonDataKinds.Phone.TYPE_MOBILE: return "móvil";
            case ContactsContract.CommonDataKinds.Phone.TYPE_HOME:   return "casa";
            case ContactsContract.CommonDataKinds.Phone.TYPE_WORK:   return "trabajo";
            default: return "otro";
        }
    }

    /**
     * `llamar`: con permiso, `ACTION_CALL` (marca y llama). Sin él,
     * `ACTION_DIAL` (abre el marcador con el número puesto) — que es lo que
     * Android permite a una app normal por defecto.
     */
    static String llamar(Context c, String quien) {
        List<Contacto> hallados = buscar(c, quien, 1);
        String numero;
        String nombre;
        if (hallados.isEmpty()) {
            // ¿Ya es un número? («llama al 611 22 33 44») se usa tal cual.
            numero = soloDigitosYPlus(quien);
            if (numero.length() < 3) return "{\"ok\":false,\"error\":\"no encuentro a "
                    + Reproductor.esc(quien) + " en tus contactos\"}";
            nombre = numero;
        } else {
            nombre = hallados.get(0).nombre;
            numero = hallados.get(0).numero;
        }
        Intent i = new Intent(puedeMarcarDirecto(c) ? Intent.ACTION_CALL : Intent.ACTION_DIAL);
        i.setData(Uri.parse("tel:" + numero));
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            c.startActivity(i);
            return "{\"ok\":true,\"nombre\":\"" + Reproductor.esc(nombre)
                 + "\",\"numero\":\"" + Reproductor.esc(numero)
                 + "\",\"directo\":" + puedeMarcarDirecto(c) + "}";
        } catch (Exception noPuedo) {
            return "{\"ok\":false,\"error\":\"" + Reproductor.esc(noPuedo.getMessage()) + "\"}";
        }
    }

    private static String soloDigitosYPlus(String s) {
        StringBuilder out = new StringBuilder();
        for (char ch : s.trim().toCharArray()) {
            if (Character.isDigit(ch) || ch == '+' || ch == ' ') out.append(ch);
        }
        return out.toString().trim();
    }

    /** Para que la cara pueda decir «¿a quién llamo?» con nombres de verdad. */
    static String contactosJson(Context c, String quien) {
        List<Contacto> lista = buscar(c, quien, 8);
        StringBuilder s = new StringBuilder("[");
        for (int i = 0; i < lista.size(); i++) {
            if (i > 0) s.append(',');
            Contacto k = lista.get(i);
            s.append("{\"nombre\":\"").append(Reproductor.esc(k.nombre))
             .append("\",\"numero\":\"").append(Reproductor.esc(k.numero))
             .append("\",\"tipo\":\"").append(Reproductor.esc(k.letraPrimera)).append("\"}");
        }
        return s.append(']').toString();
    }
}
