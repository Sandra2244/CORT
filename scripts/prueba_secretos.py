#!/usr/bin/env python3
"""SPEC-SEC-001: las claves no se guardan ni viajan en ajustes generales.

Usa valores de prueba, un estado temporal y JavaScript evaluado por Node. No lee
`backend/.env`, no abre el estado vivo del puente y no ejecuta acciones reales.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PUENTE = RAIZ / "cort-bridge" / "cort_server.py"
WEB = RAIZ / "cort-web"
ANDROID = RAIZ / "apps" / "android"

RESULTADOS: list[tuple[str, bool, str]] = []


def prueba(nombre: str, ok: bool, detalle: str = "") -> None:
    RESULTADOS.append((nombre, bool(ok), detalle))
    print(f"  [{'ok' if ok else 'FALLO'}] {nombre}" + (f" — {detalle}" if detalle else ""))


def lee(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8") if ruta.is_file() else ""


def node(programa: str) -> tuple[int, str, str]:
    entorno = dict(os.environ, ELECTRON_RUN_AS_NODE="1")
    p = subprocess.run([os.environ.get("CORT_NODE", "node"), "-e", programa],
                       text=True, capture_output=True, timeout=30, env=entorno)
    return p.returncode, p.stdout, p.stderr


def cargar_puente(estado: Path):
    os.environ["CORT_STATE"] = str(estado)
    os.environ["CORT_HOME"] = str(estado.parent)
    os.environ["CORT_DATOS"] = str(estado.parent / "datos")
    spec = importlib.util.spec_from_file_location("cort_server_seguridad", PUENTE)
    if spec is None or spec.loader is None:
        raise RuntimeError("no se pudo cargar el puente")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def main() -> int:
    print("\n== Web: saneamiento y legado ==")
    escudo = WEB / "cort" / "cort-secretos.js"
    prueba("existe el escudo cort-secretos.js", escudo.is_file(), str(escudo.relative_to(RAIZ)))
    mock = lee(WEB / "cort" / "cort-mock.js")
    html = lee(WEB / "index.html")
    prueba("el escudo se carga antes que el mock y el bundle",
           html.find("cort/cort-secretos.js") >= 0
           and html.find("cort/cort-secretos.js") < html.find("cort/cort-mock.js")
           and html.find("cort/cort-secretos.js") < html.find("assets/main-"))
    prueba("el mock no conserva objetos arbitrarios sin sanear",
           "CORTsecretos.sanear" in mock and "CORTsecretos.tieneSecretos" in mock)

    if escudo.is_file():
        codigo, salida, error = node(f"""
const almacen = globalThis;
globalThis.window = globalThis;
const storage = new Map();
const localStorage = {{
  getItem: k => storage.has(k) ? storage.get(k) : null,
  setItem: (k, v) => storage.set(k, v),
  removeItem: k => storage.delete(k)
}};
{escudo.read_text()}
const original = {{
  user_city: 'Madrid',
  api_keys: {{ GEMINI_API_KEY: 'clave-de-prueba' }},
  clave: 'otra-de-prueba',
  proveedor_API_KEY: 'tercera-de-prueba',
  access_token: 'token-de-prueba',
  usuario_password: 'password-de-prueba',
  anidado: [{{ nombre: 'CORT', secret: 'secreto-de-prueba' }}, 'conservar']
}};
const limpio = CORTsecretos.sanear(original);
if ('api_keys' in limpio || 'clave' in limpio || 'proveedor_API_KEY' in limpio ||
    'access_token' in limpio || 'usuario_password' in limpio || 'secret' in limpio.anidado[0]) {{
  throw new Error('quedó una propiedad sensible');
}}
if (limpio.user_city !== 'Madrid' || limpio.anidado[1] !== 'conservar') throw new Error('perdió datos públicos');
if (!original.api_keys || original.clave !== 'otra-de-prueba') throw new Error('mutó el original');
localStorage.setItem('cort_web_v1', JSON.stringify(original));
CORTsecretos.purgarLegado();
const guardado = JSON.parse(localStorage.getItem('cort_web_v1'));
if ('clave' in guardado || 'api_keys' in guardado || guardado.user_city !== 'Madrid') {{
  throw new Error('el legado no quedó limpio');
}}
process.stdout.write('ok');
""")
        prueba("SEC-01/02: saneamiento recursivo, copia y purga del legado", codigo == 0,
               salida.strip() or "\n".join(error.strip().splitlines()[:3]))
    else:
        prueba("SEC-01/02: saneamiento recursivo, copia y purga del legado", False,
               "falta el escudo")

    prueba("SEC-03: update_settings no se reenvía con secretos",
           'if (type === "update_settings" && msg.settings && CORTsecretos.tieneSecretos(msg.settings))' in mock
           and "CORTsecretos.sanear" in mock
           and "no se guardaron claves" in mock.lower())

    print("\n== Puente PC: estado, allowlist y permisos ==")
    with tempfile.TemporaryDirectory(prefix="cort-secretos-") as tmp:
        estado = Path(tmp) / "estado.json"
        estado.write_text(json.dumps({
            "user_city": "Madrid",
            "api_keys": {"GEMINI_API_KEY": "clave-de-prueba"},
            "nested": {"clave": "otra-de-prueba", "secret": "tercera-de-prueba", "public": 7},
            "desconocido": "no debe salir en ajustes"
        }), encoding="utf-8")
        try:
            puente = cargar_puente(estado)
            leido = puente.leer_estado()
            prueba("SEC-04: leer_estado sanea secretos anidados",
                   leido.get("user_city") == "Madrid"
                   and "api_keys" not in leido
                   and "clave" not in leido.get("nested", {})
                   and "secret" not in leido.get("nested", {}))
            texto = estado.read_text(encoding="utf-8")
            prueba("SEC-04: el legado se reescribe sin secretos",
                   "clave-de-prueba" not in texto and "otra-de-prueba" not in texto
                   and "tercera-de-prueba" not in texto)
            modo = stat.S_IMODE(estado.stat().st_mode)
            prueba("SEC-04: el estado queda con permisos 0600 (POSIX)",
                   modo == 0o600 if os.name != "nt" else True,
                   oct(modo) if os.name != "nt" else "Windows: ACL se valida en CI Linux")
            puente.escribir_estado({"user_city": "Sevilla", "clave": "no-guardar",
                                    "nested": {"access_token": "tampoco"}})
            texto = estado.read_text(encoding="utf-8")
            prueba("SEC-04: escribir_estado sanea antes de persistir",
                   "no-guardar" not in texto and "tampoco" not in texto)
            settings = puente.ajustes_reales()
            permitidas = {"user_name", "user_age", "user_city", "language",
                          "local_model", "reminders", "shopping"}
            prueba("SEC-05: ajustes_reales usa allowlist", set(settings) <= permitidas,
                   ", ".join(sorted(settings)))
        except Exception as exc:
            prueba("cargar y ejercitar el puente en arena", False, f"{type(exc).__name__}: {exc}")

    fuente = lee(PUENTE)
    bloque_ajustes = fuente[fuente.find('elif t in ("settings-save"'):][:1200]
    prueba("el puente no persiste claves recibidas en update_settings",
           "sanear" in bloque_ajustes and "CAMPOS_SENSIBLES" in fuente)
    prueba("la escritura del puente es atómica y fija 0600",
           "os.replace" in fuente and "fsync" in fuente and "0o600" in fuente)
    prueba("cada escritura del puente usa un temporal único",
           "tempfile.mkstemp" in fuente and 'ESTADO.name + ".tmp"' not in fuente)

    print("\n== Android: sobre, migración y consentimiento ==")
    sobre = lee(ANDROID / "src" / "dev" / "sandra" / "cort" / "movil" / "SobreSecreto.java")
    nube = lee(ANDROID / "src" / "dev" / "sandra" / "cort" / "movil" / "Nube.java")
    cara = lee(ANDROID / "src" / "dev" / "sandra" / "cort" / "movil" / "Cara.java")
    nexo = lee(ANDROID / "src" / "dev" / "sandra" / "cort" / "movil" / "Nexo.java")
    build = lee(ANDROID / "compilar.sh")
    prueba("SEC-06: SobreSecreto usa AES/GCM, IV y AAD versionados",
           all(x in sobre for x in ("AES/GCM/NoPadding", "GCMParameterSpec", '"v1"'))
           and "new byte[IV_BYTES]" in sobre and "128" in sobre)
    prueba("SEC-06: Nube crea la llave AES-256 en AndroidKeyStore",
           "AndroidKeyStore" in nube and "KeyGenParameterSpec" in nube and ".setKeySize(256)" in nube)
    prueba("Nube exige una clave descifrable y la abre una vez por petición",
           "return p != null && !clave(p).isEmpty()" in nube
           and "String claveApi = clave(p)" in nube
           and "if (claveApi.isEmpty()) return null" in nube
           and 'conexion.setRequestProperty("x-api-key", claveApi)' in nube
           and 'conexion.setRequestProperty("Authorization", "Bearer " + claveApi)' in nube)
    prueba("SEC-07: Nube cifra y no escribe la clave plana",
           "SobreSecreto" in nube and '.putString("clave"' not in nube
           and "commit()" in nube)
    prueba("SEC-07: un commit rechazado deja la clave inutilizable en el proceso",
           "guardadoRechazado" in nube and "if (!editor.commit())" in nube
           and "guardadoRechazado = true" in nube)
    prueba("SEC-08: existe borrado de sobre, alias y legado",
           "borrarClave()" in nube and "deleteEntry" in nube and ".remove(CLAVE_PLANA)" in nube)
    prueba("SEC-08: persiste el borrado antes de eliminar el alias",
           0 <= nube.find(".putString(CLAVE_PERFILES, j.toString()).commit()",
                         nube.find("public void borrarClave"))
           and 0 <= nube.find("if (!prefs.edit().putString(CLAVE_PERFILES, j.toString())",
                              nube.find("public boolean borrarPerfil"))
           < nube.find("if (!quedaClave) borrarAlias()", nube.find("public boolean borrarPerfil")))
    prueba("la pantalla no muestra la longitud del secreto",
           "nube.clave().length()" not in cara and "hayClave()" in cara)
    prueba("SEC-10: el modo local bloquea la nube en Cara y Nexo",
           '"local".equals(cerebroLocal.modo())' in cara
           and '"local".equals(cerebroLocal.modo())' in nexo)
    prueba("SEC-11: el modo automático pide consentimiento",
           "pedirConsentimientoNube" in cara and "pedirConsentimientoNube" in nexo)
    prueba("SEC-11: negar, cancelar o agotar la espera no habilita la nube",
           all("decision.await(120, TimeUnit.SECONDS) && permitido[0]" in fuente
               and "import android.app.AlertDialog;" in fuente
               and '.setNegativeButton("No, seguir local", (d, w) -> decision.countDown())' in fuente
               and ".setOnCancelListener(d -> decision.countDown())" in fuente
               for fuente in (cara, nexo)))
    prueba("el build ejecuta SecretoTest antes de dex",
           "SecretoTest.java" in build and build.find("SecretoTest.java") < build.find('"$BT/d8"'))

    puente_js = lee(ANDROID / "web" / "cort-android.js")
    planes = lee(ANDROID / "src" / "dev" / "sandra" / "cort" / "movil" / "Planes.java")
    integridad = lee(ANDROID / "src" / "dev" / "sandra" / "cort" / "movil" / "IntegridadGguf.java")
    cerebro = lee(ANDROID / "src" / "dev" / "sandra" / "cort" / "movil" / "CerebroLocal.java")
    apk = lee(RAIZ / ".github" / "workflows" / "apk-movil.yml")
    motor = lee(RAIZ / ".github" / "workflows" / "motor-local.yml")
    prueba("el puente WebView exige token y lo revoca al cerrar",
           "autorizado(String token)" in nexo and "tokenPuente.equals(token)" in nexo
           and 'tokenPuente = ""' in nexo and "window.__cortPuenteToken" in nexo
           and "NATIVA.recibir(token," in puente_js)
    prueba("los permisos WebView sólo se conceden al origen de CORT",
           'if (!ORIGEN.equals(pedido.getOrigin().toString()))' in nexo and "pedido.deny()" in nexo)
    prueba("la nube usa endpoints oficiales y no sigue redirecciones",
           "ProveedorNube.baseOficial" in nube and "setInstanceFollowRedirects(false)" in nube
           and "base.readOnly = true" in lee(WEB / "cort" / "cort-ui.js"))
    prueba("un plan cuya actividad terminó no ejecuta su acción tardía",
           "if (!valido.get() || actividad.isFinishing() || actividad.isDestroyed())" in planes
           and "planes.ejecutarPaso(paso)" in nexo)
    prueba("toda carga GGUF pasa por tamaño y SHA-256 antes de abrir el descriptor",
           "IntegridadGguf.verificar" in cerebro and "cargarSeguro(Ficha ficha" in cerebro
           and "private int cargar(File gguf" in cerebro
           and "nativeAbrirDescriptor" in cerebro and "/proc/self/fd/" in lee(RAIZ / "apps" / "android" / "jni" / "cort_motor.cpp")
           and 'MessageDigest.getInstance("SHA-256")' in integridad
           and "IntegridadGgufTest.java" in build)
    prueba("el estado nativo es único y se revalida antes de reutilizarlo",
           "private static volatile File activo" in cerebro
           and "ultimoMotivo = verificar(preferida)" in cerebro
           and "synchronized (CERRADURA)" in cerebro)
    prueba("cerrar el motor desde la interfaz no libera cientos de MB en el hilo principal",
           "Looper.myLooper() == Looper.getMainLooper()" in cerebro
           and 'new Thread(this::cerrar, "cort-cierra-cerebro")' in cerebro)
    prueba("un GGUF dañado se puede volver a bajar y no se ofrece al agente",
           "public boolean esta(CerebroLocal.Ficha ficha)" in lee(ANDROID / "src" / "dev" / "sandra" / "cort" / "movil" / "Bajada.java")
           and "cerebroLocal.verificar(f).isEmpty()" in nexo
           and "cerebro.verificar(d).isEmpty()" in lee(ANDROID / "src" / "dev" / "sandra" / "cort" / "movil" / "Cerebros.java"))
    prueba("planes y rutinas distinguen una acción fallida de una respuesta completada",
           "Resultado ejecutarTipado" in lee(ANDROID / "src" / "dev" / "sandra" / "cort" / "movil" / "Acciones.java")
           and "!salida.ok" in planes
           and "ejecutor.ejecutarConEstado" in lee(ANDROID / "src" / "dev" / "sandra" / "cort" / "movil" / "Rutinas.java"))
    prueba("CI ata motor, commit, hashes y certificado anterior",
           "uses: ./.github/workflows/motor-local.yml" in apk
           and "actions/download-artifact@v4" in apk
           and 'grep -Fx "commit CORT: $COMITE"' in apk
           and "sha256sum -c motor-sha256.txt" in apk
           and "commit CORT: $(git rev-parse HEAD)" in motor
           and "CORT_EXIGIR_MOTOR" in apk and "CORT_EXIGIR_FIRMA" in apk
           and "faabef468f3ae04fdfab9659d6a051c453d6ded7b965468c9c3b85caffa31977" in apk)

    print("\n== Interfaz: sólo capacidades reales ==")
    api = html[html.find('id="api-keys-modal"'):html.find('id="nemotron-modal"')]
    prueba("SEC-09: el aviso Web reemplaza las diez claves sin adaptador",
           api.count('id="api-keys-modal"') == 1
           and 'type="password"' not in api and "settings-api-" not in api
           and "no se guardan claves" in api.lower())
    selector = html[html.index('<select id="settings-preferred-brain"'):html.index('</select>', html.index('<select id="settings-preferred-brain"')) + len('</select>')]
    grupo_cerebro = html[html.rfind('<div class="settings-group"', 0, html.index('<select id="settings-preferred-brain"')):html.index('id="local-model-selector-wrap"')]
    prueba("SEC-09: el selector Web sólo ofrece rutas locales reales",
           selector.count("<option") == 3
           and all(x not in selector.lower() for x in
                   ("gemini", "groq", "grok", "openai", "claude", "mistral"))
           and "nube no está disponible" in grupo_cerebro.lower())
    prueba("SEC-09: el aviso Web no contiene campos de clave",
           'type="password"' not in api and "settings-api-" not in api
           and "no se guardan claves" in api.lower())
    prueba("SEC-09: ningún panel Web ofrece campos de clave",
           'type="password"' not in html and "tone-api-xai-key" not in html)
    prueba("SEC-09: no queda un selector oculto de nube sin adaptador",
           'id="realtime-voice-selector-wrap"' not in grupo_cerebro
           and 'id="settings-realtime-model"' not in grupo_cerebro
           and "redirigé vers xai grok" not in html.lower())

    fallos = sum(not ok for _, ok, _ in RESULTADOS)
    print(f"\n{len(RESULTADOS) - fallos}/{len(RESULTADOS)} comprobaciones de secretos")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
