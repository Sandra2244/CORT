# SPEC-ANDROID-001 — Decisión de RAM para cargar un GGUF

- **Estado:** VERIFICADA
- **Prioridad:** P0
- **Plataforma:** Android
- **Reportado por:** Sandra y revisión estática del código
- **Fecha:** 2026-11-24
- **Backlog:** CORT-AND-005

## Problema

Sandra describe que un cerebro se descarga, pero no carga o no ejecuta cuando no hay suficiente RAM libre. El código tiene dos umbrales en `apps/android/src/dev/sandra/cort/movil/CerebroLocal.java:157-176`:

- carga holgada: archivo más 200 MiB de reserva;
- intento con `mmap`: mitad del archivo más mitad de la reserva.

Hechos verificados:

1. Ambos comparan con `>`, no con `>=`. Una cantidad exactamente igual al umbral se rechaza.
2. La puerta se calcula en bytes, pero el texto dice «MB» aunque divide entre 1024 dos veces; la unidad mostrada es MiB.
3. `scripts/prueba_apk.py:703-705` sólo busca las fórmulas como texto. No comprueba valores límite, redondeo ni desbordamiento.
4. `AutoCerebro.java:107-168` usa `cabe()` para descargar en modo `auto`; la apertura automática usa `sePuedeIntentar()`. Las rutas manuales pueden forzar la apertura. La puerta estricta no bloquea toda carga.
5. `ActivityManager.MemoryInfo.availMem` es una estimación del sistema, no una reserva garantizada para CORT.
6. La suite estática de línea base pasa 234/234. Eso no demuestra que un GGUF cargue en el A16.
7. Existe un cambio local previo en `CerebroLocal.asegurar()` que, en modo `auto`, busca otro modelo descargado si el elegido no sirve. Debe conservarse; no se atribuye a este parche.

Hipótesis todavía sin confirmar: la puerta de RAM explica el fallo concreto del teléfono. La carga nativa también puede fallar por el archivo, la librería o el motor; este corte no lo da por resuelto.

## Resultado esperado

CORT decide con bytes exactos si un modelo cabe holgado, si sólo debe intentarse con `mmap` o si no debe intentarse. El número que muestra está etiquetado en MiB y una prueba automática comprueba los umbrales.

## Alcance

- Incluye:
  - extraer la decisión numérica a una clase Java sin dependencias Android;
  - usar comparaciones inclusivas y seguras ante valores grandes;
  - conservar la reserva de 200 MiB y el suelo de `mmap`;
  - mostrar la puerta como MiB enteros en los textos nativos;
  - añadir una prueba de comportamiento y ejecutarla en el build de CI;
  - preservar el cambio previo de selección automática.
- No incluye:
  - bajar la reserva o prometer que `mmap` siempre carga;
  - cambiar `llama.cpp`, la descarga o la verificación SHA-256;
  - renombrar las claves del protocolo con la PC;
  - afirmar que el A16 ya carga un modelo sin una prueba física.

## Decisiones de comportamiento

- Unidad interna: **bytes**.
- Unidad mostrada: **MiB**, donde 1 MiB = 1 048 576 bytes.
- Reserva de contexto: **209 715 200 bytes** (200 MiB).
- Redondeo mostrado: hacia abajo, sin decimales. No convierte un umbral en una promesa de RAM disponible.
- Para un modelo válido mayor que cero y RAM libre no negativa:
  - **CABE** si `libre >= modelo + reserva`;
  - **INTENTAR** si no cabe holgado, pero `libre >= modelo / 2 + reserva / 2`;
  - **NO_CABE** en cualquier otro caso.
- Las divisiones de la mitad son enteras hacia abajo. La reserva es par, así que no hay ambigüedad en su mitad.
- Modelo menor o igual que cero, o RAM libre negativa: **NO_CABE**.
- La suma de la puerta completa no debe desbordarse. La implementación puede comparar restando la reserva cuando `libre >= reserva`.
- El intento con `mmap` sólo abre la puerta a un intento; el resultado de `nativeAbrir` sigue siendo quien confirma si el modelo quedó cargado.

## Criterios de aceptación

- [x] **CA-1 — Dado** un modelo y RAM exactamente igual a `modelo + reserva`, **cuando** se evalúa, **entonces** el estado es `CABE`.
- [x] **CA-2 — Dado** un byte menos que la puerta holgada, **cuando** se evalúa, **entonces** el estado es `INTENTAR`, no `NO_CABE`.
- [x] **CA-3 — Dado** RAM exactamente igual a `modelo / 2 + reserva / 2`, **cuando** se evalúa, **entonces** el estado es `INTENTAR`.
- [x] **CA-4 — Dado** un byte menos que el suelo de `mmap`, **cuando** se evalúa, **entonces** el estado es `NO_CABE`.
- [x] **CA-5 — Dado** tamaño de modelo no positivo o RAM negativa, **cuando** se evalúa, **entonces** el estado es `NO_CABE` y no hay desbordamiento.
- [x] **CA-6 — Dados** los cuatro tamaños del catálogo, **cuando** se calcula la puerta mostrada, **entonces** sale 595, 668, 918 y 1265 MiB respectivamente.
- [x] **CA-7 — Cuando** `CerebroLocal` consulta la puerta, **entonces** delega en la decisión pura y conserva el intento de carga nativo y la selección automática previa.
- [x] **CA-8 — Cuando** termina la compilación Java, **entonces** la prueba de comportamiento corre antes de empaquetar y un fallo detiene el build.
- [x] **CA-9 — Cuando** se reporta este corte, **entonces** se distinguen prueba local, build de CI pendiente y prueba física en A16 pendiente.

## Casos de borde

- Umbral holgado exacto y un byte por debajo.
- Umbral de `mmap` exacto y un byte por debajo.
- Tamaño de modelo impar.
- Tamaño enorme que podría desbordar una suma `long`.
- Archivo local ausente, de otro tamaño o sin permiso de lectura: sigue siendo responsabilidad de la selección existente, no de la decisión numérica.
- RAM libre que cambia entre la comprobación y la apertura: el motor puede devolver error aunque la decisión dijera `CABE` o `INTENTAR`.

## Plan

1. Escribir `apps/android/tests/PuertaRamTest.java` y ejecutarlo antes de crear la clase de producción; debe fallar.
2. Crear `PuertaRam.java` con la decisión y la conversión; delegar desde `CerebroLocal`.
3. Ejecutar la prueba de comportamiento y la suite estática.
4. Enganchar la prueba en `apps/android/compilar.sh` para que corra en CI.
5. Registrar resultados y límites sin publicar ni hacer commit.

## Pruebas

| ID | Tipo | Comando o procedimiento | Resultado |
|---|---|---|---|
| T-01 | estática | `python3 scripts/prueba_apk.py` | 234/234 antes y 237/237 después; verde |
| T-02 | comportamiento | Compilar `PuertaRam.java` y `PuertaRamTest.java` con `java -m jdk.compiler/com.sun.tools.javac.Main -source 11 -target 11` en un directorio temporal y ejecutar `dev.sandra.cort.movil.PuertaRamTest` | roja por clase ausente; después 17/17, verde |
| T-03 | build | `apps/android/compilar.sh` en GitHub Actions | commit `6755e62`, run `45516435873`, job `138876957062`: success; 80 s; 237/237 en el runner |
| T-04 | dispositivo | En el A16: elegir un GGUF pequeño, intentar cargarlo y registrar RAM y error nativo | pendiente; no hay `adb` ni acceso físico |

## Evidencia

- Diff de este corte: `PuertaRam.java`, `PuertaRamTest.java`, `CerebroLocal.java`, `Nexo.java`, `Cerebros.java`, `Equipo.java`, `compilar.sh`, `scripts/prueba_apk.py` y esta SPEC.
- Fecha y entorno: 2026-11-24; Linux, OpenJDK 21 runtime con `jdk.compiler`, Python 3.13.5.
- Prueba roja: el compilador terminó con código 2 porque `PuertaRam.java` no existía.
- Prueba verde: `RAM: 17/17 comprobaciones`.
- Suite estática: 234/234 antes y 237/237 después.
- Validaciones adicionales: `bash -n apps/android/compilar.sh` y `git diff --check` sin errores.
- Selección previa: se comparó `asegurar()` con su respaldo ignorando espacios; la lógica es idéntica y sólo se normalizó la indentación.
- Respaldo: cinco archivos copiados y verificados por SHA-256 antes de editar.
- Publicación: commit `6755e62` en `web/cort-v0`; run de Actions `45516435873`, job `138876957062`, conclusión `success` (80 s).
- La única anotación del runner avisa de que `actions/cache@v4`, `actions/checkout@v4` y `actions/upload-artifact@v4` usan Node.js 20, forzado a Node.js 24; no es un fallo del parche.
- Límites de verificación: el runtime local no acepta `--release 11`; la prueba local usó `-source 11 -target 11`. CI conserva `--release 11`. No se compiló la APK localmente y no se reprodujo en el teléfono.

## Cambios de requisito

| Fecha | Qué cambió | Por qué | Quién lo aprobó |
|---|---|---|---|
| 2026-11-24 | Se creó la especificación | Convertir CORT-AND-005 en un corte pequeño y verificable | Sandra encargó mejorar CORT con SDD |
