#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# audita-apk.sh — lee el APK TERMINADO y dice, medido, si es instalable.
#
# Por qué existe: la dueña reportó «me bloquea Google / Play Protect, no me deja
# instalarlo». Antes de responder con teoría, se bajó el `CORT-IA-2.3.0.apk` ya
# publicado y se leyó byte a byte. Salió bien firmado y bien alineado, así que el
# bloqueo no era del APK. Este script convierte esa comprobación en algo que pasa
# en CADA Release y viaja público al lado del `.apk` (en `firma.txt`), porque los
# registros de Actions dan 403 sin sesión: lo que no está en el artefacto, no está.
#
# Qué mira, y por qué cada cosa es un motivo real de que el instalador diga no:
#
#   * que el ZIP abrade y no esté truncado  → «INSTALL_PARSE_FAILED_NOT_APK», el
#     clásico de la descarga a medias por Wi‑Fi floja.
#   * sha256 y peso                         → distingue «el APK está mal» de «el
#     archivo que bajaste no es el publicado».
#   * esquemas de firma v1 / v2 / v3        → con `targetSdk 34` hace falta v2 o
#     superior; la v1 (`META-INF/`) es la única legible por `keytool` y por
#     muchos exploradores, incluidos los de los teléfonos mayores.
#   * ventana de validez del certificado    → un auto-firmado «aún no válido» o
#     caducado se presenta en el teléfono como bloqueo de seguridad. Si el reloj
#     del teléfono va mal, el culpable es el reloj, y con la ventana publicada se
#     puede decir con datos.
#   * `resources.arsc` sin comprimir y      → desde Android 11 (API 30) es
#     alineado a 4                            obligación; si falla, no instala.
#   * `minSdk` / `targetSdk`                → `INSTALL_FAILED_OLDER_SDK` en
#     Android 7 o anterior.
#   * `android:debuggable` / `testOnly`     → un APK de pruebas declarado como
#     tal NO se instala normal y Play Protect lo marca.
#
# Uso:  bash scripts/audita-apk.sh <ruta.apk> [carpeta-de-build-tools]
# Sale 0 si todo está bien; 1 si algo está MAL (y entonces el pipeline se pone
# rojo: no se publica un APK que no se pueda instalar).
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

APK="${1:-}"
BT="${2:-}"
[ -n "$APK" ] || { echo "uso: audita-apk.sh <ruta.apk> [build-tools]"; exit 2; }
[ -f "$APK" ] || { echo "no existe $APK"; exit 2; }

echo "auditoría de instalabilidad (leída del APK final, no supuesta):"

# La carpeta de build-tools llega al python por entorno: el here-doc de abajo no
# recibe argumentos aparte de la ruta del APK, y `aapt dump badging` es lo único
# que lee el manifiesto BINARIO (el `.xml` del repo ya no existe en el APK).
export CORT_BUILD_TOOLS="$BT"

python3 - "$APK" <<'PY'
import hashlib, os, struct, subprocess, sys, zipfile

apk = sys.argv[1]
MAL = []

# ── 1 · que el archivo sea un ZIP completo ────────────────────────────────────
try:
    z = zipfile.ZipFile(apk)
    malo = z.testzip()          # None si ningún CRC de entrada está roto
    entradas = z.infolist()
except Exception as e:                                     # noqa: BLE001
    print(f"   · ZIP: MAL — no abre ({e}); la descarga está cortada")
    sys.exit(1)
print(f"   · ZIP: OK — {len(entradas)} entradas, CRC íntegro"
      + ("" if malo is None else f" (MAL en {malo})"))
if malo is not None:
    MAL.append(f"entrada corrupta {malo}")

peso = os.path.getsize(apk)
sha = hashlib.sha256(open(apk, "rb").read()).hexdigest()
print(f"   · peso: {peso:,} bytes  ·  sha256: {sha}")
print("     (si tu descarga no pesa esto exacto, el archivo no es el publicado)")

# ── 2 · los tres esquemas de firma, leídos del propio archivo ─────────────────
# La v1 se ve en META-INF; la v2 y la v3 viven en el «APK Signing Block», un
# bloque anónimo justo antes del Central Directory. Se buscan sus identificadores
# en little-endian en esa cola del archivo: es una lectura directa, no confiar en
# lo que imprima una herramienta.
BIN = open(apk, "rb").read()
eocd = BIN.rfind(b"PK\x05\x06")
cd = struct.unpack_from("<I", BIN, eocd + 16)[0] if eocd >= 0 else -1
firma = BIN.rfind(b"APK Sig Block 42")
ID = {0x7109871a: "v2", 0xf05368c0: "v3", 0x1b8f161e: "v3.1", 0x426a8244: "v4"}
esquemas = set()
if firma >= 0:
    for pid, nombre in ID.items():
        if BIN.rfind(struct.pack("<I", pid), max(0, firma - 65536), firma) >= 0:
            esquemas.add(nombre)
v1 = [i.filename for i in entradas if i.filename.upper().startswith("META-INF/")
      and i.filename.upper().endswith((".RSA", ".DSA", ".EC"))]
if v1:
    esquemas.add("v1")
print(f"   · firma: {'+'.join(sorted(esquemas)) or 'NINGUNA'} "
      f"(v1 = {', '.join(v1) or 'no hay archivo META-INF/*.RSA'})")
if "v2" not in esquemas:
    MAL.append("sin esquema v2: Android 11+ no instala un APK con targetSdk 30 o mayor firmado sólo por JAR")
if not esquemas:
    MAL.append("sin ninguna firma legible")

# La contradicción que hay que dejar escrita, no colleoneada. `apksigner verify
# --verbose` imprime «Verified using v1 scheme (JAR signing): false» aunque el APK
# trae `META-INF/CORT.RSA` + `CORT.SF` + `MANIFEST.MF`, y sale con código 0. Medido
# el 2026-10-21 sobre el `CORT-IA-2.3.1.apk` publicado: `keytool -printcert
# -jarfile` lo lee, imprime la huella `fa:ab:ef:46…` y termina en 0 sin una sola
# queja — o sea que la v1 está y verifica. `apksigner` reserva el `true` de esa
# línea para el caso en que la v1 hicera falta para instalar, y con `minSdk 26`
# nunca hace falta: Android 8+ comprueba el bloque v2/v3 (y ahí la hoja dice
# `true`). Como la instalación encima del anterior depende de la LLAVE y no del
# esquema, aquí se comprueba la v1 con una herramienta distinta en vez de discutir
# la semántica de `apksigner`.
import shutil
kt = shutil.which("keytool") or os.environ.get("JAVA_HOME", "") + "/bin/keytool"
if not (kt and os.path.exists(kt)):
    print("   · v1 comprobada por fuera: sin `keytool` a mano (no invalida nada)")
else:
    k = subprocess.run([kt, "-printcert", "-jarfile", apk], capture_output=True, text=True)
    quejas = [l for l in (k.stdout + k.stderr).splitlines()
              if any(w in l.lower() for w in ("verification failed", "fall", "error"))]
    # `keytool` imprime `	 SHA256: FA:AB:…:77`, así que se parte por el primer
    # `SHA256:` (no por `:`, que se quedaría con el último byte del hash).
    huella = ""
    for l in k.stdout.splitlines():
        if "SHA256:" in l:
            huella = l.split("SHA256:", 1)[1].strip().replace(":", "")
            break
    if k.returncode == 0 and not quejas:
        print(f"   · v1 verificada con keytool: sí (huella {huella[:16]}…)")
    else:
        print(f"   · v1 verificada con keytool: NO — sale {k.returncode}: "
              f"{(quejas[:1] or ['sin detalle'])[0][:120]}")
        MAL.append("la firma v1 no verifica según keytool")

# ── 3 · recursos: sin comprimir y alineados (obligatorio desde API 30) ────────
try:
    i = z.getinfo("resources.arsc")
    with open(apk, "rb") as f:
        f.seek(i.header_offset)
        cab = f.read(30)
        nombre_l, extra_l = struct.unpack("<HH", cab[26:30])
        f.seek(i.header_offset + 30 + nombre_l + extra_l)
        desvío = f.tell()
    modo = "SIN comprimir" if i.compress_type == 0 else "COMPRIMIDO (deflate)"
    alinea = "alineado a 4" if desvío % 4 == 0 else f"DESALINEADO (offset {desvío})"
    print(f"   · resources.arsc: {modo}, {alinea} · {i.file_size:,} B")
    if i.compress_type != 0:
        MAL.append("resources.arsc comprimido: Android 11+ puede rechazar la instalación")
    if desvío % 4:
        MAL.append("resources.arsc desalineado: zipalign no corrío")
except KeyError:
    print("   · resources.arsc: no existe (este APK no lo necesita para nada)")

# ── 4 · las `.so` del oído ───────────────────────────────────────────────────
so = [i for i in entradas if i.filename.startswith("lib/") and i.filename.endswith(".so")]
abis = sorted({i.filename.split("/")[1] for i in so})
print(f"   · librerías nativas: {len(so)} en {abis or 'ninguna abi'} — comprimidas, "
      f"legal porque el manifiesto trae extractNativeLibs=\"true\"")

# ── 5 · el certificado: ventana, asunto y huella ─────────────────────────────
# Se lee del PKCS#7 de la firma v1 con `openssl`; si no hay v1 o no hay openssl,
# se dice en vez de fingir. La ventana importa de verdad: el teléfono contrasta
# `Not Before`/`Not After` con SU reloj, así que un móvil desfasado ve un
# certificado «aún no válido» y el resultado es un bloqueo que parece de Play
# Protect pero es de la hora del aparato.
if v1:
    der = z.read(v1[0])
    open("/tmp/cort-audita.rsa", "wb").write(der)
    try:
        p = subprocess.run(["openssl", "pkcs7", "-inform", "DER", "-in", "/tmp/cort-audita.rsa",
                            "-print_certs"], capture_output=True, check=True)
        q = subprocess.run(["openssl", "x509", "-noout", "-subject", "-startdate", "-enddate",
                            "-fingerprint", "-sha256"],
                           input=p.stdout, capture_output=True, check=True)
        datos = {}
        for linea in q.stdout.decode().splitlines():
            clave, _, val = linea.partition("=")
            # `openssl` escribe la huella como `sha256 Fingerprint=…` con la
            # primera letra en minúscula (medido), así que las claves se guardan
            # normalizadas y no se depende del tamaño de letra del runner.
            datos[clave.strip().lower()] = val.strip()
        print(f"   · certificado: {datos.get('subject', '?')}")
        print(f"     válido desde {datos.get('notbefore', '?')} hasta {datos.get('notafter', '?')}")
        print(f"     huella sha256 {(datos.get('sha256 fingerprint') or '?').replace(':', '').lower()}")
    except Exception as e:                                 # noqa: BLE001
        print(f"   · certificado: no se pudo leer con openssl ({e}); "
              f"queda la huella que imprime apksigner más abajo")
else:
    print("   · certificado: sin firma v1 legible; sólo se ve desde Android 7+")

# ── 6 · lo que mira el explorador de Play Protect ────────────────────────────
# Los permisos salen del manifiesto binario con `aapt` si el caller pasó la
# carpeta de build-tools; sin ella se omite el renglón y no se inventa nada.
import pathlib
bt = os.environ.get("CORT_BUILD_TOOLS", "")
if bt and pathlib.Path(bt).is_dir():
    aapt = pathlib.Path(bt) / "aapt"
    if aapt.exists():
        try:
            txt = subprocess.run([str(aapt), "dump", "badging", apk],
                                 capture_output=True, text=True, check=True).stdout
        except Exception:                                  # noqa: BLE001
            txt = ""
        min_sdk = next((l for l in txt.splitlines() if l.startswith("sdkVersion:")), "")
        tgt = next((l for l in txt.splitlines() if l.startswith("targetSdkVersion:")), "")
        print(f"   · android: {min_sdk or 'sdkVersion: ?'} · {tgt or 'targetSdkVersion: ?'}")
        if "application-debuggable" in txt or "testOnly" in txt:
            MAL.append("el APK está marcado como depurable: así NO se instala normal")
        else:
            print("   · depurable (debuggable): no")
        sensibles = [l.split("'")[1] for l in txt.splitlines()
                     if l.startswith("uses-permission:") and any(k in l for k in
                     ("SYSTEM_ALERT_WINDOW", "MANAGE_EXTERNAL_STORAGE", "REQUEST_INSTALL_PACKAGES",
                      "BIND_ACCESSIBILITY", "QUERY_ALL_PACKAGES", "READ_EXTERNAL_STORAGE"))]
        print("   · permisos que Play Protect pesa más: "
              + (", ".join(p.split('.')[-1] for p in sensibles) or "ninguno"))
        if "REQUEST_INSTALL_PACKAGES" in " ".join(sensibles):
            MAL.append("REQUEST_INSTALL_PACKAGES declarado: es el permiso que más bloqueos dispara")
    else:
        print("   · aapt no estaba en la carpeta de build-tools: renglón omitido")
else:
    print("   · (sin build-tools: no se leen minSdk/targetSdk ni el manifiesto binario)")

print("   · VEREDICTO: " + ("INSTALABLE — nada de lo medido da motivo de bloqueo"
                            if not MAL else "MAL — " + "; ".join(MAL)))
sys.exit(1 if MAL else 0)
PY
ESTADO=$?
# Se sale con el veredicto de python: si algo está MAL, `compilar.sh` (que corre
# con `set -e` y con el `tee` en el mismo tubo) para rojo y no se publica un APK
# que no se pueda instalar.
exit $ESTADO
