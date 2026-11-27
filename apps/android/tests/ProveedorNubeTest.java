package dev.sandra.cort.movil;

/** Identidad explícita del proveedor; nunca se adivina leyendo la clave. */
public final class ProveedorNubeTest {
    private static int n;

    public static void main(String[] args) {
        verdad(ProveedorNube.conocido("gemini"), "Gemini tiene protocolo propio");
        verdad(ProveedorNube.conocido("openrouter"), "OpenRouter es OpenAI compatible");
        verdad(ProveedorNube.conocido("groq"), "Groq es OpenAI compatible");
        verdad(ProveedorNube.conocido("mistral"), "Mistral es OpenAI compatible");
        verdad(ProveedorNube.conocido("deepseek"), "DeepSeek es OpenAI compatible");
        verdad(ProveedorNube.conocido("xai"), "xAI es OpenAI compatible");
        falso(ProveedorNube.conocido("desconocido"), "proveedor desconocido se rechaza");
        verdad("anthropic".equals(ProveedorNube.normalizar("ANTHROPIC")), "id normalizado");
        verdad("openai".equals(ProveedorNube.normalizar(" openai ")), "espacios normalizados");

        verdad(ProveedorNube.baseSegura("https://api.openai.com/v1"), "HTTPS público");
        verdad(ProveedorNube.baseSegura("https://openrouter.ai/api/v1/"), "barra final aceptada");
        falso(ProveedorNube.baseSegura("http://api.openai.com/v1"), "HTTP rechazado");
        falso(ProveedorNube.baseSegura("https://usuario:clave@api.openai.com/v1"), "credenciales en URL rechazadas");
        falso(ProveedorNube.baseSegura("https://api.openai.com/v1?key=secreto"), "query rechazada");
        falso(ProveedorNube.baseSegura("https://127.0.0.1:11434"), "loopback rechazado");
        falso(ProveedorNube.baseSegura("https://192.168.1.10"), "LAN rechazada");
        falso(ProveedorNube.baseSegura("https://cort.local"), "host local rechazado");
        falso(ProveedorNube.baseSegura("no es una url"), "URL inválida rechazada");

        for (String id : new String[] {"anthropic", "openai", "gemini", "openrouter",
                "groq", "mistral", "deepseek", "xai"}) {
            verdad(ProveedorNube.baseOficial(id, ProveedorNube.basePorDefecto(id)),
                    "endpoint oficial de " + id);
        }
        verdad(ProveedorNube.baseOficial(" OPENAI ", "https://api.openai.com/v1/"),
                "endpoint oficial normalizado");
        falso(ProveedorNube.baseOficial("openai", "https://api.anthropic.com"),
                "proveedor y endpoint deben corresponder");
        falso(ProveedorNube.baseOficial("openai", "https://api.openai.com/v1/proxy"),
                "ruta adicional rechazada");
        falso(ProveedorNube.baseOficial("openai", "https://openai.example/v1"),
                "endpoint ajeno rechazado");
        falso(ProveedorNube.baseOficial("openai", "https://2130706433/v1"),
                "forma decimal de loopback rechazada");
        System.out.println("resultado: " + n + "/" + n + " comprobaciones de proveedores");
    }

    private static void verdad(boolean v, String m) { n++; if (!v) throw new AssertionError(m); }
    private static void falso(boolean v, String m) { n++; if (v) throw new AssertionError(m); }
}
