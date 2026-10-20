# CORT en el teléfono (APK)

Este APK **se compila en GitHub Actions**, nunca en el portátil de la dueña:
1,8 GiB de RAM, `javac` que no está (medido) y un `gradle build` que congeló la
máquina. El pipeline usa las cuatro herramientas que el runner ya trae —`aapt2`,
`javac`, `d8`, `apksigner`— y `compilar.sh` las ordena. Sin Gradle, sin AndroidX,
sin Node: la cara del teléfono es la misma carpeta `ui/` del repo.

## Qué es

| pieza | qué hace |
|---|---|
| `MainActivity.java` | un `WebView` a pantalla completa y **tres** superficies en una: la dirección del PC guardada (`http://IP:8000`, el holograma actual con sus once ventanas y su backend real), la cara embebida en el APK (`assets/ui/`, servida bajo `https://cort.local` y cortada en `shouldInterceptRequest` contra los assets), y el menú del botón «CORT · PC» para cambiar entre ellas |
| `CortNative.java` | `window.CortNative`: el micrófono (`SpeechRecognizer`), la voz (`TextToSpeech`), los permisos, el bloqueo de pantalla y la dirección del PC. Hace falta porque una página en `http` de red local **no es origen seguro** y Chrome no le presta Web Speech ni `getUserMedia` |
| `Asistente.java` + `Sesiones.java` + `Sesion.java` | el traje de **asistente predeterminado**: Ajustes ▸ Aplicaciones ▸ Aplicación de asistencia predeterminada ▸ CORT. Desde ahí, el gesto de asistente, la tecla del auricular y la pantalla bloqueada abren CORT y lo ponen a escuchar |
| `Reconocimiento.java` | el `RecognitionService` que el contrato de AOSP **exige** para aparecer en esa lista. CORT no trae modelo propio de palabra de activación, así que cede el oído al micrófono de la cara y cierra con `ERROR_NO_MATCH` |
| `MediaSession` (dentro de `MainActivity`) | el **doble toque del auricular**: dos pulsaciones de `HEADSETHOOK` / `PLAY_PAUSE` en menos de 500 ms abren el micrófono. La primera pulsación se devuelve `false`, así que pausar la música sigue siendo cosa de Spotify o de quien la mande |
| `AndroidManifest.xml` | permisos (`INTERNET`, `RECORD_AUDIO`, `MODIFY_AUDIO_SETTINGS`, `VIBRATE`), el `<service>` del asistente con `BIND_VOICE_INTERACTION` y la meta-datos hacia `res/xml/asistente.xml`, y `usesCleartextTraffic` para la Wi‑Fi sin TLS |
| `res/xml/asistente.xml` | el contrato del asistente, con los atributos **sin** prefijo `android:` (son recursos internos del sistema y `aapt2` rechazaría la forma con prefijo) |

`assets/ui/` y `res/mipmap-*/` están en `.gitignore`: son generados. La única
copia buena de la cara es la que sale del `ui/` del commit etiquetado, y el
icono lo dibuja `scripts/marca.py` (el mismo anillo del logo del README).

## Usarlo

1. En la Release, descarga **`CORT-IA-1.2.0.apk`** (es el botón que ves en la
   página de la etiqueta).
2. **Desinstala el APK anterior** la primera vez. No es capricho: este APK se
   firma con una llave del pipeline, y para Android una firma distinta es otra
   aplicación. Si la dueña guarda el secreto `CORT_APK_KEYSTORE_B64` en
   Settings ▸ Secrets and variables ▸ Actions, las Releases siguientes **sí** se
   instalan encima. El run publica a lado del APK un
   `CORT-IA-1.2.0-firma.txt` con la huella del certificado usado: esa es la
   prueba pública de con qué llave salió, porque los logs de Actions no son
   públicos.
3. Instálalo y concede el micrófono cuando lo pida.
4. Para que use tu PC por Wi‑Fi: en el portátil, `bash scripts/telefono.sh` y
   anota la dirección que imprime; en el teléfono, botón **CORT · PC** ▸
   «Conectar con mi PC por Wi‑Fi» y escríbela (`http://192.168.100.171:8000`).
   Los dos tienen que estar en la misma red. Si el PC no contesta, la app abre
   sola la cara embebida y funciona sin servidor.
5. Para que mande el doble toque de los audífonos: botón **CORT · PC** ▸ «Poner
   CORT como asistente» (o Ajustes ▸ Aplicaciones ▸ Aplicación de asistencia
   predeterminada ▸ **CORT**). En los Galaxy Buds, la acción del doble toque se
   deja en «Asistente digital».

## Lo que NO hace, dicho sin adornos

- **No** mantiene el «OK Google» con la pantalla apagada: esa palabra de
  activación la dice el servidor de Google y no viaja con este APK.
- **No** oye «Oye CORT» con la app cerrada: la escucha continua vive dentro del
  WebView, así que funciona con la cara abierta.
- La cara embebida, sin PC, **no** tiene cerebro de nube propio: la conversación
  libre, los modelos de Ollama y el optimizador viven en el backend del
  portátil. Por eso el paso 4 es el que de verdad le da las once ventanas.
- Nada de esto está verificado con un dedo encima: no hay teléfono en esta
  máquina. Lo que sí comprueba el pipeline es que el Java compila contra la
  plataforma (`javac` revisa las firmas de `VoiceInteractionSession.onShow`,
  `RecognitionService.Callback.error` y compañía), que `aapt2` enlace el
  manifiesto, que `apksigner` valide la firma y que el APK quede alineado.
