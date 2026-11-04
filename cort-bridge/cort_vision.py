"""S2 — la mano delante de la cámara convertida en órdenes de ventana.

Lo que se pidió: «lo de la cámara para mover ventanas». Lo que mide este equipo
(Canaima, Celeron N2805, navegador cerrado): la webcam entrega **YUY2 320×240 a
14,9–15,1 cuadros por segundo**, con **67–68 ms entre cuadros** y **1,9–2,5 ms de
cálculo por cuadro** — alrededor del 3 % de un núcleo mientras CORT mira. Tardan
**~2,4 s** en caer los primeros cuadros desde que se enciende la mirada. RGB 320×240
no negocia, así que se trabaja sobre YUY2 sin convertir: el formato ya trae luma y
croma separados y la piel se detecta sobre el croma.

Un detalle que costó encontrar: pedir `framerate=10/1` **clavado** hace que la
tubería entre en `failure` y no salga ni un cuadro — esta cámara sólo sabe dar 15/1 a
ese tamaño. Se pide el rango `[1/1, 30/1]` y negocia lo que puede dar.

Tres decisiones de diseño, dichas en seco:

* **No hay modelo de visión.** No cabe: con el navegador abierto quedan 174–282 MB
  libres y MediaPipe/NN-A son GB. Aquí se detecta *piel + bulto + movimiento*, que
  es lo que hace falta para cuatro gestos, no 21 articulaciones.
* **Los cuadros no se guardan nunca.** El worker los lee, saca cuatro números
  (área, centro, movimiento, hora) y tira el cuadro. En el registro no entra ni una
  imagen; si algún día entra, esta frase se borra y se dice.
* **El gesto manda, la mano no arrastra.** Mover una ventana píxel a píxel con una
  webcam de 320×240 a 15 fps daría un puntero tembloroso; con gestos discretos
  (barrido, palma, puño) la orden es clara y se puede verificar después.

        .venv/bin/python cort-bridge/cort_vision.py selftest   # sin cámara
        /usr/bin/python3 cort-bridge/cort_vision.py captura     # cuadros crudos (debug)
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from collections import deque
from pathlib import Path

ANCHO = int(os.environ.get("CORT_VISION_ANCHO", "320"))
ALTO = int(os.environ.get("CORT_VISION_ALTO", "240"))
BYTES_CUADRO = ANCHO * ALTO * 2          # YUY2: 2 bytes por píxel
FPS_MIRADA = int(os.environ.get("CORT_VISION_FPS", "10"))

# Umbrales de piel en croma (YUY2 trae Cb/Cr con sesgo 128). Son los clásicos de
# chroma YCbCr: Cb entre 77 y 127, Cr entre 133 y 173, y brillo por encima de 60
# para no tomar como piel una sombra negra.
CB_MIN, CB_MAX = -51, -1
CR_MIN, CR_MAX = 5, 45
LUMA_MIN = 60

# Qué tiene que verse para contar como «hay una mano delante».
AREA_MINIMA = float(os.environ.get("CORT_VISION_AREA", "0.012"))   # 1,2 % del cuadro
UMBRAL_MOVIMIENTO = 28          # diferencia de luma que cuenta como cambio
MIN_CUADROS = 3                 # cuadros con mano antes de decidir nada

# Movimiento mínimo que tiene que haber en la ventana para que un gesto *estático*
# (palma, puño) cuente. Medido con la cámara real apuntando a una persona sentada
# quieta: área 15 %, centro y=0,28 y `mov` entre 0,0000 y 0,0003. Sin este piso, la
# cara cumple la regla de «palma abierta» y el gesto se dispara una vez por segundo
# — medido: 8 gestos en 8 segundos — maximizando ventanas mientras nadie hace nada.
# Una mano que entra en cuadro mueve bastante más del 2 % de los píxeles.
MOV_MINIMO = float(os.environ.get("CORT_VISION_MOV", "0.02"))

# Tiempo que hay entre dos órdenes, pase lo que pase. Con 1 s la misma mano quieta
# volvía a disparar; con 2 s hace falta un gesto nuevo de verdad.
REFRACCARIO = float(os.environ.get("CORT_VISION_REFRACCARIO", "2.0"))

PYTHON_GST = os.environ.get("CORT_PYTHON_GST", "/usr/bin/python3")

# Qué orden de ventana ejecuta cada gesto. La lista es corta a propósito: son las
# cuatro cosas que se pueden hacer con una mano delante de una webcam de 320×240 y
# verificar después con `xprop`. El puente (cort_server) la obedece tal cual.
GESTO_A_ACCION = {
    "barrido_derecha": ("cambiar_ventana", {"direccion": "siguiente"}),
    "barrido_izquierda": ("cambiar_ventana", {"direccion": "anterior"}),
    "levantar_mano": ("maximizar", {}),
    "palma_arriba": ("maximizar", {}),
    "punar": ("minimizar_activa", {}),
    "empujar_abajo": ("restaurar", {}),
}


def _np():
    """numpy se importa tarde: el worker de captura corre con el Python del sistema,
    que tiene GStreamer pero no numpy, y no debe romperse por eso."""
    import numpy as np
    return np


def cuadro_a_canal(bruto: bytes):
    """YUY2 → (luma, Cb, Cr) sin pasar por RGB.

    El orden del muestreo es Y0 Cb Y1 Cr, así que la luma de cada par de píxeles es
    el mayor de los dos Y y el croma va por columna (mitad de resolución horizontal).
    """
    np = _np()
    m = np.frombuffer(bruto, dtype=np.uint8)
    esperado = BYTES_CUADRO
    if m.size != esperado:
        raise ValueError(f"cuadro de {m.size} bytes, se esperaban {esperado}")
    plano = m.reshape((ALTO, ANCHO // 2, 4))
    luma = np.maximum(plano[:, :, 0], plano[:, :, 2])
    cb = plano[:, :, 1].astype(np.int16) - 128
    cr = plano[:, :, 3].astype(np.int16) - 128
    return luma, cb, cr


def medida(bruto: bytes, anterior=None) -> dict:
    """Los cuatro números que se sacan de un cuadro; el cuadro se tira después."""
    np = _np()
    luma, cb, cr = cuadro_a_canal(bruto)
    mascara = ((cb >= CB_MIN) & (cb <= CB_MAX) & (cr >= CR_MIN) & (cr <= CR_MAX)
               & (luma > LUMA_MIN))
    area = float(mascara.mean())
    out = {"area": round(area, 4), "cx": None, "cy": None,
           "mov": None, "t": time.monotonic()}
    if area >= AREA_MINIMA:
        filas, cols = np.nonzero(mascara)
        # x2: el croma va a media resolución horizontal
        out["cx"] = round(float(cols.mean()) * 2 / ANCHO, 3)
        out["cy"] = round(float(filas.mean()) / ALTO, 3)
        # caja del bulto: sirve para distinguir palma abierta de puño cerrado
        out["caja"] = [int(cols.min()) * 2, int(filas.min()), int(cols.max()) * 2, int(filas.max())]
    if anterior is not None:
        dif = np.abs(luma.astype(np.int16) - anterior.astype(np.int16))
        out["mov"] = round(float((dif > UMBRAL_MOVIMIENTO).mean()), 4)
    return out, luma


def gesto(ventana: list[dict]) -> dict | None:
    """Cuatro gestos discretos sobre los últimos cuadros medidos.

    `ventana` es una cola de dicts de `medida()` (los que tienen `cx`). Devuelve
    `{"gesto": nombre, "por": texto_con_numero}` o None. Cada umbral está dicho en
    números para poder rebajarlo o subirlo sin adivinar.

    Los dos gestos *quietos* (palma y puño) piden además **movimiento en la ventana**
    y, en el caso de la palma, que el bulto **haya llegado** durante ella: una persona
    sentada delante de la cámara es un bulto de piel permanente en la mitad de arriba
    y, medido, cumplía la regla de palma abierta 8 veces en 8 segundos.
    """
    con_mano = [m for m in ventana if m.get("cx") is not None]
    if len(con_mano) < MIN_CUADROS:
        return None
    primero, ultimo = con_mano[0], con_mano[-1]
    dt = ultimo["t"] - primero["t"]
    if dt <= 0:
        return None
    areas = [m["area"] for m in con_mano]
    dx = ultimo["cx"] - primero["cx"]
    dy = ultimo["cy"] - primero["cy"]
    movs = [m["mov"] for m in ventana if m.get("mov") is not None]
    mov_max = max(movs) if movs else 0.0
    llego = any((m["area"] or 0.0) < AREA_MINIMA for m in ventana)

    # Barrido: el centro cruza media pantalla en menos de un segundo.
    if abs(dx) >= 0.30 and dt <= 1.0:
        return {"gesto": "barrido_derecha" if dx > 0 else "barrido_izquierda",
                "por": f"el centro pasó de {primero['cx']:.2f} a {ultimo['cx']:.2f} en {dt:.2f} s"}
    # Empujar hacia abajo / levantar: el centro baja o sube un tercio de pantalla.
    if dy >= 0.30 and dt <= 1.0:
        return {"gesto": "empujar_abajo", "por": f"el centro bajó {dy:.2f} en {dt:.2f} s"}
    if dy <= -0.30 and dt <= 1.0:
        return {"gesto": "levantar_mano", "por": f"el centro subió {-dy:.2f} en {dt:.2f} s"}
    # Puño: la misma mano presente, pero el bulto se encoge a menos del 60 %.
    if (mov_max >= MOV_MINIMO and max(areas) >= AREA_MINIMA * 2
            and ultimo["area"] <= 0.6 * max(areas)):
        return {"gesto": "punar",
                "por": f"el bulto pasó de {max(areas)*100:.1f} % a {ultimo['area']*100:.1f} % del cuadro "
                       f"(movió {mov_max*100:.1f} % del cuadro)"}
    # Palma abierta quieta en la mitad de arriba: «enséñame la mano» = maximizar.
    if (ultimo["area"] >= AREA_MINIMA * 3 and ultimo["cy"] < 0.45 and abs(dx) < 0.06
            and mov_max >= MOV_MINIMO and llego):
        return {"gesto": "palma_arriba",
                "por": f"área {ultimo['area']*100:.1f} % con el centro en y={ultimo['cy']:.2f}, "
                       f"movió {mov_max*100:.1f} % y llegó dentro de la ventana"}
    return None


class Mirada:
    """Mira la cámara en un hilo: lee cuadros del worker y emite gestos.

    El worker es un proceso aparte con `/usr/bin/python3`, que es el Python que tiene
    GStreamer; este módulo corre en el venv, que tiene numpy pero no gi. Por el pipe
    sólo viajan bytes crudos de un cuadro, nunca archivos.
    """

    def __init__(self, dispositivo: str = "/dev/video0", fps: int = FPS_MIRADA,
                 al_gesto=None, al_estado=None):
        self.dispositivo = dispositivo
        self.fps = fps
        self.al_gesto = al_gesto
        self.al_estado = al_estado
        self.proceso = None
        self.hilo = None
        self.seguir = False
        self.cola = deque(maxlen=max(6, int(fps * 1.2)))
        self.cuadros = 0
        self.ms_ultimo = 0.0
        self.ms_calculo = 0.0
        self.ultima_gesto = None
        self.motivo = ""

    # ---- ciclo de vida -------------------------------------------------------
    def arrancar(self) -> dict:
        if not Path(self.dispositivo).exists():
            self.motivo = f"{self.dispositivo} no existe en este equipo"
            return {"ok": False, "origen": "no disponible", "motivo": self.motivo}
        if self.proceso and self.proceso.poll() is None:
            return {"ok": True, "origen": "real", "motivo": "ya estaba mirando",
                    "cuadros": self.cuadros}
        try:
            self.proceso = subprocess.Popen(
                (os.environ.get("CORT_PYTHON_GST", PYTHON_GST),
                 os.environ.get("CORT_VISION_WORKER", str(Path(__file__).resolve())),
                 "captura", self.dispositivo,
                 str(ANCHO), str(ALTO), str(self.fps)),
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=BYTES_CUADRO)
        except OSError as e:
            self.motivo = f"no se pudo levantar el worker de cámara: {type(e).__name__}: {e}"
            return {"ok": False, "origen": "no disponible", "motivo": self.motivo}
        import threading
        self.seguir = True
        self.hilo = threading.Thread(target=self._mirar, daemon=True, name="cort-mirada")
        self.hilo.start()
        return {"ok": True, "origen": "real", "cuadros": 0, "fps": self.fps,
                "motivo": f"mirando {self.dispositivo} a {ANCHO}×{ALTO}"}

    def apagar(self) -> dict:
        self.seguir = False
        if self.proceso:
            try:
                self.proceso.terminate()
                self.proceso.wait(timeout=3)
            except Exception:
                try:
                    self.proceso.kill()
                except Exception:
                    pass
        r = {"ok": True, "origen": "real", "cuadros": self.cuadros,
             "ultimo_gesto": self.ultima_gesto}
        self.proceso = None
        return r

    def estado(self) -> dict:
        # Mirando = el hilo sigue vivo y el proceso también. Basta con que uno de los
        # dos se apague para dejar de decir que hay mirada.
        vivo = bool(self.seguir and self.proceso and self.proceso.poll() is None)
        tiempos = [m["t"] for m in self.cola if m.get("t")]
        # El promedio desde que arrancó castiga los ~2 s que tarda encenderse la
        # cámara; este se mide sobre los últimos cuadros, que es el ritmo que de
        # verdad sostiene la máquina mientras CORT mira.
        fps_reciente = 0.0
        if vivo and len(tiempos) >= 3 and tiempos[-1] > tiempos[0]:
            fps_reciente = round((len(tiempos) - 1) / (tiempos[-1] - tiempos[0]), 1)
        return {"ok": vivo, "origen": "real", "mirando": vivo, "dispositivo": self.dispositivo,
                "cuadros": self.cuadros,
                "fps_medidos": round(self.cuadros / max(1e-6, self._segundos_vivos()), 1)
                if vivo else 0, "fps_reciente": fps_reciente,
                "ms_por_cuadro": round(self.ms_ultimo, 1), "ms_calculo": round(self.ms_calculo, 1),
                "ultimo_gesto": self.ultima_gesto, "motivo": self.motivo}

    def _segundos_vivos(self):
        return time.monotonic() - getattr(self, "_t0", time.monotonic())

    # ---- el hilo -------------------------------------------------------------
    def _mirar(self):
        self._t0 = time.monotonic()
        bruto = bytearray()
        anterior = None
        ultimo_emitido = 0.0
        stdout = self.proceso.stdout
        try:
            self._leer_cuadros(stdout, bruto, anterior, ultimo_emitido)
        finally:
            # Si el hilo se apaga solo —cámara tapada, worker que no entregó cuadros,
            # formato que no cuadra— el puente tiene que enterarse en el momento, no
            # cuando la usuaria pregunte. Sin esto la interfaz quedaría diciendo
            # «mirando» con cero cuadros toda la tarde.
            se_apago_solo = self.seguir
            self.seguir = False
            if se_apago_solo and self.al_estado:
                try:
                    self.al_estado(self.estado())
                except Exception:
                    pass

    def _leer_cuadros(self, stdout, bruto, anterior, ultimo_emitido):
        while self.seguir:
            t_antes = time.monotonic()
            pedidos = BYTES_CUADRO - len(bruto)
            trozo = stdout.read(pedidos)
            if not trozo:      # el worker se cerró: cámara desconectada o se acabó la prueba
                self.motivo = ("el worker de cámara cerró el conducto sin dar cuadros"
                               if self.cuadros == 0 else "el worker de cámara cerró el conducto")
                break
            bruto += trozo
            if len(bruto) < BYTES_CUADRO:
                continue
            cuadro = bytes(bruto[:BYTES_CUADRO])
            del bruto[:BYTES_CUADRO]
            t_calculo = time.monotonic()
            try:
                m, luma = medida(cuadro, anterior)
            except ValueError as e:
                self.motivo = str(e)
                break
            anterior = luma
            self.cuadros += 1
            # Dos números distintos y no confundibles: lo que cuesta mirar un cuadro
            # (la pasada de numpy) y el ritmo real de la cámara, que incluye la espera
            # del conducto. El primero decide si la máquina aguanta; el segundo, fps.
            self.ms_calculo = (time.monotonic() - t_calculo) * 1000
            self.ms_ultimo = (time.monotonic() - t_antes) * 1000
            self.cola.append(m)
            # Un gesto cada REFRACCARIO (2 s medidos, no 1 s: con 1 s la misma mano
            # quieta volvía a cumplir la regla y ordenaba maximizar otra vez).
            if m["t"] - ultimo_emitido < REFRACCARIO:
                continue
            g = gesto(list(self.cola))
            if g:
                ultimo_emitido = m["t"]
                self.ultima_gesto = dict(g, cuadro=self.cuadros)
                self.cola.clear()
                if self.al_gesto:
                    try:
                        self.al_gesto(self.ultima_gesto)
                    except Exception:
                        pass
            if self.al_estado and self.cuadros % 30 == 0:
                try:
                    self.al_estado(self.estado())
                except Exception:
                    pass


# ------------------------------------------------------------------ worker (sin numpy) ----
def captura_continua(dispositivo: str, ancho: int, alto: int, fps: int) -> int:
    """Rama que corre con el Python del sistema: vierte cuadros crudos por stdout.

    No calcula nada ni guarda nada: es un conducto. Si el formato pedido no da
    cuadros, lo dice por stderr con el estado de la tubería y sale con código 2.

    El `framerate` va como **rango**, no clavado: medido en esta máquina, pedir
    `framerate=10/1` exacto hace que la tubería entre en `failure` y no salga ni un
    cuadro, porque la cámara sólo sabe dar 15/1 a 320×240. Con `[1/1, 30/1]` negocia
    lo que pueda dar y cada muestra llega de exactamente ancho×alto×2 bytes.
    """
    try:
        import gi
        gi.require_version("Gst", "1.0")
        from gi.repository import Gst, GLib
    except Exception as e:
        sys.stderr.write(f"gstreamer no disponible en {sys.executable}: {e}\n")
        return 3
    Gst.init(None)
    salida = sys.stdout.buffer
    n = [0]
    rotos = [0]

    def nuevo(sink):
        muestra = sink.emit("pull-sample")
        if muestra is None:
            return Gst.FlowReturn.ERROR
        b = muestra.get_buffer()
        ok, mapa = b.map(Gst.MapFlags.READ)
        if ok:
            try:
                salida.write(mapa.data[:ancho * alto * 2])
                salida.flush()
                n[0] += 1
            except BrokenPipeError:      # el puente se fue: no tiene sentido seguir capturando
                rotos[0] = 1
            b.unmap(mapa)
        return Gst.FlowReturn.OK

    tuberia = (f"v4l2src device={dispositivo} ! "
               f"video/x-raw,format=YUY2,width={ancho},height={alto},framerate=[1/1,30/1] ! "
               f"appsink name=sk emit-signals=true sync=false max-buffers=2 drop=true")
    pipeline = Gst.parse_launch(tuberia)
    pipeline.get_by_name("sk").connect("new-sample", nuevo)
    lazo = GLib.MainLoop()
    # Sólo velamos el arranque: si en 6 s no ha caído un cuadro, la cámara no da más.
    # Después manda el puente, que apaga el proceso con una señal.
    def velar_arranque():
        if n[0] == 0:
            lazo.quit()
        return False
    GLib.timeout_add_seconds(6, velar_arranque)
    pipeline.set_state(Gst.State.PLAYING)
    lazo.run()
    pipeline.set_state(Gst.State.NULL)
    if rotos[0]:
        return 0
    if n[0] == 0:
        estado, _, _ = pipeline.get_state(0)
        sys.stderr.write(f"cero cuadros (estado {estado.value_nick})\n")
        return 2
    return 0


def selftest() -> int:
    """Cuadros sintéticos: una mancha de piel cruzando el cuadro. Sin cámara, sin inventar."""
    np = _np()

    def cuadro(cx=None, cy=0.5, radio=22, piel=True):
        plano = np.zeros((ALTO, ANCHO // 2, 4), dtype=np.uint8)
        plano[:, :, 0] = 90
        plano[:, :, 2] = 90
        plano[:, :, 1] = 128
        plano[:, :, 3] = 128
        if cx is not None:
            x = int(cx * (ANCHO // 2))
            y = int(cy * ALTO)
            filas = slice(max(0, y - radio), min(ALTO, y + radio))
            cols = slice(max(0, x - radio // 2), min(ANCHO // 2, x + radio // 2))
            plano[filas, cols, 0] = 150
            plano[filas, cols, 2] = 150
            if piel:
                plano[filas, cols, 1] = 128 - 30      # Cb -30
                plano[filas, cols, 3] = 128 + 25      # Cr +25
        return plano.tobytes()

    # a) la mancha existe y se localiza donde se pintó
    m, _ = medida(cuadro(cx=0.25, cy=0.30))
    print(f"mancha en (0.25,0.30) → área {m['area']*100:.2f} % centro ({m['cx']},{m['cy']})")
    ok_a = m["cx"] is not None and abs(m["cx"] - 0.25) < 0.06 and abs(m["cy"] - 0.30) < 0.06

    # b) cuadro sin piel: área cero y ningún gesto
    m_vacio, _ = medida(cuadro())
    ok_b = m_vacio["area"] < AREA_MINIMA and gesto([m_vacio] * 6) is None

    # c) barrido de izquierda a derecha en 8 cuadros
    ventana = []
    t = 0.0
    for i in range(8):
        mm, _ = medida(cuadro(cx=0.15 + i * 0.10))
        mm["t"] = t
        t += 0.09
        ventana.append(mm)
    g = gesto(ventana)
    ok_c = bool(g and g["gesto"] == "barrido_derecha")
    print("barrido:", g)

    # d) levantar la mano
    ventana = []
    t = 0.0
    for i in range(6):
        mm, _ = medida(cuadro(cx=0.5, cy=0.8 - i * 0.10))
        mm["t"] = t
        t += 0.1
        ventana.append(mm)
    g2 = gesto(ventana)
    ok_d = bool(g2 and g2["gesto"] == "levantar_mano")
    print("levantar:", g2)

    # e) el color de la pared no es una mano (piel falsa = croma equivocado)
    mf, _ = medida(cuadro(cx=0.5, piel=False))
    ok_e = mf["area"] < AREA_MINIMA
    print(f"muro sin croma de piel → área {mf['area']*100:.2f} %")

    # f) UNA PERSONA SENTADA QUIETA DELANTE DE LA CÁMARA. Este caso no es teórico: es
    # lo que midió la webcam real el 2026-11-04 — área 15 %, centro (0,53 / 0,28),
    # `mov` 0,0000–0,0003 — y con la regla vieja disparaba `palma_arriba` ocho veces
    # en ocho segundos, maximizando ventanas mientras nadie hacía nada.
    ventana = []
    t, luma_prev = 0.0, None
    for i in range(12):
        mm, luma_prev = medida(cuadro(cx=0.53, cy=0.28, radio=60), luma_prev)
        mm["t"] = t
        t += 0.066
        ventana.append(mm)
    g3 = gesto(ventana)
    mov_max = max((m["mov"] or 0.0) for m in ventana)
    ok_f = g3 is None
    print(f"persona quieta (área {ventana[-1]['area']*100:.1f} %, mov {mov_max*100:.2f} %) → {g3}")

    # g) la palma que DE VERDAD llega: cuadro vacío, aparece la mano moviendo píxeles.
    ventana = []
    t, luma_prev = 0.0, None
    for i in range(10):
        bruto = cuadro() if i < 3 else cuadro(cx=0.53, cy=0.28, radio=60)
        mm, luma_prev = medida(bruto, luma_prev)
        mm["t"] = t
        t += 0.066
        ventana.append(mm)
    g4 = gesto(ventana)
    ok_g = bool(g4 and g4["gesto"] == "palma_arriba")
    print("palma que llega:", g4)

    casos = [("la mancha se localiza", ok_a), ("cuadro vacío no dispara", ok_b),
             ("barrido derecha", ok_c), ("levantar la mano", ok_d),
             ("un muro no es una mano", ok_e),
             ("una persona quieta no es un gesto", ok_f),
             ("la palma que llega sí lo es", ok_g)]
    for nombre, ok in casos:
        print(f"{'ok  ' if ok else 'FALLO'} {nombre}")
    return 0 if all(ok for _, ok in casos) else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "captura":
        dev = sys.argv[2] if len(sys.argv) > 2 else "/dev/video0"
        w = int(sys.argv[3]) if len(sys.argv) > 3 else ANCHO
        h = int(sys.argv[4]) if len(sys.argv) > 4 else ALTO
        f = int(sys.argv[5]) if len(sys.argv) > 5 else FPS_MIRADA
        if (w, h) != (ANCHO, ALTO):
            sys.stderr.write("el worker sólo sirve el tamaño declarado por el puente\n")
            sys.exit(4)
        sys.exit(captura_continua(dev, w, h, f))
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.exit(selftest())
    print(__doc__)
