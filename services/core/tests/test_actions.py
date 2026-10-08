import os
import pathlib
import sys
import tempfile
import unittest
from datetime import datetime
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from cort_core import actions


class FakeRunner:
    """Registra el argv que le pasan y devuelve lo pactado, sin ejecutar nada.

    La prueba de que la capa de permisos funciona es que el sistema de audio de
    Sandra no se enteró de que corrimos la suite.

    `levels` es lo que responde cada `wpctl get-volume`, en orden: el volumen se
    lee antes y después de mandarlo, y un fake que devolviera siempre lo mismo
    no podría contar las dos historias distintas que hay (subió / no se movió).
    """

    def __init__(self, replies=None, levels=()):
        self.calls: list[list[str]] = []
        self.replies = replies or {}
        self.levels = list(levels)

    async def __call__(self, argv):
        self.calls.append(list(argv))
        if "get-volume" in argv and self.levels:
            out = self.levels.pop(0) if len(self.levels) > 1 else self.levels[0]
            return 0, f"Volume: {out}"
        for key, (code, out) in self.replies.items():
            if key in argv:
                return code, out
        return 0, ""


def with_env(**pairs):
    """Variables de entorno durante el test, y nada después."""
    old = {k: os.environ.get(k) for k in pairs}
    for k, v in pairs.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

    def restore():
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    return restore


class TestArgv(unittest.TestCase):
    """El argv es la superficie de ataque. Si esto cambia, es una decisión."""

    def test_volume_up(self):
        self.assertEqual(
            actions.volume_argv(10),
            ["wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", "10%+"],
        )

    def test_volume_down_uses_the_minus_suffix(self):
        self.assertEqual(actions.volume_argv(-10)[-1], "10%-")

    def test_argv_has_no_shell_metacharacters(self):
        """`shell=True` no se usa en ningún sitio, y el argv no lo pediría."""
        for delta in (-25, -1, 1, 25):
            joined = " ".join(actions.volume_argv(delta))
            for bad in (";", "|", "&", "$", "`", "\n"):
                self.assertNotIn(bad, joined)

    def test_only_our_own_numbers_reach_the_argv(self):
        """El delta viene de la tabla de `intents.py`, no del texto del usuario."""
        self.assertEqual(actions.volume_argv(3)[5], "3%+")

    def test_the_screenshot_argv_is_a_fixed_three_piece(self):
        path = pathlib.Path("/tmp/donde-sea/cort-una.png")
        self.assertEqual(actions.screenshot_argv(path), ["scrot", "-o", str(path)])

    def test_nobody_can_park_a_command_in_a_capture_name(self):
        """El nombre lo genera `shot_path`, no el texto que se escribe."""
        name = actions.shot_path(datetime(2026, 10, 7, 23, 30, 5, 123456))
        self.assertEqual(name.name, "cort-20261007-233005-123456.png")
        joined = " ".join(actions.screenshot_argv(name))
        for bad in (";", "|", "&", "$", "`", "\n", ".."):
            self.assertNotIn(bad, joined.replace(str(actions.SHOTS_DIR), ""))

    def test_two_captures_in_the_same_second_do_not_overwrite_each_other(self):
        a = actions.shot_path(datetime(2026, 10, 7, 23, 30, 5, 1))
        b = actions.shot_path(datetime(2026, 10, 7, 23, 30, 5, 2))
        self.assertNotEqual(a, b)


class TestVolume(unittest.IsolatedAsyncioTestCase):
    async def test_the_level_it_reports_is_the_one_it_read_back(self):
        runner = FakeRunner(levels=["1.00", "0.60"])
        ok, said = await actions.perform({"action": "volume", "delta": -10}, runner=runner)
        self.assertTrue(ok)
        self.assertEqual(said, "Volumen al 60 %.")

    async def test_a_returncode_of_zero_that_changed_nothing_is_not_a_success(self):
        """Medido en este portátil: con el sink en "Dummy Output", `wpctl set-volume`
        devuelve 0 y el nivel no se mueve. Filtrar sólo por returncode sería
        afirmar ante Sandra que subió el volumen cuando no subió nada."""
        runner = FakeRunner(levels=["0.90"])
        ok, said = await actions.perform({"action": "volume", "delta": -10}, runner=runner)
        self.assertFalse(ok)
        self.assertIn("sigue en 90 %", said)

    async def test_it_reads_then_sets_then_reads_again(self):
        runner = FakeRunner(levels=["1.00", "0.60"])
        await actions.perform({"action": "volume", "delta": -10}, runner=runner)
        self.assertEqual(runner.calls[0], ["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])
        self.assertEqual(runner.calls[1][:2], ["wpctl", "set-volume"])
        self.assertEqual(runner.calls[2], ["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])

    async def test_a_failing_setvolume_is_reported_not_glassed_over(self):
        runner = FakeRunner({"set-volume": (1, ".wpctl: no default sink")}, levels=["1.00"])
        ok, said = await actions.perform({"action": "volume", "delta": 10}, runner=runner)
        self.assertFalse(ok)
        self.assertIn("no default sink", said)
        # Y no se pregunta el nivel de algo que no se cambió.
        self.assertEqual(len(runner.calls), 2)

    async def test_a_delta_that_is_not_a_number_is_refused(self):
        runner = FakeRunner()
        ok, said = await actions.perform({"action": "volume", "delta": "10; rm -rf /"}, runner=runner)
        self.assertFalse(ok)
        self.assertEqual(runner.calls, [])

    async def test_zero_delta_does_nothing(self):
        runner = FakeRunner()
        ok, _ = await actions.perform({"action": "volume", "delta": 0}, runner=runner)
        self.assertFalse(ok)
        self.assertEqual(runner.calls, [])


class TestMedia(unittest.IsolatedAsyncioTestCase):
    async def test_known_keys_are_sent_as_a_single_arg(self):
        runner = FakeRunner()
        ok, said = await actions.perform({"action": "media", "cmd": "pause"}, runner=runner)
        self.assertTrue(ok)
        self.assertEqual(runner.calls, [["xdotool", "key", "XF86AudioPause"]])
        self.assertEqual(said, "Enviar XF86AudioPause.")

    async def test_unknown_command_is_refused(self):
        runner = FakeRunner()
        ok, _ = await actions.perform({"action": "media", "cmd": "eject"}, runner=runner)
        self.assertFalse(ok)
        self.assertEqual(runner.calls, [])


class TestScreenshot(unittest.IsolatedAsyncioTestCase):
    """La captura es la única acción cuya prueba se puede leer de verdad.

    El volumen no se puede verificar en este portátil (no hay salida de audio),
    pero un archivo sí: existe, tiene tamaño, y se puede borrar.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.shots = pathlib.Path(self.tmp.name) / "capturas"
        patcher = mock.patch.object(actions, "SHOTS_DIR", self.shots)
        patcher.start()
        self.addCleanup(patcher.stop)

    class _Scrot:
        """Fake que se comporta como scrot en las cuatro variantes que importan."""

        def __init__(self, code=0, out="", write=b"\x89PNG" + b"0" * 4096):
            self.code, self.out, self.write = code, out, write
            self.calls = []

        async def __call__(self, argv):
            self.calls.append(list(argv))
            if self.code == 0 and self.write is not None:
                pathlib.Path(argv[-1]).write_bytes(self.write)
            return self.code, self.out

    async def test_a_real_file_behind_the_command_is_what_makes_it_a_success(self):
        runner = self._Scrot()
        ok, said = await actions.perform({"action": "screenshot"}, runner=runner)
        self.assertTrue(ok)
        self.assertIn("Captura guardada", said)
        self.assertIn("4 KB", said)
        self.assertEqual(len(list(self.shots.iterdir())), 1)

    async def test_it_creates_the_folder_it_needs(self):
        self.assertFalse(self.shots.exists())
        await actions.perform({"action": "screenshot"}, runner=self._Scrot())
        self.assertTrue(self.shots.is_dir())

    async def test_zero_and_no_file_is_not_a_success(self):
        """El returncode otra vez mintiendo: scrot dice 0 y no escribió nada."""
        runner = self._Scrot(write=None)
        ok, said = await actions.perform({"action": "screenshot"}, runner=runner)
        self.assertFalse(ok)
        self.assertIn("no apareció", said)

    async def test_an_empty_image_is_reported_as_empty(self):
        runner = self._Scrot(write=b"")
        ok, said = await actions.perform({"action": "screenshot"}, runner=runner)
        self.assertFalse(ok)
        self.assertIn("vacía (0 bytes)", said)

    async def test_a_failing_scrot_says_why(self):
        runner = self._Scrot(code=1, out="scrot: Can't open X display")
        ok, said = await actions.perform({"action": "screenshot"}, runner=runner)
        self.assertFalse(ok)
        self.assertIn("Can't open X display", said)
        self.assertEqual(list(self.shots.iterdir()), [])

    async def test_the_kill_switch_takes_the_capture_off_the_table_too(self):
        restore = with_env(CORT_SYSTEM_ACTIONS="0")
        self.addCleanup(restore)
        runner = self._Scrot()
        ok, _ = await actions.perform({"action": "screenshot"}, runner=runner)
        self.assertFalse(ok)
        self.assertEqual(runner.calls, [])


class TestPermissionLayer(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.addCleanup(with_env(CORT_SYSTEM_ACTIONS="1"))

    async def test_action_not_on_the_list_is_named_and_refused(self):
        runner = FakeRunner()
        ok, said = await actions.perform({"action": "equalizer", "cmd": "toggle"}, runner=runner)
        self.assertFalse(ok)
        self.assertIn("no está en la lista permitida", said)
        self.assertEqual(runner.calls, [])

    async def test_the_kill_switch_runs_nothing(self):
        os.environ["CORT_SYSTEM_ACTIONS"] = "0"
        runner = FakeRunner()
        ok, said = await actions.perform({"action": "volume", "delta": 10}, runner=runner)
        self.assertFalse(ok)
        self.assertIn("apagadas", said)
        self.assertEqual(runner.calls, [])


class TestSpawn(unittest.IsolatedAsyncioTestCase):
    """Lo que va más allá del fake: el ejecutor de verdad, con mandos inofensivos."""

    async def test_a_real_command_reports_its_returncode(self):
        self.assertEqual((await actions.spawn(["true"]))[0], 0)
        self.assertNotEqual((await actions.spawn(["false"]))[0], 0)

    async def test_a_missing_binary_is_a_result_not_a_crash(self):
        code, out = await actions.spawn(["cort-no-existe-este-mando"])
        self.assertEqual(code, 124)
        self.assertIn("FileNotFoundError", out)

    async def test_output_comes_back_as_text(self):
        code, out = await actions.spawn(["wpctl", "--version"])
        # Si PipeWire no está disponible en este entorno el mando puede fallar;
        # lo que el ejecutor garantiza es que devuelve texto o código, nunca una
        # excepción sin capturar ni el proceso colgado.
        self.assertIsInstance(out, str)
        self.assertIsInstance(code, int)


class TestReadback(unittest.TestCase):
    def test_percent_reads_the_number_wpctl_prints(self):
        self.assertEqual(actions._percent("Volume: 0.60"), "60")
        self.assertEqual(actions._percent("Volume: 1.00\nMute: no"), "100")

    def test_unparseable_output_is_none_not_a_guess(self):
        self.assertIsNone(actions._percent("no default sink"))


class CountingRunner:
    """Responde a `pgrep -c` con los números pactados, en orden de llamada.

    Con 0 procesos `pgrep` imprime "0" y sale con código 1: el fake imita las
    dos cosas, porque un fake que siempre devolviera 0 mezclaría "no hay nadie"
    con "no sé".
    """

    def __init__(self, counts):
        self.counts = list(counts)
        self.calls: list[list[str]] = []

    async def __call__(self, argv):
        self.calls.append(list(argv))
        n = self.counts.pop(0) if self.counts else 0
        return (0, str(n)) if n else (1, "0")


class TestAbrirAplicaciones(unittest.IsolatedAsyncioTestCase):
    """`launch` es la acción más peligrosa de la lista: pone ventanas en el
    escritorio de Sandra. Aquí nada se ejecuta —el lanzador va sustituido— y lo
    que se comprueba es la tabla cerrada y la lectura del proceso después.
    """

    def setUp(self):
        self.lanzadas: list[list[str]] = []

        async def fake_launch(argv):
            self.lanzadas.append(list(argv))

        patcher = mock.patch.object(actions, "launch_detached", fake_launch)
        patcher.start()
        self.addCleanup(patcher.stop)
        # El reposo de 0,8 s existe porque una GUI tarda en aparecer; en los
        # tests no hay GUI que esperar.
        settle = mock.patch.object(actions, "SETTLE_S", 0.0)
        settle.start()
        self.addCleanup(settle.stop)

    async def test_lo_que_se_lanza_es_exactamente_la_tabla(self):
        ok, said = await actions.perform({"action": "launch", "app": "archivos"},
                                         runner=CountingRunner([0, 1]))
        self.assertTrue(ok, said)
        self.assertEqual([["thunar"]], self.lanzadas)

    async def test_lo_que_no_esta_en_la_tabla_no_se_lanza_ni_se_intenta(self):
        runner = CountingRunner([])
        ok, said = await actions.perform({"action": "launch", "app": "juegos"}, runner=runner)
        self.assertFalse(ok)
        self.assertIn("no está en la lista", said)
        self.assertEqual([], self.lanzadas)
        self.assertEqual([], runner.calls, "ni siquiera se preguntó por el proceso")

    async def test_la_prueba_de_que_abrio_es_un_proceso_mas(self):
        """El returncode de un lanzador no dice nada: lo que cuenta es que
        aparezca alguien nuevo en la lista de procesos."""
        ok, said = await actions.perform({"action": "launch", "app": "terminal"},
                                         runner=CountingRunner([0, 1]))
        self.assertTrue(ok, said)
        self.assertIn("Abriendo", said)

    async def test_ya_estaba_abierta_no_es_un_exito_que_se_atribuya(self):
        ok, said = await actions.perform({"action": "launch", "app": "archivos"},
                                         runner=CountingRunner([2, 2]))
        self.assertTrue(ok)
        self.assertIn("ya estaba en marcha", said)
        self.assertTrue(said.startswith("El"), "la frase va en mayúscula: es lo que lee Sandra")

    async def test_sin_proceso_nuevo_no_hay_exito(self):
        ok, said = await actions.perform({"action": "launch", "app": "archivos"},
                                         runner=CountingRunner([0, 0]))
        self.assertFalse(ok)
        self.assertIn("no llegó a arrancar", said)

    async def test_un_binario_que_no_existe_se_dice_como_lo_que_es(self):
        async def missing(argv):
            raise FileNotFoundError(2, "No such file")

        with mock.patch.object(actions, "launch_detached", missing):
            ok, said = await actions.perform({"action": "launch", "app": "archivos"},
                                             runner=CountingRunner([0]))
        self.assertFalse(ok)
        self.assertIn("no está instalado", said)

    async def test_el_kill_switch_tambien_cubre_las_apps(self):
        runner = CountingRunner([])
        restore = with_env(CORT_SYSTEM_ACTIONS="0")
        self.addCleanup(restore)
        ok, said = await actions.perform({"action": "launch", "app": "archivos"}, runner=runner)
        self.assertFalse(ok)
        self.assertIn("apagadas", said)
        self.assertEqual([], self.lanzadas)

    def test_pgrep_pide_el_nombre_exacto(self):
        """Con `-f` bastaría que algún proceso mencionara "thunar" en sus
        argumentos para contar una ventana que no existe."""
        self.assertEqual(["pgrep", "-c", "-x", "thunar"], actions.pgrep_argv("thunar"))

    def test_la_tabla_no_deja_pasar_texto_ajeno(self):
        for nombre, argv in actions.APPS.items():
            self.assertIsInstance(argv, list)
            self.assertTrue(argv, nombre)
            for pieza in argv:
                self.assertIsInstance(pieza, str)
                self.assertNotIn("%s", pieza)
                self.assertNotIn("{", pieza)


if __name__ == "__main__":
    unittest.main()
