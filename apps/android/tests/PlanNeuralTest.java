package dev.sandra.cort.movil;

public final class PlanNeuralTest {
    private static int comprobaciones;

    public static void main(String[] args) {
        conversacion();
        planValido();
        allowlist();
        limites();
        firmaYResumen();
        System.out.println("PlanNeuralTest: " + comprobaciones + " comprobaciones");
    }

    private static void conversacion() {
        PlanNeural.Interpretacion natural = PlanNeural.interpretar("  Hola, ¿cómo estás?  ");
        verdad(natural.valida, "una respuesta natural sigue siendo válida");
        verdad("hablar".equals(natural.tipo), "la respuesta natural se clasifica como hablar");
        verdad("Hola, ¿cómo estás?".equals(natural.texto), "el texto no se inventa ni se recorta");
        verdad(natural.plan == null, "hablar no produce herramientas");

        PlanNeural.Interpretacion json = PlanNeural.interpretar(
                "{\"tipo\":\"hablar\",\"texto\":\"Mañana te ayudo con eso.\"}");
        verdad(json.valida && "hablar".equals(json.tipo), "hablar JSON válido");
        verdad("Mañana te ayudo con eso.".equals(json.texto), "texto JSON conservado");

        PlanNeural.Interpretacion invalido = PlanNeural.interpretar(
                "{\"tipo\":\"hablar\",\"texto\":\"\"}");
        falso(invalido.valida, "hablar vacío rechazado");
        falso("hablar".equals(invalido.tipo), "una salida inválida no se hace pasar por conversación");
    }

    private static void planValido() {
        PlanNeural.Interpretacion uno = PlanNeural.interpretar(
                "{\"tipo\":\"plan\",\"pasos\":[{\"accion\":\"linterna\",\"param\":\"encender\",\"resto\":\"\"}]}");
        verdad(uno.valida && uno.plan != null, "plan de linterna válido");
        verdad(uno.plan.sensible, "la linterna exige confirmación");
        verdad("linterna".equals(uno.plan.pasos.get(0).accion), "acción conservada");
        verdad("encender".equals(uno.plan.pasos.get(0).param), "parámetro conservado");

        PlanNeural.Interpretacion dos = PlanNeural.interpretar(
                "{\"tipo\":\"plan\",\"pasos\":["
                        + "{\"accion\":\"hora\"},"
                        + "{\"accion\":\"volumen\",\"param\":\"bajar\"}]}");
        verdad(dos.valida && dos.plan.pasos.size() == 2, "plan de dos pasos válido");
        verdad(dos.plan.sensible, "un efecto en cualquier paso exige confirmación");
        PlanNeural.Interpretacion informativo = PlanNeural.interpretar(
                "{\"tipo\":\"plan\",\"pasos\":[{\"accion\":\"hora\"},{\"accion\":\"fecha\"}]}");
        verdad(!informativo.plan.sensible, "un plan sólo informativo no necesita confirmación");

        PlanNeural.Interpretacion mayusculas = PlanNeural.interpretar(
                "{\"tipo\":\"plan\",\"pasos\":[{\"accion\":\" VOLUMEN \",\"param\":\" SILENCIO \"}]}");
        verdad(mayusculas.valida, "acción y parámetro se normalizan sin ejecutar texto libre");
        verdad("silencio".equals(mayusculas.plan.pasos.get(0).param), "parámetro normalizado");

        PlanNeural.Interpretacion cerca = PlanNeural.interpretar(
                "```json\n{\"tipo\":\"plan\",\"pasos\":[{\"accion\":\"fecha\"}]}\n```");
        verdad(cerca.valida && cerca.plan != null, "se acepta una cerca JSON y nada más");
    }

    private static void allowlist() {
        invalido("{\"tipo\":\"plan\",\"pasos\":[{\"accion\":\"shell\",\"resto\":\"rm -rf /\"}]}",
                "shell fuera de la allowlist");
        invalido("{\"tipo\":\"plan\",\"pasos\":[{\"accion\":\"llamar\",\"resto\":\"123\"}]}",
                "llamadas fuera del planificador neuronal");
        invalido("{\"tipo\":\"plan\",\"pasos\":[{\"accion\":\"guardar\",\"resto\":\"dato\"}]}",
                "escritura de memoria fuera del planificador neuronal");
        invalido("{\"tipo\":\"plan\",\"pasos\":[{\"accion\":\"abrir\",\"param\":\"cualquier app\"}]}",
                "apertura arbitraria rechazada");
        invalido("{\"tipo\":\"plan\",\"pasos\":[{\"accion\":\"volumen\",\"param\":\"999\"}]}",
                "volumen arbitrario rechazado");
        invalido("{\"tipo\":\"plan\",\"pasos\":[{\"accion\":\"linterna\",\"param\":\"parpadear\"}]}",
                "modo de linterna no allowlisted");
        invalido("{\"tipo\":\"plan\",\"pasos\":[{\"accion\":\"alarma\",\"resto\":\"a las 25:00\"}]}",
                "alarma inválida rechazada");
        invalido("{\"tipo\":\"plan\",\"pasos\":[{\"accion\":\"cronometro\",\"resto\":\"25 horas\"}]}",
                "temporizador fuera de rango rechazado");
        invalido("{\"tipo\":\"plan\",\"pasos\":[{\"accion\":\"hora\",\"param\":\"extra\"}]}",
                "parámetro no admitido");
        invalido("{\"tipo\":\"plan\",\"pasos\":[{\"accion\":\"buscar\"}]}",
                "búsqueda sin texto rechazada");
        invalido("{\"tipo\":\"plan\",\"pasos\":[{\"accion\":\"saber\",\"param\":\"otro\"}]}",
                "parámetro de memoria desconocido");
        invalido("{\"tipo\":\"plan\",\"pasos\":[{\"accion\":\"linterna\",\"param\":7}]}",
                "parámetro no textual rechazado");
        invalido("{\"tipo\":\"plan\",\"pasos\":[{\"accion\":\"linterna\",\"param\":\"encender\",\"shell\":\"x\"}]}",
                "clave desconocida rechazada");
        invalido("{\"tipo\":\"plan\",\"pasos\":[{\"accion\":\"linterna\",\"param\":\"encender\"}],\"texto\":\"x\"}",
                "esquema de plan estricto");
        invalido("{\"tipo\":\"ejecutar\",\"pasos\":[]}", "tipo desconocido rechazado");
    }

    private static void limites() {
        invalido("{\"tipo\":\"plan\",\"pasos\":[]}", "plan vacío rechazado");
        String cinco = "{\"tipo\":\"plan\",\"pasos\":["
                + "{\"accion\":\"hora\"},{\"accion\":\"fecha\"},{\"accion\":\"listar\"},"
                + "{\"accion\":\"hora\"},{\"accion\":\"fecha\"}]}";
        invalido(cinco, "como máximo cuatro pasos");
        invalido("{\"tipo\":\"plan\",\"pasos\":[}", "JSON incompleto");
        invalido("{\"tipo\":\"plan\",\"pasos\":[{\"accion\":\"hora\"}]} basura",
                "basura trailing rechazada");
        invalido("[{\"accion\":\"linterna\"}]", "la raíz debe ser un objeto");
        invalido("```javascript\n{\"tipo\":\"plan\",\"pasos\":[{\"accion\":\"hora\"}]}\n```",
                "sólo se acepta cerca json");
        invalido("{\"tipo\":\"hablar\",\"texto\":\"" + repetir('a', 1201) + "\"}",
                "respuesta textual acotada");
        invalido(repetir('a', 4001), "salida total acotada");
        invalido("{\"tipo\":\"hablar\",\"texto\":\"antes\\u0000después\"}",
                "carácter de control rechazado");
        PlanNeural.Interpretacion nulo = PlanNeural.interpretar(null);
        falso(nulo.valida, "salida nula rechazada");
    }

    private static void firmaYResumen() {
        PlanNeural.Plan a = PlanNeural.interpretar(
                "{\"tipo\":\"plan\",\"pasos\":[{\"accion\":\"linterna\",\"param\":\"encender\"}]}").plan;
        PlanNeural.Plan b = PlanNeural.interpretar(
                "{\"tipo\":\"plan\",\"pasos\":[{\"accion\":\"linterna\",\"param\":\"encender\"}]}").plan;
        PlanNeural.Plan c = PlanNeural.interpretar(
                "{\"tipo\":\"plan\",\"pasos\":[{\"accion\":\"linterna\",\"param\":\"apagar\"}]}").plan;
        verdad(a.firma().equals(b.firma()), "el mismo plan tiene la misma firma");
        falso(a.firma().equals(c.firma()), "cambiar un argumento cambia la firma");
        verdad(a.resumen().contains("linterna") && a.resumen().contains("encender"),
                "la confirmación muestra la acción y el argumento exactos");
        String sistema = PlanNeural.sistema("carácter base");
        verdad(sistema.startsWith("carácter base"), "la personalidad se conserva");
        verdad(sistema.contains("\"tipo\":\"plan\"") && sistema.contains("shell"),
                "el prompt fija el esquema y prohíbe shell");
    }

    private static void invalido(String salida, String motivo) {
        PlanNeural.Interpretacion r = PlanNeural.interpretar(salida);
        falso(r.valida, motivo);
        falso(r.plan != null, motivo + ": no se entrega plan ejecutable");
    }

    private static String repetir(char c, int n) {
        StringBuilder s = new StringBuilder(n);
        for (int i = 0; i < n; i++) s.append(c);
        return s.toString();
    }

    private static void verdad(boolean valor, String nombre) {
        comprobaciones++;
        if (!valor) throw new AssertionError(nombre);
    }

    private static void falso(boolean valor, String nombre) {
        comprobaciones++;
        if (valor) throw new AssertionError(nombre);
    }
}
