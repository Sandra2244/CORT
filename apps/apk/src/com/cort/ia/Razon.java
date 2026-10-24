package com.cort.ia;

/*
 * La razón del teléfono: porcentajes, matemáticas, unidades y calendario resueltos
 * AQUÍ, sin nube, sin coste y sin red. Existe porque el oído de `Cerebro` empareja
 * frases y `Nube` pregunta a un modelo, y entre las dos no había nadie que supiera
 * cuánto es 17 por 3 — de lo más frecuente que se le pregunta a un asistente.
 *
 * Es la segunda red de seguridad de `Mente.preguntar`:
 *   1) `Cerebro` casa la frase  →  acción conocida (volumen, linterna, alarma…).
 *   2) **`Razon` sabe responderla**  →  respuesta local, sin red.  ← esta clase
 *   3) `Nube` configurada y con red  →  el modelo.
 *   4) nada de lo anterior  →  la honestidad de `sinCerebro`.
 * Así «cuánto es 240 entre 12» contesta en el avión, y «explícame la fotosíntesis»
 * sigue pidiendo la nube en vez de inventarse una respuesta con cuatro reglas.
 *
 * Reglas de esta clase:
 * · **Pura**: ni `Context`, ni permisos, ni archivos. Se puede probar sin teléfono.
 * · **Devuelve `null` cuando no es suyo.** Un `null` manda la frase a la nube; un
 *   texto mal sacado se queda para siempre como «la respuesta de CORT». Por eso
 *   cada detector exige su propia firma (dígitos y operador, unidad reconocida,
 *   palabra de calendario) en vez de intentarlo con todo.
 * · **Nadie se traga una cuenta a medias**: el parser avisa si sobran palabras
 *   (`sobra()`), porque «15 * 100 de 240» daría un número y sería mentira.
 * · Sólo API pública del SDK 34 y Java 11: `java.time` (pide 26, y este APK arranca
 *   en 26), `HashMap`, `java.util.regex`. Nada de `Map.of` (en un teléfono llega con
 *   API 30) ni `String.repeat`.
 */

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class Razon {

    private Razon() { }

    /** La respuesta en español, o `null` si esto no es de cuentas ni de calendario. */
    public static String intenta(String frase) {
        String dicho = parejo(frase);
        if (dicho.isEmpty()) return null;
        try {
            // El orden es una escalera de firmas: cada detector exige algo que el
            // anterior no mira. Propina y descuento van antes del porcentaje porque
            // LLEVAN un porcentaje dentro y, si no, el genérico se los come y
            // contesta «el 20 por ciento de 80 es 16» cuando ella preguntó cuánto
            // queda después del descuento. Mitad/doble y promedio tampoco tienen
            // operador, así que no los ve `calculo`.
            String s = propina(dicho);
            if (s != null) return s;
            s = descuento(dicho);
            if (s != null) return s;
            s = mitadDoble(dicho);
            if (s != null) return s;
            s = promedio(dicho);
            if (s != null) return s;
            // El porcentaje va antes de las cuentas: su firma («… por ciento de …»)
            // es también una corrida de palabras-número, y si la toma `calculo`
            // sale «15 * 100» con un número en la boca que no es lo que preguntó.
            s = porcentaje(dicho);
            if (s != null) return s;
            s = reglaDeTres(dicho);
            if (s != null) return s;
            s = calculo(dicho);
            if (s != null) return s;
            s = unidades(dicho);
            if (s != null) return s;
            return calendario(dicho);
        } catch (Exception cualquierCosa) {
            // Nunca se lanza: una respuesta que no salió es un `null`, y el `null`
            // manda la frase a la nube, que sí puede intentarla.
            return null;
        }
    }

    /**
     * Minúsculas, sin tildes, sin signos de exclamación e interrogación, un solo
     * espacio. **No es** `Cerebro.normaliza`, y es a propósito: esa función convierte
     * el punto y la coma en espacios (para emparejar frases habladas), y aquí un
     * `2,5` o un `1.000` que pierda su separador deja de ser un número. Los
     * paréntesis tampoco se borran: `(5+3)*2` sin ellos se convierte en `5+3*2`, que
     * es otra cuenta y da otro resultado — medido, no supuesto.
     */
    static String parejo(String texto) {
        if (texto == null) return "";
        String bajo = java.text.Normalizer.normalize(texto, java.text.Normalizer.Form.NFD)
            .replaceAll("\\p{Mn}+", "").toLowerCase(Locale.ROOT);
        bajo = bajo.replaceAll("[¿?¡!;:\"“”']", " ");
        return bajo.replaceAll("\\s+", " ").trim();
    }

    /* ══════════════════════════ porcentajes ══════════════════════════ */

    private static final Pattern PCT = Pattern.compile(
        "(\\d+(?:[.,]\\d+)?)\\s*(?:por ciento|porciento|pct|%)\\s*(?:de|del|sobre)?\\s*"
        + "(\\d+(?:[.,]\\d+)?)");

    private static final Pattern PCT_BASE = Pattern.compile(
        "(\\d+(?:[.,]\\d+)?)\\s+(?:por ciento|%)\\s*(?:de|del|sobre)\\s+(\\d+(?:[.,]\\d+)?)");

    private static final Pattern PCT_ES = Pattern.compile(
        "(?:que|cuanto) (?:por ciento|porcentaje) (?:es|de|representa|son|supone) "
        + "(\\d+(?:[.,]\\d+)?) (?:de|sobre) (\\d+(?:[.,]\\d+)?)");

    /** «cuánto es el 15 por ciento de 240», «qué porcentaje es 30 de 120». */
    static String porcentaje(String dicho) {
        // Ojo con el `if (!m.find())` seguido de otro `if (!m.find())` sobre el MISMO
        // buscador: el segundo `find()` avanza al siguiente match, casi siempre no lo
        // hay, y la frase se cae a `null` aunque el primero sí hubiera casado. Es el
        // fallo que midió la prueba local: «el 15 por ciento de 240» sin respuesta.
        // Se guarda el `find()` en una variable y se consulta una sola vez.
        Matcher m = PCT.matcher(dicho);
        boolean casado = m.find();
        if (!casado) {
            m = PCT_BASE.matcher(dicho);
            casado = m.find();
        }
        if (!casado) {
            Matcher q = PCT_ES.matcher(dicho);
            if (!q.find()) return null;
            double a = num(q.group(1)), b = num(q.group(2));
            if (Double.isNaN(a) || Double.isNaN(b) || b == 0) return null;
            return "Es el " + bonito(a / b * 100.0) + " por ciento.";
        }
        double a = num(m.group(1)), b = num(m.group(2));
        if (Double.isNaN(a) || Double.isNaN(b)) return null;
        return "El " + bonito(a) + " por ciento de " + bonito(b) + " es "
             + bonito(a / 100.0 * b) + ".";
    }

    private static double num(String s) {
        try { return Double.parseDouble(s.replace(',', '.')); }
        catch (Exception noEsNumero) { return Double.NaN; }
    }

    /* ══════════════════════════ propina y descuento ══════════════════════════ */

    private static final Pattern PROPINA_PCT = Pattern.compile(
        "propina.*?(\\d+(?:[.,]\\d+)?)\\s*(?:por ciento|porciento|%|pct)"
        + ".*?(?:de|para|por|sobre)\\s*(\\d+(?:[.,]\\d+)?)");

    private static final Pattern PROPINA_BASE = Pattern.compile(
        "propina.*?(?:de|para|por|sobre)\\s*(\\d+(?:[.,]\\d+)?)");

    private static final Pattern DESCUENTO = Pattern.compile(
        "(\\d+(?:[.,]\\d+)?)\\s*(?:euros|pesos|dolares|\\$)?\\s*"
        + "(?:con|menos|y)\\s*(?:el\\s*)?(\\d+(?:[.,]\\d+)?)\\s*"
        + "(?:por ciento|porciento|%|pct)\\s*(?:de\\s*)?(?:descuento|rebaja)");

    private static final Pattern DESCUENTO_AL_REVES = Pattern.compile(
        "(?:descuento|rebaja).*?(\\d+(?:[.,]\\d+)?)\\s*(?:por ciento|porciento|%|pct)"
        + ".*?(?:a|de|sobre)\\s*(\\d+(?:[.,]\\d+)?)");

    private static final Pattern MITAD = Pattern.compile(
        "\\b(mitad|doble|triple)\\s+de\\s+(\\d+(?:[.,]\\d+)?)");

    private static final Pattern PROMEDIO = Pattern.compile(
        "(?:el |la )?promedio de (.+)");

    private static final Pattern NUMERO = Pattern.compile("\\d+(?:[.,]\\d+)?");

    /** «cuánta propina dejo por 80», «propina del 15 por ciento de 80». */
    static String propina(String dicho) {
        if (!dicho.contains("propina")) return null;
        Matcher m = PROPINA_PCT.matcher(dicho);
        double pct = 10, base;
        if (m.find()) {
            pct = num(m.group(1));
            base = num(m.group(2));
        } else {
            m = PROPINA_BASE.matcher(dicho);
            if (!m.find()) return null;
            base = num(m.group(1));
        }
        if (Double.isNaN(pct) || Double.isNaN(base)) return null;
        return "Deja " + bonito(base * pct / 100.0) + " de propina.";
    }

    /** «80 con 20 por ciento de descuento» → lo que se paga, no lo que se rebaja. */
    static String descuento(String dicho) {
        if (!dicho.contains("descuento") && !dicho.contains("rebaja")) return null;
        Matcher m = DESCUENTO.matcher(dicho);
        boolean alReves = false;
        if (!m.find()) {
            m = DESCUENTO_AL_REVES.matcher(dicho);
            if (!m.find()) return null;
            alReves = true;
        }
        double a = num(m.group(1)), b = num(m.group(2));
        if (Double.isNaN(a) || Double.isNaN(b)) return null;
        // En «80 con 20 %» el primero es el precio; en «descuento del 20 % a 80»
        // el primero es el tanto. Confundirlos devuelve un precio que no existe.
        double precio = alReves ? b : a, pct = alReves ? a : b;
        return "Quedan " + bonito(precio * (100.0 - pct) / 100.0) + ".";
    }

    /** «la mitad de 80», «el doble de 35», «el triple de 20». */
    static String mitadDoble(String dicho) {
        Matcher m = MITAD.matcher(dicho);
        if (!m.find()) return null;
        double n = num(m.group(2));
        if (Double.isNaN(n)) return null;
        double r = "mitad".equals(m.group(1)) ? n / 2.0
                 : "doble".equals(m.group(1)) ? n * 2.0 : n * 3.0;
        return "Es " + bonito(r) + ".";
    }

    /** «el promedio de 4, 8 y 10» → 7,3333. Exige dos números o no es un promedio. */
    static String promedio(String dicho) {
        Matcher m = PROMEDIO.matcher(dicho);
        if (!m.find()) return null;
        Matcher n = NUMERO.matcher(m.group(1));
        double suma = 0;
        int cuantos = 0;
        while (n.find()) {
            double v = num(n.group());
            if (Double.isNaN(v)) continue;
            suma += v;
            cuantos++;
        }
        if (cuantos < 2) return null;
        return "Es " + bonito(suma / cuantos) + ".";
    }

    /**
     * «si 3 cuestan 9, cuánto cuestan 5» → 15.
     *
     * Es la regla de tres de la vida: el primer número es la referencia, el segundo
     * lo que vale esa referencia y el tercero lo que se quiere saber. Se exige la
     * palabra `si` al principio y `cuanto` en medio, y EXACTAMENTE tres números:
     * con cuatro no se sabe cuál sobra, y adivinar es inventar.
     */
    static String reglaDeTres(String dicho) {
        if (!dicho.startsWith("si ") || !dicho.contains("cuanto")) return null;
        Matcher n = NUMERO.matcher(dicho);
        double[] v = new double[4];
        int cuantos = 0;
        while (n.find()) {
            if (cuantos >= 4) return null;
            v[cuantos++] = num(n.group());
        }
        if (cuantos != 3 || v[0] == 0) return null;
        return "Son " + bonito(v[1] * v[2] / v[0]) + ".";
    }

    /* ══════════════════════════ matemáticas ══════════════════════════ */

    private static final Pattern FIRMA_MATH = Pattern.compile("\\d.*[+*/^%-]|[+*/^%-].*\\d");

    /** «cuánto es 17 por 3», «raíz de 144», «dos mil más quinientos». */
    static String calculo(String dicho) {
        boolean pideCuenta = dicho.contains("cuanto es") || dicho.contains("cuanto vale")
            || dicho.contains("cuanto da") || dicho.contains("calcula")
            || dicho.contains("resultado de") || dicho.contains("suma de")
            || dicho.contains("producto de") || dicho.startsWith("suma ")
            || dicho.startsWith("resta ");
        // La firma de una cuenta: un operador CON un número al lado. `FIRMA_MATH` sólo
        // ve operadores escritos con signos, y «raíz de 144», «12 al cuadrado» o
        // «dos mil más quinientos» no tienen ni uno: se miden por su palabra. Medido
        // con la prueba local: sin esta segunda firma los cinco casos se iban a la
        // nube callados.
        boolean tieneOperador = FIRMA_MATH.matcher(dicho).find()
            || dicho.contains(" mas ") || dicho.contains(" menos ") || dicho.contains(" por ")
            || dicho.contains(" entre ") || dicho.contains(" veces ")
            || dicho.contains("dividido") || dicho.contains("al cuadrado")
            || dicho.contains("al cubo") || dicho.contains("raiz")
            // «dime 11 x 11»: la equis no está en `FIRMA_MATH` porque suelta sería una
            // letra, y aquí sólo cuenta pegada a dos números (`equis()` hace el resto).
            || Pattern.compile("\\d\\s*[x×]\\s*\\d").matcher(dicho).find();
        boolean tieneNumero = dicho.matches(".*\\d.*") || tienePalabraNumero(dicho);
        if (!pideCuenta && !(tieneOperador && tieneNumero)) return null;
        String s = sinRelleno(dicho);
        s = raiz(s);
        s = potencias(s);
        s = palabrasANumeros(s);
        s = sumaDicha(s);
        s = operadoresEnPalabras(s);
        s = equis(s);
        if (!s.matches(".*\\d.*")) return null;
        Parser p = new Parser(s);
        double r = p.suma();
        if (!p.ok || p.sobra()) return null;
        return "Es " + bonito(r) + ".";
    }

    /** ¿Hay al menos una palabra-número suelta? Para no mirar cada cuenta dos veces. */
    private static boolean tienePalabraNumero(String s) {
        for (String palabra : s.split(" ")) {
            if (PALABRA_NUM.containsKey(palabra) || "mil".equals(palabra)
                    || "millon".equals(palabra) || "millones".equals(palabra)) return true;
        }
        return false;
    }

    /** Quita el hablar que rodea la cuenta: «a ver», «por favor», «oye CORT». */
    private static String sinRelleno(String s) {
        // El `(?:…)+` es la mitad del arreglo: «dime cuánto es 3 x 3» lleva DOS
        // muletillas seguidas («dime» y «cuánto es»), y con una sola pasada se
        // quedaba «cuanto es 3 * 3» delante del parser, que no sabe leer palabras.
        return s.replaceAll("^(?:(?:cuanto (?:es|vale|da)|calcula(?:r|me)?|resultado de"
                 + "|hazme el favor de|a ver|oye cort|cort|dime|por favor)\\s*)+", " ")
                .replaceAll("\\s+", " ").trim();
    }

    /** «raíz de 144», «la raíz cuadrada de 2» → `sqrt 144`, `sqrt 2`. */
    private static String raiz(String s) {
        return s.replaceAll("(la |el )?raiz (cuadrada |cubica )?de?\\s*", "sqrt ");
    }

    /** «12 al cuadrado», «5 al cubo» → `12 ^ 2`, `5 ^ 3`. */
    private static String potencias(String s) {
        return s.replaceAll("al cuadrado", "^ 2").replaceAll("al cubo", "^ 3")
                .replaceAll("\\^\\s*$", "");
    }

    /** «7 x 8», «7×8» → `7 * 8`: la equis que se escribe en el móvil, no una letra. */
    static String equis(String s) {
        return s.replaceAll("(?<=\\d)\\s*[x×]\\s*(?=\\d)", "*");
    }

    /**
     * «suma 12 y 30» / «resta 9 y 4»: cuando la frase EMPIEZA por suma o resta, la
     * «y» es el operador. En cualquier otro sitio la «y» es una conjunción («4, 8 y
     * 10» no es una cuenta), y por eso sólo se toca aquí y con la orden delante.
     */
    static String sumaDicha(String s) {
        boolean resta = s.startsWith("resta ");
        if (!resta && !s.startsWith("suma ")) return s;
        String cuerpo = s.substring(resta ? 6 : 5).replaceFirst("^de ", "");
        return cuerpo.replaceAll("\\by\\b", resta ? "-" : "+");
    }

    /** Las cuentas dichas con palabras, en español. */
    private static String operadoresEnPalabras(String s) {
        String out = s;
        // El orden importa: «dividido por» lleva `por` dentro, y si se sustituye
        // primero `por` → `*` queda «dividido *», que es multiplicar.
        out = out.replaceAll("(dividido|dividida)\\s+(entre|por)", "/");
        out = out.replaceAll("(^|\\s)entre(\\s|$)", " / ");
        out = out.replaceAll("\\bmas\\b", "+");
        out = out.replaceAll("\\bmenos\\b", "-");
        out = out.replaceAll("\\b(por|veces|multiplicad[oa]|multiplica)\\b", "*");
        out = out.replaceAll("(\\s+)(es|son|igual|queda|resulta)\\s*$", " ");
        out = out.replaceAll("(?<=\\d)[.](?=\\d{3}(\\D|$))", "");   // 1.000 = mil
        out = out.replaceAll("(?<=\\d)[,](?=\\d{3}(\\D|$))", "");   // 1,000 = mil
        out = out.replace(',', '.');                               // 2,5 → 2.5
        return out.replaceAll("\\s+", " ").trim();
    }

    /* ──────────────── números dichos con palabras ──────────────── */

    private static final Map<String, Long> PALABRA_NUM = new HashMap<>();
    static {
        String[][] tabla = {
            {"cero", "0"}, {"un", "1"}, {"una", "1"}, {"uno", "1"}, {"dos", "2"},
            {"tres", "3"}, {"cuatro", "4"}, {"cinco", "5"}, {"seis", "6"}, {"siete", "7"},
            {"ocho", "8"}, {"nueve", "9"}, {"diez", "10"}, {"once", "11"}, {"doce", "12"},
            {"trece", "13"}, {"catorce", "14"}, {"quince", "15"}, {"dieciseis", "16"},
            {"diecisiete", "17"}, {"dieciocho", "18"}, {"diecinueve", "19"},
            {"veinte", "20"}, {"veintiuno", "21"}, {"veintidos", "22"}, {"veintitres", "23"},
            {"veinticuatro", "24"}, {"veinticinco", "25"}, {"veintiseis", "26"},
            {"veintisiete", "27"}, {"veintiocho", "28"}, {"veintinueve", "29"},
            {"treinta", "30"}, {"cuarenta", "40"}, {"cincuenta", "50"}, {"sesenta", "60"},
            {"setenta", "70"}, {"ochenta", "80"}, {"noventa", "90"},
            {"cien", "100"}, {"ciento", "100"}, {"doscientos", "200"}, {"trescientos", "300"},
            {"cuatrocientos", "400"}, {"quinientos", "500"}, {"seiscientos", "600"},
            {"setecientos", "700"}, {"ochocientos", "800"}, {"novecientos", "900"},
        };
        for (String[] fila : tabla) PALABRA_NUM.put(fila[0], Long.valueOf(fila[1]));
    }

    private static final long MILLON = 1_000_000L;

    /**
     * Cambia las corridas de palabras-número por su cifra: «dos mil trescientos
     * cuarenta y cinco» → `2345`. Lo que no es número se queda como estaba, así que
     * un «por» o un «mas» siguen vivos para el paso de los operadores.
     */
    static String palabrasANumeros(String s) {
        String[] partes = s.split(" ");
        StringBuilder out = new StringBuilder();
        long acumulado = 0, total = 0;
        boolean enCorrida = false;
        for (String palabra : partes) {
            Long v = PALABRA_NUM.get(palabra);
            boolean esMil = "mil".equals(palabra);
            boolean esMillon = "millon".equals(palabra) || "millones".equals(palabra);
            boolean esY = "y".equals(palabra) && enCorrida;
            if (v != null || esMil || esMillon) {
                enCorrida = true;
                if (esMillon) { total += (acumulado == 0 ? 1 : acumulado) * MILLON; acumulado = 0; }
                else if (esMil) { total += (acumulado == 0 ? 1 : acumulado) * 1000; acumulado = 0; }
                else acumulado += v.longValue();
                continue;
            }
            if (esY) continue;                          // «treinta y dos»
            if (enCorrida) {
                out.append(Long.toString(total + acumulado)).append(' ');
                total = 0; acumulado = 0; enCorrida = false;
            }
            out.append(palabra).append(' ');
        }
        if (enCorrida) out.append(Long.toString(total + acumulado));
        return out.toString().replaceAll("\\s+", " ").trim();
    }

    /**
     * El parser de toda la vida: recursión por precedencia. Reconoce número, `sqrt`,
     * paréntesis, menos unary, `^` por la derecha y `%` como «de».
     *
     * `ok` es de INSTANCIA (no estático): los métodos del puente corren en el hilo
     * del WebView y dos CORTes pensando a la vez no pueden pisarse el estado. Con
     * `sobra()` además decimos «no es mío» antes que dar un número a medias.
     */
    private static final class Parser {
        private final String txt;
        private int i;
        boolean ok = true;

        Parser(String texto) { this.txt = texto; }

        double suma() {
            double r = termino();
            while (true) {
                char c = miro();
                if (c == '+' || c == '-') {
                    i++;
                    double o = termino();
                    r = c == '+' ? r + o : r - o;
                } else return r;
            }
        }

        private double termino() {
            double r = factor();
            while (true) {
                char c = miro();
                if (c == '*' || c == '/') {
                    i++;
                    double o = factor();
                    if (c == '/') {
                        if (o == 0) { ok = false; return Double.NaN; }
                        r /= o;
                    } else r *= o;
                } else if (c == '%') {                 // «15 % 200» = el 15% de 200
                    i++;
                    r = r / 100.0 * factor();
                } else return r;
            }
        }

        private double factor() {
            if (miro() == '-') { i++; return -potencia(); }
            if (miro() == '+') i++;
            return potencia();
        }

        private double potencia() {
            double b = atomo();
            if (miro() == '^') { i++; double e = factor(); return Math.pow(b, e); }
            return b;
        }

        private double atomo() {
            char c = miro();
            if (c == '(') {
                i++;
                double r = suma();
                if (miro() == ')') i++; else ok = false;
                return r;
            }
            if (txt.startsWith("sqrt", i)) {
                i += 4;
                double r = factor();
                if (r < 0) { ok = false; return Double.NaN; }
                return Math.sqrt(r);
            }
            int desde = i;
            while (i < txt.length()
                    && (Character.isDigit(txt.charAt(i)) || txt.charAt(i) == '.')) i++;
            if (desde == i) { ok = false; return Double.NaN; }
            try { return Double.parseDouble(txt.substring(desde, i)); }
            catch (Exception numeroRoto) { ok = false; return Double.NaN; }
        }

        private char miro() {
            while (i < txt.length() && txt.charAt(i) == ' ') i++;
            return i < txt.length() ? txt.charAt(i) : '\0';
        }

        /** ¿Quedan palabras sueltas tras la cuenta? Entonces no la entendimos entera. */
        boolean sobra() {
            String resto = txt.substring(Math.min(i, txt.length())).trim()
                              .replaceAll("^(es|son|igual|que|de)\\s*$", "").trim();
            return !resto.isEmpty();
        }
    }

    /** `12.0` → `12`; decimales con cuatro cifras como mucho y coma española. */
    static String bonito(double x) {
        if (Double.isNaN(x) || Double.isInfinite(x)) return "no se puede calcular";
        if (Math.abs(x - Math.rint(x)) < 1e-9 && Math.abs(x) < 1e15) {
            return String.valueOf((long) Math.rint(x));
        }
        String s = String.format(Locale.US, "%.4f", x);
        s = s.replaceAll("0+$", "").replaceAll("\\.$", "");
        return s.replace('.', ',');
    }

    /* ══════════════════════════ unidades ══════════════════════════ */

    /** clave normalizada → `grupo|base`; y `grupo|base` → su factor a la base. */
    private static final Map<String, String> ALIAS = new HashMap<>();
    private static final Map<String, Double> FACTOR = new HashMap<>();

    static {
        // ── longitud (base: el metro) ──
        anade("long", "m", 1, "metro", "metros", "m");
        anade("long", "km", 1000, "kilometro", "kilometros", "km");
        anade("long", "cm", 0.01, "centimetro", "centimetros", "cm");
        anade("long", "mm", 0.001, "milimetro", "milimetros", "mm");
        anade("long", "dm", 0.1, "decimetro", "decimetros", "dm");
        anade("long", "um", 1e-6, "micra", "micras", "um");
        anade("long", "mi", 1609.344, "milla", "millas", "mi");
        anade("long", "nmi", 1852, "milla marina", "millas marinas", "nautica");
        anade("long", "ft", 0.3048, "pie", "pies", "ft", "feet", "foot");
        anade("long", "yd", 0.9144, "yarda", "yardas", "yd");
        anade("long", "in", 0.0254, "pulgada", "pulgadas", "in", "pulg");
        anade("long", "legua", 5556, "legua", "leguas");

        // ── masa (base: el gramo) ──
        anade("masa", "g", 1, "gramo", "gramos", "g");
        anade("masa", "kg", 1000, "kilo", "kilos", "kilogramo", "kilogramos", "kg");
        anade("masa", "mg", 0.001, "miligramo", "miligramos", "mg");
        anade("masa", "t", 1000000.0, "tonelada", "toneladas", "ton", "t");
        anade("masa", "lb", 453.59237, "libra", "libras", "lb", "lbs");
        anade("masa", "oz", 28.349523, "onza", "onzas", "oz");
        anade("masa", "arroba", 11502, "arroba", "arrobas");

        // ── volumen (base: el litro) ──
        anade("volumen", "l", 1, "litro", "litros", "l");
        anade("volumen", "ml", 0.001, "mililitro", "mililitros", "ml");
        anade("volumen", "gal", 3.7854118, "galon", "galones", "gal");
        anade("volumen", "pinta", 0.473176, "pinta", "pintas");
        anade("volumen", "taza", 0.24, "taza", "tazas", "vaso", "vasos");
        anade("volumen", "cda", 0.015, "cuchara", "cucharas", "cda");
        anade("volumen", "cdta", 0.005, "cucharadita", "cucharaditas", "cdta");

        // ── datos (base: el byte; 1024, como lo cuenta Android) ──
        anade("datos", "b", 1, "byte", "bytes");
        anade("datos", "kb", 1024, "kilobyte", "kilobytes", "kb");
        anade("datos", "mb", 1048576, "megabyte", "megabytes", "mb", "mega", "megas");
        anade("datos", "gb", 1073741824.0, "gigabyte", "gigabytes", "gb", "giga", "gigas");
        anade("datos", "tb", 1.0995116e12, "terabyte", "terabytes", "tb", "tera", "teras");

        // ── tiempo (base: el segundo) ──
        anade("tiempo", "s", 1, "segundo", "segundos", "s", "seg");
        anade("tiempo", "min", 60, "minuto", "minutos", "min");
        anade("tiempo", "h", 3600, "hora", "horas", "h");
        anade("tiempo", "dia", 86400, "dia", "dias");
        anade("tiempo", "semana", 604800, "semana", "semanas");
        anade("tiempo", "mes", 2629800, "mes", "meses");          // 30,44 días
        anade("tiempo", "ano", 31557600, "anio", "anios", "anos");

        // ── velocidad (base: km/h) ──
        anade("velocidad", "kmh", 1, "kilometro por hora", "kilometros por hora", "kmh", "km/h");
        anade("velocidad", "mh", 1.609344, "milla por hora", "millas por hora", "mh", "mph");
        anade("velocidad", "ms", 3.6, "metro por segundo", "metros por segundo", "m/s");
        anade("velocidad", "nudo", 1.852, "nudo", "nudos", "knot");

        // ── superficie (base: el m²) ──
        anade("area", "m2", 1, "metro cuadrado", "metros cuadrados", "m2");
        anade("area", "ha", 10000, "hectarea", "hectareas", "ha");
        anade("area", "acre", 4046.8564224, "acre", "acres");
        anade("area", "km2", 1000000, "kilometro cuadrado", "kilometros cuadrados", "km2");

        // ── temperatura: no es un factor, son fórmulas ──
        ALIAS.put("c", "temp|c");      ALIAS.put("gc", "temp|c");
        ALIAS.put("celsius", "temp|c"); ALIAS.put("centigrados", "temp|c");
        ALIAS.put("f", "temp|f");      ALIAS.put("fahrenheit", "temp|f");
        ALIAS.put("k", "temp|k");      ALIAS.put("kelvin", "temp|k");
        // «grados» sin más, en español, son centígrados: es lo que la dueña dice
        // cuando habla de su cuerpo o del tiempo. `grados celsius` etc. se ponen
        // explícitos porque la frase llega con la palabra delante de la unidad.
        ALIAS.put("grados", "temp|c");
        ALIAS.put("grados celsius", "temp|c");
        ALIAS.put("grados centigrados", "temp|c");
        ALIAS.put("grados fahrenheit", "temp|f");
        ALIAS.put("grados kelvin", "temp|k");
    }

    private static void anade(String grupo, String base, double factor, String... nombres) {
        for (String n : nombres) {
            String clave = parejo(n);
            if (clave.isEmpty()) continue;
            ALIAS.put(clave, grupo + "|" + base);
        }
        FACTOR.put(grupo + "|" + base, Double.valueOf(factor));
    }

    private static final Pattern NUM_U = Pattern.compile(
        "(\\d+(?:[.,]\\d+)?)\\s+([a-z ]{1,22}?)\\s+(?:a|en|pasado a|pasados a|convertido a"
        + "|convertidos a|cuanto es en|cuantos|que es en)\\s+([a-z ]{1,22})");

    private static final Pattern DE_A = Pattern.compile(
        "(\\d+(?:[.,]\\d+)?)\\s+([a-z ]{1,22})\\s+de\\s+[a-z ]*?(?:a|en)\\s+([a-z ]{1,22})");

    /** «3 km a millas», «98.6 fahrenheit a celsius», «2 horas a minutos». */
    static String unidades(String dicho) {
        String s = dicho.trim();
        Matcher m = NUM_U.matcher(s);
        boolean encontrado = m.find();
        if (!encontrado) {
            boolean pideConversion = s.contains("convierte") || s.contains("convertir")
                || s.contains("pasa a") || s.contains("pasar a") || s.contains("cuanto son")
                || s.contains("cuantos") || s.contains("cuanta");
            if (!pideConversion) return null;
            m = DE_A.matcher(s);
            if (!m.find()) return null;
        }
        String u1 = limpiaUnidad(m.group(2));
        String u2 = limpiaUnidad(m.group(3));
        String k1 = ALIAS.get(u1), k2 = ALIAS.get(u2);
        if (k1 == null || k2 == null) return null;          // no las conocemos las dos
        String g1 = grupo(k1), g2 = grupo(k2);
        if (!g1.equals(g2)) {
            return "No puedo pasar " + u1 + " a " + u2 + ": no son del mismo tipo.";
        }
        double x = num(m.group(1));
        if (Double.isNaN(x)) return null;
        double r = "temp".equals(g1)
                 ? temperatura(x, cola(k1), cola(k2))
                 : x * FACTOR.get(k1).doubleValue() / FACTOR.get(k2).doubleValue();
        boolean aproximado = "tiempo".equals(g1)
            && (u1.contains("mes") || u2.contains("mes") || u1.startsWith("ano")
                || u2.startsWith("ano"));
        return bonito(x) + " " + u1 + " son " + bonito(r) + " " + u2
             + (aproximado ? " (aproximado: los meses y los años no duran igual)" : "") + ".";
    }

    private static String limpiaUnidad(String u) {
        // Ya viene en minúsculas y sin tildes de `parejo`: sólo se caen los artículos
        // y las preposiciones que la dueña mete delante de la unidad.
        return u.replaceAll("^(el|la|los|las|un|una|de|del|a|en)\\s+", "").trim();
    }

    private static String grupo(String clave) {
        int barra = clave.indexOf('|');
        return barra < 0 ? clave : clave.substring(0, barra);
    }

    private static String cola(String clave) {
        int barra = clave.indexOf('|');
        return barra < 0 ? clave : clave.substring(barra + 1);
    }

    private static double temperatura(double x, String de, String a) {
        double c = "c".equals(de) ? x : "f".equals(de) ? (x - 32) * 5 / 9
                 : "k".equals(de) ? x - 273.15 : x;
        if ("c".equals(a)) return c;
        if ("f".equals(a)) return c * 9 / 5 + 32;
        return c + 273.15;
    }

    /* ══════════════════════════ calendario ══════════════════════════ */

    private static final String[] DIAS = { "lunes", "martes", "miercoles", "jueves",
        "viernes", "sabado", "domingo" };
    private static final String[] MESES = { "enero", "febrero", "marzo", "abril", "mayo",
        "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre" };

    /** Las fiestas que la dueña nombra sin fecha: {día, mes}. */
    private static final String[] FIESTA = { "navidad", "reyes", "ano nuevo", "san valentin",
        "dia del trabajo", "dia de la independencia", "hispanidad", "todos los santos" };
    private static final int[][] FIESTA_DIA = {
        { 25, 12 }, { 6, 1 }, { 1, 1 }, { 14, 2 }, { 1, 5 }, { 16, 9 }, { 12, 10 }, { 1, 11 } };

    private static final Pattern HACE_DENTRO = Pattern.compile(
        "(dentro de|en|hace) (\\d+) ?(segundos?|minutos?|horas?|dias?|semanas?|meses?|anios?|anos?)?");

    /** «dentro de 3 horas», «en 2 horas», «hace 20 minutos»: la hora que será o la que era. */
    private static final Pattern HORA_DENTRO = Pattern.compile(
        "(dentro de|en|hace) (\\d+) ?(horas?|minutos?)");

    private static final Pattern DIA_MES = Pattern.compile(
        "(\\d{1,2})\\s+de\\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre"
        + "|octubre|noviembre|diciembre)");

    /** La hora y la fecha reales del teléfono: lo que `Cerebro` no podía prometer. */
    static String calendario(String dicho) {
        String s = dicho;
        // «averigua qué día es el examen» lleva las palabras de una fecha dentro,
        // pero no pide la fecha de hoy: pide que se lo pregunten a la nube. Sin esta
        // guarda, el genérico de abajo contestaba «Hoy es viernes…» con toda la
        // seguridad. Lo destapó `Prueba5` con las frases de casa y nube.
        if (s.startsWith("averigua ") || s.startsWith("investiga ") || s.startsWith("busca ")
                || s.startsWith("piensa ") || s.startsWith("explícame ")
                || s.startsWith("explicame ")) return null;
        // El ORDEN es la mitad del trabajo, y la prueba del diccionario lo destapó:
        // «qué fecha será dentro de 2 semanas» contiene «qué fecha», así que el
        // genérico de hoy contestaba la fecha de hoy como si el desplazamiento no
        // existiera. Primero lo que lleva cuenta, después lo que no.
        //  1) la hora con desplazamiento («dentro de/en/hace N horas|minutos»)
        //  2) la fecha con desplazamiento («hace/dentro de/en N días|semanas|…»)
        //  3) el día de la semana · 4) la hora de ahora · 5) lo que falta para una fecha
        //  6) la fecha de hoy · 7) bisiesto · 8) los días de un año
        Matcher h = HORA_DENTRO.matcher(s);
        if (h.find() && s.contains("hora")) {
            boolean atras = "hace".equals(h.group(1));
            int n = (int) num(h.group(2));
            LocalDateTime t = LocalDateTime.now();
            t = h.group(3).startsWith("hora") ? (atras ? t.minusHours(n) : t.plusHours(n))
                                             : (atras ? t.minusMinutes(n) : t.plusMinutes(n));
            return (atras ? "Eran las " : "Serán las ") + t.getHour() + ":"
                 + String.format(Locale.US, "%02d", t.getMinute()) + ".";
        }
        Matcher m = HACE_DENTRO.matcher(s);
        if (m.find() && (s.contains("que dia") || s.contains("fecha") || s.contains("era")
                          || s.contains("sera"))) {
            boolean atras = "hace".equals(m.group(1));
            int n = (int) num(m.group(2));
            String unidad = m.group(3) == null ? "dia" : m.group(3);
            LocalDate destino = suma(LocalDate.now(), n, unidad, atras);
            return (atras ? "Era " : "Será ") + nombreDe(destino) + ".";
        }
        if (s.contains("dia de la semana") || s.contains("jornada")) {
            DayOfWeek dow = LocalDate.now().getDayOfWeek();
            return "Hoy es " + DIAS[dow.getValue() - 1] + ".";
        }
        if (s.contains("que hora") || s.contains("hora es") || s.contains("que horas son")
            || s.contains("la hora") || s.contains("hora tienes") || s.contains("tienes hora")) {
            LocalDateTime ahora = LocalDateTime.now();
            return "Son las " + ahora.getHour() + ":"
                 + String.format(Locale.US, "%02d", ahora.getMinute())
                 + ", " + parteDelDia(ahora.getHour()) + ".";
        }
        // «cuánto falta para…», y sus formas de la calle: «cuántos días quedan para…»,
        // «falta mucho para…». Sin las tres, la mitad del diccionario se iba a la nube.
        boolean pideFalta = s.contains("falta") || s.contains("faltan")
            || s.contains("queda") || s.contains("quedan");
        if (pideFalta && s.contains(" para ")) {
            String r = faltanPara(s, LocalDate.now());
            if (r != null) return r;
        }
        if (s.contains("que dia es") || s.contains("dia es hoy") || s.contains("que dia estamos")
            || s.contains("dia estamos") || s.contains("dia vivimos") || s.contains("que fecha")
            || s.contains("la fecha") || s.contains("fecha de hoy")
            || s.contains("fecha tenemos")) {
            return "Hoy es " + nombreDe(LocalDate.now()) + ".";
        }
        if (s.contains("bisiesto")) {
            Matcher a = Pattern.compile("(\\d{4})").matcher(s);
            int anio = a.find() ? Integer.parseInt(a.group(1)) : LocalDate.now().getYear();
            boolean b = anio % 4 == 0 && (anio % 100 != 0 || anio % 400 == 0);
            return anio + (b ? " es" : " no es") + " bisiesto.";
        }
        if (s.contains("cuantos dias tiene") || s.contains("dias que tiene")
            || s.contains("cuantos dias faltan para terminar")) {
            Matcher a = Pattern.compile("(\\d{4})").matcher(s);
            int anio = a.find() ? Integer.parseInt(a.group(1)) : LocalDate.now().getYear();
            LocalDate inicio = LocalDate.of(anio, 1, 1);
            int dias = (int) ChronoUnit.DAYS.between(inicio, inicio.plusYears(1));
            return "El año " + anio + " tiene " + dias + " días.";
        }
        return null;
    }

    private static String parteDelDia(int hora) {
        if (hora < 12) return "de la mañana";
        if (hora < 19) return "de la tarde";
        return "de la noche";
    }

    static String nombreDe(LocalDate d) {
        DayOfWeek dow = d.getDayOfWeek();
        return DIAS[dow.getValue() - 1] + " " + d.getDayOfMonth() + " de "
             + MESES[d.getMonthValue() - 1] + " de " + d.getYear();
    }

    private static LocalDate suma(LocalDate desde, int n, String unidad, boolean atras) {
        int k = atras ? -n : n;
        if (unidad.startsWith("segundo") || unidad.startsWith("minuto")) return desde;
        if (unidad.startsWith("hora")) return desde.plusDays(k / 24);
        if (unidad.startsWith("dia")) return desde.plusDays(k);
        if (unidad.startsWith("semana")) return desde.plusWeeks(k);
        if (unidad.startsWith("mes")) return desde.plusMonths(k);
        return desde.plusYears(k);
    }

    /** «a cuánto falta para el 25 de diciembre», «…para navidad». */
    private static String faltanPara(String s, LocalDate hoy) {
        int dia = -1, mes = -1;
        Matcher m = DIA_MES.matcher(s);
        if (m.find()) {
            dia = Integer.parseInt(m.group(1));
            mes = mesDe(m.group(2));
        } else {
            for (int i = 0; i < FIESTA.length; i++) {
                if (s.contains(FIESTA[i])) { dia = FIESTA_DIA[i][0]; mes = FIESTA_DIA[i][1]; break; }
            }
        }
        if (dia < 1 || mes < 1) return null;
        LocalDate proxima = proximo(dia, mes, hoy);
        long dias = ChronoUnit.DAYS.between(hoy, proxima);
        String cae = " Cae en " + nombreDe(proxima) + ".";
        if (dias == 0) return "Es hoy." + cae;
        if (dias == 1) return "Falta un día." + cae;
        return "Faltan " + dias + " días"
             + (dias >= 7 ? " (unas " + (dias / 7) + " semanas)" : "") + "." + cae;
    }

    private static LocalDate proximo(int dia, int mes, LocalDate hoy) {
        LocalDate este = LocalDate.of(hoy.getYear(), mes, dia);
        if (este.isBefore(hoy)) este = este.plusYears(1);
        return este;
    }

    private static int mesDe(String nombre) {
        for (int i = 0; i < MESES.length; i++) if (MESES[i].equals(nombre)) return i + 1;
        return -1;
    }
}
