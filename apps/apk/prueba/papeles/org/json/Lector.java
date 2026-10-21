package org.json;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/* Núcleo del sustituto de org.json: un parser pequeño y las dos clases que
   usan los ficheros del APK. Los números salen siempre Double o Long. */
public final class Lector {

    private final String s;
    private int p;

    Lector(String texto) { this.s = texto; }

    Object raiz() throws JSONException {
        espacio();
        Object v = le();
        espacio();
        return v;
    }

    private Object le() throws JSONException {
        espacio();
        if (p >= s.length()) throw new JSONException("se acabó el texto");
        char c = s.charAt(p);
        switch (c) {
            case '{': return objeto();
            case '[': return array();
            case '"': return cadena();
            case 't': case 'f': return booleano();
            case 'n': literal("null"); return null;
            default:  return numero();
        }
    }

    private Map<String, Object> objeto() throws JSONException {
        Map<String, Object> out = new LinkedHashMap<>();
        p++; espacio();
        if (peek() == '}') { p++; return out; }
        for (;;) {
            espacio();
            String k = cadena();
            espacio();
            if (s.charAt(p++) != ':') throw new JSONException("esperaba :");
            out.put(k, le());
            espacio();
            char d = s.charAt(p++);
            if (d == '}') return out;
            if (d != ',') throw new JSONException("esperaba , o }");
        }
    }

    private List<Object> array() throws JSONException {
        List<Object> out = new ArrayList<>();
        p++; espacio();
        if (peek() == ']') { p++; return out; }
        for (;;) {
            out.add(le());
            espacio();
            char d = s.charAt(p++);
            if (d == ']') return out;
            if (d != ',') throw new JSONException("esperaba , o ]");
        }
    }

    private String cadena() throws JSONException {
        if (s.charAt(p) != '"') throw new JSONException("esperaba comilla");
        p++;
        StringBuilder b = new StringBuilder();
        while (p < s.length()) {
            char c = s.charAt(p++);
            if (c == '"') return b.toString();
            if (c != '\\') { b.append(c); continue; }
            char e = s.charAt(p++);
            switch (e) {
                case 'n': b.append('\n'); break;
                case 't': b.append('\t'); break;
                case 'r': b.append('\r'); break;
                case 'b': b.append('\b'); break;
                case 'f': b.append('\f'); break;
                case '/': b.append('/');  break;
                case '"': b.append('"');  break;
                case '\\': b.append('\\'); break;
                case 'u': b.append((char) Integer.parseInt(s.substring(p, p + 4), 16)); p += 4; break;
                default: throw new JSONException("escape raro " + e);
            }
        }
        throw new JSONException("cadena sin cerrar");
    }

    private Object numero() throws JSONException {
        int desde = p;
        if (peek() == '-' || peek() == '+') p++;
        while (p < s.length() && "0123456789.eE+-".indexOf(s.charAt(p)) >= 0) p++;
        String n = s.substring(desde, p).trim();
        if (n.isEmpty()) throw new JSONException("número vacío en " + desde);
        if (n.indexOf('.') >= 0 || n.indexOf('e') >= 0 || n.indexOf('E') >= 0) return Double.valueOf(n);
        return Long.valueOf(n);
    }

    private Object booleano() throws JSONException {
        if (peek() == 't') { literal("true");  return Boolean.TRUE; }
        literal("false"); return Boolean.FALSE;
    }

    private void literal(String q) throws JSONException {
        if (!s.startsWith(q, p)) throw new JSONException("esperaba " + q);
        p += q.length();
    }

    private char peek() throws JSONException {
        if (p >= s.length()) throw new JSONException("se acabó el texto");
        return s.charAt(p);
    }

    private void espacio() { while (p < s.length() && Character.isWhitespace(s.charAt(p))) p++; }
}
