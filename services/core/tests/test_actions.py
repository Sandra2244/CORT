import os
import pathlib
import sys
import unittest

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


if __name__ == "__main__":
    unittest.main()
