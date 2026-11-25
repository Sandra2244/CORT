# SPEC-SEC-001 — Secretos fuera del almacenamiento general

- **Fecha:** 2026-11-24
- **Verificación local:** 2026-11-25
- **Prioridad:** P0
- **Backlog:** `CORT-SEC-001`
- **Estado:** VERIFICADA
- **Plataformas:** PC y Android
- **Decisión de producto:** cuestionario híbrido `5A` y `6A`

## Necesidad

CORT ofrece proveedores de nube que no ejecuta y permite que claves de API entren en superficies que no fueron diseñadas para guardarlas:

- la Web las conserva dentro de `cort_web_v1` en `localStorage`;
- el puente de PC acepta campos arbitrarios y puede persistirlos en `cort_state.json`;
- Android guarda la clave de `Nube` en claro dentro de `SharedPreferences`;
- la interfaz no distingue con suficiente claridad una capacidad real de una opción heredada sin adaptador;
- el modo local de Android puede recurrir a la nube sin una confirmación específica.

No se leyeron claves reales durante el diagnóstico. La presencia de campos y rutas de persistencia se verificó por código.

## Resultado esperado

1. Ningún valor de clave de API queda persistido por CORT en `localStorage`, estado general del puente ni `SharedPreferences` en claro.
2. La clave nativa de Android se cifra con una llave de AndroidKeyStore y sólo se descifra al usarla.
3. La migración conserva una clave antigua sólo después de cifrarla y verificarla; si falla, CORT informa y no recurre a escribirla en claro.
4. La Web y el puente rechazan campos secretos por nombre, sin inspeccionar sus valores.
5. Las respuestas de ajustes contienen sólo datos públicos declarados; nunca una clave.
6. La interfaz de PC declara que el chat disponible es local/Ollama y retira las opciones de nube sin adaptador.
7. En Android, el modo local no llama a la nube. El modo automático requiere consentimiento para usar la nube.
8. La pantalla de Android explica Keystore sin volver a mostrar el valor guardado.
9. Los archivos de estado escritos por el puente quedan con permisos `0600` y sustitución atómica.
10. Toda afirmación se acompaña de prueba automatizada o se marca como verificación física pendiente.

## Alcance

### Dentro

- Escudo de saneamiento Web cargado antes del mock y del bundle.
- Eliminación del legado secreto de `localStorage`, sin registrar valores.
- Defensa en `cort-mock.js`, `leer_estado()`, `escribir_estado()` y `update_settings` del puente.
- Allowlist para las respuestas de ajustes.
- Nueva clase `SobreSecreto.java` y adaptación de `Nube.java`.
- Eliminación de la clave plana al migrar o borrar.
- Ajustes de Android sin longitud del secreto.
- Consentimiento de nube en las rutas principales de conversación.
- Retiro de la API modal no implementada, del campo xAI del panel de personalidad, del selector oculto OpenAI Realtime y de proveedores no disponibles en la configuración Web.
- Pruebas Python y Java, build Android y evidencia de CI.

### Fuera

- Construir ahora los adaptadores Gemini, OpenAI-compatible o Anthropic para PC. La UI debe decir que no existen hasta `SPEC-HIB-001`.
- Implementar el keyring completo de PC como almacén de claves, porque el chat en la nube de PC todavía no consume claves. Esta fase elimina la persistencia insegura; `SPEC-HIB-001` añadirá custodia y consumo real.
- Sincronizar secretos entre dispositivos o incluirlos en respaldos.
- Rotar automáticamente claves de proveedores.
- Afirmar que un dispositivo concreto ya migró correctamente sin una prueba en ese dispositivo.

## Decisiones de comportamiento

### Nombres de campos sensibles

Se consideran sensibles, sin distinguir mayúsculas:

- `api_keys`
- `clave`
- `secret`
- nombres que terminen en `_api_key`, `_token`, `_secret` o `_password`

La comprobación usa sólo el nombre de la propiedad. No registra, imprime ni inspecciona el valor para decidir si es secreto.

### Web

- `CORTsecretos.sanear(valor)` devuelve una copia sin propiedades sensibles, de forma recursiva.
- `CORTsecretos.purgarLegado()` quita del estado guardado los campos sensibles y conserva los demás ajustes.
- El mock no reenvía al puente un `update_settings` que contenga secretos. Responde con un aviso claro y ajustes saneados.
- `get_settings` y `settings_data` nunca incluyen secretos.
- El bundle minificado no se edita a ciegas: el escudo y el mock son la barrera, y la API modal deja de ofrecer campos de clave.

### Puente PC

- `leer_estado()` sanea antes de devolver el objeto.
- `escribir_estado()` sanea antes de escribir.
- El primer acceso al estado con legado secreto lo reescribe saneado con permisos `0600`.
- La escritura usa un temporal único en el mismo directorio, `flush`, `fsync`, `os.replace` y `chmod(0600)`, para que escrituras simultáneas no compartan el mismo archivo temporal.
- `update_settings` ignora campos sensibles y no los incorpora al estado.
- `ajustes_reales()` es una allowlist de campos públicos.

### Android

- Alias de AndroidKeyStore: `cort-nube-v1`.
- Cifrado AES-256-GCM.
- IV aleatorio de 12 bytes por cada cifrado.
- AAD versionado: bytes de `v1`.
- Tag de autenticación de 128 bits.
- Formato de sobre: `v1|IV_base64|cifrado_y_tag_base64`.
- El sobre se guarda con las preferencias privadas; la clave plana no.
- Migración: descifrar legado no es necesario; se cifra el valor existente, se verifica descifrando y comparando, y recién entonces un único `commit()` guarda el sobre y elimina el campo plano.
- Si cifrado, verificación o commit falla, `Nube` queda sin clave utilizable y no escribe un respaldo en claro. Un commit rechazado marca el fallo en memoria para que el proceso actual tampoco use un sobre que pudo no persistirse.
- `borrarClave()` confirma primero el borrado de preferencias y sólo después elimina el alias; si el primer commit falla, conserva el alias para no destruir la única vía de descifrado y lo informa.
- `hayClave()` consulta presencia, no longitud ni valor descifrado.

### Consentimiento de nube

- `modo == local`: GGUF o tabla local; ninguna ruta llama a `Nube.preguntar`.
- `modo == auto`: GGUF primero; para usar nube se pide confirmación en la interfaz.
- `modo == nube`: se usa la nube configurada, también sólo tras confirmación.
- Una confirmación cubre un turno, no habilita un envío automático permanente.
- Negar, cancelar, destruir la actividad, interrumpir la espera o llegar al límite de 120 segundos termina la espera sin enviar texto.
- Si no se confirma o no hay interfaz disponible, CORT degrada con una respuesta local honesta.
- El análisis de pantalla exige una acción explícita propia; no aprovecha el consentimiento del chat.

## Criterios de aceptación

### SEC-01 — Saneamiento recursivo Web

**Dado** un objeto con `api_keys`, `clave`, `servicio_API_KEY`, `access_token` y datos públicos anidados
**Cuando** se sanea
**Entonces** las propiedades sensibles desaparecen, los datos públicos se conservan y el objeto original no se muta.

### SEC-02 — Legado Web

**Dado** un `cort_web_v1` con una clave de prueba y otros ajustes
**Cuando** se carga CORT
**Entonces** la clave se elimina del almacenamiento y los demás ajustes permanecen.

### SEC-03 — Mensajes Web

**Dado** un `update_settings` con una clave de prueba
**Cuando** el mock lo procesa
**Entonces** no se reenvía al puente ni se persiste la clave, y la respuesta no la contiene.

### SEC-04 — Estado PC

**Dado** un archivo de estado con campos secretos anidados y `user_city`
**Cuando** se lee o escribe
**Entonces** sólo quedan campos no sensibles y el archivo resultante tiene modo `0600`.

### SEC-05 — Allowlist PC

**Dado** un estado que contiene campos arbitrarios
**Cuando** se solicita `settings_data`
**Entonces** la respuesta contiene únicamente nombre, edad, ciudad, idioma, modelo local, recordatorios y compras.

### SEC-06 — Sobre Android

**Dado** un texto de prueba
**Cuando** se cifra y descifra
**Entonces** se recupera exactamente, el IV cambia entre sobres y una modificación del cifrado hace fallar la autenticación.

### SEC-07 — Migración Android

**Dado** una clave plana de prueba
**Cuando** se migra
**Entonces** queda un sobre verificado, el campo plano desaparece y un fallo de commit no deja una clave nueva en claro.

### SEC-08 — Borrado Android

**Dado** un sobre y un alias
**Cuando** se borra la clave
**Entonces** desaparecen el sobre, el alias y cualquier campo plano.

### SEC-09 — Interfaz honesta

**Dado** la interfaz Web de PC
**Cuando** se abren los ajustes de cerebro
**Entonces** sólo se ofrecen rutas locales reales y se indica que la nube no está disponible.

### SEC-10 — Modo local sin nube

**Dado** el modo `local` y una `Nube` configurada
**Cuando** el GGUF no contesta
**Entonces** no se realiza ninguna llamada a la nube.

### SEC-11 — Consentimiento automático

**Dado** el modo `auto` y una `Nube` configurada
**Cuando** el GGUF no contesta
**Entonces** se solicita confirmación antes de enviar texto; sin confirmación se degrada localmente.

## Prueba roja antes del código

La primera corrida debe fallar por ausencia de:

- `scripts/prueba_secretos.py`;
- `cort-web/cort/cort-secretos.js`;
- saneamiento en el mock y el puente;
- `apps/android/tests/SecretoTest.java`;
- `apps/android/src/dev/sandra/cort/movil/SobreSecreto.java`;
- uso de Keystore en `Nube.java`;
- retiro de la API modal y de las opciones de nube no implementadas;
- consentimiento explícito en las rutas Android.

La prueba roja se conserva como evidencia del orden PRUEBA ROJA → CÓDIGO.

## Plan de implementación

1. Registrar las decisiones aceptadas y esta SPEC.
2. Crear las pruebas de secretos Web/Python y del sobre Java.
3. Ejecutarlas y registrar el fallo esperado.
4. Implementar el escudo Web y el saneamiento del mock.
5. Implementar saneamiento, allowlist y escritura atómica en el puente.
6. Implementar `SobreSecreto` y migrar `Nube`.
7. Retirar de la Web las capacidades de nube sin adaptador.
8. Añadir consentimiento y bloquear la nube en modo local.
9. Ejecutar suites Python/Java, build Android y revisar el diff.
10. Publicar en `web/cort-v0` sólo con CI verde y actualizar la evidencia.

## Evidencia

### Verificación local

Ejecutada el 2026-11-25 sobre código y datos de prueba; sin leer `backend/.env`, claves reales ni el estado vivo del puente:

- `python3 scripts/prueba_secretos.py`: **30/30**. Cubre saneamiento Web, legado, bloqueo antes del puente, allowlist, permisos `0600`, temporal único, sobre Android, commit rechazado, orden de borrado, consentimiento e interfaz honesta.
- `python3 scripts/prueba_apk.py`: **237/237** comprobaciones estáticas del APK.
- `python3 scripts/prueba_puente_ws.py`: **41/41**, incluido el puente de arena y la ausencia del token en respuestas y estado.
- `python3 scripts/prueba_nucleo.py`: **TODO OK**; `websockets==17.4` se instaló en un directorio temporal aislado y se eliminó al terminar.
- Pruebas Java con Java 21 y `-source 11 -target 11`: **RAM 17/17** y **Sobres 12/12**. El build de CI conserva `--release 11`.
- `py_compile`, `node --check`, `bash -n apps/android/compilar.sh` y `git diff --check`: sin errores.
- Navegador integrado, viewport 525×521 y puente aislado: carga completa, destino WebSocket correcto, cero campos de contraseña, selector sólo local, aviso de nube visible, purga del legado y ningún reenvío de secretos; **0 errores de consola** tras la interacción.

La regresión del temporal fijo falló primero (**29/30**) y pasó (**30/30**) al usar `tempfile.mkstemp`. No había SDK Android completo ni `javac` ejecutable en esta máquina; la compilación Java del sobre se hizo con el módulo compilador de la JVM. Ruff y los parseres YAML no estaban instalados, por lo que no se afirma su ejecución.

### Verificación CI

- La primera corrida, [45554793292](https://github.com/Sandra2244/CORT/actions/runs/45554793292) sobre `c85931b`, falló en `compilar`: `Nexo.java` usaba `AlertDialog` sin importarlo. La suite de secretos sí pasó; no se publicó Release.
- La corrección se hizo hacia delante en `45da233`, con una regresión estática del import.
- La corrida [45555101269](https://github.com/Sandra2244/CORT/actions/runs/45555101269) sobre `45da233` terminó **success en 57 s**: suite de secretos, descarga y colocación del motor, compilación, suite del APK y publicación del artefacto quedaron verdes. El paso de Release quedó omitido porque no hay etiqueta.
- La [Release `cort-v0.19.0`](https://github.com/Sandra2244/CORT/releases/tag/cort-v0.19.0) se publicó desde la corrida [45566400612](https://github.com/Sandra2244/CORT/actions/runs/45566400612), **success**, sobre el commit `37b4513`. El APK mide **79 246 441 B**, tiene `versionCode 1900`, SHA-256 `87fdc848c9f9b6cf52114e61eb72d5816ce1c5fadb6aadb705b69951636dbc4b` y conserva el certificado de `0.18.1`. La auditoría confirma `libcortmotor.so` en `arm64-v8a` y `armeabi-v7a`; las notas declaran pendiente el ensayo físico.

### Verificación física pendiente

- Migrar una clave real en el A16 sin leerla ni registrar su valor.
- Comprobar que una clave antigua deja de aparecer en claro en los ajustes del teléfono.
- Borrar la clave y comprobar que CORT deja de considerarla configurada sin mostrar su valor.
- Negar el consentimiento y verificar que no se realiza tráfico al proveedor.
- Activar el modo local con una nube configurada y comprobar que un fallo del GGUF no genera tráfico al proveedor.
- Confirmar que el APK actualizado conserva voz, GGUF y rutinas.

## Riesgos y límites

- El bundle minificado seguirá construyendo objetos `api_keys` en memoria. El escudo impide su persistencia y transmisión, pero no elimina esa construcción heredada. Su sustitución pertenece a una fase de interfaz/arquitectura.
- AndroidKeyStore protege la clave de cifrado, no elimina la posibilidad de que un proceso con los mismos privilegios de app la use mientras la app está desbloqueada. No se promete protección frente a un dispositivo comprometido.
- La migración sólo puede conservar una clave existente si Android permite cifrarla y verificarla. Si no, se pide volver a teclearla.
- Retirar la UI de nube de PC no construye proveedores; evita una promesa falsa mientras se construye `SPEC-HIB-001`.
