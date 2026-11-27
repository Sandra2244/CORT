package dev.sandra.cort.movil;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;

/** Proveedor y protocolo declarados por la persona, no adivinados de su secreto. */
public final class ProveedorNube {
    private static final List<String> IDS = Arrays.asList(
            "anthropic", "openai", "gemini", "openrouter", "groq", "mistral", "deepseek", "xai");

    private ProveedorNube() {
    }

    public static String[] ids() {
        return IDS.toArray(new String[0]);
    }

    public static String normalizar(String id) {
        String s = id == null ? "" : id.trim().toLowerCase(Locale.ROOT);
        return conocido(s) ? s : "";
    }

    public static boolean conocido(String id) {
        return IDS.contains(id == null ? "" : id.trim().toLowerCase(Locale.ROOT));
    }

    public static boolean antropico(String id) {
        return "anthropic".equals(normalizar(id));
    }

    public static boolean gemini(String id) {
        return "gemini".equals(normalizar(id));
    }

    public static String basePorDefecto(String id) {
        switch (normalizar(id)) {
            case "anthropic": return "https://api.anthropic.com";
            case "openai": return "https://api.openai.com/v1";
            case "gemini": return "https://generativelanguage.googleapis.com/v1beta";
            case "openrouter": return "https://openrouter.ai/api/v1";
            case "groq": return "https://api.groq.com/openai/v1";
            case "mistral": return "https://api.mistral.ai/v1";
            case "deepseek": return "https://api.deepseek.com/v1";
            case "xai": return "https://api.x.ai/v1";
            default: return "";
        }
    }

    public static boolean baseOficial(String id, String base) {
        String proveedor = normalizar(id);
        if (proveedor.isEmpty() || !baseSegura(base)) return false;
        String limpia = base.trim();
        while (limpia.endsWith("/")) limpia = limpia.substring(0, limpia.length() - 1);
        return basePorDefecto(proveedor).equals(limpia);
    }

    public static boolean baseSegura(String base) {
        if (base == null || base.trim().isEmpty()) return false;
        URI u;
        try {
            u = new URI(base.trim());
        } catch (URISyntaxException | RuntimeException invalida) {
            return false;
        }
        if (!"https".equalsIgnoreCase(u.getScheme()) || u.getHost() == null
                || u.getRawUserInfo() != null || u.getRawQuery() != null
                || u.getRawFragment() != null || (u.getPort() != -1 && u.getPort() != 443)) {
            return false;
        }
        String host = u.getHost().toLowerCase(Locale.ROOT);
        if ("localhost".equals(host) || host.endsWith(".localhost") || host.endsWith(".local")) {
            return false;
        }
        return !ipPrivada(host);
    }

    private static boolean ipPrivada(String host) {
        if (host.indexOf(':') >= 0) {
            String h = host.replace("[", "").replace("]", "");
            return "::1".equals(h) || h.startsWith("fc") || h.startsWith("fd")
                    || h.startsWith("fe8") || h.startsWith("fe9") || h.startsWith("fea")
                    || h.startsWith("feb") || h.startsWith("::ffff:");
        }
        String[] partes = host.split("\\.");
        if (partes.length != 4) return false;
        try {
            int a = Integer.parseInt(partes[0]);
            int b = Integer.parseInt(partes[1]);
            return a == 0 || a == 10 || a == 127 || (a == 169 && b == 254)
                    || (a == 172 && b >= 16 && b <= 31)
                    || (a == 192 && b == 168) || (a == 100 && b >= 64 && b <= 127)
                    || a >= 224;
        } catch (NumberFormatException noEsIp) {
            return false;
        }
    }
}
