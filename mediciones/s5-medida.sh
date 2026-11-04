#!/usr/bin/env bash
# S5 — la pregunta «¿y si escribiéramos partes en C?» contestada con números.
#
# Compila un ayudante de X11 de 34 líneas que SOLO LEE la lista de ventanas
# (no mueve, no activa, no cierra: por eso se puede correr en el equipo real)
# y lo pone al lado de lo que CORT usa hoy: wmctrl, xdotool y el propio Python.
#
# Uso:  bash mediciones/s5-medida.sh
set -e
AQUI="$(cd "$(dirname "$0")" && pwd)"
PY="${PY:-.venv/bin/python}"
[ -x "$PY" ] || PY=python3

echo "== herramienta"
gcc --version | head -1
echo "Xlib.h: $(ls /usr/include/X11/Xlib.h 2>/dev/null || echo ausente)"

echo
echo "== compilar"
T0=$(date +%s%N)
gcc -O2 -o "$AQUI/s5-ventanas" "$AQUI/s5-ventanas.c" -lX11
T1=$(date +%s%N)
echo "tarda $(( (T1-T0)/1000000 )) ms · binario $(stat -c%s "$AQUI/s5-ventanas") bytes"

echo
echo "== leer las ventanas reales (5 corridas, mediana)"
"$PY" - "$AQUI/s5-ventanas" <<'EOF'
import statistics, subprocess, sys, time
ruta = sys.argv[1]
py = sys.executable

def mediana(cmd, n=5):
    t = []
    for _ in range(n):
        a = time.perf_counter()
        subprocess.run(cmd, capture_output=True)
        t.append((time.perf_counter() - a) * 1000)
    return round(statistics.median(t), 1), round(min(t), 1)

casos = [("ayudante C (s5-ventanas)", [ruta]),
         ("wmctrl -l", ["wmctrl", "-l"]),
         ("xdotool getactivewindow", ["xdotool", "getactivewindow"]),
         ("python -c pass (intérprete frío)", [py, "-c", "pass"])]
for nombre, cmd in casos:
    try:
        med, minimo = mediana(cmd)
        print(f"{nombre:38s} mediana {med:6.1f} ms   mínima {minimo:6.1f} ms")
    except FileNotFoundError:
        print(f"{nombre:38s} no está instalado en este equipo")
EOF

echo
echo "== y desde un Python YA en marcha (lo que de verdad paga CORT por orden)"
"$PY" - "$AQUI/s5-ventanas" <<'EOF'
import statistics, subprocess, sys, time
ruta = sys.argv[1]
def dentro(cmd, n=7):
    t = []
    for _ in range(n):
        a = time.perf_counter()
        subprocess.run(cmd, capture_output=True)
        t.append((time.perf_counter() - a) * 1000)
    return round(statistics.median(t), 1)
print(f"  wmctrl -l              {dentro(['wmctrl','-l']):5.1f} ms por orden")
print(f"  xdotool getactivewindow {dentro(['xdotool','getactivewindow']):5.1f} ms por orden")
print(f"  ayudante C             {dentro([ruta]):5.1f} ms por orden")
EOF

echo
echo "Nota: el binario se compila en esta carpeta y se borra al terminar; el repo no cambia."
rm -f "$AQUI/s5-ventanas"
