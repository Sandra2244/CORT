# -*- coding: utf-8 -*-
"""
El diccionario de CORT: las intenciones que NO mueven el aparato.

`scripts/habilidades.py` genera de aquí tres cosas y no se escribe ninguna a mano:

  · `ui/js/diccionario.js` — la cara las usa para la ayuda y el Tab.
  · `apps/apk/prueba/casos-razon.txt` — una frase por intención con lo que `Razon`
    tiene que contestar. Es la prueba que hace que una frase del diccionario no
    sea promesa: si deja de contestarse sin red, la suite se pone roja.
  · `apps/apk/prueba/casos-no-locales.txt` — una frase por intención que NO puede
    contestar el teléfono sola: ni `Cerebro` la reclama ni `Razon` la resuelve, así
    que sube al cerebro de casa o a la nube. Si un día una empieza a contestarse
    localmente con una respuesta floja, se ve aquí.

Cada entrada es `(id, capa, título, [8 frases], prueba)`:
  · capa `razon`  → se contesta en el teléfono, sin red. `prueba` = (frase, prefijo).
  · capa `casa`   → la contesta el modelo de tu portátil por Wi-Fi.
  · capa `nube`   → la contesta la nube que tengas puesta.
`prueba` es `None` en casa/nube: su prueba es la contraria, que NO se contesten
localmente (va al fichero de no-locales).

Regla de contenido: ocho formas REALES de decirlo por cada intención. Nada de
variaciones de relleno para llegar a un número: las 700 frases son las que una
persona diría, y la costura comprueba el recuento para que nadie lo rellene luego.
"""

RAZON = [
    # ── la hora y el calendario ────────────────────────────────────────────────
    ("hora-ahora", "razon", "la hora", [
        "qué hora es", "dime la hora", "me dices la hora", "qué horas son",
        "la hora por favor", "dime qué hora es ahora", "qué hora tienes", "tienes hora",
    ], ("qué hora es", "Son las ")),

    ("hora-sera", "razon", "la hora dentro de un rato", [
        "qué hora será dentro de 3 horas", "qué hora será en 2 horas",
        "dime la hora dentro de 5 horas", "qué hora será dentro de 1 hora",
        "qué hora será dentro de 4 horas", "qué hora será en 6 horas",
        "dime qué hora será dentro de 2 horas", "qué hora será dentro de 8 horas",
    ], ("qué hora será dentro de 3 horas", "Serán las ")),

    ("hora-era", "razon", "la hora de antes", [
        "qué hora era hace 2 horas", "qué hora fue hace 3 horas",
        "dime la hora de hace 1 hora", "qué hora era hace 4 horas",
        "qué hora era hace 30 minutos", "qué hora fue hace 20 minutos",
        "dime qué hora era hace 5 horas", "qué hora era hace 10 minutos",
    ], ("qué hora era hace 2 horas", "Eran las ")),

    ("fecha-hoy", "razon", "la fecha de hoy", [
        "qué día es hoy", "qué fecha es hoy", "a qué día estamos", "dime la fecha",
        "qué día estamos", "fecha de hoy", "en qué día vivimos", "qué fecha tenemos",
    ], ("qué día es hoy", "Hoy es ")),

    ("dia-semana", "razon", "el día de la semana", [
        "qué día de la semana es", "qué día de la semana es hoy",
        "en qué día de la semana estamos", "dime el día de la semana",
        "qué día de la semana cae hoy", "hoy qué día de la semana es",
        "qué jornada es hoy", "día de la semana por favor",
    ], ("qué día de la semana es", "Hoy es ")),

    ("falta-fiesta", "razon", "cuánto falta para una fiesta", [
        "cuántos días faltan para navidad", "cuánto falta para navidad",
        "cuántos días faltan para los reyes", "cuánto falta para año nuevo",
        "cuántos días faltan para san valentín", "cuánto falta para el día del trabajo",
        "cuántos días quedan para navidad", "falta mucho para navidad",
    ], ("cuántos días faltan para navidad", "Falta")),

    ("falta-fecha", "razon", "cuánto falta para una fecha", [
        "cuántos días faltan para el 25 de diciembre", "cuánto falta para el 1 de enero",
        "cuántos días quedan para el 14 de febrero", "cuánto falta para el 12 de octubre",
        "cuántos días faltan para el 16 de septiembre", "cuánto falta para el 6 de enero",
        "cuántos días faltan para el 1 de mayo", "cuánto falta para el 2 de noviembre",
    ], ("cuántos días faltan para el 25 de diciembre", "Falta")),

    ("era-fecha", "razon", "la fecha de antes", [
        "qué día era hace 3 días", "qué fecha era hace 2 semanas",
        "qué día era hace 1 mes", "qué fecha era hace 10 días",
        "qué día era hace 4 semanas", "qué fecha era hace 6 meses",
        "qué día era hace 100 días", "qué fecha era hace 1 año",
    ], ("qué día era hace 3 días", "Era ")),

    ("sera-fecha", "razon", "la fecha de dentro de un rato", [
        "qué fecha será dentro de 2 semanas", "qué día será dentro de 3 días",
        "qué fecha será dentro de 1 mes", "qué día será dentro de 10 días",
        "qué fecha será dentro de 4 semanas", "qué día será dentro de 6 meses",
        "qué fecha será dentro de 2 días", "qué día será dentro de 1 semana",
    ], ("qué fecha será dentro de 2 semanas", "Será ")),

    ("bisiesto", "razon", "si un año es bisiesto", [
        "2024 es bisiesto", "es bisiesto 2024", "el año 2024 es bisiesto",
        "2023 es bisiesto", "dime si 2028 es bisiesto", "es bisiesto el año 2000",
        "el 2100 es bisiesto", "comprueba si 1996 es bisiesto",
    ], ("2024 es bisiesto", "2024 es")),

    ("dias-anio", "razon", "los días de un año", [
        "cuántos días tiene 2028", "cuántos días tiene el año 2024",
        "cuántos días tiene 2023", "dime los días que tiene 2026",
        "cuántos días tiene el año 2100", "cuántos días tiene 2000",
        "cuántos días tiene 1999", "cuántos días tiene el año 2032",
    ], ("cuántos días tiene 2028", "El año 2028")),

    # ── las cuentas ────────────────────────────────────────────────────────────
    ("cuenta-operacion", "razon", "una cuenta con signos", [
        "cuánto es 17 por 3", "cuánto es 240 entre 12", "calcula 15 más 27",
        "cuánto es 9 menos 4", "cuánto da 6 por 7", "resultado de 100 dividido entre 4",
        "suma 12 y 30", "cuánto vale 8 por 8",
    ], ("cuánto es 17 por 3", "Es 51")),

    ("cuenta-palabras", "razon", "una cuenta dicha con palabras", [
        "cuánto es dos mil más quinientos", "cuánto es trescientos por dos",
        "suma cien más cincuenta", "cuánto es mil menos doscientos",
        "cuánto da veinte por cinco", "cuánto es cuarenta y dos más ocho",
        "calcula noventa entre tres", "cuánto es setenta y cinco menos veinticinco",
    ], ("cuánto es dos mil más quinientos", "Es 2500")),

    ("cuenta-raiz", "razon", "una raíz", [
        "cuánto es la raíz de 144", "raíz cuadrada de 81", "cuánto es la raíz cuadrada de 2",
        "calcula la raíz de 169", "raíz de 25", "cuánto da la raíz cuadrada de 49",
        "dime la raíz de 9", "cuánto es raíz de 121",
    ], ("cuánto es la raíz de 144", "Es 12")),

    ("cuenta-cuadrado", "razon", "un número al cuadrado o al cubo", [
        "cuánto es 12 al cuadrado", "cuánto es 5 al cubo", "calcula 9 al cuadrado",
        "cuánto da 7 al cuadrado", "cuánto es 10 al cubo", "cuánto es 6 al cuadrado",
        "cuánto es 3 al cubo", "dime 11 al cuadrado",
    ], ("cuánto es 12 al cuadrado", "Es 144")),

    ("cuenta-x", "razon", "una multiplicación con equis", [
        "cuánto es 7 x 8", "cuánto es 9 x 9", "calcula 12 x 3", "cuánto da 6 x 7",
        "cuánto es 15 x 4", "dime cuánto es 3 x 3", "cuánto es 25 x 4", "dime 11 x 11",
    ], ("cuánto es 7 x 8", "Es 56")),

    ("porcentaje-de", "razon", "el tanto por ciento de algo", [
        "cuánto es el 15 por ciento de 240", "el 20 por ciento de 80",
        "cuánto es el 25 por ciento de 400", "calcula el 10 por ciento de 50",
        "cuánto es el 5 por ciento de 200", "el 30 por ciento de 90",
        "cuánto es el 50 por ciento de 70", "dime el 12 por ciento de 100",
    ], ("cuánto es el 15 por ciento de 240", "El 15 por ciento de 240 es 36")),

    ("porcentaje-es", "razon", "qué porcentaje es", [
        "qué porcentaje es 30 de 120", "qué porcentaje es 15 de 60",
        "cuánto porcentaje es 5 de 20", "qué porcentaje representa 40 de 200",
        "qué porcentaje es 25 de 100", "cuánto por ciento es 3 de 12",
        "qué porcentaje es 18 de 90", "qué porcentaje es 7 de 70",
    ], ("qué porcentaje es 30 de 120", "Es el 25 por ciento")),

    ("regla-tres", "razon", "la regla de tres", [
        "si 3 cuestan 9 cuánto cuestan 5", "si 2 litros son 3 euros cuánto son 7 litros",
        "si 4 kilos cuestan 12 cuánto cuestan 7 kilos",
        "si 5 obreros hacen 10 metros cuánto hacen 8 obreros",
        "si 3 días son 9 horas cuánto son 5 días",
        "si 6 lápices cuestan 18 cuánto cuestan 4 lápices",
        "si 2 horas son 120 minutos cuánto son 3 horas",
        "si 10 metros cuestan 50 cuánto cuestan 3 metros",
    ], ("si 3 cuestan 9 cuánto cuestan 5", "Son 15")),

    # ── unidades y dinero ──────────────────────────────────────────────────────
    ("conversion-unidades", "razon", "cambiar de unidad", [
        "3 km a millas", "5 metros a pies", "10 millas a kilómetros", "2 horas a minutos",
        "500 gramos a libras", "1 litro a mililitros", "30 centímetros a pulgadas",
        "4 kilos a libras",
    ], ("3 km a millas", "3 km son 1,8641 millas")),

    ("conversion-temperatura", "razon", "grados de un sistema a otro", [
        "98.6 fahrenheit a celsius", "30 grados a fahrenheit", "0 celsius a fahrenheit",
        "100 grados fahrenheit a celsius", "37 grados a fahrenheit", "25 celsius a kelvin",
        "300 kelvin a celsius", "212 fahrenheit a celsius",
    ], ("98.6 fahrenheit a celsius", "98,6 fahrenheit son 37 celsius")),

    ("conversion-datos", "razon", "megas, gigas y teras", [
        "2 gigas a megas", "1 giga a megas", "500 megas a gigas", "1024 megas a gigas",
        "1 tera a gigas", "2048 megas a gigas", "3000 megas a gigas", "0.5 gigas a megas",
    ], ("2 gigas a megas", "2 gigas son 2048 megas")),

    ("propina", "razon", "cuánta propina dejar", [
        "cuánta propina dejo por 80", "propina del 15 por ciento de 80",
        "cuánta propina dejo por 120", "propina para 60",
        "cuánta propina se deja por 100", "propina del 20 por ciento de 50",
        "cuánta propina dejo por 200", "propina del 10 por ciento de 90",
    ], ("cuánta propina dejo por 80", "Deja 8")),

    ("descuento", "razon", "cuánto queda con descuento", [
        "80 con 20 por ciento de descuento", "100 con 25 por ciento de descuento",
        "descuento del 30 por ciento a 200", "50 con 10 por ciento de descuento",
        "descuento del 15 por ciento a 80", "120 con 50 por ciento de descuento",
        "descuento del 5 por ciento a 100", "90 con 33 por ciento de descuento",
    ], ("80 con 20 por ciento de descuento", "Quedan 64")),

    ("mitad-doble", "razon", "la mitad, el doble o el triple", [
        "la mitad de 80", "el doble de 35", "el triple de 20", "la mitad de 150",
        "el doble de 48", "el triple de 7", "la mitad de 7", "el doble de 12",
    ], ("la mitad de 80", "Es 40")),

    ("promedio", "razon", "el promedio de varios números", [
        "el promedio de 4, 8 y 10", "el promedio de 10 y 20", "promedio de 2 4 y 6",
        "el promedio de 7 y 9", "promedio de 1 2 3 y 4", "el promedio de 15 y 25",
        "promedio de 100 y 200", "el promedio de 3 3 y 3",
    ], ("el promedio de 4, 8 y 10", "Es 7")),
]

CASA = [
    ("piensa", "casa", "pensar con el modelo de casa", [
        "piensa qué es la fotosíntesis", "piensa por qué está lloviendo",
        "piensa cómo se hace una paella", "piensa cuál es la capital de Australia",
        "piensa qué significa sostenible", "piensa quién fue Nikola Tesla",
        "piensa cómo funciona un reloj", "piensa qué puedo cenar hoy",
    ], None),
    ("explica", "casa", "explicar algo", [
        "explícame la gravedad", "explícame la fotosíntesis", "explícame qué es el ADN",
        "explícame cómo funciona internet", "explícame la teoría del color",
        "explícame qué es la inflación", "explícame la guerra fría",
        "explícame cómo aprende una IA",
    ], None),
    ("resume", "casa", "resumir un texto", [
        "resume este texto", "resume lo que te acabo de decir", "hazme un resumen de esto",
        "resume las ideas principales", "resume en tres frases", "resume el artículo",
        "dame un resumen corto", "resume la conversación",
    ], None),
    ("traduce", "casa", "traducir", [
        "traduce al inglés buenos días", "traduce al español good morning",
        "traduce esta frase al francés", "cómo se dice gracias en alemán",
        "traduce al inglés te quiero", "traduce al portugués hasta luego",
        "dime cómo se dice agua en italiano", "traduce al inglés buenas noches",
    ], None),
    ("escribe", "casa", "escribir un texto", [
        "escribe un correo para mi jefa", "escribe una nota de voz",
        "escribe una lista de la compra", "escribe un mensaje de cumpleaños",
        "escribe un correo formal", "escribe una invitación",
        "escribe un mensaje para disculparme", "escribe un texto corto sobre el mar",
    ], None),
    ("compara", "casa", "comparar dos cosas", [
        "compara python y javascript", "compara android y iphone",
        "compara un coche eléctrico y uno de gasolina", "compara linux y windows",
        "compara café y té", "compara dos portátiles",
        "compara el mar y la montaña", "compara cantar y bailar",
    ], None),
    ("idea", "casa", "pedir una idea", [
        "dame una idea para una cena", "dame una idea para un regalo",
        "dame ideas para el fin de semana", "dame una idea de negocio",
        "dame una idea para decorar", "dame ideas para un cumpleaños",
        "dame una idea para un juego", "dame una idea para ahorrar",
    ], None),
    ("codigo", "casa", "ayuda con código", [
        "ayúdame con código en python", "ayúdame con este error de java",
        "explícame este código", "cómo hago un bucle en python",
        "ayúdame con html y css", "revisa esta función de javascript",
        "cómo se hace una consulta en sql", "ayúdame con un script en bash",
    ], None),
    ("redacta", "casa", "redactar algo formal", [
        "redacta una carta de reclamo", "redacta un currículum corto",
        "redacta una disculpa formal", "redacta un mensaje para el banco",
        "redacta una solicitud de vacaciones", "redacta una queja por un producto",
        "redacta una respuesta educada", "redacta un anuncio corto",
    ], None),
    ("corrige", "casa", "corregir un texto", [
        "corrige esta frase", "corrige mi ortografía", "revisa este texto",
        "corrige la gramática de esto", "mejora esta redacción",
        "corrige las tildes", "revisa este correo antes de enviarlo",
        "corrige el estilo de este párrafo",
    ], None),
    ("plan", "casa", "planificar", [
        "organiza mi día", "hazme un plan para la semana", "planifica un viaje a Gijón",
        "planifica una cena para cuatro", "organiza mi estudio para el examen",
        "hazme un plan de entrenamiento", "planifica mi mudanza",
        "organiza las tareas de la casa",
    ], None),
    ("decide", "casa", "ayudar a decidir", [
        "decide entre pizza y sushi", "ayúdame a elegir un portátil",
        "qué me conviene estudiar", "decide entre playa y montaña",
        "ayúdame a elegir un regalo", "qué elijo para cenar",
        "decide entre android y iphone", "ayúdame a decidir un destino",
    ], None),
    ("ensena", "casa", "enseñar paso a paso", [
        "enséñame a programar en python", "enséñame a usar Excel",
        "enséñame inglés desde cero", "enséñame a hacer pan",
        "enséñame a cambiar una rueda", "enséñame a estudiar mejor",
        "enséñame a usar git", "enséñame a cocinar arroz",
    ], None),
]

NUBE = [
    ("noticias", "nube", "las noticias", [
        "qué noticias hay", "dime las noticias de hoy", "qué pasó en el mundo",
        "las últimas noticias", "qué noticias hay de tecnología",
        "resume las noticias de hoy", "qué ha pasado esta semana",
        "dime algo de actualidad",
    ], None),
    ("quien-es", "nube", "quién es alguien", [
        "quién es Ada Lovelace", "quién es el presidente de España",
        "quién inventó la bombilla", "quién fue Marie Curie",
        "quién es el dueño de Tesla", "quién escribió el Quijote",
        "quién descubrió América", "quién canta esa canción",
    ], None),
    ("que-es", "nube", "qué es una cosa", [
        "qué es la computación cuántica", "qué es el blockchain",
        "qué es la inteligencia artificial", "qué es un agujero negro",
        "qué es la energía solar", "qué es el cambio climático",
        "qué es una API", "qué es la realidad virtual",
    ], None),
    ("como-funciona", "nube", "cómo funciona algo", [
        "cómo funciona un motor de combustión", "cómo funciona una nevera",
        "cómo funciona el wifi", "cómo funciona un panel solar",
        "cómo funciona un microondas", "cómo funciona la gravedad",
        "cómo funciona un GPS", "cómo funciona una impresora 3D",
    ], None),
    ("historia", "nube", "historia de algo", [
        "historia de Roma", "historia de España", "historia de la imprenta",
        "historia de internet", "historia de la aviación", "historia del café",
        "historia de los aztecas", "historia de la electricidad",
    ], None),
    ("receta", "nube", "una receta", [
        "receta de tortilla de patatas", "receta de paella", "receta de arroz con pollo",
        "receta de bizcocho", "receta de gazpacho", "receta de pasta carbonara",
        "receta de lentejas", "receta de tarta de queso",
    ], None),
    ("chiste", "nube", "un chiste", [
        "cuéntame un chiste", "dime algo gracioso", "sabes un chiste",
        "cuéntame otro chiste", "hazme reír", "dime un chiste corto",
        "cuéntame un chiste de programadores", "tienes algún chiste",
    ], None),
    ("poema", "nube", "un poema", [
        "escríbeme un poema corto", "recítame un poema", "hazme un poema de amor",
        "escribe un poema sobre el mar", "dime un verso", "inventa un poema",
        "escríbeme una poesía", "hazme una rima",
    ], None),
    ("opinion", "nube", "una opinión", [
        "qué opinas de la inteligencia artificial", "qué piensas de las redes sociales",
        "qué opinas de los coches eléctricos", "qué te parece el veganismo",
        "qué opinas de trabajar desde casa", "qué piensas del espacio",
        "qué opinas de la música actual", "qué te parece aprender idiomas",
    ], None),
    ("recomendacion", "nube", "una recomendación", [
        "recomiéndame una película", "recomiéndame un libro", "recomiéndame una serie",
        "recomiéndame música", "recomiéndame un restaurante", "recomiéndame un juego",
        "recomiéndame un destino", "recomiéndame un curso",
    ], None),
    ("averigua", "nube", "averiguar un dato", [
        "averigua en la red el precio del bitcoin", "averigua quién ganó el partido",
        "averigua el tiempo de mañana", "averigua cuánto cuesta un vuelo",
        "averigua la capital de Canadá", "averigua los resultados de la lotería",
        "averigua qué día es el examen", "averigua cuántos habitantes tiene Gijón",
    ], None),
]

SABER = RAZON + CASA + NUBE
