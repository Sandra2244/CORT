"""Las herramientas del asistente: lista cerrada, argumentos validados, nada de shell.

Se prueba con un `Contexto` falso que apunta en vez de abrir: lo que se comprueba
es QUÉ se le pediría al sistema, no lo que el sistema haría (Windows no está aquí).
"""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from cort_core import herramientas as h
from cort_core.agenda import Agenda

AHORA = datetime(2026, 10, 12, 21, 30)


class Falso:
    """Un sistema operativo de mentira que anota lo que se le pide."""
    def __init__(self):
        self.abierto, self.teclas, self.recortes, self.bloqueos = [], [], 0, 0
        self.falla_abrir = None

    def abrir(self, destino):
        if self.falla_abrir:
            raise self.falla_abrir
        self.abierto.append(destino)

    def pulsar(self, tecla, veces=1):
        self.teclas.append((tecla, veces))

    def recorte(self):
        self.recortes += 1

    def bloquear(self):
        self.bloqueos += 1


class Base(unittest.TestCase):
    windows = True

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.so = Falso()
        self.ctx = h.Contexto(agenda=Agenda(Path(self.dir.name) / "agenda.json"), ahora=lambda: AHORA,
                              abrir=self.so.abrir, pulsar=self.so.pulsar, recorte=self.so.recorte,
                              bloquear=self.so.bloquear, windows=self.windows, home=Path("/casa/u"),
                              acciones=lambda: True)

    def di(self, texto):
        """Entender + ejecutar, como hace el servidor."""
        llamadas = h.entender(texto, self.ctx)
        self.assertEqual(len(llamadas), 1, llamadas)
        return h.ejecutar(llamadas[0], self.ctx)


class TestValidar(unittest.TestCase):
    def test_una_herramienta_que_no_existe_se_rechaza(self):
        for nombre in ["borrar_todo", "ejecutar", "../../x", "", None, 5, "abrir_app; rm -rf /"]:
            with self.subTest(nombre):
                llamada, motivo = h.validar({"herramienta": nombre, "args": {}})
                self.assertIsNone(llamada)
                self.assertTrue(motivo)

    def test_no_objeto(self):
        for malo in [None, "texto", 3, [], ["abrir_app"]]:
            self.assertIsNone(h.validar(malo)[0])

    def test_argumentos(self):
        self.assertEqual(h.validar({"herramienta": "youtube", "args": {"consulta": "  lofi \n beats "}})[0],
                         {"herramienta": "youtube", "args": {"consulta": "lofi beats"}})
        self.assertEqual(h.validar({"herramienta": "youtube", "args": {}})[0]["args"], {})
        self.assertIsNone(h.validar({"herramienta": "buscar_web", "args": {}})[0], "obligatorio")
        self.assertIsNone(h.validar({"herramienta": "multimedia", "args": {"orden": "formatear"}})[0], "fuera del enum")
        self.assertIsNone(h.validar({"herramienta": "volumen", "args": {"orden": "subir", "pasos": "mucho"}})[0])
        self.assertIsNone(h.validar({"herramienta": "youtube", "args": "no soy un objeto"})[0])

    def test_largos_y_caracteres_de_control(self):
        c = h.validar({"herramienta": "buscar_web", "args": {"consulta": "a\x00b\x1b[31m" + "x" * 500}})[0]
        self.assertLessEqual(len(c["args"]["consulta"]), h.MAX_CONSULTA)
        self.assertNotIn("\x00", c["args"]["consulta"])
        self.assertNotIn("\x1b", c["args"]["consulta"])

    def test_args_extra_se_descartan(self):
        c = h.validar({"herramienta": "youtube", "args": {"consulta": "x", "url": "http://malo", "cmd": "calc"}})[0]
        self.assertEqual(c["args"], {"consulta": "x"})


class TestExtraerLlamada(unittest.TestCase):
    def test_json_limpio(self):
        self.assertEqual(h.extraer_llamada('{"herramienta": "youtube", "args": {"consulta": "x"}}')["herramienta"], "youtube")

    def test_con_markdown_y_texto_alrededor(self):
        r = 'Claro:\n```json\n{"herramienta": "alarma", "args": {"cuando": "2026-10-13 07:00"}}\n```\nListo.'
        self.assertEqual(h.extraer_llamada(r)["herramienta"], "alarma")

    def test_conversacion_normal_no_es_una_llamada(self):
        for r in ["Hola, ¿en qué puedo ayudarle?", 'Dijo {"a": 1}', "la herramienta es útil", "{no json herramienta"]:
            with self.subTest(r):
                self.assertIsNone(h.extraer_llamada(r))

    def test_lo_que_extrae_aun_pasa_por_validar(self):
        obj = h.extraer_llamada('{"herramienta": "formatear_disco", "args": {}}')
        self.assertIsNone(h.validar(obj)[0])


class TestExtraerLlamadas(unittest.TestCase):
    """El bucle del agente necesita ver TODAS las llamadas de una respuesta, no
    sólo la primera: un modelo que planea puede devolver dos en un turno."""

    def test_dos_objetos_en_orden(self):
        r = ('{"herramienta": "spotify", "args": {"consulta": "bach"}} y luego '
             '{"herramienta": "hora", "args": {}}')
        self.assertEqual([c["herramienta"] for c in h.extraer_llamadas(r)], ["spotify", "hora"])

    def test_un_json_que_no_es_llamada_no_cuenta(self):
        self.assertEqual(h.extraer_llamadas('{"a": 1} hola'), [])

    def test_un_objeto_anidado_no_se_cuenta_dos_veces(self):
        """La llave interior de `{"nota": {"herramienta": …}}` también casa por
        `finditer`; si no se salta lo ya decodificado, de un objeto salen dos."""
        self.assertEqual(h.extraer_llamadas('{"nota": {"herramienta": "hora"}}'), [])

    def test_extraer_llamada_sigue_dando_la_primera(self):
        r = '{"herramienta": "hora", "args": {}} {"herramienta": "fecha", "args": {}}'
        self.assertEqual(h.extraer_llamada(r)["herramienta"], "hora")

    def test_conversacion_normal_no_devuelve_nada(self):
        for r in ["Hola, ¿en qué puedo ayudarle?", 'Dijo {"a": 1}', "la herramienta es útil"]:
            with self.subTest(r):
                self.assertEqual(h.extraer_llamadas(r), [])


class TestEntender(Base):
    def llamadas(self, texto):
        return [(c["herramienta"], c["args"]) for c in h.entender(texto, self.ctx)]

    def test_tabla(self):
        for texto, esperado in [
            ("pon una alarma a las 7", [("alarma", {"cuando": "2026-10-13 07:00"})]),
            ("recuérdame llamar a mamá a las 6", [("recordatorio", {"cuando": "2026-10-13 06:00", "texto": "llamar a mamá"})]),
            ("abre youtube", [("youtube", {})]),
            ("pon música relajante en youtube", [("youtube", {"consulta": "música relajante"})]),
            ("pon Bad Bunny en spotify", [("spotify", {"consulta": "Bad Bunny"})]),
            ("abre la calculadora", [("abrir_app", {"nombre": "la calculadora"})]),
            ("busca recetas de arepas", [("buscar_web", {"consulta": "recetas de arepas"})]),
            ("inicia el cronómetro", [("cronometro", {"orden": "iniciar"})]),
            ("anota que debo pagar el recibo", [("nota", {"texto": "debo pagar el recibo"})]),
            ("sube el volumen", [("volumen", {"orden": "subir"})]),
            ("pausa", [("multimedia", {"orden": "play_pausa"})]),
            ("ok cort abre spotify", [("spotify", {})]),
        ]:
            with self.subTest(texto):
                self.assertEqual(self.llamadas(texto), esperado)

    def test_conversacion_y_temporizadores_se_dejan_pasar(self):
        for texto in ["hola, ¿cómo estás?", "cuéntame un chiste", "pon un temporizador de 5 minutos",
                      "qué clima hace", "abre photoshop", ""]:
            with self.subTest(texto):
                self.assertEqual(self.llamadas(texto), [])

    def test_un_recordatorio_con_y_no_se_parte(self):
        self.assertEqual(self.llamadas("recuérdame comprar pan y leche a las 6"),
                         [("recordatorio", {"cuando": "2026-10-13 06:00", "texto": "comprar pan y leche"})])

    def test_una_musica_con_y_no_se_parte(self):
        self.assertEqual(self.llamadas("pon música de Calle 13 y Residente en spotify"),
                         [("spotify", {"consulta": "Calle 13 y Residente"})])

    def test_dos_ordenes_son_un_plan_en_orden(self):
        self.assertEqual(self.llamadas("abre el bloc de notas y abre youtube"),
                         [("abrir_app", {"nombre": "el bloc de notas"}), ("youtube", {})])

    def test_un_tramo_que_no_se_entiende_anula_el_plan(self):
        """Hacer la mitad de lo pedido sin avisar es peor que dejarlo al modelo."""
        self.assertEqual(self.llamadas("abre youtube y cuéntame un chiste"), [])

    def test_sin_hora_el_recordatorio_se_deja_al_modelo(self):
        self.assertEqual(self.llamadas("recuérdame llamar al médico"), [])

    def test_agenda_listar_y_cancelar(self):
        self.assertEqual(self.llamadas("qué alarmas tengo"), [("agenda_listar", {})])
        self.assertEqual(self.llamadas("cancela la alarma"), [("agenda_cancelar", {"tipo": "alarma"})])
        self.assertEqual(self.llamadas("cancela todos los recordatorios"),
                         [("agenda_cancelar", {"tipo": "recordatorio", "todas": 1})])


class TestPlanParcial(Base):
    """`entender_plan` responde a lo mismo que `entender`, pero con una salida
    más: los trozos que no se entendieron, dichos tal cual. La regla que protege
    todo: ningún mensaje que `entender` resolvía cambia de resultado."""

    def plan(self, texto):
        llamadas, cabos = h.entender_plan(texto, self.ctx)
        return [(c["herramienta"], c.get("args", {})) for c in llamadas], cabos

    def test_un_cabo_suelto_se_nombra_y_lo_demas_se_hace(self):
        self.assertEqual(self.plan("abre youtube y cuéntame un chiste"),
                         ([("youtube", {})], ["cuéntame un chiste"]))

    def test_un_plan_completo_sale_igual_que_entender(self):
        for t in ["abre el bloc de notas y abre youtube", "qué hora es y sube el volumen",
                  "pon una alarma a las 7 y abre spotify"]:
            with self.subTest(t):
                viejo = [(c["herramienta"], c.get("args", {})) for c in h.entender(t, self.ctx)]
                nuevo, cabos = self.plan(t)
                self.assertEqual((nuevo, cabos), (viejo, []))

    def test_el_verbo_se_hereda_y_el_plan_sale_entero(self):
        """«…y el bloc de notas» solo no es una orden; con el «abre» heredado, sí.
        El camino antiguo perdía el mensaje entero aquí; el parcial lo recupera."""
        self.assertEqual(self.plan("abre la calculadora y el bloc de notas")[0],
                         [("abrir_app", {"nombre": "la calculadora"}),
                          ("abrir_app", {"nombre": "el bloc de notas"})])

    def test_una_busqueda_con_y_sigue_siendo_una_sola(self):
        llamadas, cabos = h.entender_plan("pon música de Calle 13 y Residente en spotify", self.ctx)
        self.assertEqual((cabos, len(llamadas)), ([], 1))
        self.assertEqual(llamadas[0]["args"]["consulta"], "Calle 13 y Residente")

    def test_un_recordatorio_con_y_no_se_parcializa(self):
        llamadas, cabos = h.entender_plan("recuérdame comprar pan y leche a las 6", self.ctx)
        self.assertEqual(cabos, [])
        self.assertEqual([c["herramienta"] for c in llamadas], ["recordatorio"])

    def test_nada_entendido_no_inventa_nada(self):
        # sin una sola llamada no hay plan parcial que valga: el mensaje se va
        # entero al camino de siempre (temporizador → intents → modelo)
        self.assertEqual(self.plan("hola, ¿cómo estás?"), ([], []))


class TestPlanParcialCedeALaPilaAntigua(Base):
    """En Linux el volumen no vive en estas herramientas pero `intents` lo casa:
    un cabo ejecutable por la otra pila NO se parcializa —mejor ceder el mensaje
    entero, como siempre, que responder la hora y dejar el volumen mudo—."""
    windows = False

    def test_lo_que_la_pila_antigua_hace_no_se_parcializa(self):
        self.assertEqual(h.entender_plan("¿qué hora es y sube el volumen?", self.ctx), ([], []))


class TestEjecutarAbrir(Base):
    def test_youtube_construye_la_url_nosotros(self):
        r = self.di("busca tutoriales de python en youtube")
        self.assertTrue(r.ok)
        self.assertEqual(self.so.abierto, ["https://www.youtube.com/results?search_query=tutoriales+de+python"])

    def test_una_consulta_maliciosa_queda_dentro_de_la_consulta(self):
        malo = 'x"; calc & del /q * & echo "'
        h.ejecutar({"herramienta": "youtube", "args": {"consulta": malo}}, self.ctx)
        url = self.so.abierto[0]
        u = urlparse(url)
        self.assertEqual((u.scheme, u.netloc, u.path), ("https", "www.youtube.com", "/results"))
        self.assertEqual(parse_qs(u.query)["search_query"], [malo], "viaja como dato, no como orden")
        for ch in '"; &':
            self.assertNotIn(ch, url.split("?", 1)[1], "ni un carácter de shell sin escapar")

    def test_el_modelo_no_puede_abrir_una_url_suya(self):
        for args in [{"nombre": "https://malo.example/x.exe"}, {"nombre": "C:\\Windows\\System32\\cmd.exe"},
                     {"nombre": "calc.exe /c del *"}, {"nombre": "javascript:alert(1)"}]:
            with self.subTest(args):
                r = h.ejecutar({"herramienta": "abrir_app", "args": args}, self.ctx)
                self.assertFalse(r.ok)
        self.assertEqual(self.so.abierto, [], "nada llegó al sistema")

    def test_apps_sitios_y_carpetas_conocidos(self):
        self.di("abre la calculadora")
        self.di("abre gmail")
        self.di("abre descargas")
        self.assertEqual(self.so.abierto, ["calc", "https://mail.google.com", str(Path("/casa/u") / "Downloads")])

    def test_spotify_con_la_app_abre_su_busqueda(self):
        r = self.di("pon Bad Bunny en spotify")
        self.assertEqual(self.so.abierto, ["spotify:search:Bad%20Bunny"])
        self.assertIn("Pulsa reproducir", r.texto, "no promete darle play")

    def test_spotify_sin_la_app_cae_al_navegador(self):
        self.so.falla_abrir = None
        original = self.so.abrir
        def sin_app(destino):
            if destino.startswith("spotify:"):
                raise OSError("sin programa asociado")
            original(destino)
        self.ctx.abrir = sin_app
        r = self.di("pon Bad Bunny en spotify")
        self.assertTrue(r.ok)
        self.assertEqual(self.so.abierto, ["https://open.spotify.com/search/Bad%20Bunny"])

    def test_si_la_app_no_esta_instalada_se_dice(self):
        self.so.falla_abrir = FileNotFoundError()
        r = self.di("abre la calculadora")
        self.assertFalse(r.ok)
        self.assertIn("no encontré", r.texto)

    def test_maps_y_google(self):
        self.di("cómo llego a la Plaza de Bolívar")
        self.assertTrue(self.so.abierto[0].startswith("https://www.google.com/maps/search/?api=1&query="))


class TestEjecutarSistema(Base):
    def test_multimedia_y_volumen_pulsan_teclas_y_no_afirman_el_efecto(self):
        r = self.di("pausa")
        self.assertEqual(self.so.teclas, [("play_pausa", 1)])
        self.assertIn("No puedo comprobar", r.texto)
        r = self.di("sube el volumen")
        self.assertEqual(self.so.teclas[-1], ("subir_volumen", 5))
        self.assertIn("no me dice el nivel", r.texto)
        self.di("baja mucho el volumen")
        self.assertEqual(self.so.teclas[-1], ("bajar_volumen", 15))

    def test_pasos_acotados(self):
        h.ejecutar({"herramienta": "volumen", "args": {"orden": "subir", "pasos": 9999}}, self.ctx)
        self.assertEqual(self.so.teclas[-1], ("subir_volumen", 25))

    def test_recorte_y_bloqueo(self):
        self.di("captura de pantalla")
        self.di("bloquea el pc")
        self.assertEqual((self.so.recortes, self.so.bloqueos), (1, 1))

    def test_en_otro_sistema_se_dice_en_vez_de_simular(self):
        self.ctx.windows = False
        for orden in ["multimedia", "volumen", "captura", "bloquear_pc"]:
            args = {"multimedia": {"orden": "siguiente"}, "volumen": {"orden": "subir"}}.get(orden, {})
            r = h.ejecutar({"herramienta": orden, "args": args}, self.ctx)
            self.assertFalse(r.ok)
            self.assertIn("sólo está disponible en Windows", r.texto)
        self.assertEqual((self.so.teclas, self.so.recortes, self.so.bloqueos), ([], 0, 0))


class TestEjecutarAgenda(Base):
    def test_alarma_queda_en_la_agenda_y_se_confirma_con_la_hora_completa(self):
        r = self.di("pon una alarma a las 7")
        self.assertTrue(r.ok)
        self.assertIn("mañana a las 7:00 a. m.", r.texto, "se confirma para que una hora mal entendida se note")
        self.assertEqual(r.extra, {"agenda": 1})
        self.assertEqual(self.ctx.agenda.pendientes()[0]["cuando"], "2026-10-13T07:00:00")

    def test_recordatorio(self):
        r = self.di("recuérdame en 20 minutos que saque la pasta")
        self.assertIn("hoy a las 9:50 p. m.", r.texto)
        self.assertEqual(self.ctx.agenda.pendientes()[0]["texto"], "que saque la pasta")

    def test_una_hora_pasada_o_lejana_se_rechaza(self):
        for cuando in ["2026-10-12 08:00", "2030-01-01 08:00", "no es fecha"]:
            with self.subTest(cuando):
                r = h.ejecutar({"herramienta": "alarma", "args": {"cuando": cuando}}, self.ctx)
                self.assertFalse(r.ok)
        self.assertEqual(self.ctx.agenda.pendientes(), [])

    def test_listar_y_cancelar_el_mas_proximo(self):
        self.di("pon una alarma a las 7")
        self.di("recuérdame llamar a mamá a las 6")
        self.assertIn("2 pendientes", self.di("qué alarmas tengo").texto)
        r = self.di("cancela la alarma")
        self.assertIn("Cancelé alarma", r.texto)
        self.assertEqual(len(self.ctx.agenda.pendientes()), 1)
        self.assertEqual(self.di("cancela todos los recordatorios").texto, "Cancelé 1 pendiente.")
        self.assertEqual(self.di("cancela la alarma").texto, "No había nada que cancelar.")

    def test_evento_de_calendario_es_una_url_de_google(self):
        r = self.di("agenda una reunión con Juan mañana a las 3 en el calendario")
        u = urlparse(self.so.abierto[0])
        self.assertEqual((u.netloc, u.path), ("calendar.google.com", "/calendar/render"))
        q = parse_qs(u.query)
        self.assertEqual(q["text"], ["Reunión con Juan"])
        self.assertEqual(q["dates"], ["20261013T150000/20261013T160000"])
        self.assertIn("pulsa Guardar", r.texto, "no dice que ya está guardado: no lo está")

    def test_cronometro_pide_al_servidor_que_lo_lleve(self):
        self.assertEqual(self.di("inicia el cronómetro").extra, {"cronometro": "iniciar"})
        self.assertEqual(self.di("para el cronómetro").extra, {"cronometro": "parar"})

    def test_notas(self):
        self.ctx.notas = Path(self.dir.name) / "notas.txt"
        self.assertEqual(self.di("mis notas").texto, "No tienes notas guardadas.")
        self.di("anota que debo pagar el recibo")
        self.di("apunta que llamar al banco")
        self.assertIn("debo pagar el recibo | llamar al banco", self.di("mis notas").texto)


class TestHoraYFecha(Base):
    """Se responden con el reloj del equipo: sin modelo, sin internet y sin la llave
    de acciones (no tocan nada)."""

    def test_la_hora(self):
        for frase in ["¿qué hora es?", "qué horas son", "me dices la hora", "a qué hora estamos"]:
            with self.subTest(frase):
                self.assertEqual(self.di(frase).texto, "Son las 9:30 p. m.")

    def test_una_de_la_tarde_es_singular(self):
        self.ctx.ahora = lambda: datetime(2026, 10, 12, 13, 5)
        self.assertEqual(self.di("qué hora es").texto, "Es la 1:05 p. m.")

    def test_la_fecha(self):
        for frase in ["qué día es hoy", "qué fecha es", "a cuántos estamos", "fecha de hoy"]:
            with self.subTest(frase):
                self.assertEqual(self.di(frase).texto, "Hoy es lunes 12 de octubre de 2026.")

    def test_funcionan_con_las_acciones_apagadas(self):
        self.ctx.acciones = lambda: False
        self.assertTrue(self.di("qué hora es").ok)

    def test_con_cortesia_y_con_otra_orden_al_lado(self):
        self.assertEqual(self.di("por favor, ¿qué hora es?").texto, "Son las 9:30 p. m.")
        self.assertEqual(self.di("ok cort qué hora es, por favor").texto, "Son las 9:30 p. m.")
        # Con otra orden en la misma frase no se contesta sólo la hora: se deja al plan.
        self.ctx.windows = False
        self.assertEqual(h.entender("¿qué hora es y sube el volumen?", self.ctx), [])


class TestLlaveDeAcciones(Base):
    """`CORT_SYSTEM_ACTIONS=0` apaga lo que toca el sistema, y sólo eso."""

    def test_apagada_no_llega_nada_al_sistema(self):
        self.ctx.acciones = lambda: False
        for texto in ["abre youtube", "abre la calculadora", "pausa", "sube el volumen", "bloquea el pc",
                      "busca arepas", "captura de pantalla"]:
            with self.subTest(texto):
                r = self.di(texto)
                self.assertFalse(r.ok)
                self.assertIn("CORT_SYSTEM_ACTIONS=0", r.texto)
        self.assertEqual((self.so.abierto, self.so.teclas, self.so.recortes, self.so.bloqueos), ([], [], 0, 0))

    def test_apagada_la_agenda_y_el_cronometro_siguen(self):
        self.ctx.acciones = lambda: False
        self.assertTrue(self.di("pon una alarma a las 7").ok)
        self.assertTrue(self.di("inicia el cronómetro").ok)
        self.assertTrue(self.di("anota que algo").ok)


class TestInstrucciones(unittest.TestCase):
    def test_el_modelo_conoce_exactamente_las_herramientas_del_registro(self):
        texto = h.instrucciones()
        for nombre in h.HERRAMIENTAS:
            self.assertIn(nombre + "(", texto)
        self.assertIn("ÚNICAMENTE con un objeto JSON", texto)


if __name__ == "__main__":
    unittest.main()
